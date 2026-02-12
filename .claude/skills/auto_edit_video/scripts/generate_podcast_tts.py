#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SoulX-Podcast TTS 脚本
使用 SoulX-Podcast 模型生成双人播客音频
"""
import sys
import io
import os
import json
import re
import subprocess
from pathlib import Path
from utils import get_env, get_script_paths

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def parse_podcast_script(script_text: str) -> list:
    """
    解析播客脚本，将 [S1]/[S2] 格式转换为对话列表
    
    输入格式:
        [S1] 说话人1的内容
        [S2] 说话人2的内容
    
    输出格式:
        [["S1", "说话人1的内容"], ["S2", "说话人2的内容"]]
    """
    dialogues = []
    lines = script_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配 [S1] 或 [S2] 开头的行
        match = re.match(r'\[(S[12])\]\s*(.+)', line)
        if match:
            speaker = match.group(1)
            text = match.group(2).strip()
            if text:  # 确保文本不为空
                dialogues.append([speaker, text])
    
    return dialogues


def extract_prompt_text(dialogues: list, speaker: str, max_length: int = 100) -> str:
    """
    从对话中提取指定说话人的参考文本
    选择第一句话作为参考文本（用于声音克隆）
    """
    for spk, text in dialogues:
        if spk == speaker:
            # 取前 max_length 个字符作为参考文本
            return text[:max_length]
    return ""


def remove_dialect_tag(text: str) -> str:
    """移除文本中的方言标签，如 <|Yue|>, <|Henan|>, <|Sichuan|>"""
    return re.sub(r'<\|(?:Yue|Henan|Sichuan)\|>\s*', '', text)


def detect_dialect_tag(dialogues: list) -> str:
    """检测对话中是否包含方言标签"""
    for spk, text in dialogues:
        if '<|Yue|>' in text:
            return '<|Yue|>'
        elif '<|Henan|>' in text:
            return '<|Henan|>'
        elif '<|Sichuan|>' in text:
            return '<|Sichuan|>'
    return None


def create_soulx_input(dialogues: list, voice_s1: str, voice_s2: str) -> dict:
    """
    创建 SoulX-Podcast 需要的 JSON 输入格式

    普通话格式:
    {
        "speakers": {
            "S1": {"prompt_audio": "参考音频1.wav", "prompt_text": "参考文本1"},
            "S2": {"prompt_audio": "参考音频2.wav", "prompt_text": "参考文本2"}
        },
        "text": [...]
    }

    方言格式:
    {
        "speakers": {
            "S1": {
                "prompt_audio": "参考音频1.wav",
                "prompt_text": "参考文本1",
                "dialect_prompt": "<|Yue|>方言参考文本"
            },
            ...
        },
        "text": [["S1", "<|Yue|>对话内容"], ...]
    }
    """
    # 检测是否使用方言
    dialect_tag = detect_dialect_tag(dialogues)

    # 提取参考文本（去掉方言标签）
    prompt_text_s1 = ""
    prompt_text_s2 = ""
    dialect_prompt_s1 = ""
    dialect_prompt_s2 = ""

    for spk, text in dialogues:
        if spk == "S1" and not prompt_text_s1:
            # 去掉方言标签作为 prompt_text
            clean_text = remove_dialect_tag(text)
            prompt_text_s1 = clean_text[:100]  # 取前100字符
            # 如果是方言模式，添加 dialect_prompt
            if dialect_tag:
                dialect_prompt_s1 = text[:100]  # 保留方言标签
        elif spk == "S2" and not prompt_text_s2:
            clean_text = remove_dialect_tag(text)
            prompt_text_s2 = clean_text[:100]
            if dialect_tag:
                dialect_prompt_s2 = text[:100]

    # 构建 speakers 配置
    speakers = {
        "S1": {
            "prompt_audio": voice_s1,
            "prompt_text": prompt_text_s1
        },
        "S2": {
            "prompt_audio": voice_s2,
            "prompt_text": prompt_text_s2
        }
    }

    # 如果是方言模式，添加 dialect_prompt
    if dialect_tag and dialect_prompt_s1:
        speakers["S1"]["dialect_prompt"] = dialect_prompt_s1
    if dialect_tag and dialect_prompt_s2:
        speakers["S2"]["dialect_prompt"] = dialect_prompt_s2

    soulx_input = {
        "speakers": speakers,
        "text": dialogues
    }

    return soulx_input


def generate_podcast_tts(script_id: str) -> bool:
    """
    使用 SoulX-Podcast 生成播客音频
    
    输入: copys/{id}_podcast.txt ([S1]/[S2] 格式)
    输出: audios/{id}_podcast.mp3
    """
    paths = get_script_paths(script_id)
    
    # 检查输入文件
    input_file = paths["copy_podcast"]
    if not input_file.exists():
        print(f"❌ 找不到输入文件: {input_file}")
        print(f"   请先运行播客二创脚本")
        return False
    
    # 读取播客文案
    with open(input_file, 'r', encoding='utf-8') as f:
        podcast_script = f.read()
    
    if not podcast_script.strip():
        print("❌ 输入文件为空")
        return False
    
    # 检查格式
    if not ("[S1]" in podcast_script and "[S2]" in podcast_script):
        print("❌ 输入文件格式不正确，需要包含 [S1] 和 [S2] 标签")
        return False
    
    print(f"📄 播客脚本字数: {len(podcast_script)}")
    
    # 解析播客脚本
    dialogues = parse_podcast_script(podcast_script)
    if not dialogues:
        print("❌ 无法解析播客脚本，请检查格式")
        return False
    
    print(f"📝 解析到 {len(dialogues)} 条对话")
    
    # 从环境变量获取配置
    soulx_path = get_env("SOULX_PODCAST_PATH", "")
    model_path = get_env("SOULX_MODEL_PATH", "pretrained_models/SoulX-Podcast-1.7B")
    voice_s1 = get_env("SOULX_VOICE_S1", "")  # 说话人1参考音频
    voice_s2 = get_env("SOULX_VOICE_S2", "")  # 说话人2参考音频
    fp16_flow = get_env("SOULX_FP16_FLOW", "false").lower() == "true"  # FP16 加速
    
    # 可选：参考文本（如果不设置，会自动从对话中提取）
    prompt_text_s1 = get_env("SOULX_PROMPT_TEXT_S1", "")
    prompt_text_s2 = get_env("SOULX_PROMPT_TEXT_S2", "")
    
    if not soulx_path:
        print("❌ 请在 .env 中设置 SOULX_PODCAST_PATH (SoulX-Podcast 安装目录)")
        return False
    
    if not voice_s1 or not voice_s2:
        print("❌ 请在 .env 中设置 SOULX_VOICE_S1 和 SOULX_VOICE_S2 (参考音频路径)")
        return False
    
    # 验证参考音频文件存在
    if not os.path.exists(voice_s1):
        print(f"❌ 找不到参考音频文件: {voice_s1}")
        return False
    if not os.path.exists(voice_s2):
        print(f"❌ 找不到参考音频文件: {voice_s2}")
        return False
    
    output_file = paths["audio_podcast"]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 创建 SoulX-Podcast 输入 JSON
    soulx_input = create_soulx_input(dialogues, voice_s1, voice_s2)
    
    # 如果环境变量中指定了参考文本，使用指定的文本
    if prompt_text_s1:
        soulx_input["speakers"]["S1"]["prompt_text"] = prompt_text_s1
    if prompt_text_s2:
        soulx_input["speakers"]["S2"]["prompt_text"] = prompt_text_s2
    
    # 保存 JSON 输入文件
    json_input_file = output_file.parent / f"{script_id}_soulx_input.json"
    with open(json_input_file, 'w', encoding='utf-8') as f:
        json.dump(soulx_input, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已生成 SoulX-Podcast 输入文件: {json_input_file}")
    print(f"   - S1 参考音频: {voice_s1}")
    print(f"   - S1 参考文本: {soulx_input['speakers']['S1']['prompt_text'][:50]}...")
    print(f"   - S2 参考音频: {voice_s2}")
    print(f"   - S2 参考文本: {soulx_input['speakers']['S2']['prompt_text'][:50]}...")
    
    try:
        print(f"\n🎙️ 正在调用 SoulX-Podcast 生成播客音频...")

        # 调用 SoulX-Podcast CLI
        # 使用正确的调用方式：PYTHONPATH=<路径> python cli/podcast.py
        env = os.environ.copy()
        env["PYTHONPATH"] = soulx_path

        cmd = [
            "python",
            "cli/podcast.py",
            "--json_path", str(json_input_file),
            "--model_path", model_path,
            "--output_path", str(output_file.with_suffix(".wav")),  # SoulX 输出 WAV
            "--seed", "1988"
        ]

        # 添加 FP16 加速参数
        if fp16_flow:
            cmd.append("--fp16_flow")

        print(f"📌 执行命令: PYTHONPATH={soulx_path} python cli/podcast.py ...")
        print(f"   输入: {json_input_file.name}")
        print(f"   输出: {output_file.with_suffix('.wav').name}")
        if fp16_flow:
            print(f"   ⚡ FP16 加速: 已启用")

        result = subprocess.run(
            cmd,
            cwd=soulx_path,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            env=env
        )
        
        if result.returncode != 0:
            print(f"❌ SoulX-Podcast 执行失败:")
            print(f"   返回码: {result.returncode}")
            if result.stdout:
                print(f"   标准输出:\n{result.stdout}")
            if result.stderr:
                print(f"   错误输出:\n{result.stderr}")
            return False
        
        # 显示输出信息
        if result.stdout:
            print(result.stdout)
        
        # 验证输出文件（SoulX-Podcast 输出 WAV）
        output_wav = output_file.with_suffix(".wav")
        if not output_wav.exists():
            print(f"❌ 输出文件未生成: {output_wav}")
            print(f"   请检查 SoulX-Podcast 的输出日志")
            return False

        print(f"\n✅ 播客音频生成完成！")
        print(f"   - 输出文件: {output_wav}")
        print(f"   - 文件大小: {output_wav.stat().st_size / 1024 / 1024:.2f} MB")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ 找不到 SoulX-Podcast: {soulx_path}")
        print("   请确保已正确安装 SoulX-Podcast 并配置 SOULX_PODCAST_PATH")
        return False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate_podcast_tts.py <script_id>")
        sys.exit(1)
    
    script_id = sys.argv[1]
    success = generate_podcast_tts(script_id)
    sys.exit(0 if success else 1)
