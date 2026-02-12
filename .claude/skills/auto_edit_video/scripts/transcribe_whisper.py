#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
from pathlib import Path
from typing import Any, List, cast

# 设置 Hugging Face 镜像，解决国内下载模型失败的问题
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 预初始化以消除未绑定警告
WhisperModel = None
whisper = None

try:
    from faster_whisper import WhisperModel
    HAS_FASTER = True
except ImportError:
    try:
        import whisper
        HAS_FASTER = False
    except ImportError:
        print("请先安装 whisper: pip install openai-whisper 或 pip install faster-whisper")
        sys.exit(1)

def format_timestamp(seconds: float):
    """将秒数转换为 SRT 时间格式"""
    td_hours = int(seconds // 3600)
    td_mins = int((seconds % 3600) // 60)
    td_secs = int(seconds % 60)
    td_millis = int((seconds - int(seconds)) * 1000)
    return f"{td_hours:02}:{td_mins:02}:{td_secs:02},{td_millis:03}"

def split_subtitle_text(text, max_len=14):
    """
    语义优先的切分逻辑：
    1. 优先寻找标点符号进行切分。
    2. 如果没有标点，使用分词保证词语完整。
    3. 避免切分后产生极短的“尾巴”。
    """
    if not text or len(text) <= max_len:
        return [text] if text else []

    # 定义断句标点
    punctuations = ["，", "。", "！", "？", "；", "：", ",", ".", "!", "?", ";", ":"]
    
    # 如果文本中有标点，尝试在标点处切分
    split_pos = -1
    for i in range(len(text) - 1, 0, -1):
        # 寻找处于“黄金切分区”（60%-95%长度处）的标点
        if text[i] in punctuations:
            # 如果标点后的内容太短（少于3个字），继续往前找
            if len(text) - i - 1 < 3:
                continue
            # 如果标点前的内容在合理范围内（不超过 max_len * 1.5）
            if i + 1 <= max_len * 1.5:
                split_pos = i + 1
                break

    if split_pos != -1:
        part1 = text[:split_pos]
        part2 = text[split_pos:]
        # 递归处理剩余部分
        return [part1] + split_subtitle_text(part2, max_len)

    # 如果没有合适的标点，回退到词法切分
    try:
        import jieba
        import logging
        jieba.setLogLevel(logging.INFO)
        words = list(jieba.cut(text))
    except ImportError:
        import re
        words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z0-9]+|[^\u4e00-\u9fff\a-zA-Z0-9]', text)

    # 寻找最接近中间的词边界
    mid = len(text) // 2
    curr_len = 0
    best_split = -1
    min_diff = len(text)
    
    for i, word in enumerate(words):
        curr_len += len(word)
        diff = abs(curr_len - mid)
        if diff < min_diff:
            # 避开禁忌词开头
            forbidden = ["的", "了", "着", "儿", "时"]
            if i + 1 < len(words) and words[i+1] not in forbidden:
                min_diff = diff
                best_split = curr_len
    
    if best_split != -1 and best_split < len(text):
        part1 = text[:best_split]
        part2 = text[best_split:]
        return [part1] + split_subtitle_text(part2, max_len)
    
    return [text]

def transcribe(script_id):
    """根据脚本 ID 进行音频转录"""
    global WhisperModel, whisper
    
    # 使用统一的路径管理
    from utils import get_script_paths
    paths = get_script_paths(script_id)
    audio_path = paths["audio"]
    copy_dir = paths["copy_whisper"].parent
    caption_dir = paths["caption_whisper_srt"].parent
    
    if not audio_path.exists():
        print(f"❌ 找不到音频文件: {audio_path}")
        return False

    # 确保目录存在
    caption_dir.mkdir(parents=True, exist_ok=True)
    copy_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 正在转录项目: {script_id}")
    
    full_text = ""
    segments: List[Any] = []

    if HAS_FASTER and WhisperModel is not None:
        print(f"🚀 使用 faster-whisper (GPU 加速模式) 转录...")
        try:
            # 尝试使用 GPU (CUDA) 和 float16 精度
            # 升级为 medium 模型，平衡速度与极高的准确率
            model = WhisperModel("medium", device="cuda", compute_type="float16")
        except Exception as e:
            print(f"⚠️ GPU 加速启动失败，切换回 CPU 模式。错误: {e}")
            model = WhisperModel("medium", device="cpu", compute_type="int8")
        
        # 优化 initial_prompt，包含易错词纠正
        result_iter, info = model.transcribe(
            str(audio_path), 
            beam_size=5, 
            language="zh", 
            initial_prompt="这是一段关于乔丹·菲利普斯医生在中国推广腹腔镜手术的医学纪录片。关键词：塞进公文包、叹气、腹腔镜、手术刀、协和医院。"
        )
        
        segments = []
        for s in result_iter:
            # 实时进度报告
            print(f"  [{format_timestamp(s.start)}] {s.text}")
            segments.append(s)
            
        full_text = "".join([s.text for s in segments])
    elif whisper is not None:
        print("🚀 使用 standard whisper 转录...")
        # 标准版也同步升级
        model = whisper.load_model("medium")
        # 标准 whisper 库也支持 language 和 initial_prompt
        result: Any = model.transcribe(
            str(audio_path), 
            language="zh", 
            initial_prompt="这是一段关于乔丹·菲利普斯医生在中国推广腹腔镜手术的医学纪录片。关键词：塞进公文包、叹气、腹腔镜、手术刀、协和医院。"
        )
        full_text = str(result.get("text", ""))
        segments = list(result.get("segments", []))
        for s in segments:
            print(f"  [{format_timestamp(float(s['start']))}] {s['text']}")

    # 保存纯文本到 copys 目录
    txt_path = paths["copy_whisper"]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    
    # 保存 SRT 字幕和 JSON
    srt_path = paths["caption_whisper_srt"]
    json_path = paths["caption_whisper_json"]
    
    raw_segments = []
    for segment in segments:
        if HAS_FASTER:
            raw_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
        else:
            raw_segments.append({
                "start": segment['start'],
                "end": segment['end'],
                "text": segment['text'].strip()
            })

    # --- 增加：切分过长字幕逻辑 (每段不超过 9 个字) ---
    MAX_CHARS = 9
    structured_segments = []
    idx = 1
    for seg in raw_segments:
        text = seg['text']
        parts = split_subtitle_text(text, MAX_CHARS)
        
        if len(parts) == 1:
            structured_segments.append({
                "id": idx,
                "start": round(float(seg['start']), 3),
                "end": round(float(seg['end']), 3),
                "text": parts[0]
            })
            idx += 1
        else:
            start = float(seg['start'])
            end = float(seg['end'])
            duration = end - start
            total_chars = len(text)
            
            current_start = start
            for part in parts:
                part_len = len(part)
                part_duration = (part_len / total_chars) * duration
                part_end = current_start + part_duration
                
                structured_segments.append({
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
    # 扩展禁忌列表
    forbidden_at_start = [
        "的", "了", "着", "儿", "时", "）", "】", "”", "’", "》", "；", "：", "，", "。", "！", "？", "、",
        ",", ".", "!", "?", ";", ":", ")", "]", "}", ">"
    ]
    for seg in structured_segments:
        # 只要太短（<5字），或者以标点/助词开头，或者全是标点，就合并
        if final_segments and (
            len(seg['text']) < 5 or 
            seg['text'][0] in forbidden_at_start or 
            all(c in forbidden_at_start for c in seg['text'])
        ):
            # 只要合并后不超过16字
            if len(final_segments[-1]['text']) + len(seg['text']) <= 16:
                final_segments[-1]['end'] = seg['end']
                final_segments[-1]['text'] += seg['text']
            else:
                final_segments.append(seg)
        else:
            final_segments.append(seg)
    
    # 重新编号并确保时间戳精度
    for i, seg in enumerate(final_segments, 1):
        seg['id'] = i
        seg['start'] = round(seg['start'], 3)
        seg['end'] = round(seg['end'], 3)
    structured_segments = final_segments
    # ------------------------------------
    
    with open(srt_path, "w", encoding="utf-8") as f:
        for seg in structured_segments:
            # 写入 SRT
            start_str = format_timestamp(seg['start'])
            end_str = format_timestamp(seg['end'])
            f.write(f"{seg['id']}\n{start_str} --> {end_str}\n{seg['text']}\n\n")
    
    # 保存 JSON (包含完整的结构化数据，供 compose_video.py 使用)
    output_data = {
        "script_id": script_id,
        "full_text": full_text,
        "segments": structured_segments
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 转录完成！")
    print(f"   SRT: {srt_path}")
    print(f"   JSON: {json_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python transcribe_whisper.py <script_id>")
        sys.exit(1)
    
    transcribe(sys.argv[1])