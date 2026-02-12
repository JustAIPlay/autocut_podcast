#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
import subprocess
import shutil
import argparse
from pathlib import Path
from utils import run_command, format_ffmpeg_path, check_env, get_ffmpeg_cmd, get_project_root, get_script_paths
from vertical_layout import (
    generate_vertical_layout_filter,
    generate_vertical_zoompan_filter,
    generate_subtitle_style,
    LAYOUT_WIDTH,
    LAYOUT_HEIGHT,
    IMAGE_HEIGHT
)
from desensitize_subtitles import desensitize_srt, print_report

def get_ffprobe_cmd():
    """获取 ffprobe 命令路径（优先使用本地安装）"""
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

def generate_zoompan_filter(effect, duration, fps=30):
    """
    根据动效配置生成 FFmpeg zoompan 滤镜字符串
    
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
        x_expr = "'iw/2-(iw/zoom/2)+on*2'"  # on 是帧数，乘以速度系数
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
    
    # 构建 zoompan 滤镜
    # s=1920x1080 是输出分辨率，可以根据需要调整
    zoompan = f"zoompan=z={zoom_expr}:x={x_expr}:y={y_expr}:d={frames}:s=1920x1080:fps={fps}"
    
    return zoompan

def compose_video(script_id, vertical=False, book_name=None):
    """
    根据脚本 ID 合成最终视频
    
    Args:
        script_id: 脚本 ID
        vertical: 是否生成 9:16 竖屏视频（默认 False 生成 16:9 横屏）
        book_name: 书名（可选），用于从配置文件匹配并加载对应的文案，如："身体重置"
    """
    if not check_env():
        return False
    
    mode_text = "9:16 竖屏" if vertical else "16:9 横屏"
    print(f"📱 视频模式: {mode_text}")

    # 使用统一的路径管理
    paths = get_script_paths(script_id)
    scenes_json = paths["scenes"]
    captions_json = paths["word_timestamps"]  # 使用 ForcedAligner 生成的词级时间戳
    audio_path = paths["audio_tts"]  # 使用 TTS 生成的二创音频
    srt_path = paths["caption_final_srt"]  # 最终优化字幕
    output_video = paths["final_video"]
    finals_dir = output_video.parent
    concat_file = srt_path.parent / f"{script_id}_concat.txt"
    
    # 如果 TTS 音频不存在，回退到原始音频
    if not audio_path.exists():
        audio_path = paths["audio"]
        print(f"⚠️ TTS 音频不存在，使用原始音频: {audio_path}")

    if not scenes_json.exists() or not audio_path.exists() or not captions_json.exists():
        print(f"❌ 找不到必要文件:")
        print(f"   - scenes.json: {'✅' if scenes_json.exists() else '❌'} {scenes_json}")
        print(f"   - word_timestamps.json: {'✅' if captions_json.exists() else '❌'} {captions_json}")
        print(f"   - audio: {'✅' if audio_path.exists() else '❌'} {audio_path}")
        return False

    # 确保输出目录存在
    finals_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 正在合成项目: {script_id} ...")
    
    # 1. 准备数据
    with open(scenes_json, 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)
    
    # 兼容新旧格式
    if isinstance(scenes_data, dict) and "scenes" in scenes_data:
        # 新格式：包含 metadata
        scenes = scenes_data["scenes"]
        metadata = scenes_data.get("metadata", {})
        # 优先使用 scenes.json 中的书名，如果没有则使用参数传入的书名
        if not book_name:
            book_name = metadata.get("book_name")
        print(f"📖 书名: {book_name if book_name else '未指定（使用默认配置）'}")
    else:
        # 旧格式：纯数组
        scenes = scenes_data
    
    with open(captions_json, 'r', encoding='utf-8') as f:
        caption_data = json.load(f)
        segments = caption_data.get('segments', [])

    # 2. 计算每一镜的时长 (音画对齐核心逻辑)
    # 使用基于字符位置累计的匹配算法，比子串匹配更稳健
    
    # 辅助函数：标准化文本（去除标点和空格）以便匹配
    def normalize(text):
        return "".join(c for c in text if c.isalnum())

    # 全局时间偏移修正 (秒)，如果声音比画面快，设为正值；反之设为负值
    GLOBAL_OFFSET = 0.0
    FPS = 30 # 提高帧率以获得更精细的时间控制

    # 2. 核心逻辑：建立字幕片段与分镜图片的映射
    # 使用字符位置累计法：每个 scene 覆盖一定的字符范围
    has_written_file = False
    
    # 建立分镜文本到图片的快速索引，并计算字符范围
    scene_ranges = []  # [(start_char, end_char, img_path, scene_idx), ...]
    total_scene_chars = 0
    
    for idx, s in enumerate(scenes):
        img_path = Path(s['image_path'])
        if not img_path.exists():
            # 尝试旧的命名规则（兼容性处理）
            alt_path_1 = img_path.parent / img_path.name.replace('_0.png', '.png')
            if alt_path_1.exists():
                img_path = alt_path_1
            else:
                # 尝试 scene_xxx_0.png 格式
                scene_num = s['scene']
                alt_path_2 = img_path.parent / f"scene_{scene_num:03d}_0.png"
                if alt_path_2.exists():
                    img_path = alt_path_2
        
        scene_text = normalize(s['text'])
        char_count = len(scene_text)
        scene_ranges.append({
            'start_char': total_scene_chars,
            'end_char': total_scene_chars + char_count,
            'img_path': img_path.absolute().as_posix(),
            'scene_idx': idx
        })
        total_scene_chars += char_count

    # 计算 segments 的字符累计位置
    segment_char_positions = []  # 每个 segment 的起始字符位置
    current_char_pos = 0
    for seg in segments:
        seg_text = normalize(seg['text'])
        segment_char_positions.append({
            'start_char': current_char_pos,
            'end_char': current_char_pos + len(seg_text),
            'mid_char': current_char_pos + len(seg_text) // 2
        })
        current_char_pos += len(seg_text)
    
    # 计算缩放比例（因为 scene 和 segment 的总字符数可能不同）
    total_segment_chars = current_char_pos
    scale_ratio = total_scene_chars / total_segment_chars if total_segment_chars > 0 else 1.0
    
    print(f"📊 匹配统计: {len(scenes)} 个场景, {len(segments)} 个片段")
    print(f"   场景总字符: {total_scene_chars}, 片段总字符: {total_segment_chars}, 缩放比例: {scale_ratio:.3f}")

    # 预先获取一个兜底路径
    default_img = scene_ranges[0]['img_path'] if scene_ranges else ""
    
    # 根据字符位置找到对应的 scene
    def find_scene_for_segment(seg_idx):
        if seg_idx >= len(segment_char_positions):
            return default_img
        
        # 使用 segment 的中点位置来决定属于哪个 scene
        seg_mid_char = segment_char_positions[seg_idx]['mid_char']
        # 缩放到 scene 的字符范围
        scaled_pos = seg_mid_char * scale_ratio
        
        # 找到对应的 scene
        for sr in scene_ranges:
            if sr['start_char'] <= scaled_pos < sr['end_char']:
                return sr['img_path']
        
        # 如果超出范围，返回最后一个 scene
        return scene_ranges[-1]['img_path'] if scene_ranges else default_img
    
    # 遍历原始字幕片段，为每个片段分配对应的分镜图
    current_video_time = 0.0 # 记录已生成的视频精确时长（基于帧数）
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        # 写入文件头注释，方便调试
        f.write(f"# FPS: {FPS}\n")

        for i, seg in enumerate(segments):
            # 目标时间点（加上偏移）
            target_start = seg['start'] + GLOBAL_OFFSET
            target_end = seg['end'] + GLOBAL_OFFSET
            
            # 使用新算法找到最匹配的分镜图
            img_path = find_scene_for_segment(i)

            if not img_path:
                print(f"⚠️ 警告: 无法找到图片，跳过片段: {seg['text']}")
                continue

            # --- 帧对齐核心算法 ---
            
            # 1. 处理空隙 (Gap)
            # 只有当目标开始时间明显晚于当前视频时间（超过1帧）时才补黑/补图
            if target_start > current_video_time + (1.0/FPS):
                gap_duration = target_start - current_video_time
                # 量化空隙时长
                gap_frames = round(gap_duration * FPS)
                gap_final = gap_frames / FPS
                
                if gap_final > 0:
                    if has_written_file:
                        f.write(f"duration {gap_final:.3f}\n")
                    else:
                        # 开头空隙，用第一张图填补
                        f.write(f"file '{img_path}'\n")
                        f.write(f"duration {gap_final:.3f}\n")
                    
                    current_video_time += gap_final

            # 2. 计算当前图片应该持续到什么时间点
            # 默认是当前句子的结束时间
            segment_target_end = target_end
            
            # 检查下一句是否重叠
            if i < len(segments) - 1:
                next_start = segments[i+1]['start'] + GLOBAL_OFFSET
                if next_start < segment_target_end:
                    segment_target_end = next_start
            
            # 3. 计算本片段需要的时长 (目标结束时间 - 当前已生成时间)
            # 这样每次计算都是基于绝对时间轴，误差不会累积！
            needed_duration = segment_target_end - current_video_time
            
            # 量化时长
            frames = round(needed_duration * FPS)
            final_duration = frames / FPS
            
            # 容错：防止 duration < 0
            if final_duration < 0:
                 final_duration = 0.0

            # 4. 写入
            if final_duration > 0:
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {final_duration:.3f}\n")
                has_written_file = True
                current_video_time += final_duration

        # 补齐最后一点时间
        total_audio_duration = get_audio_duration(audio_path)
        if total_audio_duration > current_video_time:
            remaining = total_audio_duration - current_video_time
            frames = round(remaining * FPS)
            final_remaining = frames / FPS
            if final_remaining > 0:
                f.write(f"duration {final_remaining:.3f}\n")
            
        # FFmpeg concat 惯例：最后重复一次最后一张图
        if has_written_file:
            f.write(f"file '{img_path}'\n")
            
    # 3. 为每张图片生成带动效的视频片段
    print("\n🎬 正在为每张图片生成动效视频片段...")
    temp_segments_dir = finals_dir / f"{script_id}_temp_segments"
    temp_segments_dir.mkdir(parents=True, exist_ok=True)
    
    # 解析 concat.txt，建立图片到时长的映射
    scene_durations = {}
    current_img = None
    with open(concat_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('file '):
                current_img = line.replace("file '", "").replace("'", "")
            elif line.startswith('duration ') and current_img:
                duration = float(line.replace('duration ', ''))
                # 累加相同图片的时长
                if current_img in scene_durations:
                    scene_durations[current_img] += duration
                else:
                    scene_durations[current_img] = duration
    
    # 为每个场景生成带动效的视频片段
    segment_files = []
    for i, scene in enumerate(scenes):
        scene_num = scene['scene']
        img_path = Path(scene['image_path'])
        
        # 查找图片对应的时长
        img_path_str = str(img_path.absolute().as_posix())
        duration = scene_durations.get(img_path_str, 5.0)  # 默认5秒
        
        if duration <= 0:
            continue
        
        # 获取动效配置
        effect = scene.get('effect', {'type': 'zoom_in', 'zoom_start': 1.0, 'zoom_end': 1.2})
        
        # 生成 zoompan 滤镜（根据视频模式选择）
        if vertical:
            zoompan_filter = generate_vertical_zoompan_filter(effect, duration, FPS)
        else:
            zoompan_filter = generate_zoompan_filter(effect, duration, FPS)
        
        # 输出片段路径
        segment_path = temp_segments_dir / f"scene_{scene_num:03d}.mp4"
        segment_files.append(segment_path)
        
        # 如果片段已存在，跳过
        if segment_path.exists():
            print(f"⏩ 场景 {scene_num} 的视频片段已存在，跳过")
            continue
        
        print(f"🎨 生成场景 {scene_num} 的动效视频 ({effect['type']}, {duration:.2f}秒)...")
        
        # 构建滤镜链
        if vertical:
            # 竖屏模式：zoompan + 布局滤镜
            layout_filters = generate_vertical_layout_filter(book_name=book_name)
            full_filter = zoompan_filter + "," + ",".join(layout_filters)
        else:
            # 横屏模式：仅 zoompan
            full_filter = zoompan_filter
        
        # 生成带动效的视频片段
        cmd_segment = [
            get_ffmpeg_cmd(),
            '-loop', '1',
            '-i', str(img_path.absolute()),
            '-vf', full_filter,
            '-t', str(duration),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-r', str(FPS),
            '-y', str(segment_path)
        ]
        
        if run_command(cmd_segment, f"场景 {scene_num} 动效生成失败") is None:
            print(f"⚠️ 警告: 场景 {scene_num} 动效生成失败，跳过")
            continue
    
    # 生成新的 concat 文件（指向视频片段）
    concat_file_segments = srt_path.parent / f"{script_id}_concat_segments.txt"
    with open(concat_file_segments, 'w', encoding='utf-8') as f:
        for segment_path in segment_files:
            if segment_path.exists():
                f.write(f"file '{segment_path.absolute().as_posix()}'\n")
    
    # 4. 合并所有视频片段
    print("\n🎬 正在合并所有动效视频片段...")
    temp_video = finals_dir / f"{script_id}_temp_silent.mp4"
    cmd_base = [
        get_ffmpeg_cmd(), '-f', 'concat', '-safe', '0', '-i', str(concat_file_segments),
        '-c:v', 'copy',  # 直接复制，不重新编码
        '-y', str(temp_video)
    ]
    if run_command(cmd_base, "视频片段合并失败") is None:
        return False

    # 3. 字幕脱敏处理
    print("\n🔒 正在对字幕进行脱敏处理...")
    desensitized_srt_path = srt_path.parent / f"{script_id}_final_desensitized.srt"
    
    try:
        report = desensitize_srt(srt_path, desensitized_srt_path)
        print_report(report)
        # 使用脱敏后的字幕文件
        srt_to_use = desensitized_srt_path
    except Exception as e:
        print(f"⚠️ 警告: 字幕脱敏失败 ({e})，将使用原始字幕")
        srt_to_use = srt_path
    
    # 4. 合并音频和字幕
    srt_path_fixed = format_ffmpeg_path(str(srt_to_use))
    
    # 构建字幕滤镜（根据视频模式选择样式）
    if vertical:
        subtitle_style = generate_subtitle_style()
        subtitle_filter = f"subtitles='{srt_path_fixed}':force_style='{subtitle_style}'"
    else:
        subtitle_filter = f"subtitles='{srt_path_fixed}'"

    # 烧录字幕并合并音频
    cmd_final = [
        get_ffmpeg_cmd(), '-i', str(temp_video), '-i', str(audio_path.absolute()),
        '-vf', subtitle_filter,
        '-c:v', 'libx264',  # 需要重新编码以烧录字幕
        '-c:a', 'aac', '-shortest', '-y', str(output_video.absolute())
    ]
    
    print("🎬 正在烧录字幕并合并音频...")
    if run_command(cmd_final, "最终视频合成失败") is not None:
        print(f"✅ 视频合成成功: {output_video}")
    
    # 清理临时文件
    if concat_file.exists(): concat_file.unlink()
    if concat_file_segments.exists(): concat_file_segments.unlink()
    if temp_video.exists(): temp_video.unlink()
    
    # 清理视频片段目录（可选，如果想保留片段用于调试，可以注释掉）
    if temp_segments_dir.exists():
        shutil.rmtree(temp_segments_dir)
        print(f"🧹 已清理临时视频片段")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="合成视频")
    parser.add_argument("script_id", help="脚本 ID")
    parser.add_argument("--vertical", "-v", action="store_true", 
                       help="生成 9:16 竖屏视频（默认生成 16:9 横屏）")
    parser.add_argument("--book", "-b", type=str, default=None,
                       help="书名（用于从配置文件加载文案，如: '身体重置'）")
    
    args = parser.parse_args()
    compose_video(args.script_id, vertical=args.vertical, book_name=args.book)