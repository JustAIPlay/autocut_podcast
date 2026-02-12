import json
import os
import sys
import io
from pathlib import Path
from openai import OpenAI
from utils import get_env, get_script_paths, get_project_root

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_refined_text(raw_text):
    """调用 DeepSeek API 优化文案"""
    # 使用统一的环境变量管理
    api_key = get_env("DEEPSEEK_API_KEY")
    base_url = get_env("DEEPSEEK_BASE_URL", "https://maas-api.lanyun.net/v1")
    model_name = get_env("DEEPSEEK_MODEL", "/maas/deepseek-ai/DeepSeek-V3.2")
    
    if not api_key:
        print("❌ 请在 .env 中设置 DEEPSEEK_API_KEY")
        return None
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # 读取提示词模板
    prompt_path = get_project_root() / "PROMPTS" / "refine_subtitles.md"
    if not prompt_path.exists():
        print(f"❌ 找不到提示词文件: {prompt_path}")
        return None
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    
    # 填充文案内容
    prompt = prompt_template.replace("{raw_text}", raw_text)
    
    # 读取系统提示词
    system_prompt_path = get_project_root() / "PROMPTS" / "refine_subtitles_system.md"
    if system_prompt_path.exists():
        with open(system_prompt_path, 'r', encoding='utf-8') as f:
            system_content = f.read().strip()
    else:
        system_content = "你是一个专业的数据处理助手，严格遵守输出格式。"

    try:
        print(f"🤖 正在调用 DeepSeek ({model_name}) 进行语义优化...")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # 降低随机性，保证稳定性
            stream=False
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"调用失败: {e}")
        return None

def improve(input_txt, output_txt):
    """
    调用大模型优化文案，进行断句处理。
    
    输入：二创文案文本
    输出：断句后的文本（每行 ≤15 字）
    """
    if not os.path.exists(input_txt):
        print(f"错误：找不到输入文件 {input_txt}")
        return False

    # 1. 读取二创文案
    with open(input_txt, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    if not raw_text:
        print("错误：文件内容为空")
        return False

    print(f"📄 输入文案字数: {len(raw_text)}")

    # 2. 调用大模型优化断句
    refined_result = get_refined_text(raw_text)

    if not refined_result:
        print("处理失败。")
        return False

    # 3. 保存断句后的文本
    # 确保输出目录存在
    Path(output_txt).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(refined_result)

    print(f"✅ 语义断句完成！")
    print(f"   - 输出文件: {output_txt}")
    print(f"")
    print(f"⚠️ 下一步：请运行 match_subtitle_timeline.py 生成字幕")
    print("-" * 30)
    print("预览前几行内容：")
    print("\n".join(refined_result.splitlines()[:5]))
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python refine_subtitles.py <script_id>")
        sys.exit(1)

    script_id = sys.argv[1]
    # 使用统一的路径管理
    paths = get_script_paths(script_id)
    
    # 输入：二创文案（不再使用 Whisper JSON）
    input_txt = paths["copy_recreated"]
    output_txt = paths["copy_refined"]

    success = improve(str(input_txt), str(output_txt))
    sys.exit(0 if success else 1)


