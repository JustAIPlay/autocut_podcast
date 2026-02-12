#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建修正后的词语时间线字典
使用按位置对齐算法：保持 Whisper 的分词和时间轴，只修正文本内容
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

def clean_text(text):
    """移除标点符号和空格，用于文本对齐"""
    import string
    punctuation = '，。！？；：、,."\'!?;:""\'\'（）()【】[]《》<>·—…～｜/\\-_=+*&^%$#@`~ \n'
    punctuation += string.punctuation
    return ''.join(c for c in text if c not in punctuation)

def align_by_position(whisper_words, refined_text):
    """
    按顺序位置对齐算法（基于比例分配）
    
    策略：
    1. 计算 Whisper 总字符数和 Refined 总字符数
    2. 计算分布比例 ratio
    3. 按 ratio 将 refined_text 均匀分配给每个 whisper 单词
    
    优势：
    - 确保 refined_text 的所有字符都被包含在时间线内
    - 解决 refined.txt 变长导致文案被截断的问题
    
    Args:
        whisper_words: Whisper 分词列表（带标点）
        refined_text: 优化后的文本（去除换行）
    
    Returns:
        对齐后的词语列表
    """
    refined_clean = clean_text(refined_text)
    
    # 计算 Whisper 清洗后的总长度
    whisper_clean_lens = [len(clean_text(w)) for w in whisper_words]
    total_whisper_len = sum(whisper_clean_lens)
    total_refined_len = len(refined_clean)
    
    print(f"📊 对齐统计:")
    print(f"  - Whisper 词数: {len(whisper_words)}")
    print(f"  - Whisper 字符数: {total_whisper_len}")
    print(f"  - Refined 字符数: {total_refined_len}")
    
    if total_whisper_len == 0:
        ratio = 1.0
    else:
        ratio = total_refined_len / total_whisper_len
        
    print(f"  - 字符膨胀比: {ratio:.3f}")
    
    aligned_words = []
    current_refined_pos = 0
    accumulated_target = 0.0
    
    for i, w_word in enumerate(whisper_words):
        w_len = whisper_clean_lens[i]
        
        # 如果是纯标点，保留原标点（虽然会被清洗掉，但保持结构完整）
        if w_len == 0:
            aligned_words.append(w_word)
            continue
            
        # 计算当前词应该分到的字符数
        accumulated_target += w_len * ratio
        target_end_pos = int(round(accumulated_target))
        
        # 确保不越界
        target_end_pos = min(target_end_pos, total_refined_len)
        
        # 提取对应的 refined 文本
        chunk_len = target_end_pos - current_refined_pos
        
        if chunk_len > 0:
            chunk = refined_clean[current_refined_pos : target_end_pos]
            aligned_words.append(chunk)
            current_refined_pos = target_end_pos
        else:
            # 如果比例很小导致不需要分配字符，使用空字符串或者原词？
            # 这里的策略是：如果没有分配到字符，就给个空字符串，这样不会占用时间
            # 但为了防止空洞，如果还剩字符，至少给一个？
            # 实际上 round() 机制应该能处理好
            aligned_words.append("")
            
    # 兜底：如果还有剩余字符，全部追加到最后一个非空词
    if current_refined_pos < total_refined_len:
        remaining = refined_clean[current_refined_pos:]
        print(f"⚠️ 还有 {len(remaining)} 个未分配字符，追加到末尾")
        if aligned_words:
            # 找到最后一个非纯标点的 slot
            for j in range(len(aligned_words)-1, -1, -1):
                if aligned_words[j] and clean_text(aligned_words[j]):
                    aligned_words[j] += remaining
                    break
    
    # 简单的验证
    total_aligned_len = sum(len(clean_text(w)) for w in aligned_words)
    print(f"📝 最终分配字符数: {total_aligned_len} (应为 {total_refined_len})")
    
    return aligned_words

def build_word_dict(script_id):
    """
    构建修正后的词语时间线字典
    
    输入:
        - refined.txt: DeepSeek 优化后的文本
        - whisper.json: Whisper 词语级别时间轴
    
    输出:
        - refined_word_dict.json: 修正后的词语时间线字典
    """
    paths = get_script_paths(script_id)
    
    refined_txt_path = paths["copy_refined"]
    whisper_json_path = paths["caption_whisper_json"]
    output_path = paths["caption_refined_json"]
    
    # 检查输入文件
    if not refined_txt_path.exists():
        print(f"❌ 找不到 refined.txt: {refined_txt_path}")
        return False
    
    if not whisper_json_path.exists():
        print(f"❌ 找不到 whisper.json: {whisper_json_path}")
        return False
    
    print(f"🔨 正在构建词语时间线字典（按位置对齐算法）...")
    print(f"📄 读取优化文本: {refined_txt_path}")
    
    # 1. 读取 refined.txt
    with open(refined_txt_path, 'r', encoding='utf-8') as f:
        refined_text = f.read()
    
    # 2. 读取 whisper.json
    with open(whisper_json_path, 'r', encoding='utf-8') as f:
        whisper_data = json.load(f)
        whisper_segments = whisper_data['segments']
    
    print(f"📊 原始词语数: {len(whisper_segments)}")
    
    # 3. 提取 Whisper 的词语列表
    whisper_words = [seg['text'] for seg in whisper_segments]
    
    # 4. 按顺序位置对齐（不进行文本匹配）
    refined_text_clean = refined_text.replace('\n', '')
    aligned_words = align_by_position(whisper_words, refined_text_clean)
    
    # 5. 构建新的 segments（保持时间轴，更新文本）
    refined_segments = []
    for i, seg in enumerate(whisper_segments):
        if i < len(aligned_words):
            refined_segments.append({
                "id": seg['id'],
                "start": seg['start'],
                "end": seg['end'],
                "text": aligned_words[i]
            })
        else:
            # 如果对齐失败，保留原文
            refined_segments.append(seg)
    
    # 6. 生成修正后的词语时间线字典
    refined_word_dict = {
        "script_id": script_id,
        "full_text": refined_text,
        "segments": refined_segments,
        "segment_mode": "word_level_refined",
        "total_words": len(refined_segments),
        "note": "修正后的词语时间线字典（按位置对齐：保持分词+时间轴，按顺序替换文本）"
    }
    
    # 7. 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(refined_word_dict, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 词语时间线字典构建完成！")
    print(f"📁 输出文件: {output_path}")
    print(f"📊 修正词语数: {len(refined_segments)}")
    print(f"\n预览前10个词:")
    for seg in refined_segments[:10]:
        print(f"  [{seg['start']:.3f}-{seg['end']:.3f}] \"{seg['text']}\"")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python build_word_dict.py <script_id>")
        print("说明: 将 refined.txt 映射到 whisper.json 的词语时间轴")
        sys.exit(1)
    
    build_word_dict(sys.argv[1])
