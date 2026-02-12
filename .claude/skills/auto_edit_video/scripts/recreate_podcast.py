#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播客文案二创脚本
使用智谱 API 将 ASR 转录文本转换为带说话人标签的二创文案
"""
import sys
import io
from pathlib import Path
from zhipu_client import ZhipuClient
from utils import get_script_paths, get_project_root

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def recreate_podcast(script_id: str) -> bool:
    """
    播客文案二创
    
    输入: copys/{id}_original.txt (ASR 原始转录)
    输出: copys/{id}_podcast.txt ([S1]/[S2] 格式)
    """
    paths = get_script_paths(script_id)
    
    # 检查输入文件
    input_file = paths["copy_original"]
    if not input_file.exists():
        print(f"❌ 找不到输入文件: {input_file}")
        return False
    
    # 读取原始转录
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    if not raw_text.strip():
        print("❌ 输入文件为空")
        return False
    
    print(f"📄 输入文案字数: {len(raw_text)}")
    
    # 读取提示词模板
    prompt_path = get_project_root() / "PROMPTS" / "prompt_podcast_recreate.md"
    if not prompt_path.exists():
        print(f"❌ 找不到提示词文件: {prompt_path}")
        return False
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 填充文案内容
    prompt = prompt_template.replace("{raw_text}", raw_text)
    
    # 调用智谱 API
    try:
        client = ZhipuClient()
        # 使用智谱 GLM 模型进行处理
        result = client.chat(prompt, temperature=0.5)
        
        if not result:
            print("❌ API 返回为空")
            return False
        
        # 清理结果 (移除可能的代码块标记)
        result = result.strip()
        if result.startswith("```"):
            lines = result.split('\n')
            # 移除首尾的代码块标记
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            result = '\n'.join(lines)
        
        # 验证输出格式
        if not ("[S1]" in result and "[S2]" in result):
            print("⚠️ 警告: 输出可能不符合 [S1]/[S2] 格式，请检查")
        
        # 保存结果
        output_file = paths["copy_podcast"]
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print(f"✅ 播客文案二创完成！")
        print(f"   - 输出文件: {output_file}")
        print(f"   - 输出字数: {len(result)}")
        print()
        print("预览前 5 行：")
        print("-" * 40)
        for line in result.splitlines()[:5]:
            print(line[:80] + ("..." if len(line) > 80 else ""))
        
        return True
        
    except Exception as e:
        print(f"❌ 调用 API 失败: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python recreate_podcast.py <script_id>")
        sys.exit(1)
    
    script_id = sys.argv[1]
    success = recreate_podcast(script_id)
    sys.exit(0 if success else 1)
