import re
import sys
import json
from pathlib import Path
from funasr import AutoModel

def format_time(seconds):
    """将秒数转换为 SRT 时间格式 HH:MM:SS,mmm"""
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def clean_text(text):
    """清理 SenseVoice 或其他模型产生的特殊标签"""
    if not text:
        return ""
    # 去除 <|...|> 格式的标签
    text = re.sub(r'<\|.*?\|>', '', text)
    return text.strip()

def split_subtitle_text(text, max_len=9):
    """
    更智能的字幕切分：
    1. 保持字数限制 (默认9字)
    2. 绝不从词语中间切断 (使用分词)
    3. “的”等虚词及标点不放行首，必须合并到上一行
    4. 尽量保持每行长度平衡
    """
    if not text or len(text) <= max_len:
        return [text] if text else []
    
    # 尝试使用 jieba 分词
    try:
        import jieba
        import logging
        jieba.setLogLevel(logging.INFO)
        words = list(jieba.cut(text))
    except ImportError:
        import re
        words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+|[^\u4e00-\u9fffa-zA-Z0-9]', text)

    forbidden_at_start = ["的", "了", "着", "儿", "时", "）", "】", "”", "’", "》", "；", "：", "，", "。", "！", "？", "、"]
    
    lines = []
    current_line = ""
    
    for word in words:
        if not current_line:
            current_line = word
            continue
            
        if len(current_line) + len(word) > max_len:
            if word in forbidden_at_start:
                current_line += word
            else:
                lines.append(current_line)
                current_line = word
        else:
            current_line += word
            
    if current_line:
        lines.append(current_line)

    if len(lines) == 2:
        total_len = len("".join(lines))
        if total_len <= max_len * 1.8:
            best_split_idx = -1
            min_diff = total_len
            curr_len = 0
            for i in range(len(words) - 1):
                curr_len += len(words[i])
                if curr_len <= max_len and (total_len - curr_len) <= max_len and words[i+1] not in forbidden_at_start:
                    diff = abs(curr_len - (total_len - curr_len))
                    if diff < min_diff:
                        min_diff = diff
                        best_split_idx = i
            if best_split_idx != -1:
                lines = ["".join(words[:best_split_idx+1]), "".join(words[best_split_idx+1:])]
                
    final_lines = []
    for line in lines:
        if all(c in forbidden_at_start for c in line) and final_lines:
            final_lines[-1] += line
        else:
            final_lines.append(line)
            
    return final_lines

