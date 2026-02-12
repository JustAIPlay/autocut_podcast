# 🎬 播客视频二创工作流程图

## 完整执行流程

```mermaid
flowchart TD
    subgraph Phase1["⚙️ 阶段 1: 环境检测与准备"]
        A1[🔧 FFmpeg 检查] --> A2[🖥️ GPU/CUDA 检查]
        A2 --> A3[🔑 API 配置检查<br/>POE_API_KEY<br/>JIMENG_SESSION_ID<br/>DEEPSEEK_API_KEY]
        A3 --> A4[🎙️ SoulX-Podcast 检查]
        A4 --> A5[📂 目录结构确认]
    end

    subgraph Phase2["🎙️ 阶段 2: 音频提取与转录"]
        B1["📹 播客视频<br/>raw_materials/videos/{id}.mp4"]
        B1 -->|extract_audio.py| B2["🎵 音频文件<br/>raw_materials/audios/{id}.mp3"]
        B2 -->|transcribe_qwen_asr.py| B3["📝 原始转录<br/>copys/{id}_original.txt"]
    end

    subgraph Phase3["✍️ 阶段 3: 文案二创"]
        C1["📝 原始转录"] -->|recreate_podcast.py<br/>Poe API 说话人识别+二创| C2["🎭 二创文案<br/>copys/{id}_podcast.txt<br/>[S1]/[S2] 格式"]
    end

    subgraph Phase4["🔊 阶段 4: 播客音频生成"]
        D1["🎭 二创文案"] -->|generate_podcast_tts.py<br/>SoulX-Podcast| D2["🎙️ 播客音频<br/>audios/{id}_podcast.mp3"]
    end

    subgraph Phase5["📝 阶段 5: 字幕与时间对齐"]
        E1["🎭 二创文案"] -->|format_podcast_subtitles.py| E2["字幕文本<br/>copys/{id}_subtitle.txt"]
        D2 & E2 -->|forced_align.py --podcast| E3["词级时间戳<br/>captions/{id}_word_timestamps.json"]
        E2 & E3 -->|match_podcast_timeline.py| E4["🎞️ 最终字幕<br/>captions/{id}_final.srt"]
    end

    subgraph Phase6["🖼️ 阶段 6: 封面图生成"]
        F1["🎭 二创文案"] -->|generate_podcast_image_prompt.py<br/>DeepSeek API| F2["生图提示词<br/>copys/{id}_image_prompt.txt"]
        F2 -->|generate_images.py --single<br/>即梦 API| F3["🖼️ 封面图<br/>images/{id}/cover.jpg"]
    end

    subgraph Phase7["🎬 阶段 7: 视频合成"]
        G1["🖼️ 封面图"] & G2["🎙️ 播客音频"] & G3["🎞️ 字幕"]
        G1 & G2 & G3 -->|compose_podcast_video.py| G4["🎬 最终视频<br/>finals/{id}_final.mp4<br/>（9:16 竖屏）"]
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4
    Phase4 --> Phase5
    Phase3 --> Phase6
    Phase5 & Phase6 --> Phase7

    style Phase1 fill:#e3f2fd,stroke:#1976d2
    style Phase2 fill:#fff3e0,stroke:#f57c00
    style Phase3 fill:#f3e5f5,stroke:#7b1fa2
    style Phase4 fill:#e1f5fe,stroke:#0288d1
    style Phase5 fill:#e8f5e9,stroke:#388e3c
    style Phase6 fill:#fff8e1,stroke:#ffa000
    style Phase7 fill:#fce4ec,stroke:#c2185b
```

---

## 📊 输入输出汇总表

| 阶段 | 脚本 | 输入 | 输出 |
|:----:|------|------|------|
| **1** | 环境检测 | `.env` 配置文件 | 环境就绪状态 |
| **2.1** | `extract_audio.py` | `videos/{id}.mp4` | `audios/{id}.mp3` |
| **2.2** | `transcribe_qwen_asr.py` | `audios/{id}.mp3` | `copys/{id}_original.txt` |
| **3** | `recreate_podcast.py` | `copys/{id}_original.txt` | `copys/{id}_podcast.txt` ([S1]/[S2]) |
| **4** | `generate_podcast_tts.py` | `copys/{id}_podcast.txt` | `audios/{id}_podcast.mp3` |
| **5.1** | `format_podcast_subtitles.py` | `copys/{id}_podcast.txt` | `copys/{id}_subtitle.txt` |
| **5.2** | `forced_align.py --podcast` | 音频 + 字幕文本 | `captions/{id}_word_timestamps.json` |
| **5.3** | `match_podcast_timeline.py` | 字幕 + 时间戳 | `captions/{id}_final.srt` |
| **6.1** | `generate_podcast_image_prompt.py` | `copys/{id}_podcast.txt` | `copys/{id}_image_prompt.txt` |
| **6.2** | `generate_images.py --single` | `copys/{id}_image_prompt.txt` | `images/{id}/cover.jpg` |
| **7** | `compose_podcast_video.py` | 图片 + 音频 + 字幕 | `finals/{id}_final.mp4` |

---

## 🔗 数据流向简图

```mermaid
flowchart LR
    subgraph Input["📥 输入"]
        V["🎬 播客视频"]
    end

    subgraph Process["⚡ 处理流程"]
        direction TB
        T["Qwen3-ASR 转录"] --> R["Poe API 说话人识别+二创"]
        R --> S["SoulX-Podcast 配音"]
        R --> F["格式化字幕"]
        S --> A["ForcedAligner 对齐"]
        F --> A
        A --> SRT["SRT 字幕"]
        
        R --> P["DeepSeek 生图提示词"]
        P --> I["即梦 API 生图"]
    end

    subgraph Output["📤 输出"]
        O["🎬 9:16 竖屏播客视频"]
    end

    V --> Process
    Process --> O
```

---

## 📁 文件路径速查

```
raw_materials/
├── videos/{script_id}.mp4          ← 输入：播客视频
├── audios/
│   ├── {script_id}.mp3             ← 提取的原音频
│   └── {script_id}_podcast.mp3     ← SoulX-Podcast 生成
├── copys/
│   ├── {script_id}_original.txt    ← ASR 原始转录
│   ├── {script_id}_podcast.txt     ← 二创文案 [S1]/[S2]
│   ├── {script_id}_subtitle.txt    ← 字幕文本
│   └── {script_id}_image_prompt.txt ← 封面图提示词
├── captions/
│   ├── {script_id}_word_timestamps.json ← 词级时间戳
│   └── {script_id}_final.srt       ← 最终字幕
└── images/{script_id}/
    └── cover.jpg                   ← 封面图

finals/
└── {script_id}_final.mp4           ← 最终输出视频 (9:16)
```
