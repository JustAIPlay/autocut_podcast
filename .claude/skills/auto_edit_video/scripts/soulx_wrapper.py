"""
SoulX-Podcast 包装脚本，支持自定义采样参数
"""
import os
import sys
import json
import argparse

# 添加 SoulX-Podcast 路径
soulx_path = os.environ.get("SOULX_PODCAST_PATH", "")
if soulx_path:
    sys.path.insert(0, soulx_path)

import torch
import soundfile as sf
from soulxpodcast.utils.infer_utils import initiate_model, process_single_input
from soulxpodcast.utils.parser import podcast_format_parser
from soulxpodcast.config import SamplingParams


def run_inference(
    inputs: dict,
    model_path: str,
    output_path: str,
    llm_engine: str = "hf",
    fp16_flow: bool = False,
    seed: int = 1988,
    temperature: float = 0.6,
    repetition_penalty: float = 1.25,
    tau_r: float = 0.2,
    history_context: int = 2,
):
    # 初始化模型
    model, dataset = initiate_model(seed, model_path, llm_engine, fp16_flow)

    # 处理输入
    data = process_single_input(
        dataset,
        inputs['text'],
        inputs['prompt_wav'],
        inputs['prompt_text'],
        inputs['use_dialect_prompt'],
        inputs['dialect_prompt_text'],
    )

    # 使用自定义采样参数
    sampling_params = SamplingParams(
        temperature=temperature,
        repetition_penalty=repetition_penalty,
        top_k=100,
        top_p=0.9,
        use_ras=True,
        win_size=25,
        tau_r=tau_r
    )

    # 更新配置中的历史上下文
    model.config.history_context = history_context
    model.config.history_text_context = history_context

    print(f"[INFO] 使用自定义采样参数:")
    print(f"  - temperature: {temperature}")
    print(f"  - repetition_penalty: {repetition_penalty}")
    print(f"  - tau_r: {tau_r}")
    print(f"  - history_context: {history_context}")

    # 替换采样参数
    data["sampling_params"] = sampling_params

    print("[INFO] Start inference...")

    # 执行推理
    results_dict = model.forward_longform(**data)

    # 拼接音频
    target_audio = None
    for wav in results_dict["generated_wavs"]:
        if target_audio is None:
            target_audio = wav
        else:
            target_audio = torch.cat([target_audio, wav], dim=1)

    # 保存结果
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sf.write(output_path, target_audio.cpu().squeeze(0).numpy(), 24000)
    print(f"[INFO] Saved synthesized audio to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_path", required=True, help="Path to the input JSON file")
    parser.add_argument("--model_path", required=True, help="Path to the model file")
    parser.add_argument("--output_path", default="outputs/result.wav", help="Path to the output audio file")
    parser.add_argument("--llm_engine", default="hf", choices=["hf", "vllm"], help="Inference engine to use")
    parser.add_argument("--fp16_flow", action="store_true", help="Enable FP16 flow")
    parser.add_argument("--seed", type=int, default=1988, help="Random seed")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--repetition_penalty", type=float, default=1.1, help="Repetition penalty")
    parser.add_argument("--tau_r", type=float, default=0.3, help="Rhythm smoothness parameter")
    parser.add_argument("--history_context", type=int, default=1, help="History context rounds")
    parser.add_argument("--config", help="Path to sampling parameters config JSON (optional)")
    args = parser.parse_args()

    # 加载输入数据
    with open(args.json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    inputs = podcast_format_parser(data)

    # 如果提供了配置文件，从中读取参数
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
            args.temperature = config.get("temperature", args.temperature)
            args.repetition_penalty = config.get("repetition_penalty", args.repetition_penalty)
            args.tau_r = config.get("tau_r", args.tau_r)

    run_inference(
        inputs=inputs,
        model_path=args.model_path,
        output_path=args.output_path,
        llm_engine=args.llm_engine,
        fp16_flow=args.fp16_flow,
        seed=args.seed,
        temperature=args.temperature,
        repetition_penalty=args.repetition_penalty,
        tau_r=args.tau_r,
        history_context=args.history_context,
    )
