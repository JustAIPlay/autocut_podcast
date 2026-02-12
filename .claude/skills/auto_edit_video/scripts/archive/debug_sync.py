#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
from utils import run_command, format_ffmpeg_path, get_ffmpeg_cmd

def create_debug_video(script_id, suffix=""):
    """
    创建一个纯黑背景视频，烧录字幕和音频，用于检查同步性。
    suffix: 字幕文件后缀，如 "whisper"
    """
    base_dir = Path(__file__).parent.parent.parent.parent.parent
    audio_path = base_dir / "raw_materials" / "audios" / f"{script_id}.mp3"
    
    # 根据后缀决定字幕路径
    srt_name = f"{script_id}_{suffix}.srt" if suffix else f"{script_id}.srt"
    srt_path = base_dir / "raw_materials" / "captions" / srt_name
    
    output_name = f"{script_id}_{suffix}_debug_sync.mp4" if suffix else f"{script_id}_debug_sync.mp4"
    output_path = base_dir / "finals" / output_name

    if not audio_path.exists() or not srt_path.exists():
        print(f"❌ 找不到文件:\n音频: {audio_path}\n字幕: {srt_path}")
        return

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"🚀 正在生成同步检查视频: {script_id} ...")
    
    # 转换字幕路径格式以兼容 Windows FFmpeg
    srt_path_fixed = format_ffmpeg_path(str(srt_path.absolute()))

    # FFmpeg 命令解释：
    # -f lavfi -i color=c=black:s=1280x720:r=30  -> 生成 720p 30fps 的纯黑背景
    # -i audio_path                             -> 输入音频
    # -vf "subtitles=..."                       -> 烧录字幕
    # -c:a copy                                 -> 音频流直接复制（保持原始时间戳）
    # -shortest                                 -> 在音频结束时停止视频
    cmd = [
        get_ffmpeg_cmd(),
        '-f', 'lavfi', '-i', 'color=c=black:s=1280x720:r=30',
        '-i', str(audio_path.absolute()),
        '-vf', f"subtitles='{srt_path_fixed}':force_style='FontSize=24,PrimaryColour=&H00FFFF'",
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-shortest',
        '-y', str(output_path.absolute())
    ]

    if run_command(cmd, "同步检查视频生成失败") is not None:
        print(f"\n✅ 生成成功！请查看：\n{output_path}")
        print("\n检查要点：")
        print("1. 听声音开始时，第一句字幕是否准时出现。")
        print("2. 观察视频中后段，字幕是否逐渐变快或变慢。")
        print("3. 如果这个视频是对的，说明问题出在 compose_video.py 的图片拼接逻辑。")
        print("4. 如果这个视频就不对，说明 funasr 提取的时间轴有问题。")

if __name__ == "__main__":
    import sys
    sid = sys.argv[1] if len(sys.argv) > 1 else "AITSmx000087"
    suf = sys.argv[2] if len(sys.argv) > 2 else ""
    create_debug_video(sid, suf)