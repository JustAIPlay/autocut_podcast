#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试防重复机制
"""

def should_add_tag(text: str) -> bool:
    """检查是否应该添加标签"""
    # 检查是否已有标签
    if "`<|" in text:
        return False
    return True


# 测试用例
test_cases = [
    ("是的，这个问题很常见", True, "没有标签，应该添加"),
    ("是的 `<|sigh|>` 这个问题很常见", False, "已有标签，不应该添加"),
    ("没错 `<|laughter|>` 就是这样", False, "已有标签，不应该添加"),
    ("那么，我们接下来说说", True, "没有标签，应该添加"),
    ("第一个是 `<|breathing|>` 南瓜", False, "已有标签，不应该添加"),
]

print("=" * 60)
print("防重复机制测试")
print("=" * 60)

for text, expected, description in test_cases:
    result = should_add_tag(text)
    status = "✅ 通过" if result == expected else "❌ 失败"
    
    print(f"\n{status}")
    print(f"文本: {text}")
    print(f"预期: {'添加' if expected else '跳过'}")
    print(f"实际: {'添加' if result else '跳过'}")
    print(f"说明: {description}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
