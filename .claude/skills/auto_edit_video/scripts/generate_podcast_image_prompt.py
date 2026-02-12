#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播客封面图提示词生成脚本
使用 DeepSeek API 根据播客内容生成图像提示词
"""
import sys
import io
from pathlib import Path
from openai import OpenAI
from utils import get_env, get_script_paths, get_project_root

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def generate_image_prompt(script_id: str) -> bool:
    """
    生成播客封面图提示词
    
    输入: copys/{id}_podcast.txt
    输出: copys/{id}_image_prompt.txt
    """
    paths = get_script_paths(script_id)
    
    # 检查输入文件
    input_file = paths["copy_podcast"]
    if not input_file.exists():
        print(f"❌ 找不到输入文件: {input_file}")
        print(f"   请先运行: python recreate_podcast.py {script_id}")
        return False
    
    # 读取播客文案
    with open(input_file, 'r', encoding='utf-8') as f:
        podcast_script = f.read()
    
    if not podcast_script.strip():
        print("❌ 输入文件为空")
        return False
    
    # 提取内容摘要（取前 500 字作为上下文）
    content_summary = podcast_script[:500]
    if len(podcast_script) > 500:
        content_summary += "..."
    
    print(f"📄 播客内容摘要长度: {len(content_summary)}")
    
    # 读取提示词模板
    prompt_path = get_project_root() / "PROMPTS" / "prompt_podcast_image.md"
    if not prompt_path.exists():
        print(f"❌ 找不到提示词文件: {prompt_path}")
        return False
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 填充内容
    prompt = prompt_template.replace("{content_summary}", content_summary)
    
    # 调用 DeepSeek API
    api_key = get_env("DEEPSEEK_API_KEY")
    base_url = get_env("DEEPSEEK_BASE_URL", "https://maas-api.lanyun.net/v1")
    model_name = get_env("DEEPSEEK_MODEL", "/maas/deepseek-ai/DeepSeek-V3.2")
    
    if not api_key:
        print("❌ 请在 .env 中设置 DEEPSEEK_API_KEY")
        return False
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    try:
        print(f"🤖 正在调用 DeepSeek ({model_name}) 生成图像提示词...")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的 AI 绘图提示词工程师。请直接输出英文提示词，不要输出任何解释或前言。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            stream=False
        )
        
        result = response.choices[0].message.content.strip()
        
        if not result:
            print("❌ API 返回为空")
            return False
        
        # 保存结果
        output_file = paths["image_prompt"]
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        
        print(f"✅ 图像提示词生成完成！")
        print(f"   - 输出文件: {output_file}")
        print()
        print("生成的提示词：")
        print("-" * 40)
        print(result)
        
        return True
        
    except Exception as e:
        print(f"❌ 调用 API 失败: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate_podcast_image_prompt.py <script_id>")
        sys.exit(1)
    
    script_id = sys.argv[1]
    success = generate_image_prompt(script_id)
    sys.exit(0 if success else 1)
