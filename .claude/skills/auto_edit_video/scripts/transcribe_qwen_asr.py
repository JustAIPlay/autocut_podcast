#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-ASR 语音转录脚本
使用 Qwen3-ASR-1.7B 模型进行语音识别，提取原视频文案
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

# 尝试导入 Qwen3-ASR
try:
    from qwen_asr import Qwen3ASRModel as QwenASR
    HAS_QWEN_ASR = True
except ImportError:
    HAS_QWEN_ASR = False
    print("⚠️ 警告: 未安装 qwen-asr，请运行: pip install qwen-asr")


def transcribe_with_qwen_asr(audio_path: str, output_path: str) -> dict:
    """
    使用 Qwen3-ASR-1.7B 进行语音转录
    
    Args:
        audio_path: 音频文件路径
        output_path: 输出文本路径
        
    Returns:
        包含转录结果的字典
    """
    if not HAS_QWEN_ASR:
        print("❌ qwen-asr 未安装，无法进行转录")
        return None
    
    print(f"🎙️ 正在使用 Qwen3-ASR-1.7B 进行转录...")
    print(f"📂 音频文件: {audio_path}")
    
    try:
        # 初始化 ASR 模型 (使用 Transformers 后端 + GPU 优化)
        import torch
        asr = QwenASR.from_pretrained(
            "Qwen/Qwen3-ASR-1.7B",
            max_new_tokens=4096,  # 增加到 4096 以支持长音频
            torch_dtype=torch.float16,  # 使用 float16 减少 GPU 内存占用
            device_map="auto"  # 自动使用 GPU
        )

        # 验证设备
        device = asr.model.device if hasattr(asr, 'model') else "unknown"
        print(f"🔧 模型设备: {device} (使用 GPU 加速模式)")

        # 进行转录
        results = asr.transcribe(audio_path)

        # 提取文本 (results 是列表，取第一个结果)
        full_text = results[0].text if results else ""
        
        # 保存转录结果
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        print(f"✅ 转录完成！")
        print(f"📝 输出文件: {output_path}")
        print(f"📊 文案字数: {len(full_text)}")
        print("-" * 40)
        print("预览前200字：")
        print(full_text[:200] + "..." if len(full_text) > 200 else full_text)
        
        return {
            "text": full_text,
            "char_count": len(full_text),
            "output_path": str(output_path)
        }
        
    except Exception as e:
        print(f"❌ 转录失败: {e}")
        return None


def transcribe(script_id: str) -> bool:
    """
    根据 script_id 进行音频转录
    
    Args:
        script_id: 项目标识符
        
    Returns:
        是否成功
    """
    paths = get_script_paths(script_id)
    
    # 输入：音频文件
    audio_path = paths["audio"]
    
    # 输出：原始文案
    output_path = paths["copy_original"]
    
    # 检查音频文件是否存在
    if not audio_path.exists():
        print(f"❌ 找不到音频文件: {audio_path}")
        print(f"💡 请先运行 extract_audio.py 提取音频")
        return False
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 执行转录
    result = transcribe_with_qwen_asr(str(audio_path), str(output_path))
    
    return result is not None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 Qwen3-ASR 进行语音转录")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    
    args = parser.parse_args()
    
    success = transcribe(args.script_id)
    sys.exit(0 if success else 1)
