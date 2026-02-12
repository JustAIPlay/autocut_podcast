import json
import os
import sys
import io
from pathlib import Path
from utils import get_script_paths

# 修复 Windows 控制台编码问题
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def format_time(seconds):
    millis = int((seconds - int(seconds)) * 1000)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def rebuild(input_json, refined_txt, output_srt):
    if not os.path.exists(input_json) or not os.path.exists(refined_txt):
        print("错误：找不到输入文件，请确保前几步已运行成功。")
        return

    # 1. 加载 segment 级别时间轴
    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
        segments = data['segments']

    # 2. 加载大模型优化后的断句
    with open(refined_txt, 'r', encoding='utf-8') as f:
        refined_lines = [line.strip() for line in f if line.strip()]

    # 3. 基于字符位置累计的时间分配算法
    # 核心思路：根据字符数量按比例分配时间
    
    # 计算总时长和总字符数
    total_duration = segments[-1]['end'] - segments[0]['start']
    total_chars = sum(len(line) for line in refined_lines)
    
    if total_chars == 0:
        print("错误：优化后的文本为空")
        return
    
    # 计算每个字符的平均时长
    char_duration = total_duration / total_chars
    
    # 为每行分配时间
    line_data = []
    current_time = segments[0]['start']  # 从第一个 segment 的开始时间开始
    
    for line in refined_lines:
        line_chars = len(line)
        line_duration = line_chars * char_duration
        
        start_time = current_time
        end_time = current_time + line_duration
        
        line_data.append({
            "text": line,
            "start": start_time,
            "end": end_time
        })
        
        current_time = end_time
    
    # 4. 微调：使用 segment 边界校准关键点
    # 找到一些锚点进行校准，提高准确性
    all_text = ''.join([seg['text'].replace(' ', '') for seg in segments])
    refined_full = ''.join([line.replace(' ', '') for line in refined_lines])
    
    # 简单校准：确保最后一行的结束时间不超过音频结束时间
    if line_data:
        line_data[-1]['end'] = segments[-1]['end']

    # 5. 生成 SRT
    srt_content = []
    for i, line in enumerate(line_data):
        srt_content.append(f"{i+1}")
        srt_content.append(f"{format_time(line['start'])} --> {format_time(line['end'])}")
        srt_content.append(line['text'])
        srt_content.append("")

    # 6. 保存最终结果
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.write("\n".join(srt_content))

    print(f"🎉 成功！最终优化版字幕已生成：{output_srt}")
    print(f"   共 {len(line_data)} 条字幕，总时长 {format_time(total_duration)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python rebuild_srt.py <script_id>")
        sys.exit(1)

    script_id = sys.argv[1]
    # 使用统一的路径管理
    paths = get_script_paths(script_id)
    
    input_json = paths["caption_refined_json"]
    refined_txt = paths["copy_refined"]
    output_srt = paths["caption_final_srt"]

    rebuild(str(input_json), str(refined_txt), str(output_srt))