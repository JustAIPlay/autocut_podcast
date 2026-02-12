#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper 转录脚本 - 词语级别时间线版本
生成每个词都有独立时间轴的"字幕时间线词典"
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
from pathlib import Path
from typing import Any, List

# 设置 Hugging Face 镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 预初始化
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

def transcribe_word_level(script_id):
    """词语级别转录：每个词都有独立的时间轴"""
    global WhisperModel, whisper
    
    from utils import get_script_paths
    paths = get_script_paths(script_id)
    audio_path = paths["audio"]
    copy_dir = paths["copy_whisper"].parent
    caption_dir = paths["caption_whisper_srt"].parent
    
    if not audio_path.exists():
        print(f"❌ 找不到音频文件: {audio_path}")
        return False

    caption_dir.mkdir(parents=True, exist_ok=True)
    copy_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 正在转录项目: {script_id}")
    print(f"📌 模式: 词语级别时间线（字幕时间线词典）")
    
    full_text = ""
    segments: List[Any] = []

    if HAS_FASTER and WhisperModel is not None:
        print(f"🚀 使用 faster-whisper (GPU 加速模式) 转录...")
        try:
            model = WhisperModel("medium", device="cuda", compute_type="float16")
        except Exception as e:
            print(f"⚠️ GPU 加速启动失败，切换回 CPU 模式。错误: {e}")
            model = WhisperModel("medium", device="cpu", compute_type="int8")
        
        result_iter, info = model.transcribe(
            str(audio_path), 
            beam_size=5, 
            language="zh", 
            initial_prompt="这是一段关于乔丹·菲利普斯医生在中国推广腹腔镜手术的医学纪录片。关键词：塞进公文包、叹气、腹腔镜、手术刀、协和医院。"
        )
        
        segments = []
        for s in result_iter:
            print(f"  [{format_timestamp(s.start)}] {s.text}")
            segments.append(s)
            
        full_text = "".join([s.text for s in segments])
    elif whisper is not None:
        print("🚀 使用 standard whisper 转录...")
        model = whisper.load_model("medium")
        result: Any = model.transcribe(
            str(audio_path), 
            language="zh", 
            initial_prompt="这是一段关于乔丹·菲利普斯医生在中国推广腹腔镜手术的医学纪录片。关键词：塞进公文包、叹气、腹腔镜、手术刀、协和医院。"
        )
        full_text = str(result.get("text", ""))
        segments = list(result.get("segments", []))
        for s in segments:
            print(f"  [{format_timestamp(float(s['start']))}] {s['text']}")

    # 保存纯文本
    txt_path = paths["copy_whisper"]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    
    # 提取原始 segments
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

    # ========== 词语级别分词 ==========
    print("\n📝 正在进行词语级别分词...")
    
    try:
        import jieba
        import logging
        jieba.setLogLevel(logging.INFO)
        HAS_JIEBA = True
    except ImportError:
        print("⚠️ 警告：jieba 未安装，将按字符切分")
        print("   建议安装: pip install jieba")
        HAS_JIEBA = False
    
    word_segments = []
    idx = 1
    
    for seg in raw_segments:
        text = seg['text'].strip()
        if not text:
            continue
        
        start = float(seg['start'])
        end = float(seg['end'])
        duration = end - start
        total_chars = len(text)
        
        if HAS_JIEBA:
            # 使用 jieba 分词
            words = list(jieba.cut(text))
        else:
            # 回退到字符切分
            words = list(text)
        
        current_start = start
        for word in words:
            word = word.strip()
            if not word:
                continue
            
            # 根据词语字符数分配时长
            word_len = len(word)
            word_duration = (word_len / total_chars) * duration if total_chars > 0 else 0
            word_end = current_start + word_duration
            
            word_segments.append({
                "id": idx,
                "start": round(current_start, 3),
                "end": round(word_end, 3),
                "text": word
            })
            idx += 1
            current_start = word_end
    
    print(f"✅ 词语级别分词完成，共 {len(word_segments)} 个词")
    
    # 保存 JSON
    json_path = paths["caption_whisper_json"]
    output_data = {
        "script_id": script_id,
        "full_text": full_text,
        "segments": word_segments,
        "segment_mode": "word_level",
        "total_words": len(word_segments)
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # 保存 SRT
    srt_path = paths["caption_whisper_srt"]
    with open(srt_path, "w", encoding="utf-8") as f:
        for seg in word_segments:
            start_str = format_timestamp(seg['start'])
            end_str = format_timestamp(seg['end'])
            f.write(f"{seg['id']}\n{start_str} --> {end_str}\n{seg['text']}\n\n")
    
    print(f"✅ 转录完成！")
    print(f"   模式: 词语级别时间线")
    print(f"   词数: {len(word_segments)}")
    print(f"   SRT: {srt_path}")
    print(f"   JSON: {json_path}")
    
    # 显示前几个词的时间线
    print(f"\n📊 前10个词的时间线示例:")
    for seg in word_segments[:10]:
        print(f"   [{seg['start']:.3f}-{seg['end']:.3f}] \"{seg['text']}\"")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python transcribe_whisper_word_level.py <script_id>")
        print("说明: 生成词语级别的时间线（字幕时间线词典）")
        sys.exit(1)
    
    transcribe_word_level(sys.argv[1])
