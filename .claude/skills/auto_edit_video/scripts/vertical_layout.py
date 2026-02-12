#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9:16 竖屏视频布局处理模块

功能：
- 生成 9:16 比例竖屏视频布局滤镜（1080x1920）
- 添加固定文案（标题、免责声明）- 从配置文件读取书籍信息
- 配置字幕样式（黄色、粗体、大字号）
- 图片保持4:3原始比例，居中放置
- 布局比例：上28.9% + 中42.2% (4:3图片) + 下28.9%
"""

import sys
import io
import json
from pathlib import Path

# 设置 UTF-8 输出（只在需要时设置）
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ================== 布局配置 ==================

# 画布尺寸（9:16 比例）
LAYOUT_WIDTH = 1080
LAYOUT_HEIGHT = 1920         # 1080 * 16 / 9 = 1920

# 区域高度（图片保持4:3原始比例，居中放置）
TOP_AREA_HEIGHT = 555        # 上方黑边区域
IMAGE_HEIGHT = 810           # 图片区域 (1080 * 3 / 4 = 810，保持4:3比例)
BOTTOM_AREA_HEIGHT = 555     # 下方黑边区域（与上方对称）

# Y 坐标
TOP_TITLE_Y = 200            # 主标题：上方区域居中偏上
TOP_SUBTITLE_Y = 350         # 副标题：上方区域居中偏下
IMAGE_TOP_Y = TOP_AREA_HEIGHT
IMAGE_BOTTOM_Y = TOP_AREA_HEIGHT + IMAGE_HEIGHT  # = 1365px
DISCLAIMER_LINE1_Y = 1550    # 图片下方留约185px + 第1行（字号20px）
DISCLAIMER_LINE2_Y = 1580    # 第2行（间隔30px）
DISCLAIMER_LINE3_Y = 1610    # 第3行（间隔30px）

# 字幕配置（使用绝对Y坐标定位）
SUBTITLE_FONTSIZE = 12       # 字幕字号
SUBTITLE_Y = 1855            # 字幕底部的Y坐标（MarginV=65时的位置）
SUBTITLE_MARGIN = LAYOUT_HEIGHT - SUBTITLE_Y  # 自动计算MarginV = 1920-1855 = 65
SUBTITLE_ALIGNMENT = 2       # 底部居中对齐
SUBTITLE_BOLD = 1            # 字幕加粗

# ================== 固定文案（默认值，可通过配置文件覆盖）==================

# 默认配置（当找不到配置文件或匹配失败时使用）
TOP_TITLE = "《身体重置》"
TOP_SUBTITLE = "50+人群逆龄健康法则"

DISCLAIMER_LINES = [
    "本视频基于<<身体重置>>及相关研究资料整理。",
    "仅用于科普分享，不构成任何建议或行为引导。",
    "如需具体诊断或干预，请根据自身情况线下专业咨询。"
]

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "video_text_config.json"

# ================== 字体配置 ==================

# Windows 字体路径
FONT_HEAVY = "C\\:/Windows/Fonts/SourceHanSansSC-Heavy.otf"  # 思源黑体 Heavy（主标题）
FONT_BOLD = "C\\:/Windows/Fonts/SourceHanSansSC-Bold.otf"    # 思源黑体 Bold（副标题）
FONT_REGULAR = "C\\:/Windows/Fonts/msyh.ttc"                 # 微软雅黑（免责声明）

# 字幕字体名称（用于 ASS/SRT 样式）
SUBTITLE_FONT = "KaiTi"  # 楷体

# ================== 颜色配置 ==================

COLOR_GOLD = "0xFFD700"  # 金黄色 (drawtext 格式)
COLOR_WHITE = "white"     # 白色

# ASS 字幕颜色（BGR 顺序）
SUBTITLE_COLOR_ASS = "&H0000D7FF"  # #FFD700 转换为 BGR


def load_book_config(book_name):
    """
    从配置文件加载书籍配置
    
    Args:
        book_name: 书名（用于匹配配置），比如："身体重置"
    
    Returns:
        配置字典，包含 main_title, sub_title, disclaimer
        如果找不到匹配，返回 None
    """
    if not CONFIG_FILE.exists():
        print(f"⚠️ 配置文件不存在: {CONFIG_FILE}")
        return None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 遍历所有书籍配置，按书名匹配
        for book in config.get('books', []):
            if book.get('book_name') == book_name:
                return {
                    'main_title': book.get('main_title', TOP_TITLE),
                    'sub_title': book.get('sub_title', TOP_SUBTITLE),
                    'disclaimer': book.get('disclaimer', DISCLAIMER_LINES)
                }
        
        print(f"⚠️ 未找到书籍配置: '{book_name}'，使用默认配置")
        return None
    
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None


def escape_text_for_ffmpeg(text):
    """
    转义文本用于 FFmpeg drawtext
    
    Args:
        text: 原始文本
    
    Returns:
        转义后的文本
    """
    # FFmpeg drawtext 需要转义的字符
    text = text.replace("'", "\\'")  # 单引号
    text = text.replace(":", "\\:")  # 冒号
    text = text.replace("\\", "\\\\")  # 反斜杠
    return text


def generate_drawtext_filter(text, fontfile, fontsize, fontcolor, x, y):
    """
    生成单个 drawtext 滤镜
    
    Args:
        text: 显示的文本
        fontfile: 字体文件路径
        fontsize: 字体大小
        fontcolor: 字体颜色
        x: X 坐标表达式
        y: Y 坐标
    
    Returns:
        drawtext 滤镜字符串
    """
    escaped_text = escape_text_for_ffmpeg(text)
    return f"drawtext=text='{escaped_text}':fontfile='{fontfile}':fontsize={fontsize}:fontcolor={fontcolor}:x={x}:y={y}"


def generate_vertical_layout_filter(book_name=None):
    """
    生成 9:16 竖屏布局的完整滤镜链（不包括字幕）
    
    Args:
        book_name: 书名（可选），用于从配置文件加载对应的文案
    
    返回滤镜数组，每个元素是一个滤镜字符串
    """
    # 加载书籍配置（如果提供了书名）
    if book_name:
        book_config = load_book_config(book_name)
        if book_config:
            main_title = book_config['main_title']
            sub_title = book_config['sub_title']
            disclaimer_lines = book_config['disclaimer']
            print(f"✅ 已加载书籍配置: {book_name}")
        else:
            main_title = TOP_TITLE
            sub_title = TOP_SUBTITLE
            disclaimer_lines = DISCLAIMER_LINES
    else:
        main_title = TOP_TITLE
        sub_title = TOP_SUBTITLE
        disclaimer_lines = DISCLAIMER_LINES
    
    filters = []
    
    # 1. 缩放图片到 1080x810 (保持4:3原始比例)
    filters.append(f"scale={LAYOUT_WIDTH}:{IMAGE_HEIGHT}")
    
    # 2. 添加上下黑边 (上555 + 图810 + 下555 = 1920，图片居中)
    filters.append(f"pad={LAYOUT_WIDTH}:{LAYOUT_HEIGHT}:0:{TOP_AREA_HEIGHT}:black")
    
    # 3. 添加上方主标题（金黄色，思源黑体 Heavy，128px）
    filters.append(generate_drawtext_filter(
        text=main_title,
        fontfile=FONT_HEAVY,
        fontsize=128,
        fontcolor=COLOR_GOLD,
        x="(w-text_w)/2",  # 居中
        y=TOP_TITLE_Y
    ))
    
    # 4. 添加上方副标题（白色，思源黑体 Bold，80px）
    filters.append(generate_drawtext_filter(
        text=sub_title,
        fontfile=FONT_BOLD,
        fontsize=80,
        fontcolor=COLOR_WHITE,
        x="(w-text_w)/2",
        y=TOP_SUBTITLE_Y
    ))
    
    # 5. 添加免责声明第1行（白色，微软雅黑，20px）
    filters.append(generate_drawtext_filter(
        text=disclaimer_lines[0],
        fontfile=FONT_REGULAR,
        fontsize=20,
        fontcolor=COLOR_WHITE,
        x="(w-text_w)/2",
        y=DISCLAIMER_LINE1_Y
    ))
    
    # 6. 添加免责声明第2行（白色，微软雅黑，20px）
    filters.append(generate_drawtext_filter(
        text=disclaimer_lines[1],
        fontfile=FONT_REGULAR,
        fontsize=20,
        fontcolor=COLOR_WHITE,
        x="(w-text_w)/2",
        y=DISCLAIMER_LINE2_Y
    ))
    
    # 7. 添加免责声明第3行（白色，微软雅黑，20px）
    filters.append(generate_drawtext_filter(
        text=disclaimer_lines[2],
        fontfile=FONT_REGULAR,
        fontsize=20,
        fontcolor=COLOR_WHITE,
        x="(w-text_w)/2",
        y=DISCLAIMER_LINE3_Y
    ))
    
    return filters


def generate_subtitle_style():
    """
    生成字幕样式配置（用于 FFmpeg subtitles 滤镜）
    
    Returns:
        字幕样式字符串
    """
    style_params = [
        f"FontName={SUBTITLE_FONT}",
        f"Fontsize={SUBTITLE_FONTSIZE}",
        f"PrimaryColour={SUBTITLE_COLOR_ASS}",
        f"MarginV={SUBTITLE_MARGIN}",
        f"Alignment={SUBTITLE_ALIGNMENT}",
        "Bold=1"  # 粗体
    ]
    return ",".join(style_params)


def generate_vertical_video_filter_chain(srt_path=None, include_subtitles=True):
    """
    生成完整的竖屏视频滤镜链（包括字幕）
    
    Args:
        srt_path: SRT 字幕文件路径（如果需要添加字幕）
        include_subtitles: 是否包含字幕滤镜
    
    Returns:
        完整的滤镜链字符串
    """
    filters = generate_vertical_layout_filter()
    
    # 如果需要添加字幕
    if include_subtitles and srt_path:
        from utils import format_ffmpeg_path
        srt_path_fixed = format_ffmpeg_path(str(srt_path))
        subtitle_style = generate_subtitle_style()
        filters.append(f"subtitles='{srt_path_fixed}':force_style='{subtitle_style}'")
    
    return ",".join(filters)


def generate_vertical_zoompan_filter(effect, duration, fps=30):
    """
    生成 9:16 竖屏视频的 zoompan 滤镜（用于视频片段生成阶段）
    
    这个滤镜用于在生成视频片段时应用动效
    注意：输出分辨率设置为 1080x810（图片区域，保持4:3比例），后续会用 pad 添加黑边
    
    Args:
        effect: 动效配置字典
        duration: 持续时间（秒）
        fps: 帧率
    
    Returns:
        zoompan 滤镜字符串
    """
    frames = int(duration * fps)
    effect_type = effect.get('type', 'zoom_in')
    zoom_start = effect.get('zoom_start', 1.0)
    zoom_end = effect.get('zoom_end', 1.3)
    
    # 计算缩放速度（每帧的缩放变化量）
    zoom_speed = (zoom_end - zoom_start) / frames
    
    if effect_type == 'zoom_in':
        # 渐进放大
        zoom_expr = f"'min(zoom+{abs(zoom_speed)},{zoom_end})'"
        x_expr = "'iw/2-(iw/zoom/2)'"
        y_expr = "'ih/2-(ih/zoom/2)'"
    elif effect_type == 'zoom_out':
        # 渐进缩小
        zoom_expr = f"'if(lte(zoom,{zoom_end}),{zoom_start},max({zoom_end},zoom-{abs(zoom_speed)}))'"
        x_expr = "'iw/2-(iw/zoom/2)'"
        y_expr = "'ih/2-(ih/zoom/2)'"
    elif effect_type == 'pan_right':
        # 向右平移 + 轻微缩放
        zoom_expr = f"'{zoom_start}'"
        x_expr = "'iw/2-(iw/zoom/2)+on*2'"
        y_expr = "'ih/2-(ih/zoom/2)'"
    elif effect_type == 'pan_left':
        # 向左平移 + 轻微缩放
        zoom_expr = f"'{zoom_start}'"
        x_expr = "'iw/2-(iw/zoom/2)-on*2'"
        y_expr = "'ih/2-(ih/zoom/2)'"
    else:
        # 默认：轻微放大
        zoom_expr = f"'min(zoom+0.0015,1.2)'"
        x_expr = "'iw/2-(iw/zoom/2)'"
        y_expr = "'ih/2-(ih/zoom/2)'"
    
    # 输出分辨率：1080x810（图片区域，保持4:3原始比例）
    zoompan = f"zoompan=z={zoom_expr}:x={x_expr}:y={y_expr}:d={frames}:s={LAYOUT_WIDTH}x{IMAGE_HEIGHT}:fps={fps}"
    
    return zoompan


def print_layout_info():
    """打印布局配置信息（用于调试）"""
    print("=" * 60)
    print("9:16 竖屏视频布局配置")
    print("=" * 60)
    print(f"画布尺寸: {LAYOUT_WIDTH}x{LAYOUT_HEIGHT} (9:16 比例)")
    print(f"上方区域高度: {TOP_AREA_HEIGHT}px (28.9%)")
    print(f"图片区域高度: {IMAGE_HEIGHT}px (42.2%, {LAYOUT_WIDTH}x{IMAGE_HEIGHT}, 保持4:3原始比例)")
    print(f"下方区域高度: {BOTTOM_AREA_HEIGHT}px (28.9%)")
    print()
    print("固定文案:")
    print(f"  主标题: {TOP_TITLE}")
    print(f"  副标题: {TOP_SUBTITLE}")
    print(f"  免责声明: {len(DISCLAIMER_LINES)} 行")
    print()
    print("字幕配置:")
    print(f"  字体: {SUBTITLE_FONT}")
    print(f"  字号: {SUBTITLE_FONTSIZE}px")
    print(f"  颜色: 金黄色 ({SUBTITLE_COLOR_ASS})")
    print(f"  位置: Y={SUBTITLE_Y}px (字幕底部的绝对Y坐标)")
    print(f"  MarginV: {SUBTITLE_MARGIN}px (自动计算: {LAYOUT_HEIGHT}-{SUBTITLE_Y})")
    print("=" * 60)


if __name__ == "__main__":
    # 测试：打印配置信息
    print_layout_info()
    print()
    
    # 测试：生成滤镜链
    print("生成的滤镜链（不含字幕）:")
    filters = generate_vertical_layout_filter()
    for i, f in enumerate(filters, 1):
        print(f"{i}. {f}")
    print()
    
    # 测试：生成字幕样式
    print("字幕样式:")
    print(generate_subtitle_style())
