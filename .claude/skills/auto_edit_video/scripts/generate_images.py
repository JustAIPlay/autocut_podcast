#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

# 导入同目录下的 jimeng_client
from jimeng_client import JimengClient


def find_book_image(book_name: str, assets_dir: Path) -> str:
    """
    在 assets 目录下查找书籍图片
    
    Args:
        book_name: 书籍名称（不含书名号）
        assets_dir: assets 目录路径
        
    Returns:
        图片路径，未找到返回 None
    """
    if not assets_dir.exists():
        return None

    # 支持的图片扩展名
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']

    # 首先尝试精确匹配（不含扩展名）
    for ext in image_extensions:
        image_path = assets_dir / f"{book_name}{ext}"
        if image_path.exists():
            return str(image_path)

    # 其次尝试模糊匹配（文件名包含书名）
    for file in assets_dir.iterdir():
        if file.suffix.lower() in image_extensions:
            if book_name in file.stem:
                return str(file)

    return None


def generate_single_image(client, scene, script_id, images_dir, reference_image=None):
    """
    为单个场景生成图片
    
    Args:
        client: JimengClient 实例
        scene: 场景配置字典
        script_id: 项目标识符
        images_dir: 图片输出目录
        reference_image: 参考图路径（可选）
    """
    idx = scene['scene']
    
    # 如果已经有图片路径且文件存在，跳过
    if scene.get('image_path') and Path(scene['image_path']).exists():
        return {
            'success': True,
            'scene': idx,
            'skipped': True,
            'message': f"分镜 {idx} 已有图片，跳过"
        }
    
    prompt = scene['prompt']
    flag = scene.get('flag', 0)
    
    # 判断是否需要使用参考图
    use_reference = flag == 1 and reference_image is not None
    
    try:
        # 使用新的命名规则：script_id_scene.png
        filename_prefix = f"{script_id}_{idx}"
        
        if use_reference:
            images = client.text_to_image(
                prompt=prompt,
                output_dir=str(images_dir),
                filename_prefix=filename_prefix,
                reference_image=reference_image,
                is_local_image=True
            )
        else:
            images = client.text_to_image(
                prompt=prompt,
                output_dir=str(images_dir),
                filename_prefix=filename_prefix
            )
        
        if images and len(images) > 0:
            main_image = images[0]
            image_path = str(Path(main_image['local_path']).absolute())
            
            mode_text = "（参考图模式）" if use_reference else ""
            return {
                'success': True,
                'scene': idx,
                'skipped': False,
                'image_path': image_path,
                'message': f"分镜 {idx} 生图成功{mode_text}"
            }
        else:
            return {
                'success': False,
                'scene': idx,
                'skipped': False,
                'message': f"分镜 {idx} 生图失败：未返回图片"
            }
            
    except Exception as e:
        return {
            'success': False,
            'scene': idx,
            'skipped': False,
            'message': f"分镜 {idx} 生图失败: {e}"
        }


def generate_single_cover(script_id):
    """
    生成单张播客封面图
    
    Args:
        script_id: 项目标识符
    
    输入: copys/{id}_image_prompt.txt
    输出: images/{id}/cover.jpg
    """
    paths = get_script_paths(script_id)
    prompt_file = paths["image_prompt"]
    images_dir = paths["images_dir"]
    cover_image = paths["cover_image"]
    
    if not prompt_file.exists():
        print(f"❌ 找不到提示词文件: {prompt_file}")
        print(f"   请先运行: python generate_podcast_image_prompt.py {script_id}")
        return False
    
    # 读取提示词
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt = f.read().strip()
    
    if not prompt:
        print("❌ 提示词文件为空")
        return False
    
    print(f"🎨 正在生成播客封面图...")
    print(f"📝 提示词: {prompt[:100]}...")
    
    client = JimengClient()
    if not client.session_id:
        print("❌ 错误: 未在 .env 中设置 JIMENG_SESSION_ID")
        return False
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        images = client.text_to_image(
            prompt=prompt,
            output_dir=str(images_dir),
            filename_prefix="cover"
        )
        
        if images and len(images) > 0:
            main_image = images[0]
            # 重命名为 cover.jpg
            downloaded_path = Path(main_image['local_path'])
            if downloaded_path.exists() and downloaded_path != cover_image:
                import shutil
                shutil.move(str(downloaded_path), str(cover_image))
            
            print(f"✅ 封面图生成成功！")
            print(f"   - 输出文件: {cover_image}")
            return True
        else:
            print("❌ 封面图生成失败：未返回图片")
            return False
            
    except Exception as e:
        print(f"❌ 封面图生成失败: {e}")
        return False


