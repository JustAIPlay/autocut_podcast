#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path
from utils import run_command, check_env, get_ffmpeg_cmd, get_script_paths

def extract_audio(script_id):
    """根据脚本 ID 从 raw_materials 提取音频"""
    if not check_env():
        return False

    # 使用统一的路径管理
    paths = get_script_paths(script_id)
    video_path = paths["video"]
    audio_path = paths["audio"]
    audio_dir = audio_path.parent

    if not video_path.exists():
        print(f"❌ 找不到原视频: {video_path}")
        return False

    print(f"🚀 正在处理项目: {script_id}")
    print(f"正在从 {video_path} 提取音频...")
    
    # 确保目录存在
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        get_ffmpeg_cmd(), '-i', str(video_path.absolute()),
        '-vn',
        '-acodec', 'libmp3lame',
        '-q:a', '2',
        '-y',
        str(audio_path.absolute())
    ]
    
    if run_command(cmd, "音频提取失败") is not None:
        print(f"✅ 音频提取完成: {audio_path}")
        return True
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract_audio.py <script_id>")
        print("例如: python extract_audio.py AITSmx007685")
        sys.exit(1)
    
    extract_audio(sys.argv[1])