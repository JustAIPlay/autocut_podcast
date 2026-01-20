# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 Claude Code Skills 的视频二创工具，从飞书多维表格读取数据，自动下载视频、提取音视频、AI生图、合成视频。

## 架构

项目采用 Skills 架构，所有功能模块位于 `.claude/skills/` 目录：

### Skill 模块

| Skill | 功能描述 | 触发词 |
|-------|----------|--------|
| `video:安装` | 环境准备、依赖安装、验证环境 | 安装、环境准备、初始化 |
| `feishu:读取` | 从飞书多维表格读取数据（脚本号+视频链接+原视频文案） | 读取飞书、获取表格 |
| `video:下载` | 下载视频到 `/videos/{脚本号}.mp4` | 下载视频 |
| `media:提取` | 提取音频到 `/audios/`，提取/生成字幕到 `/captions/` | 提取媒体、提取音视频 |
| `comfyui:生图` | 基于原视频文案生成配图到 `/images/{脚本号}.png` | 生图、生成封面 |
| `video:合成` | 合成视频到 `/outputs/{脚本号}_final.mp4`（1080x1920） | 合成视频、剪辑 |

### 核心依赖

- **FFmpeg**：视频处理（下载、提取、合成）
- **Whisper**：语音识别生成字幕（medium / large-v3）
- **ComfyUI API**：AI生图（`http://127.0.0.1:8188`）
- **飞书API**：读取多维表格数据
- **yt-dlp**（可选）：下载平台视频

模型下载位置：
- Whisper: `~/.cache/whisper/`

### 目录结构

```
autocut_podcast/
├── .claude/
│   └── skills/           # Skills定义文件
├── workflow/             # ComfyUI工作流
│   └── wst_workflow.json
├── videos/               # 下载的原始视频
├── audios/               # 提取的音频
├── captions/             # 提取/生成的字幕（srt格式）
├── images/               # ComfyUI生成的图片
└── outputs/              # 最终合成的视频
```

## 工作流

```
安装（首次使用）
    ↓
feishu:读取 → 获取飞书表格数据（脚本号+视频链接+原视频文案）
    ↓
video:下载 → 下载视频到 /videos/{脚本号}.mp4
    ↓
media:提取 → 提取音频到 /audios/{脚本号}.mp3
            → 生成字幕到 /captions/{脚本号}.srt
    ↓
comfyui:生图 → 基于原视频文案生成图片到 /images/{脚本号}.png
    ↓
video:合成 → 合成视频到 /outputs/{脚本号}_final.mp4（1080x1920）
```

### 文件命名规范

所有文件使用**脚本号**作为名称前缀：

```
/videos/001.mp4          # 原始视频
/audios/001.mp3          # 提取的音频
/captions/001.srt        # 字幕文件
/images/001.png          # 生成的配图
/outputs/001_final.mp4   # 最终合成视频
```

## 核心设计原则

### 文件命名统一使用脚本号

所有素材文件使用相同的脚本号命名，确保素材关联正确：

```
/videos/001.mp4          # 原始视频
/audios/001.mp3          # 提取的音频
/captions/001.srt        # 字幕文件
/images/001.png          # 生成的配图
/outputs/001_final.mp4   # 最终合成视频
```

### 字幕规范

| 规则 | 说明 |
|------|------|
| 一屏一行 | 不换行，不堆叠 |
| ≤15字/行 | 超过必须拆分（1080x1920竖屏） |
| 句尾无标点 | `你好` 不是 `你好。` |
| 句中保留标点 | `先点这里，再点那里` |

## 开发注意事项

1. **文件命名统一使用脚本号**，确保素材关联正确
2. **ComfyUI API 地址**：`http://127.0.0.1:8188`，确保服务运行
3. **字幕提取**：原视频通常是硬字幕，使用 Whisper 转录 + 原视频文案纠正
4. **视频输出规格**：1080x1920 竖屏，白字黑边字幕
5. **飞书 API**：注意调用频率限制，确保应用有足够权限
