#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
播客视频合成脚本
使用单张封面图 + 播客音频 + 字幕合成最终视频
"""
import sys
import io
import subprocess
import argparse
from pathlib import Path
from utils import (
    run_command, format_ffmpeg_path, check_env, 
    get_ffmpeg_cmd, get_script_paths
)

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# 竖屏视频参数
LAYOUT_WIDTH = 1080
LAYOUT_HEIGHT = 1920
FPS = 30


def get_ffprobe_cmd():
    """获取 ffprobe 命令路径"""
    from utils import get_project_root
    PROJECT_ROOT = get_project_root()
    ffprobe_path = PROJECT_ROOT / "tools" / "ffmpeg" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffprobe.exe"
    return str(ffprobe_path) if ffprobe_path.exists() else "ffprobe"


def get_audio_duration(audio_path):
    """获取音频时长（秒）"""
    cmd = [
        get_ffprobe_cmd(), '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def generate_subtitle_style():
    """生成竖屏视频的字幕样式"""
    return (
        "FontName=Microsoft YaHei UI,"
        "FontSize=20,"
        "PrimaryColour=&H00DDFF,"   # 金黄色 #FFDD00 (BGR格式)
        "OutlineColour=&H000000,"   # 黑色描边
        "Outline=2,"
        "Shadow=0,"                 # 无阴影
        "MarginV=60,"                # 距底部60像素
        "Alignment=2"  # 底部居中
    )


def wrap_text_line(text: str, max_chars_per_line: int = 12) -> str:
    """
    将单条字幕文本按字符数自动换行

    Args:
        text: 原始字幕文本
        max_chars_per_line: 每行最大字符数（默认12，适合竖屏）

    Returns:
        换行后的文本，使用 \\N 作为换行符（ASS/SRT 格式）
    """
    # 统计字符数（中文、英文单词、数字都算字符）
    char_count = 0
    for char in text:
        if '\u4e00' <= char <= '\u9fa5':
            char_count += 1  # 中文
        elif char.isalpha():
            # 英文不单独计数，按空格分词
            pass
        else:
            char_count += 1  # 数字、标点

    if char_count <= max_chars_per_line:
        return text  # 无需换行

    # 需要换行，按字符数均分
    # 简单策略：尽量在标点后换行，否则按字符数切分
    lines = []
    current_line = ""
    current_count = 0

    for char in text:
        current_line += char

        if '\u4e00' <= char <= '\u9fa5':
            current_count += 1
        elif char in '，。！？；：、,!?;:':
            current_count += 1
            # 标点符号后检查是否需要换行
            if current_count >= max_chars_per_line - 2:
                lines.append(current_line)
                current_line = ""
                current_count = 0
        elif char == ' ':
            # 空格后可能是英文单词
            if current_count >= max_chars_per_line:
                lines.append(current_line.rstrip())
                current_line = ""
                current_count = 0
        elif char.isalpha():
            # 英文字母，不增加计数（单词整体计数）
            pass
        else:
            current_count += 0.5

        # 硬性限制：超过最大字符数必须换行
        if current_count >= max_chars_per_line:
            lines.append(current_line)
            current_line = ""
            current_count = 0

    # 添加剩余内容
    if current_line:
        lines.append(current_line)

    # 使用 ASS 格式的换行符 \\N
    return '\\N'.join(lines)


def process_srt_wrapping(srt_path: Path, output_path: Path, max_chars: int = 12) -> None:
    """
    处理 SRT 文件，对长字幕进行换行

    Args:
        srt_path: 原始 SRT 文件路径
        output_path: 输出 SRT 文件路径
        max_chars: 每行最大字符数
    """
    import re

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # SRT 格式：序号 + 时间戳 + 文本 + 空行
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n([^\n]+)\n'

    def replace_subtitle(match):
        index = match.group(1)
        timestamp = match.group(2)
        text = match.group(3)

        # 对文本进行换行处理
        wrapped_text = wrap_text_line(text, max_chars)

        return f"{index}\n{timestamp}\n{wrapped_text}\n"

    new_content = re.sub(pattern, replace_subtitle, content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)


def compose_podcast_video(script_id: str, vertical: bool = True) -> bool:
    """
    合成播客视频
    
    Args:
        script_id: 脚本 ID
        vertical: 是否竖屏 (默认 True，9:16)
    
    输入:
        - images/{id}/cover.jpg (封面图)
        - audios/{id}_podcast.mp3 (播客音频)
        - captions/{id}_final.srt (字幕)
    输出:
        - finals/{id}_final.mp4
    """
    if not check_env():
        return False
    
    paths = get_script_paths(script_id)
    
    # 检查输入文件
    cover_image = paths["cover_image"]
    audio_path = paths["audio_podcast"]
    srt_path = paths["caption_final_srt"]
    output_video = paths["final_video"]
    
    # 如果 cover.jpg 不存在，尝试查找目录下的第一张图片
    if not cover_image.exists():
        images_dir = paths["images_dir"]
        if images_dir.exists():
            for ext in ['jpg', 'jpeg', 'png', 'webp']:
                found = list(images_dir.glob(f"*.{ext}"))
                if found:
                    cover_image = found[0]
                    break
    
    # 验证文件存在
    missing_files = []
    if not cover_image.exists():
        missing_files.append(f"封面图: {cover_image}")
    if not audio_path.exists():
        missing_files.append(f"播客音频: {audio_path}")
    if not srt_path.exists():
        missing_files.append(f"字幕文件: {srt_path}")
    
    if missing_files:
        print("❌ 找不到必要文件:")
        for f in missing_files:
            print(f"   - {f}")
        return False
    
    # 获取音频时长
    audio_duration = get_audio_duration(audio_path)
    print(f"🎙️ 播客音频时长: {audio_duration:.2f} 秒")
    
    # 确保输出目录存在
    output_video.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 正在合成播客视频: {script_id} ...")
    print(f"   📱 视频模式: {'9:16 竖屏' if vertical else '16:9 横屏'}")
    print(f"   🖼️ 封面图: {cover_image}")
    print(f"   🎵 音频: {audio_path}")
    print(f"   📝 字幕: {srt_path}")

    # 处理字幕换行（竖屏视频每行最多9字）
    if vertical:
        wrapped_srt_path = srt_path.parent / f"{srt_path.stem}_wrapped.srt"
        print(f"   🔄 正在处理字幕换行（每行最多9字）...")
        process_srt_wrapping(srt_path, wrapped_srt_path, max_chars=9)
        srt_path = wrapped_srt_path
        print(f"   ✅ 换行处理完成: {wrapped_srt_path.name}")

    # 构建 FFmpeg 命令
    ffmpeg_cmd = get_ffmpeg_cmd()
    
    # 设置视频尺寸
    if vertical:
        width, height = LAYOUT_WIDTH, LAYOUT_HEIGHT
    else:
        width, height = 1920, 1080
    
    # 静态图片缩放到目标尺寸
    scale_filter = f"scale={width}:{height}"
    
    # 字幕滤镜
    srt_path_fixed = format_ffmpeg_path(str(srt_path))
    subtitle_style = generate_subtitle_style()
    subtitle_filter = f"subtitles='{srt_path_fixed}':force_style='{subtitle_style}'"
    
    # 组合滤镜链（封面图已是 9:16，静态展示 + 字幕）
    filter_complex = f"{scale_filter},{subtitle_filter}"
    
    # FFmpeg 命令
    cmd = [
        ffmpeg_cmd,
        '-loop', '1',
        '-i', str(cover_image),
        '-i', str(audio_path),
        '-vf', filter_complex,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        '-pix_fmt', 'yuv420p',
        '-y',
        str(output_video)
    ]
    
    print("\n🎬 正在渲染视频...")
    result = run_command(cmd, "视频合成失败")
    
    if result is not None:
        print(f"\n✅ 播客视频合成成功！")
        print(f"   - 输出文件: {output_video}")
        return True
    else:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="合成播客视频")
    parser.add_argument("script_id", help="脚本 ID")
    parser.add_argument("--vertical", "-v", action="store_true", default=True,
                       help="生成 9:16 竖屏视频（默认）")
    parser.add_argument("--horizontal", "-H", action="store_true",
                       help="生成 16:9 横屏视频")
    
    args = parser.parse_args()
    
    # --horizontal 优先级更高
    vertical = not args.horizontal
    
    success = compose_podcast_video(args.script_id, vertical=vertical)
    sys.exit(0 if success else 1)
