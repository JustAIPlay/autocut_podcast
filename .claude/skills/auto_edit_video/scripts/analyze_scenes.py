#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分镜分析脚本（使用 Poe API）
分两步完成：
1. 场景拆分
2. 生成生图提示词
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
import random
from pathlib import Path
from utils import get_env, get_project_root, get_script_paths
from poe_client import PoeClient


def clean_json_content(content: str) -> str:
    """清理 AI 输出的 JSON，修复常见格式问题"""
    # 移除 markdown 代码块标记
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 3:
            content = parts[1]
        else:
            content = content.replace("```", "")
    
    content = content.strip()
    
    # 修复中文引号问题
    content = content.replace('"', '"').replace('"', '"')
    content = content.replace(''', "'").replace(''', "'")
    
    return content


def step1_split_scenes(script_id: str, poe_client: PoeClient) -> list:
    """
    步骤 1: 场景拆分
    
    Args:
        script_id: 项目 ID
        poe_client: Poe API 客户端
        
    Returns:
        场景列表 [{"scene": 1, "text": "..."}, ...]
    """
    print("\n" + "="*60)
    print("步骤 1/2: 场景拆分")
    print("="*60)
    
    # 获取路径
    paths = get_script_paths(script_id)
    
    # 优先使用二创文案，其次使用断句文案
    transcript_path = paths["copy_recreated"]
    
    if not transcript_path.exists():
        # 如果二创文案不存在，尝试使用断句文案
        transcript_path = paths["copy_refined"]
        if not transcript_path.exists():
            raise FileNotFoundError(f"❌ 找不到文案文件: {paths['copy_recreated']}\n"
                                    f"💡 请先运行 recreate_copy.py 进行文案二创")
    
    print(f"📄 读取文案: {transcript_path}")
    with open(transcript_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 读取场景拆分 prompt
    prompt_path = get_project_root() / "PROMPTS" / "prompt_scene_split.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"❌ 找不到提示词文件: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 填充文案内容
    prompt = prompt_template.replace("{text}", text)
    
    # 调用 Poe API
    print("🤖 正在调用 Poe API 进行场景拆分...")
    response = poe_client.chat(prompt)
    
    # 清理和解析 JSON
    content = clean_json_content(response)
    
    try:
        scenes = json.loads(content)
        
        # 验证数据结构
        if not isinstance(scenes, list):
            raise ValueError("场景数据应该是一个数组")
        
        for scene in scenes:
            if "scene" not in scene or "text" not in scene:
                raise ValueError("每个场景必须包含 'scene' 和 'text' 字段")
        
        print(f"✅ 场景拆分完成，共 {len(scenes)} 个分镜")
        
        # 保存中间结果
        temp_path = paths["scenes"].parent / f"{script_id}_scenes_temp.json"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(scenes, f, ensure_ascii=False, indent=2)
        print(f"💾 中间结果已保存: {temp_path}")
        
        return scenes
        
    except json.JSONDecodeError as e:
        print(f"❌ 解析 JSON 失败: {e}")
        print(f"错误位置: line {e.lineno}, column {e.colno}")
        print("\n原始输出（前 1000 字符）:")
        print(content[:1000] if len(content) > 1000 else content)
        raise
    except Exception as e:
        print(f"❌ 处理场景数据失败: {e}")
        raise


def step2_generate_prompts(script_id: str, scenes: list, poe_client: PoeClient) -> list:
    """
    步骤 2: 生成生图提示词（只返回 scene 和 prompt，不包含 text）
    
    Args:
        script_id: 项目 ID
        scenes: 步骤 1 生成的场景列表
        poe_client: Poe API 客户端
        
    Returns:
        只包含 scene 和 prompt 的场景列表 [{"scene": 1, "prompt": "..."}, ...]
    """
    print("\n" + "="*60)
    print("步骤 2/2: 生成生图提示词")
    print("="*60)
    
    # 读取生图提示词 prompt
    prompt_path = get_project_root() / "PROMPTS" / "prompt_image_generation.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"❌ 找不到提示词文件: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 将场景列表转换为格式化的字符串
    scenes_text = json.dumps(scenes, ensure_ascii=False, indent=2)
    
    # 填充场景内容
    prompt = prompt_template.replace("{scenes}", scenes_text)
    
    # 调用 Poe API
    print(f"🎨 正在为 {len(scenes)} 个分镜生成生图提示词...")
    response = poe_client.chat(prompt)
    
    # 清理和解析 JSON
    content = clean_json_content(response)
    
    try:
        prompts_only = json.loads(content)
        
        # 验证数据结构（只验证 scene 和 prompt，不验证 text）
        if not isinstance(prompts_only, list):
            raise ValueError("返回数据应该是一个数组")
        
        for item in prompts_only:
            if "scene" not in item or "prompt" not in item:
                raise ValueError("每个场景必须包含 'scene' 和 'prompt' 字段")
        
        print(f"✅ 生图提示词生成完成")
        
        # 验证数量一致性
        if len(prompts_only) != len(scenes):
            print(f"⚠️ 警告: 输入场景数 ({len(scenes)}) 与输出场景数 ({len(prompts_only)}) 不一致")
        
        return prompts_only
        
    except json.JSONDecodeError as e:
        print(f"❌ 解析 JSON 失败: {e}")
        print(f"错误位置: line {e.lineno}, column {e.colno}")
        print("\n原始输出（前 1000 字符）:")
        print(content[:1000] if len(content) > 1000 else content)
        raise
    except Exception as e:
        print(f"❌ 处理提示词数据失败: {e}")
        raise


def analyze_scenes(script_id: str, book_name: str = None):
    """
    完整的分镜分析流程
    
    Args:
        script_id: 项目 ID
        book_name: 书名（可选），用于保存元数据
        
    Returns:
        是否成功
    """
    try:
        # 初始化 Poe 客户端
        poe_client = PoeClient()
        
        print("\n" + "="*60)
        print(f"🎬 开始分镜分析: {script_id}")
        print("="*60)
        
        # 步骤 1: 场景拆分（返回 [{"scene": 1, "text": "..."}, ...]）
        scenes = step1_split_scenes(script_id, poe_client)
        
        # 步骤 2: 生成生图提示词（只返回 [{"scene": 1, "prompt": "..."}, ...]）
        prompts_only = step2_generate_prompts(script_id, scenes, poe_client)
        
        # 合并步骤1和步骤2的结果
        print("\n" + "="*60)
        print("🔄 合并场景文本和生图提示词...")
        print("="*60)
        
        # 创建 scene -> text 的映射
        scenes_dict = {scene["scene"]: scene["text"] for scene in scenes}
        
        # 创建 scene -> (prompt, flag) 的映射，flag 用于判断是否需要图生图
        prompts_dict = {}
        for item in prompts_only:
            prompts_dict[item["scene"]] = {
                "prompt": item["prompt"],
                "flag": item.get("flag", None)  # 保存 Poe 返回的 flag
            }
        
        # 合并数据并添加随机动效
        final_scenes = []
        
        # 定义可用的动效类型
        effect_types = [
            {
                "type": "zoom_in",
                "zoom_start": 1.0,
                "zoom_end": 1.3,
                "speed": "slow"
            },
            {
                "type": "zoom_in",
                "zoom_start": 1.0,
                "zoom_end": 1.2,
                "speed": "normal"
            },
            {
                "type": "zoom_out",
                "zoom_start": 1.3,
                "zoom_end": 1.0,
                "speed": "slow"
            },
            {
                "type": "zoom_out",
                "zoom_start": 1.2,
                "zoom_end": 1.0,
                "speed": "normal"
            },
            {
                "type": "pan_right",
                "zoom_start": 1.2,
                "zoom_end": 1.2,
                "pan_direction": "right",
                "speed": "slow"
            },
            {
                "type": "pan_left",
                "zoom_start": 1.2,
                "zoom_end": 1.2,
                "pan_direction": "left",
                "speed": "slow"
            }
        ]
        
        for scene_num in sorted(scenes_dict.keys()):
            if scene_num not in prompts_dict:
                print(f"⚠️ 警告: 场景 {scene_num} 缺少 prompt，跳过")
                continue
            
            # 随机选择一个动效
            effect = random.choice(effect_types).copy()
            
            prompt_data = prompts_dict[scene_num]
            scene_data = {
                "scene": scene_num,
                "text": scenes_dict[scene_num],
                "prompt": prompt_data["prompt"],
                "effect": effect
            }
            # 如果有 flag，添加到场景数据中
            if prompt_data["flag"] is not None:
                scene_data["flag"] = prompt_data["flag"]
            final_scenes.append(scene_data)
        
        if len(final_scenes) != len(scenes):
            print(f"⚠️ 警告: 合并后场景数 ({len(final_scenes)}) 与原始场景数 ({len(scenes)}) 不一致")
        else:
            print(f"✅ 合并完成，共 {len(final_scenes)} 个分镜")
        
        # 保存最终结果（新格式：包含 metadata）
        paths = get_script_paths(script_id)
        output_path = paths["scenes"]
        
        from datetime import datetime
        
        # 包装成包含元数据的格式
        scenes_data = {
            "metadata": {
                "script_id": script_id,
                "book_name": book_name,  # 可能为 None
                "created_at": datetime.now().isoformat()
            },
            "scenes": final_scenes
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scenes_data, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*60)
        print(f"✅ 分镜分析完成！")
        print(f"📁 输出文件: {output_path}")
        print(f"📊 共 {len(final_scenes)} 个分镜")
        if book_name:
            print(f"📖 书名: {book_name}")
        print("="*60)
        
        # 清理临时文件
        temp_path = paths["scenes"].parent / f"{script_id}_scenes_temp.json"
        if temp_path.exists():
            temp_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 分镜分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="分析场景并生成分镜")
    parser.add_argument("script_id", help="脚本 ID")
    parser.add_argument("--book", "-b", type=str, default=None,
                       help="书名（用于保存元数据，如: '身体重置'）")
    
    args = parser.parse_args()
    
    success = analyze_scenes(args.script_id, book_name=args.book)
    sys.exit(0 if success else 1)
