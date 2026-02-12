#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 flag=1 的场景，使用图生图重新生成图片
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import get_script_paths, get_project_root
from jimeng_client import JimengClient


def find_book_image(book_name: str, assets_dir: Path) -> str:
    """在 assets 目录下查找书籍图片"""
    if not assets_dir.exists():
        return None

    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']

    for ext in image_extensions:
        image_path = assets_dir / f"{book_name}{ext}"
        if image_path.exists():
            return str(image_path)

    for file in assets_dir.iterdir():
        if file.suffix.lower() in image_extensions:
            if book_name in file.stem:
                return str(file)

    return None


def regenerate_single_image(client, scene, script_id, images_dir, reference_image):
    """
    重新生成单个场景的图片（使用图生图模式）
    """
    idx = scene['scene']
    prompt = scene['prompt']
    
    # 获取当前图片路径作为输入
    current_image = scene.get('image_path')
    if not current_image or not Path(current_image).exists():
        return {
            'success': False,
            'scene': idx,
            'message': f"分镜 {idx} 没有现有图片，无法进行图生图"
        }
    
    try:
        # 使用新的命名规则：script_id_scene.png
        filename_prefix = f"{script_id}_{idx}"
        
        # 先删除旧图片
        old_path = Path(current_image)
        backup_path = old_path.with_suffix('.bak.png')
        if old_path.exists():
            old_path.rename(backup_path)
        
        # 使用参考图（书籍图片）+ 当前图片进行图生图
        images = client.text_to_image(
            prompt=prompt,
            output_dir=str(images_dir),
            filename_prefix=filename_prefix,
            reference_image=reference_image,
            is_local_image=True
        )
        
        if images and len(images) > 0:
            main_image = images[0]
            image_path = str(Path(main_image['local_path']).absolute())
            
            # 删除备份
            if backup_path.exists():
                backup_path.unlink()
            
            return {
                'success': True,
                'scene': idx,
                'image_path': image_path,
                'message': f"分镜 {idx} 图生图成功"
            }
        else:
            # 恢复备份
            if backup_path.exists():
                backup_path.rename(old_path)
            
            return {
                'success': False,
                'scene': idx,
                'message': f"分镜 {idx} 图生图失败：未返回图片"
            }
            
    except Exception as e:
        # 恢复备份
        if backup_path.exists():
            backup_path.rename(old_path)
        
        return {
            'success': False,
            'scene': idx,
            'message': f"分镜 {idx} 图生图失败: {e}"
        }


def regenerate_flagged_images(script_id, book_name):
    """
    重新生成所有 flag=1 的场景图片
    """
    paths = get_script_paths(script_id)
    scenes_json = paths["scenes"]
    images_dir = paths["images_dir"]
    
    project_root = get_project_root()
    assets_dir = project_root / ".claude" / "skills" / "auto_edit_video" / "assets"
    
    if not scenes_json.exists():
        print(f"❌ 找不到分镜文件: {scenes_json}")
        return False

    client = JimengClient()
    if not client.session_id:
        print("❌ 错误: 未在 .env 中设置 JIMENG_SESSION_ID")
        return False
    
    with open(scenes_json, 'r', encoding='utf-8') as f:
        scenes_data = json.load(f)
    
    if isinstance(scenes_data, dict) and "scenes" in scenes_data:
        scenes = scenes_data["scenes"]
    else:
        scenes = scenes_data
    
    # 查找参考图
    reference_image = None
    if book_name:
        print(f"📚 使用书籍: {book_name}")
        reference_image = find_book_image(book_name, assets_dir)
        if reference_image:
            print(f"   ✅ 找到书籍图片: {reference_image}")
        else:
            print(f"   ❌ 未找到《{book_name}》的图片，无法进行图生图")
            return False
    else:
        print("❌ 必须指定书名才能进行图生图")
        return False
    
    # 筛选 flag=1 的场景
    flagged_scenes = [s for s in scenes if s.get('flag', 0) == 1]
    
    if not flagged_scenes:
        print("✅ 没有 flag=1 的场景需要重新生成")
        return True
    
    print(f"\n🚀 正在为项目 {script_id} 重新生成图片（图生图模式）...")
    print(f"📊 flag=1 场景数: {len(flagged_scenes)}")
    print(f"{'='*60}")
    
    success_count = 0
    failed_count = 0
    
    for scene in flagged_scenes:
        idx = scene['scene']
        print(f"\n🔄 处理场景 {idx}...")
        
        result = regenerate_single_image(
            client, 
            scene, 
            script_id, 
            images_dir, 
            reference_image
        )
        
        if result['success']:
            scene['image_path'] = result['image_path']
            print(f"✅ {result['message']}")
            success_count += 1
        else:
            print(f"❌ {result['message']}")
            failed_count += 1
        
        # 间隔避免限流
        time.sleep(1)
    
    # 保存更新后的 scenes.json
    print(f"\n{'='*60}")
    print(f"💾 保存更新后的场景配置...")
    
    if isinstance(scenes_data, dict) and "metadata" in scenes_data:
        scenes_data["scenes"] = scenes
        output_data = scenes_data
    else:
        output_data = scenes
    
    with open(scenes_json, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ 图生图完成！")
    print(f"📊 统计结果:")
    print(f"   - 成功: {success_count} 张")
    print(f"   - 失败: {failed_count} 张")
    print(f"{'='*60}")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 flag=1 重新生成图片（图生图模式）")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    parser.add_argument("--book-name", "-b", type=str, required=True,
                        help="书籍名称（必填，用于图生图参考）")
    
    args = parser.parse_args()
    
    regenerate_flagged_images(
        script_id=args.script_id,
        book_name=args.book_name
    )
