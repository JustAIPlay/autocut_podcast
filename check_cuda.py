import os
import sys
from typing import Any

def diagnose_cuda():
    print("🔍 正在诊断 CUDA 运行环境...\n")
    
    # 1. 检查 PyTorch 是否能识别 GPU (基础环境检查)
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"--- PyTorch ---")
        print(f"PyTorch 识别 CUDA: {'✅ 是' if cuda_available else '❌ 否'}")
        if cuda_available:
            print(f"显卡型号: {torch.cuda.get_device_name(0)}")
            # 将 torch 模块强制转换为 Any 以避开所有静态属性检查
            torch_any: Any = torch
            cuda_ver = getattr(torch_any.version, 'cuda', 'Unknown')
            print(f"CUDA 版本: {cuda_ver}")
    except ImportError:
        print("❌ 未安装 torch，请运行 pip install torch")

    # 2. 检查 CTranslate2 (faster-whisper 的核心引擎)
    print(f"\n--- faster-whisper / CTranslate2 ---")
    cuda_device_count = 0
    try:
        import ctranslate2
        cuda_device_count = ctranslate2.get_cuda_device_count()
        print(f"CTranslate2 识别 GPU 数量: {cuda_device_count}")
        if cuda_device_count > 0:
            print(f"✅ CTranslate2 环境正常，GPU 加速可用。")
        else:
            print(f"❌ CTranslate2 未识别到 GPU。")
            print(f"   建议安装: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12")
    except ImportError:
        print("❌ 未安装 faster-whisper 或 ctranslate2")
    except Exception as e:
        print(f"❌ CTranslate2 运行时错误: {e}")
        print("   这通常意味着缺少 cublas64_12.dll 或 cudnn64_12.dll")

    # 3. 检查系统环境变量
    print(f"\n--- 系统路径检查 ---")
    path = os.environ.get('PATH', '')
    if 'CUDA' in path.upper():
        print("✅ 环境变量中包含 CUDA 路径")
    else:
        print("⚠️ 环境变量中未发现 CUDA 路径 (如果已安装 nvidia-cublas-cu12 库，这通常没关系)")

    print("\n" + "="*40)
    if 'cuda_device_count' in locals() and cuda_device_count > 0:
        print("🚀 结论：你的 CUDA 环境【符合要求】，可以流畅运行 GPU 转录！")
    else:
        print("😟 结论：你的 CUDA 环境【尚不完善】，请根据上方提示修复。")

if __name__ == "__main__":
    diagnose_cuda()