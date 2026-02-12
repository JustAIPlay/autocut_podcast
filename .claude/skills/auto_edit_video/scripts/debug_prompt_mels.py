#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 prompt_mels_lens 的值
"""
import sys
import os
import json
import torch
from pathlib import Path

# 设置环境变量
soulx_path = "D:/AI/SoulX-Podcast"
os.environ["PYTHONPATH"] = soulx_path
os.environ["PYTHONIOENCODING"] = "utf-8"

# 添加到 Python 路径
sys.path.insert(0, soulx_path)

from soulxpodcast.utils.parser import podcast_format_parser
from soulxpodcast.utils.infer_utils import initiate_model, process_single_input
import torchaudio

print("=" * 60)
print("调试 prompt_mels_lens")
print("=" * 60)

# 加载输入 JSON
json_path = "D:/autocut_podcast/raw_materials/audios/HFlyx001159_soulx_input.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 解析输入
inputs = podcast_format_parser(data)

# 初始化模型
model_path = "D:/AI/SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B-dialect"
model, dataset = initiate_model(1988, model_path, "hf", True)

# 处理输入
data_item = process_single_input(
    dataset,
    inputs['text'],
    inputs['prompt_wav'],
    inputs['prompt_text'],
    inputs['use_dialect_prompt'],
    inputs['dialect_prompt_text'],
)

# 检查 prompt_mels_for_flow
prompt_mels_for_flow = data_item["prompt_mels_for_flow"]
prompt_mels_lens_for_flow = data_item["prompt_mels_lens_for_flow"]

print(f"\nprompt_mels_for_flow:")
for i, (mel, length) in enumerate(zip(prompt_mels_for_flow, prompt_mels_lens_for_flow)):
    print(f"  说话人 {i}:")
    print(f"    mel shape: {mel.shape}")
    print(f"    mel length: {length.item()}")
    print(f"    预计时长: {length.item() / 100:.2f} 秒 (假设 100 frames/sec)")

    # 读取原始参考音频
    ref_audio_path = inputs['prompt_wav'][i]
    print(f"    参考音频: {ref_audio_path}")
    if Path(ref_audio_path).exists():
        audio, sr = torchaudio.load(ref_audio_path)
        audio_duration = audio.shape[1] / sr
        print(f"    原始音频时长: {audio_duration:.2f} 秒")
        print(f"    原始音频采样率: {sr} Hz")

# 检查第一轮对话
print(f"\n第一轮对话:")
text_tokens_for_llm = data_item["text_tokens_for_llm"]
spk_ids = data_item["spks_list"]

print(f"  说话人 ID: {spk_ids[0]}")
print(f"  prompt_mels_lens_for_flow[0]: {prompt_mels_lens_for_flow[0].item()}")

# 模拟 Flow 输入
from soulxpodcast.models.soulxpodcast import s3tokenizer

prompt_mels_for_llm = data_item["prompt_mels_for_llm"]
prompt_mels_lens_for_llm = data_item["prompt_mels_lens_for_llm"]

prompt_speech_tokens_ori, prompt_speech_tokens_lens_ori = model.audio_tokenizer.quantize(
    prompt_mels_for_llm.cuda(), prompt_mels_lens_for_llm.cuda()
)

turn_spk = spk_ids[0]
prompt_speech_token = prompt_speech_tokens_ori[turn_spk].tolist()
generated_speech_tokens = [1, 2, 3, 4, 5]  # 模拟 5 个生成的 token

flow_input = torch.tensor([prompt_speech_token + generated_speech_tokens])
flow_inputs_len = torch.tensor([len(prompt_speech_token) + len(generated_speech_tokens)])

print(f"  prompt_speech_token 长度: {len(prompt_speech_token)}")
print(f"  generated_speech_tokens 长度: {len(generated_speech_tokens)}")
print(f"  flow_input 总长度: {flow_inputs_len.item()}")

# 检查 token 到 mel 的比例
print(f"\nToken 到 Mel 的比例:")
print(f"  prompt_speech_token 长度: {len(prompt_speech_token)}")
print(f"  prompt_mels_lens_for_flow[0]: {prompt_mels_lens_for_flow[0].item()}")
print(f"  比例: {prompt_mels_lens_for_flow[0].item() / len(prompt_speech_token):.2f}")

# 假设 Flow 输出
print(f"\n假设 Flow 输出:")
print(f"  generated_mels shape: [1, 80, {flow_inputs_len.item() * 2}]")
print(f"  generated_mels_lens: {flow_inputs_len.item()}")
print(f"  prompt_mels_lens[0]: {prompt_mels_lens_for_flow[0].item()}")

# 计算切片
start = prompt_mels_lens_for_flow[0].item()
end = flow_inputs_len.item() * 2

print(f"\n切片计算:")
print(f"  起始位置: {start}")
print(f"  结束位置: {end}")
print(f"  切片长度: {end - start}")
print(f"  切片时长: {(end - start) / 100:.2f} 秒 (假设 100 frames/sec)")

# 检查不同的切片方式
print(f"\n不同的切片方式:")
print(f"  方式1: generated_mels[:, :, {start}:{end}] -> 长度: {end - start}")
print(f"  方式2: generated_mels[:, :, {start}:] -> 长度: {end - start}")
print(f"  方式3: generated_mels[:, :, {start}:{start + 100}] -> 长度: 100")

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
