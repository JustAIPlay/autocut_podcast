#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给 scenes.json 添加 flag 字段
flag: true 表示需要图生图，false 表示不需要
"""
import json
import sys
from pathlib import Path

def add_flag_to_scenes(script_id: str):
    """给 scenes.json 的每个场景添加 flag 字段"""
    
    # 构建路径
    project_root = Path(__file__).parent.parent.parent.parent.parent
    scenes_path = project_root / "raw_materials" / "copys" / f"{script_id}_scenes.json"
    
    if not scenes_path.exists():
        print(f"❌ 找不到文件: {scenes_path}")
        return False
    
    # 读取现有数据
    with open(scenes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    scenes = data.get("scenes", [])
    
    # 给每个场景添加 flag 字段（如果没有的话）
    count = 0
    for scene in scenes:
        if "flag" not in scene:
            scene["flag"] = 0  # 默认为 0，不需要图生图；1 表示需要图生图
            count += 1
    
    # 保存回去
    with open(scenes_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已为 {count} 个场景添加 flag 字段")
    print(f"📁 文件: {scenes_path}")
    print(f"")
    print(f"📝 现在请手动编辑文件，将需要图生图的场景的 flag 改为 true")
    print(f"   例如：\"flag\": true")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python add_flag.py <script_id>")
        sys.exit(1)
    
    add_flag_to_scenes(sys.argv[1])
