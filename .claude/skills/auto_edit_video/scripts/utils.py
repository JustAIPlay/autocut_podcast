#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的工具函数和配置管理模块
提供项目路径、环境变量加载、FFmpeg 命令等通用功能
"""
import subprocess
import os
import sys
from pathlib import Path
from typing import Optional

# ============= 路径管理 =============
# 从 scripts/ 到项目根目录: scripts -> auto_edit_video -> skills -> .claude -> 2nd_video
# 需要 4 级 parent
_SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent.parent

def get_project_root() -> Path:
    """获取项目根目录（统一路径计算）"""
    return PROJECT_ROOT

def get_raw_materials_dir() -> Path:
    """获取原始素材目录"""
    return PROJECT_ROOT / "raw_materials"

def get_finals_dir() -> Path:
    """获取最终输出目录"""
    return PROJECT_ROOT / "finals"

# ============= 环境变量管理 =============
_ENV_LOADED = False

def load_env():
    """加载 .env 文件（统一配置加载，避免重复加载）"""
    global _ENV_LOADED
    if not _ENV_LOADED:
        try:
            from dotenv import load_dotenv
            env_path = PROJECT_ROOT / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                _ENV_LOADED = True
        except ImportError:
            print("⚠️ 警告: 未安装 python-dotenv，无法加载 .env 文件")

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取环境变量（自动加载 .env）"""
    load_env()
    return os.environ.get(key, default)

# ============= FFmpeg 路径管理 =============
# 优先级：1. 项目本地安装 2. C:\ffmpeg\bin 3. 系统 PATH
FFMPEG_LOCAL_PATH = PROJECT_ROOT / "tools" / "ffmpeg" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe"
FFMPEG_SYSTEM_PATH = Path("C:/ffmpeg/bin/ffmpeg.exe")

if FFMPEG_LOCAL_PATH.exists():
    FFMPEG_CMD = str(FFMPEG_LOCAL_PATH)
elif FFMPEG_SYSTEM_PATH.exists():
    FFMPEG_CMD = str(FFMPEG_SYSTEM_PATH)
else:
    FFMPEG_CMD = "ffmpeg"


# ============= 脚本路径生成 =============
def get_script_paths(script_id: str) -> dict:
    """
    根据 script_id 生成所有相关文件路径（统一路径管理）
    
    Args:
        script_id: 项目标识符
        
    Returns:
        包含所有路径的字典
    """
    raw_dir = get_raw_materials_dir()
    finals_dir = get_finals_dir()
    
    return {
        # 原始视频
        "video": raw_dir / "videos" / f"{script_id}.mp4",
        
        # 音频
        "audio": raw_dir / "audios" / f"{script_id}.mp3",
        "audio_tts": raw_dir / "audios" / f"{script_id}_tts.mp3",  # 二创配音
        "audio_podcast": raw_dir / "audios" / f"{script_id}_podcast.wav",  # 播客音频 (SoulX-Podcast 输出 WAV)
        
        # 文案文本
        "copy_original": raw_dir / "copys" / f"{script_id}_original.txt",  # ASR 原始转录
        "copy_recreated": raw_dir / "copys" / f"{script_id}_recreated.txt",  # 二创文案
        "copy_refined": raw_dir / "copys" / f"{script_id}_refined.txt",  # 断句优化
        "copy_podcast": raw_dir / "copys" / f"{script_id}_podcast.txt",  # 播客二创 ([S1]/[S2] 格式)
        "copy_subtitle": raw_dir / "copys" / f"{script_id}_subtitle.txt",  # 字幕文本 (移除标签)
        
        # 分镜 JSON
        "scenes": raw_dir / "copys" / f"{script_id}_scenes.json",
        "image_prompt": raw_dir / "copys" / f"{script_id}_image_prompt.txt",  # 播客封面图提示词
        
        # 字幕与时间戳
        "word_timestamps": raw_dir / "captions" / f"{script_id}_word_timestamps.json",  # ForcedAligner 输出
        "caption_final_srt": raw_dir / "captions" / f"{script_id}_final.srt",
        
        # 图片目录
        "images_dir": raw_dir / "images" / script_id,
        "cover_image": raw_dir / "images" / script_id / "cover.jpg",  # 播客封面图
        
        # 最终视频
        "final_video": finals_dir / f"{script_id}_final.mp4",
        
        # [已废弃] 保留兼容性
        "copy_whisper": raw_dir / "copys" / f"{script_id}_whisper.txt",
        "caption_whisper_srt": raw_dir / "captions" / f"{script_id}_whisper.srt",
        "caption_whisper_json": raw_dir / "captions" / f"{script_id}_whisper.json",
        "caption_refined_json": raw_dir / "captions" / f"{script_id}_refined.json",
    }

# ============= 命令执行工具 =============
def run_command(cmd, error_msg="命令执行失败"):
    """通用的命令行执行工具"""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=False)
        # 使用 UTF-8 解码，忽略无法解码的字符
        stdout = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
        return stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {error_msg}")
        # 安全地解码错误信息
        stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "无错误信息"
        print(f"错误详情: {stderr}")
        return None

# ============= FFmpeg 工具 =============
def format_ffmpeg_path(path):
    """处理 Windows 下 FFmpeg 滤镜路径的特殊转义"""
    abs_path = str(Path(path).absolute()).replace("\\", "/")
    if ":" in abs_path:
        abs_path = abs_path.replace(":", "\\:")
    return abs_path

def get_ffmpeg_cmd():
    """获取 FFmpeg 命令路径（优先使用本地安装）"""
    if FFMPEG_LOCAL_PATH.exists():
        return str(FFMPEG_LOCAL_PATH)
    return "ffmpeg"

def check_env():
    """检查必要的工具是否安装"""
    ffmpeg_cmd = get_ffmpeg_cmd()
    if not run_command([ffmpeg_cmd, '-version'], "未检测到 FFmpeg"):
        print(f"请先安装 FFmpeg 到: {FFMPEG_LOCAL_PATH}")
        print("或运行: python tools/download_ffmpeg.py")
        return False
    return True