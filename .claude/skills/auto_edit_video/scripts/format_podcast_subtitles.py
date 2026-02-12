#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播客字幕格式化脚本
将 [S1]/[S2] 格式的播客文案转换为纯字幕文本
支持 DeepSeek API 智能断句
"""
import sys
import io
import re
import argparse
from pathlib import Path
from openai import OpenAI
from utils import get_script_paths, get_env, get_project_root

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def remove_tags(text: str) -> str:
    """
    使用正则表达式移除说话人标签和语言标签
    
    移除内容:
    - [S1] / [S2] 说话人标签
    - <|Yue|> 等语言标签
    """
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        
        # 移除 [S1] 或 [S2] 标签
        cleaned = re.sub(r'^\[S[12]\]\s*', '', line)
        # 移除语言标签 <|xxx|>
        cleaned = re.sub(r'<\|[^|]+\|>', '', cleaned)
        cleaned = cleaned.strip()
        
        if cleaned:
            lines.append(cleaned)
    
    return '\n'.join(lines)


def segment_with_deepseek(raw_text: str) -> str:
    """
    调用 DeepSeek API 进行智能断句
    
    Args:
        raw_text: 移除标签后的纯文本
        
    Returns:
        断句后的文本，每行不超过9个字
    """
    # 获取 API 配置
    api_key = get_env("DEEPSEEK_API_KEY")
    base_url = get_env("DEEPSEEK_BASE_URL", "https://maas-api.lanyun.net/v1")
    model_name = get_env("DEEPSEEK_MODEL", "/maas/deepseek-ai/DeepSeek-V3.2")
    
    if not api_key:
        print("❌ 请在 .env 中设置 DEEPSEEK_API_KEY")
        return None
    
    # 读取提示词模板
    prompt_path = get_project_root() / "PROMPTS" / "prompt_podcast_subtitle_format.md"
    if not prompt_path.exists():
        print(f"❌ 找不到提示词文件: {prompt_path}")
        return None
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 填充文案内容
    prompt = prompt_template.replace("{raw_text}", raw_text)
    
    # 调用 API
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        print(f"🤖 正在调用 DeepSeek ({model_name}) 进行智能断句...")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的视频字幕处理专家，严格遵守输出格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            stream=False
        )
        
        result = response.choices[0].message.content.strip()
        
        # 清理可能的代码块标记
        if result.startswith("```"):
            lines = result.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            result = '\n'.join(lines)
        
        return result
        
    except Exception as e:
        print(f"❌ 调用 DeepSeek API 失败: {e}")
        return None


def format_podcast_subtitles(script_id: str, skip_ai: bool = False) -> bool:
    """
    格式化播客字幕
    
    Args:
        script_id: 项目标识符
        skip_ai: 是否跳过 AI 断句（仅使用正则移除标签）
    
    输入: copys/{id}_podcast.txt ([S1]/[S2] 格式)
    输出: copys/{id}_subtitle.txt (纯文本，每行一句)
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
    
    print(f"📄 输入文案字数: {len(podcast_script)}")
    
    # 第一步：正则移除标签
    print("📝 正在移除说话人标签...")
    cleaned_text = remove_tags(podcast_script)
    
    if not cleaned_text:
        print("❌ 未找到有效的对话内容")
        return False
    
    print(f"   - 移除标签后行数: {len(cleaned_text.splitlines())}")
    
    # 第二步：DeepSeek API 智能断句
    if not skip_ai:
        result = segment_with_deepseek(cleaned_text)
        if not result:
            print("⚠️ AI 断句失败，将使用正则处理的结果")
            result = cleaned_text
    else:
        print("⏭️ 跳过 AI 断句，仅使用正则处理")
        result = cleaned_text
    
    # 保存结果
    output_file = paths["copy_subtitle"]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result)
    
    # 统计信息
    lines = [l for l in result.splitlines() if l.strip()]
    line_lengths = [len(l) for l in lines]
    avg_length = sum(line_lengths) / len(line_lengths) if line_lengths else 0
    max_length = max(line_lengths) if line_lengths else 0
    over_9_count = sum(1 for l in line_lengths if l > 9)
    
    print(f"✅ 字幕格式化完成！")
    print(f"   - 输出文件: {output_file}")
    print(f"   - 总行数: {len(lines)}")
    print(f"   - 平均每行: {avg_length:.1f} 字")
    print(f"   - 最长行: {max_length} 字")
    if over_9_count > 0:
        print(f"   ⚠️ 超过9字的行: {over_9_count} 行")
    print()
    print("预览前 5 行：")
    print("-" * 40)
    for line in lines[:5]:
        print(line[:60] + ("..." if len(line) > 60 else ""))
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="播客字幕格式化")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    parser.add_argument("--skip-ai", action="store_true", 
                        help="跳过 AI 断句，仅使用正则移除标签")
    
    args = parser.parse_args()
    success = format_podcast_subtitles(args.script_id, skip_ai=args.skip_ai)
    sys.exit(0 if success else 1)
