#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 SoulX-Podcast 源代码中的音频切片 bug

问题描述：生成的音频中包含了参考音频，参考音频在最前面重复几次，后面才是生成的 TTS。

原因：在 soulxpodcast/models/soulxpodcast.py 第 159 行，音频切片的结束索引使用错误，
导致切片包含了参考音频部分。

修复方法：将结束索引从 generated_mels_lens[0].item() 改为 generated_mels.shape[2]，
这样就能正确提取从参考音频结束到整个生成音频末尾的部分。
"""
import sys
import os
from pathlib import Path


def fix_soulx_bug(soulx_path: str = None) -> bool:
    """
    修复 SoulX-Podcast 源代码中的音频切片 bug

    Args:
        soulx_path: SoulX-Podcast 安装目录路径，如果不提供则从环境变量读取

    Returns:
        bool: 修复是否成功
    """
    # 获取 SoulX-Podcast 路径
    if soulx_path is None:
        soulx_path = os.environ.get("SOULX_PODCAST_PATH", "")

    if not soulx_path:
        print("❌ 请提供 SoulX-Podcast 安装目录路径")
        print("   方法1: 设置环境变量 SOULX_PODCAST_PATH")
        print("   方法2: 直接传入路径参数")
        return False

    soulx_path = Path(soulx_path)
    if not soulx_path.exists():
        print(f"❌ SoulX-Podcast 目录不存在: {soulx_path}")
        return False

    # 源代码文件路径
    source_file = soulx_path / "soulxpodcast" / "models" / "soulxpodcast.py"

    if not source_file.exists():
        print(f"❌ 源代码文件不存在: {source_file}")
        return False

    print(f"📄 源代码文件: {source_file}")

    # 读取文件内容
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找需要修复的行
    old_line = '            mel = generated_mels[:, :, prompt_mels_lens[0].item():generated_mels_lens[0].item()]'
    new_line = '            mel = generated_mels[:, :, prompt_mels_lens[0].item():]'

    if old_line not in content:
        print("⚠️  未找到需要修复的代码行，可能已经修复过或版本不同")
        print(f"   查找的代码: {old_line}")

        # 尝试查找类似的代码
        if 'generated_mels[:, :, prompt_mels_lens[0].item():' in content:
            print("✅ 找到类似的代码，可能已经修复")
            return True
        return False

    # 备份原文件
    backup_file = source_file.with_suffix('.py.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 已备份原文件: {backup_file}")

    # 修复代码
    content = content.replace(old_line, new_line)

    # 写入修复后的文件
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ 修复完成！")
    print(f"   修改前: {old_line}")
    print(f"   修改后: {new_line}")
    print("\n💡 提示：修复后重新运行 generate_podcast_tts.py 即可生成正确的音频")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="修复 SoulX-Podcast 音频切片 bug")
    parser.add_argument("--path", "-p", help="SoulX-Podcast 安装目录路径")

    args = parser.parse_args()

    success = fix_soulx_bug(args.path)
    sys.exit(0 if success else 1)
