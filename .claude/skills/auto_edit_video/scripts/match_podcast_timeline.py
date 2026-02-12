#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播客时间线匹配脚本
将字幕文本与词级时间戳匹配，生成最终 SRT 字幕

匹配算法：
- 字幕和词级时间戳都是顺序的
- 逐字符顺序匹配，累积每行的起止时间
"""
import sys
import io
import json
import re
from pathlib import Path
from utils import get_script_paths

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def format_srt_time(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def clean_char(c: str) -> str:
    """清理字符，移除不用于匹配的字符"""
    if re.match(r'[\u4e00-\u9fa5a-zA-Z0-9]', c):
        return c.lower()
    return ''


def match_podcast_timeline(script_id: str) -> bool:
    """
    匹配播客字幕时间线
    
    使用顺序匹配算法：
    1. 将所有词级时间戳按顺序排列
    2. 对每行字幕，逐字符匹配对应的时间戳
    3. 累积该行的起止时间
    
    输入: 
      - copys/{id}_subtitle.txt (字幕文本)
      - captions/{id}_word_timestamps.json (词级时间戳)
    输出: captions/{id}_final.srt
    """
    paths = get_script_paths(script_id)
    
    # 检查输入文件
    subtitle_file = paths["copy_subtitle"]
    timestamps_file = paths["word_timestamps"]
    
    if not subtitle_file.exists():
        print(f"❌ 找不到字幕文件: {subtitle_file}")
        print(f"   请先运行: python format_podcast_subtitles.py {script_id}")
        return False
    
    if not timestamps_file.exists():
        print(f"❌ 找不到时间戳文件: {timestamps_file}")
        print(f"   请先运行: python forced_align.py {script_id} --podcast")
        return False
    
    # 读取字幕文本
    with open(subtitle_file, 'r', encoding='utf-8') as f:
        subtitle_lines = [line.strip() for line in f.readlines() if line.strip()]
    
    # 读取词级时间戳
    with open(timestamps_file, 'r', encoding='utf-8') as f:
        word_data = json.load(f)

    # 提取 segments 数组
    word_segments = word_data.get("segments", [])

    print(f"📄 字幕行数: {len(subtitle_lines)}")
    print(f"📄 词级时间戳数: {len(word_segments)}")

    if not word_segments:
        print("❌ 时间戳数据为空")
        return False

    # 构建词列表，每个词包含 {text, start, end}
    words = []
    for seg in word_segments:
        text = seg.get("text", "").strip()
        if text:  # 只保留非空词
            words.append({
                "text": text,
                "start": seg.get("start", 0),
                "end": seg.get("end", 0)
            })
    
    print(f"📄 有效词数: {len(words)}")
    
    # 顺序匹配
    srt_entries = []
    word_idx = 0  # 当前词索引

    for line_idx, line in enumerate(subtitle_lines):
        # 提取当前行的所有有效字符
        line_chars = [c for c in line if clean_char(c)]
        
        if not line_chars:
            # 空行或纯标点行，使用上一条的结束时间
            if srt_entries:
                prev_end = srt_entries[-1]["end"]
                srt_entries.append({
                    "index": line_idx + 1,
                    "start": prev_end,
                    "end": prev_end + 0.5,
                    "text": line
                })
            continue
        
        # 找到该行对应的起始和结束时间
        start_time = None
        end_time = None
        matched_count = 0
        
        # 逐字符匹配
        for char in line_chars:
            char_clean = clean_char(char)
            if not char_clean:
                continue
            
            # 在当前位置往后找匹配的词
            found = False
            search_limit = min(word_idx + 20, len(words))  # 最多往后看20个词
            
            for i in range(word_idx, search_limit):
                word_text = clean_char(words[i]["text"])
                if word_text == char_clean:
                    # 匹配成功
                    if start_time is None:
                        start_time = words[i]["start"]
                    end_time = words[i]["end"]
                    matched_count += 1
                    word_idx = i + 1  # 移动到下一个词
                    found = True
                    break
            
            if not found:
                # 未找到匹配，可能是分段边界处的问题
                # 尝试继续匹配下一个字符
                pass
        
        # 如果没有找到任何匹配，使用估算
        if start_time is None:
            if srt_entries:
                # 使用上一条字幕的结束时间
                start_time = srt_entries[-1]["end"]
                # 估算时长：每字约0.15秒
                end_time = start_time + len(line_chars) * 0.15
            else:
                start_time = 0
                end_time = len(line_chars) * 0.15
        
        # 确保时间递增
        if srt_entries and start_time < srt_entries[-1]["end"]:
            start_time = srt_entries[-1]["end"]
            if end_time <= start_time:
                end_time = start_time + len(line_chars) * 0.15
        
        srt_entries.append({
            "index": line_idx + 1,
            "start": start_time,
            "end": end_time,
            "text": line
        })
    
    # 后处理：将每条字幕的结束时间对齐到下一条的开始时间
    # 这样字幕在播放时会无缝衔接
    for i in range(len(srt_entries) - 1):
        srt_entries[i]["end"] = srt_entries[i + 1]["start"]
    
    # 生成 SRT 文件
    output_file = paths["caption_final_srt"]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in srt_entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{format_srt_time(entry['start'])} --> {format_srt_time(entry['end'])}\n")
            f.write(f"{entry['text']}\n\n")
    
    # 统计
    total_duration = srt_entries[-1]["end"] if srt_entries else 0
    
    print(f"✅ SRT 字幕生成完成！")
    print(f"   - 输出文件: {output_file}")
    print(f"   - 字幕条数: {len(srt_entries)}")
    print(f"   - 总时长: {format_srt_time(total_duration)}")
    print()
    print("预览前 5 条字幕：")
    print("-" * 50)
    for entry in srt_entries[:5]:
        print(f"{entry['index']}")
        print(f"{format_srt_time(entry['start'])} --> {format_srt_time(entry['end'])}")
        text_preview = entry['text'][:40] + "..." if len(entry['text']) > 40 else entry['text']
        print(f"{text_preview}")
        print()
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python match_podcast_timeline.py <script_id>")
        sys.exit(1)
    
    script_id = sys.argv[1]
    success = match_podcast_timeline(script_id)
    sys.exit(0 if success else 1)
