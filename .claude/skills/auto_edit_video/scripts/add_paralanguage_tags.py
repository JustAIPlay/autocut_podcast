#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为播客 JSON 文件添加副语言标签
根据文本内容智能添加笑声、叹气、呼吸等标签
"""
import json
import re
import sys
from pathlib import Path


# 副语言标签规则
PARALANGUAGE_RULES = [
    # 笑声标签 - 用于轻松、幽默的时刻
    {
        "tag": "`<|laughter|>`",  # 注意：包含反引号
        "keywords": ["哈哈", "呵呵", "笑", "有趣", "好玩", "太棒了", "太好了", "没错", "对", "是啊", "真的", "确实如此"],
        "position": "after_keyword"  # 在关键词后添加
    },
    # 叹气标签 - 用于感慨、无奈的时刻
    {
        "tag": "`<|sigh|>`",
        "keywords": ["唉", "哎呀", "哎", "可惜", "遗憾", "无奈", "是的", "确实", "真是", "居然", "竟然"],
        "position": "after_keyword"
    },
    # 呼吸标签 - 用于停顿、思考的时刻
    {
        "tag": "`<|breathing|>`",
        "keywords": ["那么", "然后", "接下来", "另外", "还有", "嗯", "这样", "所以", "因此", "不过", "但是"],
        "position": "end"  # 在句尾添加
    },
]


def should_add_tag(text: str, rule: dict) -> tuple:
    """
    判断是否应该添加标签
    返回 (是否添加, 关键词位置)
    """
    for keyword in rule["keywords"]:
        if keyword in text:
            # 避免重复添加标签（检查是否已有反引号包裹的标签）
            if "`<|" in text:
                return False, -1
            
            # 找到关键词位置
            pos = text.find(keyword)
            return True, pos + len(keyword)
    
    return False, -1


def add_paralanguage_tag(text: str, rule: dict) -> str:
    """
    为文本添加副语言标签
    """
    should_add, keyword_pos = should_add_tag(text, rule)
    
    if not should_add:
        return text
    
    tag = f" {rule['tag']}"
    
    if rule["position"] == "after_keyword" and keyword_pos > 0:
        # 在关键词后添加
        return text[:keyword_pos] + tag + text[keyword_pos:]
    elif rule["position"] == "end":
        # 在句尾添加（标点符号前）
        # 找到最后一个标点符号
        for punct in ["。", "！", "？", "，", "、", "："]:
            if text.endswith(punct):
                return text[:-1] + tag + text[-1]
        # 如果没有标点，直接添加到末尾
        return text + tag
    
    return text


def add_paralanguage_tags_to_json(input_file: Path, output_file: Path, probability: float = 0.4):
    """
    为 JSON 文件中的对话添加副语言标签
    
    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径
        probability: 添加标签的概率（0.0-1.0），默认 40%
    """
    # 读取 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if "text" not in data:
        print("❌ JSON 文件格式不正确，缺少 'text' 字段")
        return False
    
    modified_count = 0
    total_count = len(data["text"])
    
    # 遍历每条对话
    for i, dialogue in enumerate(data["text"]):
        if len(dialogue) != 2:
            continue
        
        speaker, text = dialogue
        original_text = text
        
        # 尝试应用每个规则
        for rule in PARALANGUAGE_RULES:
            # 根据概率决定是否添加
            import random
            if random.random() > probability:
                continue
            
            text = add_paralanguage_tag(text, rule)
            
            # 如果添加了标签，跳出循环（每句话最多添加一个标签）
            if text != original_text:
                break
        
        # 更新对话
        if text != original_text:
            data["text"][i][1] = text
            modified_count += 1
            print(f"✅ 修改 #{i+1}: {original_text[:30]}... → {text[:30]}...")
    
    # 保存修改后的 JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 统计:")
    print(f"   - 总对话数: {total_count}")
    print(f"   - 添加标签: {modified_count}")
    print(f"   - 修改比例: {modified_count/total_count*100:.1f}%")
    print(f"\n✅ 已保存到: {output_file}")
    
    return True


def manual_add_tags(input_file: Path, output_file: Path):
    """
    手动模式：显示每条对话，让用户选择是否添加标签
    """
    # 读取 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 60)
    print("手动添加副语言标签模式")
    print("=" * 60)
    print("\n可用标签:")
    print("  1. `<|laughter|>`      - 笑声")
    print("  2. `<|sigh|>`          - 叹气")
    print("  3. `<|breathing|>`     - 呼吸")
    print("  4. `<|coughing|>`      - 咳嗽")
    print("  5. `<|throat_clearing|>` - 清嗓")
    print("  0. 跳过")
    print("  q. 退出并保存")
    print()
    
    tags = {
        "1": "`<|laughter|>`",
        "2": "`<|sigh|>`",
        "3": "`<|breathing|>`",
        "4": "`<|coughing|>`",
        "5": "`<|throat_clearing|>`"
    }
    
    modified_count = 0
    
    for i, dialogue in enumerate(data["text"]):
        if len(dialogue) != 2:
            continue
        
        speaker, text = dialogue
        
        # 如果已经有标签，跳过
        if "`<|" in text:
            continue
        
        print(f"\n[{i+1}/{len(data['text'])}] [{speaker}] {text}")
        choice = input("选择标签 (0-5, q): ").strip()
        
        if choice == "q":
            break
        elif choice == "0":
            continue
        elif choice in tags:
            # 添加标签到句尾
            tag = f" {tags[choice]}"
            data["text"][i][1] = text + tag
            modified_count += 1
            print(f"✅ 已添加: {tags[choice]}")
    
    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 已保存 {modified_count} 处修改到: {output_file}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  自动模式: python add_paralanguage_tags.py <input_json> [output_json] [probability]")
        print("  手动模式: python add_paralanguage_tags.py <input_json> --manual")
        print()
        print("示例:")
        print("  python add_paralanguage_tags.py HFlyx000418_soulx_input.json")
        print("  python add_paralanguage_tags.py HFlyx000418_soulx_input.json output.json 0.4")
        print("  python add_paralanguage_tags.py HFlyx000418_soulx_input.json --manual")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"❌ 文件不存在: {input_file}")
        sys.exit(1)
    
    # 手动模式
    if len(sys.argv) > 2 and sys.argv[2] == "--manual":
        output_file = input_file.parent / f"{input_file.stem}_tagged{input_file.suffix}"
        manual_add_tags(input_file, output_file)
        sys.exit(0)
    
    # 自动模式
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file.parent / f"{input_file.stem}_tagged{input_file.suffix}"
    probability = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4  # 默认 40%
    
    print(f"📄 输入文件: {input_file}")
    print(f"📄 输出文件: {output_file}")
    print(f"🎲 添加概率: {probability*100:.0f}%")
    print()
    
    success = add_paralanguage_tags_to_json(input_file, output_file, probability)
    sys.exit(0 if success else 1)
