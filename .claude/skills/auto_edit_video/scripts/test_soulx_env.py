#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 SoulX-Podcast 是否能正常运行
"""
import sys
import os
from pathlib import Path

# 设置环境变量
soulx_path = "D:/AI/SoulX-Podcast"
os.environ["PYTHONPATH"] = soulx_path
os.environ["PYTHONIOENCODING"] = "utf-8"

# 添加到 Python 路径
sys.path.insert(0, soulx_path)

print("=" * 60)
print("SoulX-Podcast 环境测试")
print("=" * 60)

# 测试 1: 检查 Python 环境
print("\n1. 检查 Python 环境...")
print(f"   Python 版本: {sys.version}")
print(f"   SoulX-Python: D:/AI/SoulX-Podcast/env/python.exe")

# 测试 2: 检查 CUDA
print("\n2. 检查 CUDA...")
try:
    import torch
    print(f"   PyTorch 版本: {torch.__version__}")
    print(f"   CUDA 可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   CUDA 版本: {torch.version.cuda}")
        print(f"   GPU 数量: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
            props = torch.cuda.get_device_properties(i)
            print(f"         显存: {props.total_memory / 1024**3:.2f} GB")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 测试 3: 检查模型文件
print("\n3. 检查模型文件...")
model_path = Path(soulx_path) / "pretrained_models" / "SoulX-Podcast-1.7B-dialect"
print(f"   模型路径: {model_path}")
print(f"   存在: {model_path.exists()}")
if model_path.exists():
    required_files = [
        "soulxpodcast_config.json",
        "flow.pt",
        "hift.pt",
        "campplus.onnx"
    ]
    for f in required_files:
        file_path = model_path / f
        exists = file_path.exists()
        status = "✅" if exists else "❌"
        print(f"   {status} {f}: {exists}")

# 测试 4: 检查参考音频
print("\n4. 检查参考音频...")
ref_audio1 = Path(soulx_path) / "voices" / "speaker1.wav"
ref_audio2 = Path(soulx_path) / "voices" / "speaker2.wav"
print(f"   speaker1.wav: {ref_audio1.exists()}")
print(f"   speaker2.wav: {ref_audio2.exists()}")

# 测试 5: 尝试导入 SoulX-Podcast
print("\n5. 尝试导入 SoulX-Podcast...")
try:
    from soulxpodcast.models.soulxpodcast import SoulXPodcast
    print("   ✅ 导入成功")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 6: 检查输入 JSON
print("\n6. 检查输入 JSON...")
json_path = Path("D:/autocut_podcast/raw_materials/audios/HFlyx001159_soulx_input.json")
print(f"   JSON 路径: {json_path}")
print(f"   存在: {json_path.exists()}")

if json_path.exists():
    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"   说话人数量: {len(data.get('speakers', {}))}")
    print(f"   对话条数: {len(data.get('text', []))}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
