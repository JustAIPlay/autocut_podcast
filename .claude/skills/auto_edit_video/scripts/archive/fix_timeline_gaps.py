#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复时间线间隙：确保字幕和场景时间线完全连续
"""
import json
import sys
import io
from pathlib import Path
from utils import get_script_paths

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def parse_srt_time(time_str):
    """将 SRT 时间格式转换为秒数"""
    # 格式：00:00:00,000
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    secs_millis = parts[2].split(',')
    seconds = int(secs_millis[0])
    millis = int(secs_millis[1])
    
    total_seconds = hours * 3600 + minutes * 60 + seconds + millis / 1000.0
    return total_seconds

def format_srt_time(seconds):
    """将秒数转换为 SRT 时间格式"""
    millis = int((seconds - int(seconds)) * 1000)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def fix_subtitle_gaps(script_id):
    """修复字幕时间线间隙"""
    paths = get_script_paths(script_id)
    srt_path = paths["caption_final_srt"]
    
    if not srt_path.exists():
        print(f"❌ 找不到字幕文件: {srt_path}")
        return False
    
    print(f"🔍 检查字幕时间线: {srt_path}")
    
    # 读取 SRT 文件
    with open(srt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 解析字幕条目
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.isdigit():  # 字幕ID
            subtitle_id = int(line)
            i += 1
            
            # 时间行
            if i < len(lines):
                time_line = lines[i].strip()
                if '-->' in time_line:
                    times = time_line.split(' --> ')
                    start_time = parse_srt_time(times[0])
                    end_time = parse_srt_time(times[1])
                    i += 1
                    
                    # 文本行
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    text = '\n'.join(text_lines)
                    entries.append({
                        'id': subtitle_id,
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })
        i += 1
    
    print(f"📊 字幕总数: {len(entries)}")
    
    # 检查间隙
    gaps_found = 0
    for i in range(len(entries) - 1):
        current = entries[i]
        next_entry = entries[i + 1]
        gap = next_entry['start'] - current['end']
        
        if abs(gap) > 0.001:  # 间隙大于1毫秒
            gaps_found += 1
            print(f"  ⚠️ 第{current['id']}条 → 第{next_entry['id']}条: 间隙 {gap:.3f}秒")
    
    if gaps_found == 0:
        print("✅ 字幕时间线已经连续！")
        return True
    
    print(f"\n🔨 发现 {gaps_found} 个间隙，开始修复...")
    
    # 修复间隙：将每条字幕的结束时间设为下一条的开始时间
    for i in range(len(entries) - 1):
        current = entries[i]
        next_entry = entries[i + 1]
        current['end'] = next_entry['start']
        print(f"  ✅ 修复第{current['id']}条: 结束时间 → {current['end']:.3f}秒")
    
    # 生成新的 SRT 内容
    srt_content = []
    for entry in entries:
        srt_content.append(f"{entry['id']}")
        srt_content.append(f"{format_srt_time(entry['start'])} --> {format_srt_time(entry['end'])}")
        srt_content.append(entry['text'])
        srt_content.append("")
    
    # 保存
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_content))
    
    print(f"\n✅ 字幕时间线修复完成！")
    return True

def fix_scene_gaps(script_id):
    """修复场景时间线间隙"""
    paths = get_script_paths(script_id)
    scenes_path = paths["scenes"]
    
    if not scenes_path.exists():
        print(f"❌ 找不到场景文件: {scenes_path}")
        return False
    
    print(f"\n🔍 检查场景时间线: {scenes_path}")
    
    # 读取场景文件
    with open(scenes_path, 'r', encoding='utf-8') as f:
        scenes = json.load(f)
    
    print(f"📊 场景总数: {len(scenes)}")
    
    # 检查间隙
    gaps_found = 0
    for i in range(len(scenes) - 1):
        current = scenes[i]
        next_scene = scenes[i + 1]
        
        if current['end_time'] is None or next_scene['start_time'] is None:
            continue
        
        gap = next_scene['start_time'] - current['end_time']
        
        if abs(gap) > 0.001:  # 间隙大于1毫秒
            gaps_found += 1
            print(f"  ⚠️ 场景{current['scene']} → 场景{next_scene['scene']}: 间隙 {gap:.3f}秒")
    
    if gaps_found == 0:
        print("✅ 场景时间线已经连续！")
        return True
    
    print(f"\n🔨 发现 {gaps_found} 个间隙，开始修复...")
    
    # 修复间隙：将每个场景的结束时间设为下一个场景的开始时间
    for i in range(len(scenes) - 1):
        current = scenes[i]
        next_scene = scenes[i + 1]
        
        if current['end_time'] is not None and next_scene['start_time'] is not None:
            old_end = current['end_time']
            current['end_time'] = next_scene['start_time']
            current['duration'] = current['end_time'] - current['start_time']
            print(f"  ✅ 修复场景{current['scene']}: 结束时间 {old_end:.3f} → {current['end_time']:.3f}秒")
    
    # 保存
    with open(scenes_path, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 场景时间线修复完成！")
    return True

def fix_timeline_gaps(script_id):
    """修复字幕和场景的时间线间隙"""
    print("=" * 60)
    print("🔧 时间线间隙修复工具")
    print("=" * 60)
    
    # 修复字幕时间线
    subtitle_ok = fix_subtitle_gaps(script_id)
    
    # 修复场景时间线
    scene_ok = fix_scene_gaps(script_id)
    
    print("\n" + "=" * 60)
    if subtitle_ok and scene_ok:
        print("✅ 所有时间线修复完成！")
    else:
        print("⚠️ 部分时间线修复失败，请检查日志")
    print("=" * 60)
    
    return subtitle_ok and scene_ok

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fix_timeline_gaps.py <script_id>")
        print("说明: 修复字幕和场景的时间线间隙，确保时间线连续")
        sys.exit(1)
    
    fix_timeline_gaps(sys.argv[1])
