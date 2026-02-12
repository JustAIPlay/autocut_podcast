"""
使用 Coze MCP genPodcastURL 生成播客音频

参数：
- input_text: 播客文本内容
- use_head_music: 是否添加片头音乐 (true/false)

返回：
- podcast_url: MP3 播放链接
- usage: token 使用统计

限制：
- input_text 最大 15000 字符
- 处理时间约 90-120 秒（取决于文本长度）
- 仅支持单人语音（不支持 S1/S2 对话切换）
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
load_dotenv()

COZE_API_TOKEN = os.getenv('COZE_API_TOKEN')
COZE_MCP_URL = os.getenv('COZE_MCP_URL', 'https://mcp.coze.cn/v1/plugins/7537547135328419903')

# Windows 控制台编码修复
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = open(sys.stdout.buffer.fileno(), mode='w', encoding='utf-8', buffering=1)


def generate_coze_podcast(input_text: str, use_head_music: bool = False, timeout: int = 480):
    """
    调用 Coze MCP genPodcastURL 生成播客音频

    Args:
        input_text: 播客文本内容（最大 15000 字符）
        use_head_music: 是否添加片头音乐
        timeout: 超时时间（秒），默认 480 秒（8 分钟）

    Returns:
        dict: {
            'podcast_url': str,        # MP3 下载链接
            'input_tokens': int,       # 输入 token 数
            'output_tokens': int,      # 输出 token 数
            'text': str                # 实际生成的文本（可能被改写）
        }
    """

    if len(input_text) > 15000:
        raise ValueError(f"输入文本过长 ({len(input_text)} > 15000 字符)")

    print(f"[INFO] Coze MCP genPodcastURL")
    print(f"[INFO] 输入文本长度: {len(input_text)} 字符")
    print(f"[INFO] 片头音乐: {use_head_music}")
    print(f"[INFO] 超时设置: {timeout} 秒 ({timeout // 60} 分钟)")
    print()

    # 构造 JSON-RPC 2.0 请求
    headers = {
        'Authorization': f'Bearer {COZE_API_TOKEN}',
        'Content-Type': 'application/json'
    }

    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {
            'name': 'genPodcastURL',
            'arguments': {
                'input_text': input_text,
                'use_head_music': use_head_music
            }
        }
    }

    try:
        print(f"[INFO] 发送请求到 Coze MCP...")
        response = requests.post(
            COZE_MCP_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
            stream=True  # 启用流式响应
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")

        # 解析 SSE 响应
        print(f"[INFO] 解析 SSE 响应...")
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data:'):
                    json_str = line_str[5:].strip()
                    try:
                        data = json.loads(json_str)
                        if 'result' in data and 'content' in data['result']:
                            for item in data['result']['content']:
                                if item.get('type') == 'text':
                                    text_content = item.get('text', '')
                                    # 解析嵌套的 JSON
                                    if 'call tool success' in text_content:
                                        start = text_content.find('{')
                                        end = text_content.rfind('}') + 1
                                        if start >= 0 and end > start:
                                            inner_json = json.loads(text_content[start:end])
                                            if inner_json.get('code') == 0:
                                                content_data = inner_json['data']['content']
                                                usage_data = inner_json['data']['usage']

                                                result = {
                                                    'podcast_url': content_data['podcast_url'],
                                                    'input_tokens': usage_data['input_text_tokens'],
                                                    'output_tokens': usage_data['output_audio_tokens'],
                                                    'text': content_data['text']
                                                }

                                                print(f"[SUCCESS] 播客音频生成成功!")
                                                print(f"[INFO] 输入 tokens: {result['input_tokens']}")
                                                print(f"[INFO] 输出 tokens: {result['output_tokens']}")
                                                print()
                                                return result
                    except json.JSONDecodeError:
                        pass

        raise Exception("未能从响应中提取 podcast_url")

    except requests.exceptions.Timeout:
        raise Exception(f"请求超时 ({timeout} 秒)，请增加超时时间或检查服务状态")
    except Exception as e:
        raise Exception(f"Coze MCP 调用失败: {e}")


def download_podcast_audio(podcast_url: str, output_path: str):
    """
    下载播客音频文件

    Args:
        podcast_url: MP3 下载链接
        output_path: 输出文件路径
    """
    print(f"[INFO] 正在下载音频: {output_path}")
    response = requests.get(podcast_url, timeout=60)
    response.raise_for_status()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(response.content)

    file_size = len(response.content)
    print(f"[SUCCESS] 音频下载完成! 大小: {file_size / 1024 / 1024:.2f} MB")
    return file_size


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="使用 Coze MCP 生成播客音频")
    parser.add_argument("--input", required=True, help="输入文本文件路径")
    parser.add_argument("--output", required=True, help="输出 MP3 文件路径")
    parser.add_argument("--use-head-music", action="store_true", help="添加片头音乐")
    parser.add_argument("--timeout", type=int, default=480, help="超时时间（秒），默认 480")

    args = parser.parse_args()

    # 读取输入文本
    with open(args.input, 'r', encoding='utf-8') as f:
        input_text = f.read()

    # 生成播客音频
    result = generate_coze_podcast(
        input_text=input_text,
        use_head_music=args.use_head_music,
        timeout=args.timeout
    )

    # 下载音频
    download_podcast_audio(result['podcast_url'], args.output)

    print()
    print(f"[INFO] 播客 URL: {result['podcast_url']}")
    print(f"[INFO] 输出文件: {args.output}")
