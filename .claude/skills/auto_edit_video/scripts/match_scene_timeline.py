#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分镜时间线匹配脚本
将分镜文本与词级时间戳匹配，为每个分镜添加时间线
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


def clean_text_for_match(text: str) -> str:
    """清理文本用于匹配：移除所有标点符号和空格"""
    import string
    punctuation = '，。！？；：、,."\' !?;:""\'\' （）()【】[]《》<>·—…～｜/\\-_=+*&^%$#@`~ \n\r\t'
    punctuation += string.punctuation
    return ''.join(c for c in text if c not in punctuation)


def match_scene_timeline(script_id: str) -> bool:
    """
    将分镜文本与词级时间戳匹配，为每个分镜添加时间线
    
    Args:
        script_id: 项目标识符
        
    Returns:
        是否成功
    """
    paths = get_script_paths(script_id)
    
    # 输入
    scenes_path = paths["scenes"]  # 分镜 JSON
    timestamps_path = paths["word_timestamps"]  # 词级时间戳
    
    # 检查输入文件
    if not scenes_path.exists():
        print(f"❌ 找不到分镜文件: {scenes_path}")
        print(f"💡 请先运行 analyze_scenes.py 进行分镜分析")
        return False
    
    if not timestamps_path.exists():
        print(f"❌ 找不到时间戳文件: {timestamps_path}")
        print(f"💡 请先运行 forced_align.py 生成时间戳")
        return False
    
    # 读取分镜
    with open(scenes_path, 'r', encoding='utf-8') as f:
        scenes = json.load(f)
    
    # 读取时间戳
    with open(timestamps_path, 'r', encoding='utf-8') as f:
        timestamps_data = json.load(f)
    
    segments = timestamps_data.get("segments", [])
    
    print(f"🎬 正在匹配分镜时间线...")
    print(f"📄 分镜数量: {len(scenes)}")
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
    
    # 匹配每个分镜
    current_char_pos = 0
    
    for scene in scenes:
        scene_text = scene.get("text", "")
        clean_scene = clean_text_for_match(scene_text)
        scene_length = len(clean_scene)
        
        if scene_length == 0:
            scene["start_time"] = current_char_pos
            scene["end_time"] = current_char_pos
            scene["duration"] = 0.0
            continue
        
        target_start_pos = current_char_pos
        target_end_pos = current_char_pos + scene_length
        
        # 找到覆盖这个范围的第一个和最后一个 segment
        start_time = None
        end_time = None
        
        for sp in segment_positions:
            # 找到第一个与当前分镜有交集的 segment
            if sp["end_pos"] > target_start_pos and start_time is None:
                start_time = sp["start_time"]
            
            # 找到最后一个与当前分镜有交集的 segment
            if sp["start_pos"] < target_end_pos:
                end_time = sp["end_time"]
        
        # 如果没找到，使用默认值
        if start_time is None:
            start_time = 0.0
        if end_time is None:
            end_time = start_time + 3.0  # 默认 3 秒
        
        # 更新分镜时间线
        scene["start_time"] = round(start_time, 3)
        scene["end_time"] = round(end_time, 3)
        scene["duration"] = round(end_time - start_time, 3)
        
        current_char_pos = target_end_pos
    
    # 保存更新后的分镜
    with open(scenes_path, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)
    
    # 计算统计信息
    total_duration = scenes[-1]["end_time"] if scenes else 0.0
    avg_duration = sum(s.get("duration", 0) for s in scenes) / len(scenes) if scenes else 0.0
    
    print(f"✅ 分镜时间匹配完成！")
    print(f"📁 输出文件: {scenes_path}")
    print(f"📊 分镜数量: {len(scenes)}")
    print(f"⏱️ 总时长: {total_duration:.2f} 秒")
    print(f"⏱️ 平均时长: {avg_duration:.2f} 秒/分镜")
    print("-" * 40)
    print("预览前5个分镜：")
    for scene in scenes[:5]:
        print(f"  [{scene.get('start_time', 0):.2f}-{scene.get('end_time', 0):.2f}s] "
              f"({scene.get('duration', 0):.1f}s) {scene.get('text', '')[:25]}...")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分镜时间线匹配")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    
    args = parser.parse_args()
    
    success = match_scene_timeline(args.script_id)
    sys.exit(0 if success else 1)
