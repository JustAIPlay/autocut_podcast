#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移除播客 JSON 文件中的所有副语言标签
"""
import json
import re
import sys
from pathlib import Path


def remove_paralanguage_tags(input_file: Path, output_file: Path = None):
    """
    移除 JSON 文件中的所有副语言标签
    
    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径（如果为 None，则覆盖原文件）
    """
    if output_file is None:
        output_file = input_file
    
    # 读取 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if "text" not in data:
        print("❌ JSON 文件格式不正确，缺少 'text' 字段")
        return False
    
    # 统计修改前的标签数量
    tag_count = 0
    modified_count = 0
    
    # 处理 speakers 中的 prompt_text
    if "speakers" in data:
        for speaker_id, speaker_info in data["speakers"].items():
            if "prompt_text" in speaker_info:
                original_text = speaker_info["prompt_text"]
                # 移除标签
                cleaned_text = re.sub(r'\s*`<\|[^|]+\|>`\s*', ' ', original_text)
                cleaned_text = cleaned_text.strip()
                
                if cleaned_text != original_text:
                    data["speakers"][speaker_id]["prompt_text"] = cleaned_text
                    tag_count += len(re.findall(r'`<\|[^|]+\|>`', original_text))
                    modified_count += 1
                    print(f"✅ 清理 speakers.{speaker_id}.prompt_text")
    
    # 处理对话文本
    for i, dialogue in enumerate(data["text"]):
        if len(dialogue) != 2:
            continue
        
        speaker, text = dialogue
        original_text = text
        
        # 移除所有标签（格式：`<|tag|>`）
        cleaned_text = re.sub(r'\s*`<\|[^|]+\|>`\s*', ' ', text)
        # 清理多余空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        # 统计标签数量
        tags_in_text = len(re.findall(r'`<\|[^|]+\|>`', original_text))
        if tags_in_text > 0:
            tag_count += tags_in_text
            modified_count += 1
        
        # 更新对话
        data["text"][i][1] = cleaned_text
    
    # 保存修改后的 JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 统计:")
    print(f"   - 总对话数: {len(data['text'])}")
    print(f"   - 移除标签: {tag_count} 个")
    print(f"   - 修改对话: {modified_count} 条")
    print(f"\n✅ 已保存到: {output_file}")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python remove_tags.py <input_json> [output_json]")
        print()
        print("示例:")
        print("  # 覆盖原文件")
        print("  python remove_tags.py HFlyx000418_soulx_input.json")
        print()
        print("  # 保存到新文件")
        print("  python remove_tags.py HFlyx000418_soulx_input.json HFlyx000418_clean.json")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"❌ 文件不存在: {input_file}")
        sys.exit(1)
    
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print(f"📄 输入文件: {input_file}")
    if output_file:
        print(f"📄 输出文件: {output_file}")
    else:
        print(f"📄 输出文件: {input_file} (覆盖)")
    print()
    
    success = remove_paralanguage_tags(input_file, output_file)
    sys.exit(0 if success else 1)
