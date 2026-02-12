#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理播客文案中的反引号
将 `<|tag|>` 格式转换为 <|tag|> 格式
"""
import sys
import re
from pathlib import Path


def clean_backticks(input_file: Path, output_file: Path = None):
    """
    清理文件中副语言标签的反引号
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径（如果为 None，则覆盖原文件）
    """
    if output_file is None:
        output_file = input_file
    
    # 读取文件
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 统计修改前的标签数量
    before_count = len(re.findall(r'`<\|[^|]+\|>`', content))
    
    # 清理反引号
    # 匹配 `<|xxx|>` 格式，替换为 <|xxx|>
    cleaned_content = re.sub(r'`(<\|[^|]+\|>)`', r'\1', content)
    
    # 统计修改后的标签数量
    after_count = len(re.findall(r'<\|[^|]+\|>', cleaned_content))
    
    # 保存文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"✅ 清理完成！")
    print(f"   - 输入文件: {input_file}")
    print(f"   - 输出文件: {output_file}")
    print(f"   - 清理前: {before_count} 个带反引号的标签")
    print(f"   - 清理后: {after_count} 个正确格式的标签")
    
    if before_count > 0:
        print(f"   - 已修复: {before_count} 个标签")
    else:
        print(f"   - 未发现需要清理的标签")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python clean_backticks.py <input_file> [output_file]")
        print()
        print("示例:")
        print("  # 覆盖原文件")
        print("  python clean_backticks.py raw_materials/copys/HFlyx000418_podcast.txt")
        print()
        print("  # 保存到新文件")
        print("  python clean_backticks.py input.txt output.txt")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        print(f"❌ 文件不存在: {input_file}")
        sys.exit(1)
    
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    success = clean_backticks(input_file, output_file)
    sys.exit(0 if success else 1)
