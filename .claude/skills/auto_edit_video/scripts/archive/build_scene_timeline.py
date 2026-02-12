#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于词语时间线字典计算场景时间线
输入:
  - scenes.json: 场景列表（包含text, prompt, effect）
  - refined_word_dict.json: 修正后的词语时间线字典
输出:
  - scenes_with_timeline.json: 包含时间线的场景列表
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

def find_text_in_dict(text, word_dict_segments, start_from_index=0):
    """
    在词语时间线字典中查找文本，返回起始和结束时间
    
    策略（针对场景文本 = 多句合并）：
    1. 提取场景文本的开头部分（前10个有效字符）
    2. 在词典中查找开头位置
    3. 从开头位置继续匹配尽可能多的内容
    4. 返回匹配的时间范围
    
    优化：完全忽略标点符号，只匹配文本内容
    
    Args:
        text: 要查找的文本（可能是多句合并）
        word_dict_segments: 词语时间线列表
        start_from_index: 从哪个索引开始查找（避免重复匹配）
    
    Returns:
        (start_time, end_time, last_matched_index) 或 (None, None, start_from_index)
    """
    # 清理查找文本（移除所有标点）
    text_clean = clean_text_for_match(text)
    
    if not text_clean or len(text_clean) < 3:
        return None, None, start_from_index
    
    # 提取开头部分用于定位（前10个字符）
    head_text = text_clean[:min(10, len(text_clean))]
    
    # 先找到开头位置
    found_start_idx = None
    for idx in range(start_from_index, len(word_dict_segments)):
        seg = word_dict_segments[idx]
        word = seg['text']
        word_clean = clean_text_for_match(word)
        
        if not word_clean:
            continue
        
        # 检查是否匹配开头
        if head_text.startswith(word_clean):
            found_start_idx = idx
            break
        elif word_clean in head_text:
            found_start_idx = idx
            break
    
    if found_start_idx is None:
        return None, None, start_from_index
    
    # 从找到的位置开始，尽可能多地匹配
    matched_words = []
    search_pos = 0
    last_matched_idx = found_start_idx
    
    for idx in range(found_start_idx, len(word_dict_segments)):
        seg = word_dict_segments[idx]
        word = seg['text']
        word_clean = clean_text_for_match(word)
        
        if not word_clean:
            continue
        
        # 检查是否匹配
        if search_pos < len(text_clean):
            if text_clean[search_pos:search_pos+len(word_clean)] == word_clean:
                matched_words.append(seg)
                search_pos += len(word_clean)
                last_matched_idx = idx
            else:
                # 如果不匹配，检查是否已经匹配了足够多的内容（至少50%）
                if search_pos >= len(text_clean) * 0.5:
                    break
                # 否则继续尝试匹配（可能有轻微差异）
                if len(matched_words) > 5:
                    # 已经匹配了一些内容，允许结束
                    break
        else:
            # 已匹配完整个文本
            break
    
    if matched_words and search_pos >= len(text_clean) * 0.4:  # 至少匹配40%
        start_time = matched_words[0]['start']
        end_time = matched_words[-1]['end']
        return start_time, end_time, last_matched_idx + 1
    else:
        return None, None, start_from_index

def build_scene_timeline(script_id):
    """
    为场景添加时间线信息
    """
    paths = get_script_paths(script_id)
    
    scenes_path = paths["scenes"]
    word_dict_path = paths["caption_refined_json"]
    
    if not scenes_path.exists():
        print(f"❌ 找不到 scenes.json: {scenes_path}")
        return False
    
    if not word_dict_path.exists():
        print(f"❌ 找不到词语字典: {word_dict_path}")
        return False
    
    print(f"🔨 正在计算场景时间线...")
    
    # 1. 读取 scenes.json（兼容新旧格式）
    with open(scenes_path, 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)
    
    # 兼容新旧格式
    if isinstance(scenes_data, dict) and "scenes" in scenes_data:
        scenes = scenes_data["scenes"]  # 新格式
    else:
        scenes = scenes_data  # 旧格式（纯数组）
    
    # 2. 读取词语时间线字典
    with open(word_dict_path, 'r', encoding='utf-8') as f:
        word_dict = json.load(f)
        word_segments = word_dict['segments']
    
    print(f"📝 场景数量: {len(scenes)}")
    print(f"📊 词典词数: {len(word_segments)}")
    
    # 3. 为每个场景匹配时间
    search_start_idx = 0  # 跟踪搜索起始位置，避免重复匹配
    
    for scene in scenes:
        text = scene['text']
        scene_num = scene['scene']
        
        start_time, end_time, next_idx = find_text_in_dict(text, word_segments, search_start_idx)
        
        if start_time is not None and end_time is not None:
            scene['start_time'] = round(start_time, 3)
            scene['end_time'] = round(end_time, 3)
            scene['duration'] = round(end_time - start_time, 3)
            search_start_idx = next_idx
            
            print(f"  ✅ 场景{scene_num}: [{start_time:.2f}-{end_time:.2f}] ({scene['duration']:.2f}s) {text[:30]}...")
        else:
            print(f"  ⚠️ 场景{scene_num}: 未找到匹配 - {text[:30]}...")
            scene['start_time'] = None
            scene['end_time'] = None
            scene['duration'] = None
    
    # 🔧 修复时间线间隙：确保时间线连续
    print(f"\n🔧 修复时间线间隙...")
    gaps_fixed = 0
    for i in range(len(scenes) - 1):
        current = scenes[i]
        next_scene = scenes[i + 1]
        
        # 只处理有时间线的场景
        if current.get('end_time') is not None and next_scene.get('start_time') is not None:
            # 如果有间隙，将当前场景的结束时间设为下一场景的开始时间
            if next_scene['start_time'] > current['end_time']:
                gap = next_scene['start_time'] - current['end_time']
                if gap > 0.001:  # 间隙大于1毫秒
                    current['end_time'] = next_scene['start_time']
                    current['duration'] = round(current['end_time'] - current['start_time'], 3)
                    gaps_fixed += 1
    
    if gaps_fixed > 0:
        print(f"  ✅ 修复了 {gaps_fixed} 个时间线间隙")
    else:
        print(f"  ✅ 时间线已连续，无需修复")
    
    # 4. 保存（覆盖原 scenes.json，保持元数据）
    if isinstance(scenes_data, dict) and "metadata" in scenes_data:
        # 新格式：保持 metadata
        scenes_data["scenes"] = scenes
        output_data = scenes_data
    else:
        # 旧格式：保持兼容
        output_data = scenes
    
    with open(scenes_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 场景时间线计算完成！")
    print(f"📁 输出文件: {scenes_path}")
    print(f"📊 成功匹配: {sum(1 for s in scenes if s.get('start_time') is not None)}/{len(scenes)}")
    
    # 统计
    total_duration = sum(s['duration'] for s in scenes if s.get('duration') is not None)
    print(f"⏱️  总时长: {total_duration:.2f}秒")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python build_scene_timeline.py <script_id>")
        print("说明: 为场景添加时间线信息")
        sys.exit(1)
    
    build_scene_timeline(sys.argv[1])
