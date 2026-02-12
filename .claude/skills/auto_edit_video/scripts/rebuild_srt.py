#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于词语时间线字典重建 SRT 字幕（新版本）
输入:
  - refined.txt: DeepSeek 优化后的断句文本
  - refined_word_dict.json: 修正后的词语时间线字典
输出:
  - final.srt: 最终字幕文件
"""
import json
import os
import sys
import io
from pathlib import Path
from utils import get_script_paths

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def format_time(seconds):
    """将秒数转换为 SRT 时间格式"""
    millis = int((seconds - int(seconds)) * 1000)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def clean_text_for_match(text):
    """
    清理文本用于匹配：移除所有标点符号和空格
    只保留汉字、字母、数字
    """
    import string
    # 中文标点 + 英文标点 + 其他符号
    punctuation = '，。！？；：、,."\'!?;:""''（）()【】[]《》<>·—…～｜/\\-_=+*&^%$#@`~'
    punctuation += string.punctuation  # 添加所有英文标点
    
    # 移除所有标点和空格
    cleaned = ''.join(c for c in text if c not in punctuation and c.strip())
    return cleaned

def find_text_by_position(text, word_dict_segments, cumulative_char_pos, segment_char_positions):
    """
    按累计字符位置切分时间线（改进算法）
    
    策略：
    1. 预先计算每个 segment 的累计字符位置
    2. 根据当前行的累计起止位置，找到覆盖这个范围的 segments
    3. 返回这些 segments 的起止时间
    
    这样可以避免字符浪费，确保所有行都能获得时间线
    
    Args:
        text: 字幕文本
        word_dict_segments: 词语时间线列表
        cumulative_char_pos: 当前行的起始累计字符位置
        segment_char_positions: 预计算的每个 segment 的 (start_pos, end_pos)
    
    Returns:
        (start_time, end_time, next_cumulative_pos)
    """
    # 计算目标字符数（去除标点）
    text_clean = clean_text_for_match(text)
    target_char_count = len(text_clean)
    
    if target_char_count == 0:
        return None, None, cumulative_char_pos
    
    # 计算当前行的字符范围
    line_start = cumulative_char_pos
    line_end = cumulative_char_pos + target_char_count
    
    # 找到覆盖这个范围的 segments
    matched_segments = []
    for i, (seg_start, seg_end) in enumerate(segment_char_positions):
        # 如果 segment 和当前行有交集
        if seg_end > line_start and seg_start < line_end:
            matched_segments.append(word_dict_segments[i])
    
    if matched_segments:
        start_time = matched_segments[0]['start']
        end_time = matched_segments[-1]['end']
        return start_time, end_time, line_end
    else:
        return None, None, cumulative_char_pos

def rebuild_srt_v2(script_id):
    """
    基于词语时间线字典重建 SRT
    """
    paths = get_script_paths(script_id)
    
    refined_txt_path = paths["copy_refined"]
    word_dict_path = paths["caption_refined_json"]
    output_srt_path = paths["caption_final_srt"]
    
    if not refined_txt_path.exists():
        print(f"❌ 找不到 refined.txt: {refined_txt_path}")
        return False
    
    if not word_dict_path.exists():
        print(f"❌ 找不到词语字典: {word_dict_path}")
        return False
    
    print(f"🔨 正在重建 SRT 字幕...")
    
    # 1. 读取 refined.txt（按行分段的字幕文本）
    with open(refined_txt_path, 'r', encoding='utf-8') as f:
        refined_lines = [line.strip() for line in f if line.strip()]
    
    # 2. 读取词语时间线字典
    with open(word_dict_path, 'r', encoding='utf-8') as f:
        word_dict = json.load(f)
        word_segments = word_dict['segments']
    
    # ⚠️ 数据格式验证：确保是词级字典
    segment_mode = word_dict.get('segment_mode', 'unknown')
    if segment_mode != 'word_level_refined':
        print(f"⚠️ 警告：词典格式可能不正确！")
        print(f"   期望: 'word_level_refined'")
        print(f"   实际: '{segment_mode}'")
        print(f"   这可能导致时间线错误。请先运行 build_word_dict.py")
    
    print(f"📝 字幕行数: {len(refined_lines)}")
    print(f"📊 词典词数: {len(word_segments)}")
    print(f"📋 词典模式: {segment_mode}")
    
    # 3. 预计算每个 segment 的累计字符位置
    segment_char_positions = []
    cumulative_pos = 0
    for seg in word_segments:
        seg_clean = clean_text_for_match(seg['text'])
        seg_len = len(seg_clean)
        segment_char_positions.append((cumulative_pos, cumulative_pos + seg_len))
        cumulative_pos += seg_len
    
    print(f"📊 总字符数: {cumulative_pos}")
    
    # 4. 为每行字幕按累计字符位置切分时间线（改进算法：避免字符浪费）
    subtitle_entries = []
    current_char_pos = 0  # 跟踪当前累计字符位置
    
    for i, line in enumerate(refined_lines):
        start_time, end_time, next_pos = find_text_by_position(
            line, word_segments, current_char_pos, segment_char_positions
        )
        
        if start_time is not None and end_time is not None:
            subtitle_entries.append({
                "id": i + 1,
                "start": start_time,
                "end": end_time,
                "text": line
            })
            current_char_pos = next_pos  # 更新累计字符位置
            print(f"  ✅ 第{i+1}行: [{start_time:.2f}-{end_time:.2f}] {line[:30]}...")
        else:
            print(f"  ⚠️ 第{i+1}行: 未找到匹配 - {line[:30]}...")
    
    # 🔧 修复时间线问题：确保时间线不重叠、不间隙
    print(f"\n🔧 修复时间线问题...")
    
    # 步骤1：从后往前修复重叠（智能分割重叠时间段）
    overlaps_fixed = 0
    for i in range(len(subtitle_entries) - 1, 0, -1):  # 从最后一条往前遍历
        current = subtitle_entries[i]
        prev_entry = subtitle_entries[i - 1]
        
        # 如果有重叠（前一行的结束时间 > 后一行的开始时间）
        if prev_entry['end'] > current['start']:
            # 特殊情况：如果开始时间相同，按比例分割
            if prev_entry['start'] == current['start']:
                # 计算总时长和各自的字符数
                total_duration = max(prev_entry['end'], current['end']) - prev_entry['start']
                prev_chars = len(clean_text_for_match(prev_entry['text']))
                curr_chars = len(clean_text_for_match(current['text']))
                total_chars = prev_chars + curr_chars
                
                if total_chars > 0:
                    # 按字符数比例分割时间
                    prev_ratio = prev_chars / total_chars
                    split_point = prev_entry['start'] + total_duration * prev_ratio
                    prev_entry['end'] = split_point
                    current['start'] = split_point
            else:
                # 普通重叠：前一行结束时间 = 后一行开始时间
                prev_entry['end'] = current['start']
            overlaps_fixed += 1
    
    # 步骤2：从前往后修复间隙（前一行结束时间 = 后一行开始时间）
    gaps_fixed = 0
    for i in range(len(subtitle_entries) - 1):
        current = subtitle_entries[i]
        next_entry = subtitle_entries[i + 1]
        
        # 如果有间隙，将当前条的结束时间设为下一条的开始时间
        if next_entry['start'] > current['end']:
            gap = next_entry['start'] - current['end']
            if gap > 0.001:  # 间隙大于1毫秒
                current['end'] = next_entry['start']
                gaps_fixed += 1
    
    if overlaps_fixed > 0:
        print(f"  ✅ 修复了 {overlaps_fixed} 个时间线重叠")
    if gaps_fixed > 0:
        print(f"  ✅ 修复了 {gaps_fixed} 个时间线间隙")
    if overlaps_fixed == 0 and gaps_fixed == 0:
        print(f"  ✅ 时间线已连续，无需修复")
    
    # 4. 生成 SRT
    srt_content = []
    for entry in subtitle_entries:
        # 去除末尾标点符号
        text = entry['text'].rstrip('，。！？；：、,."\'!?;:')
        
        srt_content.append(f"{entry['id']}")
        srt_content.append(f"{format_time(entry['start'])} --> {format_time(entry['end'])}")
        srt_content.append(text)
        srt_content.append("")
    
    # 5. 保存
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(srt_content))
    
    print(f"\n✅ SRT 重建完成！")
    print(f"📁 输出文件: {output_srt_path}")
    print(f"📊 字幕条数: {len(subtitle_entries)}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python rebuild_srt_v2.py <script_id>")
        print("说明: 基于词语时间线字典重建 SRT 字幕")
        sys.exit(1)
    
    rebuild_srt_v2(sys.argv[1])
