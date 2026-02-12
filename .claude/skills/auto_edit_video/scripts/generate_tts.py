#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-TTS 配音脚本
使用 Qwen3-TTS 模型生成二创音频
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

# 尝试导入 Qwen3-TTS
try:
    from qwen_tts import QwenTTS
    HAS_QWEN_TTS = True
except ImportError:
    HAS_QWEN_TTS = False
    print("⚠️ 警告: 未安装 qwen-tts，请运行: pip install qwen-tts")


def generate_tts(script_id: str) -> bool:
    """
    使用 Qwen3-TTS 生成配音
    
    Args:
        script_id: 项目标识符
        
    Returns:
        是否成功
    """
    if not HAS_QWEN_TTS:
        print("❌ qwen-tts 未安装，无法生成配音")
        return False
    
    paths = get_script_paths(script_id)
    
    # 输入：二创文案
    input_path = paths["copy_recreated"]
    
    # 输出：二创音频
    output_path = paths["audio_tts"]
    
    # 检查输入文件
    if not input_path.exists():
        print(f"❌ 找不到二创文案: {input_path}")
        print(f"💡 请先运行 recreate_copy.py 进行文案二创")
        return False
    
    # 读取二创文案
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"🔊 正在使用 Qwen3-TTS 生成配音...")
    print(f"📄 输入文案: {input_path}")
    print(f"📊 文案字数: {len(text)}")
    
    # 从环境变量读取 TTS 配置
    voice = get_env("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    speed = float(get_env("TTS_SPEED", "1.0"))
    emotion = get_env("TTS_EMOTION", "gentle")
    
    print(f"🎤 音色: {voice}")
    print(f"⏱️ 语速: {speed}")
    print(f"😊 情感: {emotion}")
    
    try:
        # 初始化 TTS 模型
        tts = QwenTTS(
            model_name="Qwen/Qwen3-TTS",
            device="cuda"  # 本地 GPU 部署
        )
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成音频
        tts.synthesize(
            text=text,
            output_path=str(output_path),
            voice=voice,
            speed=speed,
            emotion=emotion
        )
        
        # 获取音频时长
        try:
            import soundfile as sf
            audio_data, sample_rate = sf.read(str(output_path))
            duration = len(audio_data) / sample_rate
        except:
            duration = 0
        
        print(f"✅ 配音生成完成！")
        print(f"🎵 输出文件: {output_path}")
        if duration > 0:
            print(f"⏱️ 音频时长: {duration:.1f} 秒")
        
        return True
        
    except Exception as e:
        print(f"❌ TTS 生成失败: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 Qwen3-TTS 生成配音")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    
    args = parser.parse_args()
    
    success = generate_tts(args.script_id)
    sys.exit(0 if success else 1)
