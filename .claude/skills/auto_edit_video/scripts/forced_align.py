#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen3-ForcedAligner 时间戳对齐脚本
使用 Qwen3-ForcedAligner-0.6B 生成词级时间戳
支持长音频自动分段处理（超过5分钟自动切分）
"""
import os
import sys
import io
import json
import argparse
import tempfile
from pathlib import Path

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils import get_script_paths, get_project_root

# 尝试导入依赖
try:
    from qwen_asr import Qwen3ForcedAligner
    HAS_ALIGNER = True
except ImportError:
    HAS_ALIGNER = False
    print("⚠️ 警告: 未安装 qwen-asr，请运行: pip install qwen-asr")

try:
    import librosa
    import soundfile as sf
    import numpy as np
    HAS_AUDIO_LIBS = True
except ImportError:
    HAS_AUDIO_LIBS = False
    print("⚠️ 警告: 未安装 librosa/soundfile，长音频分段功能不可用")

# 常量
MAX_AUDIO_DURATION = 270  # 4.5分钟，保留余量（官方限制5分钟）
MIN_SILENCE_DURATION = 0.3  # 最小静音时长（秒）
SILENCE_THRESHOLD = 0.02  # 静音阈值


def extract_word_info(word_item) -> dict:
    """
    从词项中提取信息，支持字典和对象两种格式
    返回: {"word": str, "start": float, "end": float}
    """
    # 尝试字典访问
    if isinstance(word_item, dict):
        return {
            "word": word_item.get("word", word_item.get("text", "")),
            "start": word_item.get("start", word_item.get("start_time", 0.0)),
            "end": word_item.get("end", word_item.get("end_time", 0.0))
        }
    # 尝试对象属性访问
    else:
        word = getattr(word_item, "word", None) or getattr(word_item, "text", "")
        start = getattr(word_item, "start", None) or getattr(word_item, "start_time", 0.0)
        end = getattr(word_item, "end", None) or getattr(word_item, "end_time", 0.0)
        return {"word": str(word), "start": float(start), "end": float(end)}



def get_audio_duration(audio_path: Path) -> float:
    """获取音频时长（秒）"""
    if not HAS_AUDIO_LIBS:
        return 0.0
    y, sr = librosa.load(str(audio_path), sr=None)
    return len(y) / sr


def find_silence_points(audio_path: Path, min_silence_sec: float = 0.3) -> list:
    """
    找到音频中的静音点，用于切分
    返回: [(start, end), ...] 静音区间列表
    """
    if not HAS_AUDIO_LIBS:
        return []
    
    y, sr = librosa.load(str(audio_path), sr=None)
    
    # 计算短时能量
    frame_length = int(sr * 0.025)  # 25ms
    hop_length = int(sr * 0.010)    # 10ms
    
    # 使用 RMS 能量
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    # 归一化
    rms_normalized = rms / (np.max(rms) + 1e-10)
    
    # 找静音帧
    is_silence = rms_normalized < SILENCE_THRESHOLD
    
    # 转换为时间
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    
    # 找连续静音区间
    silence_regions = []
    in_silence = False
    silence_start = 0
    
    for i, silent in enumerate(is_silence):
        if silent and not in_silence:
            in_silence = True
            silence_start = times[i]
        elif not silent and in_silence:
            in_silence = False
            silence_end = times[i]
            if silence_end - silence_start >= min_silence_sec:
                silence_regions.append((silence_start, silence_end))
    
    # 处理结尾静音
    if in_silence:
        silence_end = times[-1]
        if silence_end - silence_start >= min_silence_sec:
            silence_regions.append((silence_start, silence_end))
    
    return silence_regions


def split_audio_by_duration(audio_path: Path, max_duration: float = MAX_AUDIO_DURATION) -> list:
    """
    按时长切分音频，在静音点切分
    返回: [(chunk_path, start_time, end_time), ...]
    """
    if not HAS_AUDIO_LIBS:
        return [(audio_path, 0.0, 0.0)]
    
    y, sr = librosa.load(str(audio_path), sr=None)
    total_duration = len(y) / sr
    
    if total_duration <= max_duration:
        # 不需要切分
        return [(audio_path, 0.0, total_duration)]
    
    print(f"📐 音频时长 {total_duration:.1f}s 超过限制 {max_duration}s，正在分段...")
    
    # 找静音点
    silence_points = find_silence_points(audio_path)
    
    # 选择合适的切分点
    chunks = []
    current_start = 0.0
    temp_dir = tempfile.mkdtemp(prefix="forced_align_")
    
    while current_start < total_duration:
        target_end = current_start + max_duration
        
        if target_end >= total_duration:
            # 最后一段
            chunk_end = total_duration
        else:
            # 在目标点附近找一个静音点
            best_split = target_end
            best_distance = float('inf')
            
            for silence_start, silence_end in silence_points:
                # 静音中点
                silence_mid = (silence_start + silence_end) / 2
                
                # 只考虑在目标附近的静音点（前后30秒范围）
                if current_start + 60 < silence_mid < target_end + 30:
                    distance = abs(silence_mid - target_end)
                    if distance < best_distance:
                        best_distance = distance
                        best_split = silence_mid
            
            chunk_end = best_split
        
        # 提取音频片段
        start_sample = int(current_start * sr)
        end_sample = int(chunk_end * sr)
        chunk_audio = y[start_sample:end_sample]
        
        # 保存临时文件
        chunk_path = Path(temp_dir) / f"chunk_{len(chunks):03d}.wav"
        sf.write(str(chunk_path), chunk_audio, sr)
        
        chunks.append((chunk_path, current_start, chunk_end))
        print(f"  📦 片段 {len(chunks)}: {current_start:.1f}s - {chunk_end:.1f}s ({chunk_end - current_start:.1f}s)")
        
        current_start = chunk_end
    
    print(f"✅ 共切分为 {len(chunks)} 个片段")
    return chunks


def estimate_text_split_position(text: str, audio_chunks: list, total_duration: float) -> list:
    """
    根据音频切分点估算文本切分位置
    返回: [text_chunk1, text_chunk2, ...]
    """
    if len(audio_chunks) == 1:
        return [text]
    
    # 按时间比例估算字符位置
    text_chunks = []
    total_chars = len(text)
    
    for i, (_, start_time, end_time) in enumerate(audio_chunks):
        # 计算这段对应的字符范围
        start_ratio = start_time / total_duration
        end_ratio = end_time / total_duration
        
        start_char = int(start_ratio * total_chars)
        end_char = int(end_ratio * total_chars)
        
        # 调整到句子边界（向前找标点）
        if i > 0 and start_char > 0:
            # 往前找最近的句号/逗号
            search_start = max(0, start_char - 50)
            for j in range(start_char, search_start, -1):
                if text[j] in '。！？，、；：':
                    start_char = j + 1
                    break
        
        if i < len(audio_chunks) - 1 and end_char < total_chars:
            # 往后找最近的句号/逗号
            search_end = min(total_chars, end_char + 50)
            for j in range(end_char, search_end):
                if text[j] in '。！？，、；：':
                    end_char = j + 1
                    break
        
        text_chunk = text[start_char:end_char].strip()
        text_chunks.append(text_chunk)
        print(f"  📝 文本片段 {i+1}: {len(text_chunk)} 字符")
    
    return text_chunks


def forced_align(script_id: str, podcast_mode: bool = False, use_cpu: bool = False) -> bool:
    """
    使用 Qwen3-ForcedAligner 生成词级时间戳
    支持长音频自动分段处理
    
    Args:
        script_id: 项目标识符
        podcast_mode: 是否为播客模式（使用播客音频和字幕文本）
        use_cpu: 是否使用 CPU 模式
        
    Returns:
        是否成功
    """
    if not HAS_ALIGNER:
        print("❌ qwen-asr 未安装，无法进行强制对齐")
        return False
    
    paths = get_script_paths(script_id)
    
    if podcast_mode:
        # 播客模式：使用播客音频 + 字幕文本
        audio_path = paths["audio_podcast"]
        text_path = paths["copy_subtitle"]
        print("🎙️ 播客模式：使用播客音频进行对齐")
    else:
        # 常规模式：二创音频 + 二创文案
        audio_path = paths["audio_tts"]
        text_path = paths["copy_recreated"]
    
    # 输出：词级时间戳
    output_path = paths["word_timestamps"]
    
    # 检查输入文件
    if not audio_path.exists():
        print(f"❌ 找不到音频文件: {audio_path}")
        print(f"💡 请先准备音频文件")
        return False
    
    if not text_path.exists():
        print(f"❌ 找不到文本文件: {text_path}")
        print(f"💡 请先准备文本文件")
        return False
    
    # 读取文案
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 获取音频时长
    total_duration = get_audio_duration(audio_path)
    
    print(f"🎯 正在使用 Qwen3-ForcedAligner 进行强制对齐...")
    print(f"🎵 音频文件: {audio_path}")
    print(f"⏱️ 音频时长: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分钟)")
    print(f"📄 文案文件: {text_path}")
    print(f"📊 文案字数: {len(text)}")
    
    try:
        import torch
        # 清空 GPU 缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # 检查是否需要分段
        audio_chunks = split_audio_by_duration(audio_path, MAX_AUDIO_DURATION)
        needs_chunking = len(audio_chunks) > 1
        
        if needs_chunking:
            text_chunks = estimate_text_split_position(text, audio_chunks, total_duration)
        else:
            text_chunks = [text]
        
        # 初始化模型
        print(f"\n🔄 正在加载模型...")
        if use_cpu:
            print("⚠️ 使用 CPU 模式（速度较慢）")
            aligner = Qwen3ForcedAligner.from_pretrained(
                "Qwen/Qwen3-ForcedAligner-0.6B",
                device_map="cpu"
            )
            device_info = "cpu"
        else:
            aligner = Qwen3ForcedAligner.from_pretrained(
                "Qwen/Qwen3-ForcedAligner-0.6B",
                device_map="auto",
                dtype=torch.float16
            )
            device_info = "cuda (FP16)"
        
        print(f"🔧 模型设备: {device_info}")
        
        # 处理每个片段
        all_words = []
        
        for i, ((chunk_path, chunk_start, chunk_end), text_chunk) in enumerate(zip(audio_chunks, text_chunks)):
            if needs_chunking:
                print(f"\n📦 处理片段 {i+1}/{len(audio_chunks)}...")
            
            try:
                # 执行强制对齐
                result = aligner.align(
                    audio=str(chunk_path),
                    text=text_chunk,
                    language="zh"
                )
                
                # 提取词级时间戳，调整时间偏移
                # align() 返回格式: [ForcedAlignResult(items=[ForcedAlignItem(...), ...])]
                # 即：一个列表，包含一个 ForcedAlignResult 对象
                words = []
                if isinstance(result, list) and len(result) > 0:
                    first_item = result[0]
                    if hasattr(first_item, 'items'):
                        # result = [ForcedAlignResult(items=[...])]
                        words = first_item.items
                    else:
                        # result = [word1, word2, ...] 直接是词列表
                        words = result
                elif hasattr(result, 'items'):
                    # result = ForcedAlignResult(items=[...])
                    words = result.items
                elif isinstance(result, dict):
                    words = result.get("words", result.get("items", []))
                else:
                    print(f"⚠️ 未知返回类型: {type(result)}")
                
                for w in words:
                    info = extract_word_info(w)
                    all_words.append({
                        "word": info["word"],
                        "start": info["start"] + chunk_start,
                        "end": info["end"] + chunk_start
                    })
                
                if needs_chunking:
                    print(f"  ✅ 片段 {i+1} 完成，获取 {len(words)} 个词")
                    
            except RuntimeError as e:
                if "CUDA out of memory" in str(e) and not use_cpu:
                    print(f"⚠️ GPU 显存不足，自动切换到 CPU 模式...")
                    # 重新加载 CPU 模型
                    del aligner
                    torch.cuda.empty_cache()
                    aligner = Qwen3ForcedAligner.from_pretrained(
                        "Qwen/Qwen3-ForcedAligner-0.6B",
                        device_map="cpu"
                    )
                    # 重试当前片段
                    result = aligner.align(
                        audio=str(chunk_path),
                        text=text_chunk,
                        language="zh"
                    )
                    # 同样处理 [ForcedAlignResult(items=[...])] 格式
                    words = []
                    if isinstance(result, list) and len(result) > 0:
                        first_item = result[0]
                        if hasattr(first_item, 'items'):
                            words = first_item.items
                        else:
                            words = result
                    elif hasattr(result, 'items'):
                        words = result.items
                    elif isinstance(result, dict):
                        words = result.get("words", result.get("items", []))
                    
                    for w in words:
                        info = extract_word_info(w)
                        all_words.append({
                            "word": info["word"],
                            "start": info["start"] + chunk_start,
                            "end": info["end"] + chunk_start
                        })
                else:
                    raise
        
        # 清理临时文件
        if needs_chunking:
            import shutil
            temp_dir = audio_chunks[0][0].parent
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 构建输出格式
        output_data = {
            "script_id": script_id,
            "full_text": text,
            "segments": [
                {
                    "id": i,
                    "text": w["word"],
                    "start": w["start"],
                    "end": w["end"]
                }
                for i, w in enumerate(all_words)
            ],
            "total_words": len(all_words),
            "segment_mode": "forced_alignment",
            "chunked": needs_chunking,
            "total_duration": total_duration
        }
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存结果
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # 计算总时长
        if all_words:
            final_duration = all_words[-1]["end"]
        else:
            final_duration = 0.0
        
        print(f"\n✅ 强制对齐完成！")
        print(f"📁 输出文件: {output_path}")
        print(f"📊 词语数量: {len(all_words)}")
        print(f"⏱️ 总时长: {final_duration:.2f} 秒")
        
        if needs_chunking:
            print(f"📦 分段处理: {len(audio_chunks)} 个片段")
        
        print("-" * 40)
        print("预览前10个词：")
        for seg in output_data["segments"][:10]:
            print(f"  [{seg['start']:.3f}-{seg['end']:.3f}] \"{seg['text']}\"")
        
        return True
        
    except Exception as e:
        print(f"❌ 强制对齐失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 Qwen3-ForcedAligner 生成词级时间戳")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    parser.add_argument("--podcast", "-p", action="store_true",
                       help="播客模式：使用播客音频和字幕文本进行对齐")
    parser.add_argument("--cpu", action="store_true",
                       help="使用 CPU 模式（GPU 显存不足时使用）")

    args = parser.parse_args()

    success = forced_align(args.script_id, podcast_mode=args.podcast, use_cpu=args.cpu)
    sys.exit(0 if success else 1)
