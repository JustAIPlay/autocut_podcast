#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复 SoulX-Podcast 源代码到修改前的状态
"""
import sys
from pathlib import Path


def restore_backup(soulx_path: str = None) -> bool:
    """
    恢复 SoulX-Podcast 源代码备份

    Args:
        soulx_path: SoulX-Podcast 安装目录路径

    Returns:
        bool: 恢复是否成功
    """
    if soulx_path is None:
        soulx_path = "D:/AI/SoulX-Podcast"

    soulx_path = Path(soulx_path)
    source_file = soulx_path / "soulxpodcast" / "models" / "soulxpodcast.py.backup"
    target_file = soulx_path / "soulxpodcast" / "models" / "soulxpodcast.py"

    if not source_file.exists():
        print(f"❌ 备份文件不存在: {source_file}")
        return False

    print(f"📄 恢复文件: {target_file}")

    # 读取备份文件
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 写入目标文件
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ 恢复完成！")
    print(f"   已将 {source_file.name} 恢复到 {target_file.name}")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="恢复 SoulX-Podcast 源代码备份")
    parser.add_argument("--path", "-p", help="SoulX-Podcast 安装目录路径", default="D:/AI/SoulX-Podcast")

    args = parser.parse_args()

    success = restore_backup(args.path)
    sys.exit(0 if success else 1)