def transcribe(script_id):
    # 路径逻辑
    base_dir = Path(__file__).parent.parent.parent.parent.parent
    audio_path = base_dir / "raw_materials" / "audios" / f"{script_id}.mp3"
    copy_dir = base_dir / "raw_materials" / "copys"
    caption_dir = base_dir / "raw_materials" / "captions"

    if not audio_path.exists():
        print(f"❌ 找不到音频文件: {audio_path}")
        return False

    print(f"🚀 正在还原 Paraformer 黄金配置转录: {script_id}")

    # 加载模型 (完全同步 temp 项目配置)
    model = AutoModel(
        model="paraformer-zh",
        model_revision="v2.0.4",
        vad_model="fsmn-vad",
        vad_model_revision="v2.0.4",
        punc_model="ct-punc-c",
        punc_model_revision="v2.0.4",
        device="cuda:0",
        disable_update=True
    )

    # 开始推理
    res = model.generate(
        input=str(audio_path),
        batch_size_s=300,
        hotword='腹腔镜 乔丹·菲利普斯 止血钳 仁济医院 妇科 手术 辩友 手艺 产妇',
        sentence_timestamp=True 
    )

    if not res or len(res) == 0:
        print("❌ 转录失败")
        return False

    result = res[0]
    full_text = clean_text(result.get('text', ''))

    # 1. 保存纯文案
    copy_dir.mkdir(parents=True, exist_ok=True)
    txt_path = copy_dir / f"{script_id}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"✅ 文案已保存: {txt_path}")

    # 2. 构造结构化的 segments 数据
    caption_dir.mkdir(parents=True, exist_ok=True)
    srt_path = caption_dir / f"{script_id}.srt"
    json_path = caption_dir / f"{script_id}.json"
    
    raw_segments = []
    sentences = result.get('sentences')
    
    if sentences:
        print(f"DEBUG: 找到 {len(sentences)} 条句子级时间轴数据")
        for i, s in enumerate(sentences):
            raw_segments.append({
                "start": float(s.get('start', 0)) / 1000.0,
                "end": float(s.get('end', 0)) / 1000.0,
                "text": clean_text(s.get('text', ''))
            })
    elif 'timestamp' in result and len(result['timestamp']) > 0:
        print(f"DEBUG: 启动字符级时间戳聚合逻辑 (精准模式)")
        raw_ts = result['timestamp']  # [[start, end], [start, end], ...]
        raw_text = result.get('text', '')
        
        # 移除空格但保留标点用于切分
        chars = [c for c in raw_text if not c.isspace()]
        
        current_seg_text = ""
        current_start = -1.0
        
        # 标点符号定义
        punctuations = "，。？！；,.;?!"
        
        for i, (ts, char) in enumerate(zip(raw_ts, chars)):
            if current_start < 0:
                current_start = float(ts[0]) / 1000.0
            
            current_seg_text += char
            
            # 遇到标点或最后一个字，结束当前段落
            if char in punctuations or i == len(chars) - 1:
                end_time = float(ts[1]) / 1000.0
                if len(current_seg_text.strip()) > 1: # 避免只有标点的行
                    raw_segments.append({
                        "start": round(current_start, 3),
                        "end": round(end_time, 3),
                        "text": current_seg_text.strip()
                    })
                current_start = -1.0
                current_seg_text = ""
    else:
        print("DEBUG: 警告！未找到任何时间戳数据，启动字数估算兜底")

    # --- 增加：切分过长字幕逻辑 (每段不超过 9 个字) ---
    MAX_CHARS = 9
    segments = []
    idx = 1
    for seg in raw_segments:
        text = seg['text']
        parts = split_subtitle_text(text, MAX_CHARS)
        
        if len(parts) == 1:
            seg['id'] = idx
            segments.append(seg)
            idx += 1
        else:
            start = seg['start']
            end = seg['end']
            duration = end - start
            total_chars = len(text)
            
            current_start = start
            for part in parts:
                part_len = len(part)
                part_duration = (part_len / total_chars) * duration
                part_end = current_start + part_duration
                
                segments.append({
                    "id": idx,
                    "start": round(current_start, 3),
                    "end": round(part_end, 3),
                    "text": part
                })
                idx += 1
                current_start = part_end
    # -----------------------------------------------

    # --- 增加：最后清理，合并纯标点段落或禁忌开头的段落 ---
    final_segments = []
    forbidden_at_start = ["的", "了", "着", "儿", "时", "）", "】", "”", "’", "》", "；", "：", "，", "。", "！", "？", "、"]
    for seg in segments:
        # 如果当前段落全是标点，或者当前段落以禁忌词开头且有前序段落，则合并
        if final_segments and (all(c in forbidden_at_start for c in seg['text']) or seg['text'][0] in forbidden_at_start):
            final_segments[-1]['end'] = seg['end']
            final_segments[-1]['text'] += seg['text']
        else:
            final_segments.append(seg)
    
    # 重新编号并确保时间戳精度
    for i, seg in enumerate(final_segments, 1):
        seg['id'] = i
        seg['start'] = round(seg['start'], 3)
        seg['end'] = round(seg['end'], 3)
    segments = final_segments
    # ------------------------------------

    # 3. 保存结构化 JSON
    output_data = {
        "script_id": script_id,
        "full_text": full_text,
        "segments": segments
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 结构化数据已保存: {json_path}")

    # 4. 保存 SRT 字幕
    with open(srt_path, "w", encoding="utf-8") as f:
        for seg in segments:
            start_str = format_time(seg['start'])
            end_str = format_time(seg['end'])
            f.write(f"{seg['id']}\n{start_str} --> {end_str}\n{seg['text']}\n\n")
    
    print(f"✅ 字幕已保存: {srt_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe_funasr.py <script_id>")
        sys.exit(1)
    transcribe(sys.argv[1])