import stable_whisper
import json
import os

def generate_precise_assets(audio_path, output_dir="output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. 加载模型并识别
    # 'medium' 是精度和速度的最佳平衡点
    # 如果显存不足（报错 CUDA out of memory），再考虑切回 'base'
    model_size = 'medium' 
    print(f"正在加载 Whisper 模型 ({model_size})...")
    model = stable_whisper.load_model(model_size)
    
    print(f"正在识别音频: {audio_path} ...")
    try:
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            vad=True, # 修复：较新版本使用 vad=True 而非 vad_filter=True
            language='zh'
        )
    except TypeError as e:
        print(f"尝试使用 vad=True 失败，正在尝试不带 VAD 参数运行... ({e})")
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            language='zh'
        )

    # 2. 强制对齐（确保时间戳与音频波形完全吻合）
    print("正在进行时间戳对齐...")
    result = model.align(audio_path, result, language='zh')

    # 3. 导出字幕
    srt_path = os.path.join(output_dir, 'subtitles.srt')
    # 导出包含词级高亮标签的原始 SRT，供预览对齐精度
    result.to_srt_vtt(srt_path, word_level=True)
    
    # 4. 导出详细的 JSON 数据
    # 这份数据将包含每一个字的精确时间，是后续交给 AI 进行语义断句的核心依据
    subtitle_data = result.to_dict()
    json_path = os.path.join(output_dir, 'subtitles.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(subtitle_data, f, ensure_ascii=False, indent=2)

    print(f"✓ 已生成字幕: {srt_path}")
    print(f"✓ 已生成数据: {json_path}")
    return subtitle_data

def create_ffmpeg_concat(scenes, images_dir, output_file='concat.txt'):
    """
    根据分镜时间生成 FFmpeg concat 文件
    scenes: 包含 start_time, end_time, image_name 的列表
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, scene in enumerate(scenes):
            duration = scene['end_time'] - scene['start_time']
            img_path = os.path.join(images_dir, scene['image_name']).replace('\\', '/')
            f.write(f"file '{img_path}'\n")
            f.write(f"duration {duration:.3f}\n")
        
        # FFmpeg 规范：最后一张图需要重复一次
        if scenes:
            last_img = os.path.join(images_dir, scenes[-1]['image_name']).replace('\\', '/')
            f.write(f"file '{last_img}'\n")

    print(f"✓ 已生成 FFmpeg 串联表: {output_file}")

# --- 调试入口 ---
if __name__ == "__main__":
    # 使用用户提供的音频路径
    AUDIO_PATH = r"D:\channel\video_projects\2nd_video\raw_materials\audios\AITSmx000087.mp3"
    # 输出目录设在项目根目录下的 output
    OUTPUT_DIR = r"D:\channel\video_projects\2nd_video\output"
    
    if os.path.exists(AUDIO_PATH):
        generate_precise_assets(AUDIO_PATH, OUTPUT_DIR)
    else:
        print(f"错误：找不到音频文件: {AUDIO_PATH}")
        # 尝试相对路径
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        REL_PATH = os.path.join(BASE_DIR, "raw_materials", "audios", "AITSmx000087.mp3")
        if os.path.exists(REL_PATH):
            generate_precise_assets(REL_PATH, OUTPUT_DIR)
        else:
            print(f"尝试相对路径也失败了: {REL_PATH}")