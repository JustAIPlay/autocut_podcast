#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文案二创脚本
调用 Poe API (Gemini 2.5 Flash) 进行文案二创
"""
import os
import sys
import io
import json
import argparse
from pathlib import Path

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils import get_script_paths, get_project_root, get_env
from poe_client import PoeClient


def load_prompt_template() -> str:
    """加载二创提示词模板"""
    prompt_path = get_project_root() / "PROMPTS" / "prompt_recreate.md"
    
    if not prompt_path.exists():
        print(f"❌ 找不到提示词模板: {prompt_path}")
        return None
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def recreate_copy(script_id: str, book_name: str) -> bool:
    """
    对原始文案进行二创
    
    Args:
        script_id: 项目标识符
        book_name: 书名（用于二创植入）
        
    Returns:
        是否成功
    """
    paths = get_script_paths(script_id)
    
    # 输入：原始文案
    input_path = paths["copy_original"]
    
    # 输出：二创文案
    output_path = paths["copy_recreated"]
    
    # 检查输入文件
    if not input_path.exists():
        print(f"❌ 找不到原始文案: {input_path}")
        print(f"💡 请先运行 transcribe_qwen_asr.py 进行转录")
        return False
    
    # 读取原始文案
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    original_length = len(raw_text)
    print(f"📄 原始文案字数: {original_length}")
    
    # 加载提示词模板
    prompt_template = load_prompt_template()
    if not prompt_template:
        return False
    
    # 填充模板
    prompt = prompt_template.replace("{book_name}", book_name)
    prompt = prompt.replace("{raw_text}", raw_text)
    
    # 调用 Poe API
    print(f"🤖 正在调用 Poe API (Gemini 2.5 Flash) 进行文案二创...")
    print(f"📚 书名: 《{book_name}》")
    
    try:
        # 初始化 Poe 客户端
        # 使用 Gemini 2.5 Flash
        poe_client = PoeClient(bot_name="Gemini-2.5-Flash")
        
        # 发送请求
        response = poe_client.send_message(prompt)
        
        if not response:
            print("❌ Poe API 返回为空")
            return False
        
        # 提取二创文案（清理可能的代码块标记）
        recreated_text = response.strip()
        if recreated_text.startswith("```"):
            # 移除代码块标记
            lines = recreated_text.split("\n")
            if len(lines) > 2:
                recreated_text = "\n".join(lines[1:-1])
        
        recreated_length = len(recreated_text)
        
        # 计算统计信息
        length_ratio = recreated_length / original_length if original_length > 0 else 0
        
        # 保存二创文案
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(recreated_text)
        
        print(f"✅ 文案二创完成！")
        print(f"📝 输出文件: {output_path}")
        print(f"📊 原始字数: {original_length}")
        print(f"📊 二创字数: {recreated_length}")
        print(f"📊 字数比例: {length_ratio:.1%}")
        
        # 检查是否满足 ±10% 要求
        if 0.9 <= length_ratio <= 1.1:
            print(f"✅ 字数控制在 ±10% 范围内")
        else:
            print(f"⚠️ 警告: 字数偏差超过 ±10%，可能需要调整")
        
        print("-" * 40)
        print("预览前300字：")
        print(recreated_text[:300] + "..." if len(recreated_text) > 300 else recreated_text)
        
        return True
        
    except Exception as e:
        print(f"❌ 文案二创失败: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="文案二创 - 使用 Poe API")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    parser.add_argument("--book", "-b", required=True, help="书名（必填）")
    
    args = parser.parse_args()
    
    success = recreate_copy(args.script_id, args.book)
    sys.exit(0 if success else 1)
