# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 AI 驱动的**播客视频二创**工具。主要功能是基于对标播客视频进行文案二次创作，并自动生成新的播客视频。

工作流程：提取音频 → Qwen3-ASR 转录 → 智谱 API 说话人识别+二创 → SoulX-Podcast 配音 → ForcedAligner 对齐 → 生成字幕 → DeepSeek 生图提示词 → 即梦 API 生图 → FFmpeg 合成视频。

## 环境准备

### 系统依赖
- **FFmpeg**: 需要安装到 `C:\ffmpeg\bin\` 或项目的 `tools\ffmpeg\` 目录
  ```bash
  C:\ffmpeg\bin\ffmpeg.exe -version  # 验证安装
  ```

### Python 依赖
```bash
pip install -r requirements.txt
```

### 模型部署

**Qwen3-ASR (本地 GPU)**
```bash
pip install qwen-asr soundfile librosa
python -c "from qwen_asr import QwenASR; print('✅ Qwen3-ASR OK')"
```

**SoulX-Podcast (本地 GPU)**
```bash
# 克隆仓库
git clone https://github.com/Soul-AILab/SoulX-Podcast.git
# 下载模型
huggingface-cli download Soul-AILab/SoulX-Podcast-1.7B --local-dir pretrained_models/SoulX-Podcast-1.7B
```

### 环境变量 (.env)
```
# 必需 API
ZHIPU_API_KEY=your_zhipu_api_key      # 文案二创 (智谱 GLM-4-Flash)
JIMENG_SESSION_ID=your_jimeng_session_id # 即梦生图
DEEPSEEK_API_KEY=your_deepseek_api_key   # 生图提示词

# 智谱 API 配置
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_MODEL=glm-4-flash

# SoulX-Podcast 配置
SOULX_PODCAST_PATH=D:/AI/SoulX-Podcast
SOULX_MODEL_PATH=pretrained_models/SoulX-Podcast-1.7B
SOULX_VOICE_S1=D:/AI/SoulX-Podcast/voices/speaker1.wav
SOULX_VOICE_S2=D:/AI/SoulX-Podcast/voices/speaker2.wav
# 可选：参考文本（不设置则自动从对话中提取）
# SOULX_PROMPT_TEXT_S1=这是说话人1的参考文本
# SOULX_PROMPT_TEXT_S2=这是说话人2的参考文本

# 生图参数
JIMENG_MODEL=jimeng-4.0
JIMENG_RATIO=4:3
JIMENG_RESOLUTION=2k
```

## 目录结构

```
5th_video/
├── PROMPTS/                    # AI 提示词
│   ├── prompt_podcast_recreate.md  # 播客二创
│   ├── prompt_podcast_image.md     # 封面图提示词
│   └── ...
│
├── raw_materials/              # 原始素材及中间产物
│   ├── audios/                 # {id}.mp3, {id}_podcast.mp3
│   ├── captions/               # 字幕和时间戳
│   ├── copys/                  # 文案和分镜 JSON
│   ├── images/                 # AI 生成图片
│   └── videos/                 # 原始视频
│
├── finals/                     # 最终输出视频
│
└── .claude/skills/auto_edit_video/
    ├── SKILL.md                # 详细工作流程
    └── scripts/                # 核心脚本
```

## 快速开始

### 执行播客视频二创

```
请根据脚本号:PODCAST001，剪辑播客视频
```

### 工作流程概览

| 阶段 | 脚本 | 说明 |
|------|------|------|
| 2.1 | extract_audio.py | 提取音频 |
| 2.2 | transcribe_qwen_asr.py | Qwen3-ASR 转录 |
| 3 | recreate_podcast.py | 智谱 API 说话人识别+二创 |
| 4 | generate_podcast_tts.py | SoulX-Podcast 配音 |
| 5.1 | format_podcast_subtitles.py | 格式化字幕 |
| 5.2 | forced_align.py | ForcedAligner 对齐 |
| 5.3 | match_podcast_timeline.py | 匹配字幕时间线 |
| 6.1 | generate_podcast_image_prompt.py | DeepSeek 生图提示词 |
| 6.2 | generate_images.py --single | 即梦 API 生成封面图 |
| 7 | compose_podcast_video.py | FFmpeg 合成视频 |

## 技术栈

- **转录**: Qwen3-ASR (GPU)
- **强制对齐**: Qwen3-ForcedAligner (GPU) - 支持长音频自动分段（官方限制≤5分钟，脚本自动切分）
- **播客配音**: SoulX-Podcast (GPU)
- **文案二创**: 智谱 API (GLM-4-Flash)
- **生图提示词**: DeepSeek API
- **生图**: 即梦 API (jimeng-4.0)
- **合成**: FFmpeg

## SoulX-Podcast 数据格式

### 输入文本格式

播客二创脚本使用 `[S1]`/`[S2]` 标签格式：

```
[S1] 说话人1的内容
[S2] 说话人2的内容
[S1] 说话人1继续说话
```

**重要要求**：
- 每行长度控制在 50-150 字符之间
- 长段落需要拆分成多个短句
- 保持自然的对话节奏

### JSON 格式转换

`generate_podcast_tts.py` 会自动将文本格式转换为 SoulX-Podcast 需要的 JSON 格式：

```json
{
  "speakers": {
    "S1": {
      "prompt_audio": "参考音频1.wav",
      "prompt_text": "参考文本1"
    },
    "S2": {
      "prompt_audio": "参考音频2.wav",
      "prompt_text": "参考文本2"
    }
  },
  "text": [
    ["S1", "说话人1的台词"],
    ["S2", "说话人2的台词"]
  ]
}
```

**参考文本**：
- 如果未在 `.env` 中设置 `SOULX_PROMPT_TEXT_S1/S2`
- 脚本会自动从对话中提取每个说话人的第一句话作为参考文本
- 用于声音克隆和韵律学习

**参考音频要求**：
- 时长：5-30 秒
- 格式：WAV（推荐）或 MP3
- 采样率：16kHz 或更高
- 内容：清晰的单人语音，最好包含参考文本的内容
