#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试 SoulX-Podcast 的音频生成过程
"""
import sys
import os
import json
from pathlib import Path

# 设置环境变量
soulx_path = "D:/AI/SoulX-Podcast"
os.environ["PYTHONPATH"] = soulx_path
os.environ["PYTHONIOENCODING"] = "utf-8"

# 添加到 Python 路径
sys.path.insert(0, soulx_path)

import torch
from soulxpodcast.config import Config, SoulXPodcastLLMConfig, SamplingParams
from soulxpodcast.models.soulxpodcast import SoulXPodcast
from soulxpodcast.utils.parser import podcast_format_parser
from soulxpodcast.utils.infer_utils import initiate_model, process_single_input

print("=" * 60)
print("调试 SoulX-Podcast 音频生成")
print("=" * 60)

# 加载输入 JSON
json_path = "D:/autocut_podcast/raw_materials/audios/HFlyx001159_soulx_input.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"\n输入文件: {json_path}")
print(f"说话人数量: {len(data['speakers'])}")
print(f"对话条数: {len(data['text'])}")

# 解析输入
inputs = podcast_format_parser(data)
print(f"\n解析结果:")
print(f"  prompt_wav 数量: {len(inputs['prompt_wav'])}")
print(f"  text 数量: {len(inputs['text'])}")

# 初始化模型
print(f"\n初始化模型...")
model_path = "D:/AI/SoulX-Podcast/pretrained_models/SoulX-Podcast-1.7B-dialect"
model, dataset = initiate_model(1988, model_path, "hf", True)

# 处理输入
print(f"\n处理输入...")
data_item = process_single_input(
    dataset,
    inputs['text'],
    inputs['prompt_wav'],
    inputs['prompt_text'],
    inputs['use_dialect_prompt'],
    inputs['dialect_prompt_text'],
)

# 只处理第一轮对话来调试
print(f"\n调试第一轮对话...")

# 提取第一轮的数据
prompt_mels_for_llm = data_item["prompt_mels_for_llm"]
prompt_mels_lens_for_llm = data_item["prompt_mels_lens_for_llm"]

# Audio tokenization
from soulxpodcast.models.soulxpodcast import s3tokenizer

prompt_speech_tokens_ori, prompt_speech_tokens_lens_ori = model.audio_tokenizer.quantize(
    prompt_mels_for_llm.cuda(), prompt_mels_lens_for_llm.cuda()
)

print(f"\nPrompt speech tokens:")
for i, (tokens, length) in enumerate(zip(prompt_speech_tokens_ori, prompt_speech_tokens_lens_ori)):
    print(f"  说话人 {i}: tokens={tokens.shape}, length={length.item()}")

# 提取第一轮对话的 token
text_tokens_for_llm = data_item["text_tokens_for_llm"]
prompt_text_tokens_for_llm = data_item["prompt_text_tokens_for_llm"]
spk_ids = data_item["spks_list"]

print(f"\n第一轮对话:")
print(f"  文本 tokens: {text_tokens_for_llm[0][:10]}...")
print(f"  说话人 ID: {spk_ids[0]}")

# 模拟 LLM 生成（只取前 10 个 token）
llm_outputs = {'token_ids': text_tokens_for_llm[0][:10]}

# Prepare Flow inputs
turn_spk = spk_ids[0]
generated_speech_tokens = [token - model.config.hf_config.speech_token_offset for token in llm_outputs['token_ids'][:-1]]
prompt_speech_token = prompt_speech_tokens_ori[turn_spk].tolist()

print(f"\nFlow 输入:")
print(f"  prompt_speech_token 长度: {len(prompt_speech_token)}")
print(f"  generated_speech_tokens 长度: {len(generated_speech_tokens)}")
print(f"  flow_input 总长度: {len(prompt_speech_token) + len(generated_speech_tokens)}")

flow_input = torch.tensor([prompt_speech_token + generated_speech_tokens])
flow_inputs_len = torch.tensor([len(prompt_speech_token) + len(generated_speech_tokens)])

# Prompt mels for flow
prompt_mels_for_flow = data_item["prompt_mels_for_flow_ori"]
prompt_mels_lens_for_flow = data_item["prompt_mels_lens_for_flow"]

start_idx = spk_ids[0]
prompt_mels = prompt_mels_for_flow[start_idx][None]
prompt_mels_lens = prompt_mels_lens_for_flow[start_idx][None]

print(f"\nPrompt mels for flow:")
print(f"  prompt_mels shape: {prompt_mels.shape}")
print(f"  prompt_mels_lens: {prompt_mels_lens.item()}")

# Flow generation
print(f"\n执行 Flow 生成...")
with torch.amp.autocast("cuda", dtype=torch.float16):
    generated_mels, generated_mels_lens = model.flow(
        flow_input.cuda(), flow_inputs_len.cuda(),
        prompt_mels, prompt_mels_lens, model.config.hf_config.fp16_flow,
        streaming=False, finalize=True
    )

print(f"\nFlow 输出:")
print(f"  generated_mels shape: {generated_mels.shape}")
print(f"  generated_mels_lens: {generated_mels_lens.item()}")

# 分析切片
print(f"\n切片分析:")
print(f"  prompt_mels_lens[0].item(): {prompt_mels_lens[0].item()}")
print(f"  generated_mels_lens[0].item(): {generated_mels_lens[0].item()}")
print(f"  generated_mels.shape[2]: {generated_mels.shape[2]}")

# 尝试不同的切片方式
slice1 = generated_mels[:, :, prompt_mels_lens[0].item():generated_mels_lens[0].item()]
slice2 = generated_mels[:, :, prompt_mels_lens[0].item():]
slice3 = generated_mels[:, :, generated_mels_lens[0].item():]

print(f"\n切片结果:")
print(f"  slice1 [prompt_mels_lens:generated_mels_lens]: {slice1.shape}")
print(f"  slice2 [prompt_mels_lens:]: {slice2.shape}")
print(f"  slice3 [generated_mels_lens:]: {slice3.shape}")

# HiFi-GAN 生成
print(f"\n执行 HiFi-GAN 生成...")
mel = generated_mels[:, :, prompt_mels_lens[0].item():]
wav, _ = model.hift(speech_feat=mel)

print(f"\nHiFi-GAN 输出:")
print(f"  wav shape: {wav.shape}")
print(f"  预计时长: {wav.shape[1] / 24000:.2f} 秒")

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