def generate_images(script_id, limit=None, batch_size=30, book_name=None):
    """
    根据分镜脚本批量并发生成图片
    
    Args:
        script_id: 项目标识符
        limit: 限制生成的图片数量，None 表示全部生成
        batch_size: 每批并发生成的数量，默认30
        book_name: 书籍名称（可选，用于查找参考图）
    """
    # 使用统一的路径管理
    paths = get_script_paths(script_id)
    scenes_json = paths["scenes"]
    images_dir = paths["images_dir"]
    
    # assets 目录路径
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
    
    # 兼容新旧格式
    if isinstance(scenes_data, dict) and "scenes" in scenes_data:
        scenes = scenes_data["scenes"]  # 新格式
    else:
        scenes = scenes_data  # 旧格式（纯数组）
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 处理书名和参考图
    reference_image = None
    if book_name:
        print(f"📚 使用书籍: {book_name}")
        reference_image = find_book_image(book_name, assets_dir)
        if reference_image:
            print(f"   ✅ 找到书籍图片: {reference_image}")
            print(f"   📌 flag=1 的场景将使用参考图模式")
        else:
            print(f"   ⚠️ 未找到《{book_name}》的图片，将使用常规生图")
    
    print(f"\n🚀 正在为项目 {script_id} 生成图片...")
    print(f"📊 总场景数: {len(scenes)}")
    
    if limit:
        print(f"⚠️ 测试模式: 仅生成前 {limit} 张图片")
        scenes = scenes[:limit]
    
    # 按批次处理
    total_scenes = len(scenes)
    total_batches = (total_scenes + batch_size - 1) // batch_size
    
    print(f"📦 批次配置: 每批 {batch_size} 张，共 {total_batches} 批")
    print(f"{'='*60}")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    ref_mode_count = 0
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total_scenes)
        batch_scenes = scenes[start_idx:end_idx]
        
        print(f"\n🔄 批次 {batch_idx + 1}/{total_batches}: 处理场景 {start_idx + 1}-{end_idx}")
        print(f"{'-'*60}")
        
        # 批量并发生成
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # 提交所有任务
            futures = {
                executor.submit(
                    generate_single_image, 
                    client, 
                    scene, 
                    script_id, 
                    images_dir,
                    reference_image
                ): scene
                for scene in batch_scenes
            }
            
            # 处理完成的任务
            for future in as_completed(futures):
                scene = futures[future]
                try:
                    result = future.result()
                    
                    if result['skipped']:
                        print(f"⏩ {result['message']}")
                        skipped_count += 1
                    elif result['success']:
                        # 更新场景的 image_path
                        scene['image_path'] = result['image_path']
                        print(f"✅ {result['message']}")
                        success_count += 1
                        if "参考图模式" in result['message']:
                            ref_mode_count += 1
                    else:
                        print(f"❌ {result['message']}")
                        failed_count += 1
                        
                except Exception as e:
                    scene_idx = scene.get('scene', '?')
                    print(f"❌ 分镜 {scene_idx} 处理异常: {e}")
                    failed_count += 1
        
        # 批次间隔（避免API限流）
        if batch_idx < total_batches - 1:
            print(f"\n⏸️  批次间隔：等待 2 秒...")
            time.sleep(2)
    
    # 保存更新后的 scenes.json（保持元数据）
    print(f"\n{'='*60}")
    print(f"💾 保存更新后的场景配置...")
    
    if isinstance(scenes_data, dict) and "metadata" in scenes_data:
        # 新格式：保持 metadata
        scenes_data["scenes"] = scenes
        output_data = scenes_data
    else:
        # 旧格式：保持兼容
        output_data = scenes
    
    with open(scenes_json, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # 统计结果
    print(f"\n{'='*60}")
    print(f"✅ 图片生成完成！")
    print(f"📊 统计结果:")
    print(f"   - 成功: {success_count} 张")
    if ref_mode_count > 0:
        print(f"     └─ 其中参考图模式: {ref_mode_count} 张")
    print(f"   - 失败: {failed_count} 张")
    print(f"   - 跳过: {skipped_count} 张")
    print(f"   - 总计: {total_scenes} 张")
    print(f"{'='*60}")
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据分镜脚本批量生成图片")
    parser.add_argument("script_id", help="项目标识符 (script_id)")
    parser.add_argument("--test-first", action="store_true", 
                        help="测试模式：仅生成第一张图片")
    parser.add_argument("--limit", type=int, default=None,
                        help="限制生成的图片数量")
    parser.add_argument("--batch-size", type=int, default=30,
                        help="每批并发生成的数量（默认30）")
    parser.add_argument("--book-name", "-b", type=str, default=None,
                        help="书籍名称（不含书名号），用于查找参考图，flag=1 的场景将使用参考图模式")
    parser.add_argument("--single", "-s", action="store_true",
                        help="播客模式：仅生成单张封面图")
    
    args = parser.parse_args()
    
    if args.single:
        # 播客模式：生成单张封面图
        success = generate_single_cover(args.script_id)
        sys.exit(0 if success else 1)
    else:
        # 常规模式：批量生成分镜图片
        limit = 1 if args.test_first else args.limit
        
        generate_images(
            script_id=args.script_id, 
            limit=limit, 
            batch_size=args.batch_size,
            book_name=args.book_name
        )