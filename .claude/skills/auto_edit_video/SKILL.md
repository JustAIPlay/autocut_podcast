---
name: auto-edit-podcast
description: >
  播客视频二创生成工具。从对标播客视频提取音频、通过 Qwen3-ASR 转录、使用 Poe API 进行说话人识别和文案二创、
  调用 SoulX-Podcast 生成双人播客音频、使用 ForcedAligner 对齐时间戳、生成字幕、调用即梦 API 生成封面图，最后合成视频。
  使用场景：基于对标播客视频进行文案二次创作，并自动生成二创播客视频。
  关键词：播客二创、Qwen3-ASR、SoulX-Podcast、ForcedAligner、Poe API、即梦 API、视频合成、ffmpeg
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# 播客视频二创生成工具

此技能通过 AI 流程将对标播客视频转化为全新的二创播客视频。

## 核心原则

请严格按照下面的工作流程来执行，不要遗漏任何一个步骤。

> **⚠️ 重要：Windows 环境**
> - 本项目运行在 **Windows** 系统上
> - 所有命令必须使用 **PowerShell 语法**，不要使用 Bash/Linux 语法
> - 路径使用 Windows 格式：`D:\channel\video_projects\5th_video\`
> - 执行 Python 脚本时直接使用：`python scripts/xxx.py`

## 工作流程

你将按照以下 7 个阶段执行播客视频二创任务：

### 阶段 1: 环境检测与准备

**目标**: 确保所有必需工具、API 配置和模型都已就绪。

1. **基础工具检查**
   - FFmpeg: `ffmpeg -version` (用于音视频处理)
   - Python: `python --version` (建议 3.10+)

2. **GPU 加速检查**
   - 运行 `nvidia-smi` 确认 GPU 可用

3. **模型检查**
   ```powershell
   python -c "from qwen_asr import QwenASR; print('✅ Qwen3-ASR 已安装')"
   python -c "from qwen_asr import QwenForcedAligner; print('✅ Qwen3-ForcedAligner 已安装')"
   python -c "import s3tokenizer; print('✅ s3tokenizer 已安装')"
   ```
   > **SoulX-Podcast 依赖**: `pip install s3tokenizer`
   > SoulX-Podcast 需要单独部署，参见 https://github.com/Soul-AILab/SoulX-Podcast

4. **API 配置检查**
   - 检查根目录是否存在 `.env` 文件
   - 确认 `POE_API_KEY`、`JIMENG_SESSION_ID`、`DEEPSEEK_API_KEY` 已配置
   - 确认 `SOULX_PODCAST_PATH`、`SOULX_VOICE_S1`、`SOULX_VOICE_S2` 已配置

5. **目录结构确认**
   - 输入视频：`raw_materials/videos/`
   - 中间音频：`raw_materials/audios/`
   - 文本/文案：`raw_materials/copys/`
   - 生成图片：`raw_materials/images/`
   - 字幕文件：`raw_materials/captions/`
   - 最终视频：`finals/`

---

### 阶段 2: 音频提取与转录

**目标**: 从对标播客视频提取音频，使用 Qwen3-ASR 转录原始对话。

1. **提取音频**: `python scripts/extract_audio.py <script_id>`
   - 输出：`raw_materials/audios/{script_id}.mp3`

2. **Qwen3-ASR 转录**: `python scripts/transcribe_qwen_asr.py <script_id>`
   - 输出：`raw_materials/copys/{id}_original.txt`（原始转录，无说话人标注）

---

### 阶段 3: 文案二创（含说话人识别）

**目标**: 调用 Poe API (Gemini 2.5 Flash) 对原文案进行说话人识别和二次创作。

1. **播客文案二创**: `python scripts/recreate_podcast.py <script_id>`
   - 使用 `PROMPTS/prompt_podcast_recreate.md` 提示词
   - 输出：`raw_materials/copys/{id}_podcast.txt`（`[S1]`/`[S2]` 格式）

**输出格式示例**：
```
[S1] 今天我们来聊聊关于睡眠的话题
[S2] 是的，失眠已经成为现代人的通病了
[S1] 我之前也有这个问题，后来通过调整作息改善了很多
```

---

### 阶段 4: 播客音频生成

**目标**: 使用 SoulX-Podcast 生成双人播客音频。

1. **SoulX-Podcast TTS**: `python scripts/generate_podcast_tts.py <script_id>`
   - 输入：`copys/{id}_podcast.txt`（`[S1]`/`[S2]` 格式）
   - 参考音频：从 `.env` 读取 `SOULX_VOICE_S1` 和 `SOULX_VOICE_S2`
   - 输出：`raw_materials/audios/{id}_podcast.wav`

#### 方言支持（粤语/河南话/四川话）

**普通话版本**（默认）：
- `.env` 配置：
  ```
  SOULX_MODEL_PATH=pretrained_models/SoulX-Podcast-1.7B
  SOULX_VOICE_S1=D:/path/to/mandarin_speaker1.wav
  SOULX_VOICE_S2=D:/path/to/mandarin_speaker2.wav
  ```
- 文案不含方言标签

**方言版本**（如粤语）：
- `.env` 配置：
  ```
  SOULX_MODEL_PATH=pretrained_models/SoulX-Podcast-1.7B-dialect
  SOULX_VOICE_S1=D:/AI/SoulX-Podcast/example/audios/female_cantonese.WAV
  SOULX_VOICE_S2=D:/AI/SoulX-Podcast/example/audios/male_cantonese.WAV
  ```
- 文案需包含方言标签：`[S1] <|Yue|>粤语内容` 或 `[S1] <|Henan|>河南话内容` 或 `[S1] <|Sichuan|>四川话内容`

**切换普通话/方言版本**：
1. 修改 `.env` 中的 `SOULX_MODEL_PATH` 和 `SOULX_VOICE_S1/S2`
2. 修改 `PROMPTS/prompt_podcast_recreate.md` 添加/移除方言标签要求
3. 重新运行阶段 3（文案二创）和阶段 4（TTS 生成）

---

### 阶段 5: 字幕与时间对齐

**目标**: 生成字幕并匹配时间线。

1. **字幕格式化**: `python scripts/format_podcast_subtitles.py <script_id>`
   - 输入：`copys/{id}_podcast.txt`
   - 输出：`copys/{id}_subtitle.txt`（移除 `[S1]`/`[S2]` 标签）

2. **ForcedAligner 对齐**: `python scripts/forced_align.py <script_id> --podcast`
   - 输入：`audios/{id}_podcast.mp3` + `copys/{id}_subtitle.txt`
   - 输出：`captions/{id}_word_timestamps.json`（词级时间戳）
   
   > **⚠️ 长音频自动处理**
   > - Qwen3-ForcedAligner 官方限制：单次处理 **≤5 分钟** 音频
   > - 脚本已支持自动分段：超过 4.5 分钟的音频会在静音点自动切分
   > - 分段处理后自动合并时间戳，无需手动干预
   > - 如遇 GPU 显存不足，可添加 `--cpu` 参数使用 CPU 模式

3. **时间线匹配**: `python scripts/match_podcast_timeline.py <script_id>`
   - 输入：`copys/{id}_subtitle.txt` + `captions/{id}_word_timestamps.json`
   - 输出：`captions/{id}_final.srt`

---

### 阶段 6: 封面图生成

**目标**: 调用 DeepSeek 生成图像提示词，使用即梦 API 生成封面图。

1. **生成图像提示词**: `python scripts/generate_podcast_image_prompt.py <script_id>`
   - 使用 `PROMPTS/prompt_podcast_image.md` 提示词
   - 输出：`copys/{id}_image_prompt.txt`

2. **生成封面图**: `python scripts/generate_images.py <script_id> --single`
   - 输入：`copys/{id}_image_prompt.txt`
   - 输出：`images/{id}/cover.jpg`

---

### 阶段 7: 视频合成

**目标**: 将封面图、播客音频和字幕合成最终视频。

1. **合成视频**: `python scripts/compose_podcast_video.py <script_id> --vertical`
   - 输入：`images/{id}/cover.jpg` + `audios/{id}_podcast.mp3` + `captions/{id}_final.srt`
   - 输出：`finals/{id}_final.mp4`（9:16 竖屏）

---

## 命令速查表

| 阶段 | 命令 |
|------|------|
| 2.1 | `python scripts/extract_audio.py <id>` |
| 2.2 | `python scripts/transcribe_qwen_asr.py <id>` |
| 3 | `python scripts/recreate_podcast.py <id>` |
| 4 | `python scripts/generate_podcast_tts.py <id>` |
| 5.1 | `python scripts/format_podcast_subtitles.py <id>` |
| 5.2 | `python scripts/forced_align.py <id> --podcast` |
| 5.3 | `python scripts/match_podcast_timeline.py <id>` |
| 6.1 | `python scripts/generate_podcast_image_prompt.py <id>` |
| 6.2 | `python scripts/generate_images.py <id> --single` |
| 7 | `python scripts/compose_podcast_video.py <id> --vertical` |

---

## 文件路径速查

```
raw_materials/
├── videos/{id}.mp4          # 输入：对标播客视频
├── audios/
│   ├── {id}.mp3             # 提取的原音频
│   ├── {id}_podcast.wav     # SoulX-Podcast 生成的播客音频 (WAV)
│   └── {id}_soulx_input.json # SoulX-Podcast 输入 JSON
├── copys/
│   ├── {id}_original.txt    # ASR 原始转录
│   ├── {id}_podcast.txt     # 二创文案 ([S1]/[S2] 格式)
│   ├── {id}_subtitle.txt    # 字幕文本 (移除标签)
│   └── {id}_image_prompt.txt # 封面图提示词
├── captions/
│   ├── {id}_word_timestamps.json  # 词级时间戳
│   └── {id}_final.srt       # 最终字幕
└── images/{id}/
    └── cover.jpg            # 封面图

finals/
└── {id}_final.mp4           # 最终输出视频 (9:16)
```