#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 SoulX-Podcast 是否能正常运行（使用 SoulX-Python）
"""
import subprocess
import sys
from pathlib import Path

soulx_path = "D:/AI/SoulX-Podcast"
soulx_python = Path(soulx_path) / "env" / "python.exe"

print("=" * 60)
print("SoulX-Podcast 环境测试（使用 SoulX-Python）")
print("=" * 60)

# 测试 1: 检查 Python 环境
print("\n1. 检查 Python 环境...")
result = subprocess.run(
    [str(soulx_python), "-c", "import sys; print('Python 版本:', sys.version)"],
    capture_output=True
)
stdout = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
print(f"   {stdout.strip()}")

# 测试 2: 检查 CUDA
print("\n2. 检查 CUDA...")
test_cuda = "import torch; print('PyTorch 版本:', torch.__version__); print('CUDA 可用:', torch.cuda.is_available())"
result = subprocess.run(
    [str(soulx_python), "-c", test_cuda],
    capture_output=True
)
stdout = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
print(f"   {stdout.strip()}")

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
test_import = """
import sys
sys.path.insert(0, 'D:/AI/SoulX-Podcast')
try:
    from soulxpodcast.models.soulxpodcast import SoulXPodcast
    print('✅ 导入成功')
except Exception as e:
    print('❌ 导入失败:', str(e))
"""
result = subprocess.run(
    [str(soulx_python), "-c", test_import],
    capture_output=True,
    cwd=soulx_path
)
stdout = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
print(f"   {stdout.strip()}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
