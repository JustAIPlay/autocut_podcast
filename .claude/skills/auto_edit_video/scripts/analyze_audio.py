#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查生成的音频文件
"""
import soundfile as sf
from pathlib import Path

audio_path = Path("D:/autocut_podcast/raw_materials/audios/HFlyx001159_podcast.wav")

print("=" * 60)
print("音频文件分析")
print("=" * 60)

# 读取音频
audio, sr = sf.read(str(audio_path))

print(f"\n音频信息:")
print(f"  采样率: {sr} Hz")
print(f"  时长: {len(audio) / sr:.2f} 秒")
print(f"  声道数: {audio.shape}")
print(f"  数据类型: {audio.dtype}")

# 检查参考音频
ref_audio1 = Path("D:/AI/SoulX-Podcast/voices/speaker1.wav")
ref_audio2 = Path("D:/AI/SoulX-Podcast/voices/speaker2.wav")

print(f"\n参考音频:")
if ref_audio1.exists():
    ref1, sr1 = sf.read(str(ref_audio1))
    print(f"  speaker1.wav: {len(ref1) / sr1:.2f} 秒, 采样率: {sr1}")
if ref_audio2.exists():
    ref2, sr2 = sf.read(str(ref_audio2))
    print(f"  speaker2.wav: {len(ref2) / sr2:.2f} 秒, 采样率: {sr2}")

# 分析音频波形
print(f"\n音频波形分析:")
print(f"  最大值: {audio.max():.6f}")
print(f"  最小值: {audio.min():.6f}")
print(f"  均值: {audio.mean():.6f}")
print(f"  标准差: {audio.std():.6f}")

# 检查前15秒的音频
first_15_sec = int(15 * sr)
first_15_sec_audio = audio[:first_15_sec]

print(f"\n前15秒音频:")
print(f"  长度: {len(first_15_sec_audio)} 采样点")
print(f"  最大值: {first_15_sec_audio.max():.6f}")
print(f"  最小值: {first_15_sec_audio.min():.6f}")
print(f"  均值: {first_15_sec_audio.mean():.6f}")
print(f"  标准差: {first_15_sec_audio.std():.6f}")

# 检查是否有静音段（参考音频可能有静音）
silence_threshold = 0.01
silence_samples = (audio < silence_threshold).sum()
silence_ratio = silence_samples / len(audio)

print(f"\n静音分析:")
print(f"  静音阈值: {silence_threshold}")
print(f"  静音采样点: {silence_samples}")
print(f"  静音比例: {silence_ratio * 100:.2f}%")

# 检查前15秒的静音比例
first_15_silence = (first_15_sec_audio < silence_threshold).sum()
first_15_silence_ratio = first_15_silence / len(first_15_sec_audio)

print(f"  前15秒静音比例: {first_15_silence_ratio * 100:.2f}%")

print("\n" + "=" * 60)
print("分析完成")
print("=" * 60)
