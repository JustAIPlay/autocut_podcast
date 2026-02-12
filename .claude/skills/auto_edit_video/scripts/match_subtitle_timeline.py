#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕时间线匹配脚本
将断句文本与词级时间戳匹配，生成 SRT 字幕
"""
import os
import sys
import io
import json
import re
import argparse
from pathlib import Path

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils import get_script_paths


def format_time(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def clean_text_for_match(text: str) -> str:
    """清理文本用于匹配：移除所有标点符号和空格"""
    import string
    punctuation = '，。！？；：、,."\' !?;:""\'\' （）()【】[]《》<>·—…～｜/\\-_=+*&^%$#@`~ \n\r\t'
    punctuation += string.punctuation
    return ''.join(c for c in text if c not in punctuation)


def match_subtitle_timeline(script_id: str) -> bool:
    """
    将断句文本与词级时间戳匹配，生成 SRT 字幕
    
    Args:
        script_id: 项目标识符
        
    Returns:
        是否成功
    """
    paths = get_script_paths(script_id)
    
    # 输入
    refined_path = paths["copy_refined"]  # 断句文本
    timestamps_path = paths["word_timestamps"]  # 词级时间戳
    
    # 输出
    output_path = paths["caption_final_srt"]
    
    # 检查输入文件
    if not refined_path.exists():
        print(f"❌ 找不到断句文本: {refined_path}")
        print(f"💡 请先运行 refine_subtitles.py 进行断句")
        return False
    
    if not timestamps_path.exists():
        print(f"❌ 找不到时间戳文件: {timestamps_path}")
        print(f"💡 请先运行 forced_align.py 生成时间戳")
        return False
    
    # 读取断句文本
    with open(refined_path, 'r', encoding='utf-8') as f:
        refined_text = f.read()
    
    # 按行分割为字幕条目
    subtitle_lines = [line.strip() for line in refined_text.split('\n') if line.strip()]
    
    # 读取时间戳
    with open(timestamps_path, 'r', encoding='utf-8') as f:
        timestamps_data = json.load(f)
    
    segments = timestamps_data.get("segments", [])
    
    print(f"📝 正在匹配字幕时间线...")
    print(f"📄 断句行数: {len(subtitle_lines)}")
    print(f"📊 词语数量: {len(segments)}")
    
    # 构建累计字符位置索引
    segment_positions = []
    cumulative_pos = 0
    for seg in segments:
        clean_word = clean_text_for_match(seg.get("text", ""))
        segment_positions.append({
            "start_pos": cumulative_pos,
            "end_pos": cumulative_pos + len(clean_word),
            "start_time": seg.get("start", 0.0),
            "end_time": seg.get("end", 0.0),
            "text": seg.get("text", "")
        })
        cumulative_pos += len(clean_word)
    
    # 匹配每个字幕行
    srt_entries = []
    current_char_pos = 0
    
    for idx, line in enumerate(subtitle_lines):
        clean_line = clean_text_for_match(line)
        line_length = len(clean_line)
        
        if line_length == 0:
            continue
        
        target_start_pos = current_char_pos
        target_end_pos = current_char_pos + line_length
        
        # 找到覆盖这个范围的第一个和最后一个 segment
        start_time = None
        end_time = None
        
        for sp in segment_positions:
            # 找到第一个与当前行有交集的 segment
            if sp["end_pos"] > target_start_pos and start_time is None:
                start_time = sp["start_time"]
            
            # 找到最后一个与当前行有交集的 segment
            if sp["start_pos"] < target_end_pos:
                end_time = sp["end_time"]
        
        # 如果没找到，使用默认值
        if start_time is None:
            start_time = 0.0
        if end_time is None:
            end_time = start_time + 2.0  # 默认 2 秒
        
        srt_entries.append({
            "index": idx + 1,
            "start": start_time,
            "end": end_time,
            "text": line
        })
        
        current_char_pos = target_end_pos
    
    # 生成 SRT 文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in srt_entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{format_time(entry['start'])} --> {format_time(entry['end'])}\n")
            f.write(f"{entry['text']}\n")
            f.write("\n")
    
    # 计算总时长
    if srt_entries:
        total_duration = srt_entries[-1]["end"]
    else:
        total_duration = 0.0
    
    print(f"✅ 字幕时间匹配完成！")
    print(f"📁 输出文件: {output_path}")
    print(f"📊 字幕条数: {len(srt_entries)}")
    print(f"⏱️ 总时长: {total_duration:.2f} 秒")
    print("-" * 40)
    print("预览前5条字幕：")
    for entry in srt_entries[:5]:
        print(f"  [{format_time(entry['start'])} -> {format_time(entry['end'])}] {entry['text'][:30]}...")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="字幕时间线匹配")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    
    args = parser.parse_args()
    
    success = match_subtitle_timeline(args.script_id)
    sys.exit(0 if success else 1)
