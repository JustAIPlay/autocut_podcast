#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
from pathlib import Path
from utils import get_env, get_project_root, get_script_paths

try:
    import requests
except ImportError:
    print("请先安装 requests: pip install requests")
    sys.exit(1)

def clean_json_content(content: str) -> str:
    """清理 Gemini 输出的 JSON，修复常见格式问题"""
    import re

    # 移除 markdown 代码块标记
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    content = content.strip()

    # 修复中文引号问题（将中文引号替换为英文引号）
    content = content.replace('"', '"').replace('"', '"')

    # 修复常见的未转义引号问题
    # 匹配 JSON 字符串值中的未转义双引号并转义
    # 这里处理 prompt 字段中包含引号的情况
    def escape_quotes_in_strings(match):
        s = match.group(0)
        # 在字符串内部的引号前添加转义符
        # 简单处理：将 "健康标准" 这类模式改为 \"健康标准\"
        # 但要保留 JSON 结构的引号
        return s

    # 尝试直接解析，失败则进行修复
    return content

def analyze_scenes(script_id):
    """使用 Gemini REST API 分析文案并生成分镜（支持系统代理）"""
    # 使用统一的环境变量管理
    api_key = get_env("GEMINI_API_KEY")
    if not api_key:
        print("❌ 请在 .env 中设置 GEMINI_API_KEY")
        return False

    # 使用统一的路径管理
    paths = get_script_paths(script_id)
    transcript_path = paths["copy_refined"]

    if not transcript_path.exists():
        print(f"❌ 找不到文案文件: {transcript_path}")
        return False

    # 优先级：.env 中的 GEMINI_MODEL > 默认值
    model_name = get_env("GEMINI_MODEL", "gemini-2.0-pro-exp-02-05")
    print(f"🤖 使用模型: {model_name}")

    with open(transcript_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 从 PROMPTS 目录读取旧版提示词（已弃用，建议使用 analyze_scenes.py）
    prompt_path = get_project_root() / "PROMPTS" / "scene_split_and_prompts_legacy.md"
    if not prompt_path.exists():
        print(f"❌ 找不到提示词文件: {prompt_path}")
        print(f"💡 提示：建议使用新脚本 analyze_scenes.py 替代本脚本")
        return False

    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    # 填充文案内容
    prompt = prompt_template.replace("{text}", text)

    print(f"🚀 正在为项目 {script_id} 请求 Gemini 分析分镜 (使用 REST API)...")

    # 使用 REST API 调用（requests 会自动使用系统代理设置）
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 16384
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()

        # 解析响应
        if "candidates" not in result or not result["candidates"]:
            print("❌ Gemini 返回空响应")
            print("原始响应:", json.dumps(result, ensure_ascii=False, indent=2))
            return False

        content = result["candidates"][0]["content"]["parts"][0]["text"]

        # 清理内容
        content = clean_json_content(content)

        scenes = json.loads(content)

        output_path = paths["scenes"]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)

        print(f"✅ 分镜分析完成: {output_path}")
        print(f"   共 {len(scenes)} 个分镜")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求 Gemini API 失败: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 解析 JSON 失败: {e}")
        print(f"错误位置: line {e.lineno}, column {e.colno}")
        print("\n原始输出（前 500 字符）:")
        print(content[:500] if len(content) > 500 else content)
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_gemini.py <script_id>")
        sys.exit(1)

    analyze_scenes(sys.argv[1])
