#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生图提示词合规检查脚本

功能：
1. 读取 scenes.json 中的生图提示词
2. 调用 Poe API 进行合规审查
3. 自动修正违规内容
4. 输出审查后的 scenes.json
"""
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
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


def load_compliance_rules() -> str:
    """加载合规规则参考文档 (references/compliance.md)"""
    # 首先尝试 skill 内部的 references 目录
    script_dir = Path(__file__).parent
    ref_path = script_dir.parent / "references" / "compliance.md"
    
    # 如果不存在，尝试项目根目录
    if not ref_path.exists():
        ref_path = get_project_root() / "ref.md"
    
    if not ref_path.exists():
        print(f"⚠️ 警告：未找到合规参考文档，将使用内置规则")
        return "使用内置的即梦AI社区规范"
    
    print(f"📋 加载合规规则: {ref_path}")
    with open(ref_path, 'r', encoding='utf-8') as f:
        return f.read()


def compliance_check(script_id: str, dry_run: bool = False) -> bool:
    """
    执行生图提示词合规检查
    
    Args:
        script_id: 项目 ID
        dry_run: 如果为 True，只检查不修改原文件
        
    Returns:
        是否所有提示词都通过合规检查
    """
    try:
        print("\n" + "="*60)
        print(f"🔍 开始合规检查: {script_id}")
        print("="*60)
        
        # 获取路径
        paths = get_script_paths(script_id)
        scenes_path = paths["scenes"]
        
        if not scenes_path.exists():
            raise FileNotFoundError(f"❌ 找不到场景文件: {scenes_path}")
        
        # 读取 scenes.json
        print(f"📄 读取场景文件: {scenes_path}")
        with open(scenes_path, 'r', encoding='utf-8') as f:
            scenes_data = json.load(f)
        
        # 兼容新旧两种格式
        if isinstance(scenes_data, dict) and "scenes" in scenes_data:
            metadata = scenes_data.get("metadata", {})
            scenes = scenes_data["scenes"]
        else:
            metadata = {}
            scenes = scenes_data
        
        print(f"📊 共 {len(scenes)} 个分镜待审查")
        
        # 提取所有 prompt
        prompts_to_check = []
        for scene in scenes:
            prompts_to_check.append({
                "scene": scene["scene"],
                "prompt": scene["prompt"]
            })
        
        # 读取合规检查 prompt 模板
        prompt_path = get_project_root() / "PROMPTS" / "prompt_compliance_check.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"❌ 找不到提示词文件: {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # 加载合规规则
        compliance_rules = load_compliance_rules()
        
        # 填充模板
        prompts_json = json.dumps(prompts_to_check, ensure_ascii=False, indent=2)
        prompt = prompt_template.replace("{compliance_rules}", compliance_rules)
        prompt = prompt.replace("{prompts}", prompts_json)
        
        # 初始化 Poe 客户端并调用 API
        poe_client = PoeClient()
        print("🤖 正在调用 Poe API 进行合规审查...")
        response = poe_client.chat(prompt)
        
        # 解析审查结果
        content = clean_json_content(response)
        
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ 解析审查结果失败: {e}")
            print(f"\n原始输出（前 2000 字符）:")
            print(content[:2000] if len(content) > 2000 else content)
            raise
        
        # 显示审查摘要
        summary = result.get("compliance_summary", {})
        print("\n" + "-"*40)
        print("📋 审查结果摘要")
        print("-"*40)
        print(f"   总场景数: {summary.get('total_scenes', len(scenes))}")
        print(f"   ✅ 通过: {summary.get('passed', 0)}")
        print(f"   🔧 已修正: {summary.get('modified', 0)}")
        print(f"   ❌ 拦截: {summary.get('blocked', 0)}")
        
        # 处理审查结果
        checked_scenes = result.get("scenes", [])
        scene_results = {s["scene"]: s for s in checked_scenes}
        
        modified_count = 0
        blocked_count = 0
        
        for scene in scenes:
            scene_num = scene["scene"]
            check_result = scene_results.get(scene_num)
            
            if not check_result:
                print(f"⚠️ 场景 {scene_num} 未返回审查结果，保持原样")
                continue
            
            status = check_result.get("status", "pass")
            
            if status == "modified":
                # 更新为修正后的提示词
                old_prompt = scene["prompt"]
                new_prompt = check_result.get("final_prompt", old_prompt)
                
                if old_prompt != new_prompt:
                    scene["prompt"] = new_prompt
                    scene["compliance_modified"] = True
                    modified_count += 1
                    
                    print(f"\n🔧 场景 {scene_num} 已修正:")
                    for issue in check_result.get("issues", []):
                        print(f"   - [{issue.get('type')}] {issue.get('description')}")
                        print(f"     修复: {issue.get('fix')}")
            
            elif status == "blocked":
                # 标记为被拦截
                scene["compliance_blocked"] = True
                blocked_count += 1
                
                print(f"\n❌ 场景 {scene_num} 被拦截:")
                for issue in check_result.get("issues", []):
                    print(f"   - [{issue.get('type')}] {issue.get('description')}")
                    print(f"     建议: {issue.get('fix')}")
            
            else:
                # 通过
                scene["compliance_passed"] = True
        
        # 保存结果
        if not dry_run:
            # 更新元数据
            metadata["compliance_checked"] = True
            metadata["compliance_modified_count"] = modified_count
            metadata["compliance_blocked_count"] = blocked_count
            
            from datetime import datetime
            metadata["compliance_checked_at"] = datetime.now().isoformat()
            
            # 保存
            output_data = {
                "metadata": metadata,
                "scenes": scenes
            }
            
            with open(scenes_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 已保存审查结果: {scenes_path}")
        else:
            print("\n🔍 预览模式，未修改原文件")
        
        # 最终结果
        print("\n" + "="*60)
        if blocked_count > 0:
            print(f"⚠️ 合规检查完成，有 {blocked_count} 个场景被拦截，需人工处理")
            print("   请检查被拦截的场景并手动修改后重新运行")
            return False
        elif modified_count > 0:
            print(f"✅ 合规检查完成，已自动修正 {modified_count} 个场景")
            return True
        else:
            print("✅ 所有场景均通过合规检查")
            return True
        
    except Exception as e:
        print(f"\n❌ 合规检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生图提示词合规检查")
    parser.add_argument("script_id", help="脚本 ID")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="预览模式，只检查不修改原文件")
    
    args = parser.parse_args()
    
    success = compliance_check(args.script_id, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
