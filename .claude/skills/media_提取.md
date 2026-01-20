---
name: media:提取
description: 从视频中提取音频和字幕。触发词：提取媒体、提取音视频、处理媒体
---

# 媒体提取

> 从视频中提取音频到 /audios，提取/生成字幕到 /captions

## 快速使用

```
用户: 提取媒体，脚本号001
用户: 处理视频001的音频和字幕
```

## 前置条件

需要先执行 `video:下载`，视频文件存在于 `/videos/{脚本号}.mp4`

## 流程

```
1. 提取音频（FFmpeg）
    ↓
2. 检查视频是否有软字幕流
    ↓
3a. 有软字幕 → 直接提取字幕
3b. 无软字幕 → Whisper转录 + 词典纠正
    ↓
4. 保存文件
```

## 一、提取音频

### FFmpeg命令

```bash
ffmpeg -i "videos/{脚本号}.mp4" \
  -vn -acodec libmp3lame -q:a 2 \
  "audios/{脚本号}.mp3"
```

| 参数 | 说明 |
|------|------|
| `-vn` | 不处理视频流 |
| `-acodec libmp3lame` | MP3编码 |
| `-q:a 2` | 高质量音频（0-9，越小越好） |

### 输出

```
/audios/001.mp3
```

## 二、提取/生成字幕

### 检查字幕流

```bash
ffprobe -v quiet -print_format json -show_streams "videos/{脚本号}.mp4"
```

查找 `codec_type` 为 `subtitle` 的流。

### 方案A：有软字幕 - 直接提取

```bash
ffmpeg -i "videos/{脚本号}.mp4" \
  -map 0:s:0 \
  "captions/{脚本号}.srt"
```

### 方案B：无软字幕 - Whisper生成

由于原视频字幕是硬字幕（烧录在画面上），无法直接提取，使用 Whisper 转录：

```bash
whisper "audios/{脚本号}.mp3" \
  --model medium \
  --language zh \
  --output_format srt \
  --output_dir "captions" \
  --output_filename "{脚本号}"
```

### 字幕纠正

使用飞书表格中的"原视频文案"进行纠正：

1. 读取原视频文案
2. 使用文本匹配算法对齐
3. 替换识别错误的词汇

### 输出

```
/captions/001.srt
```

## 字幕规范

| 规则 | 说明 |
|------|------|
| 一屏一行 | 不换行 |
| ≤15字/行 | 1080x1920竖屏 |
| 句尾无标点 | `你好` 不是 `你好。` |
| 句中保留标点 | `先点这里，再点那里` |

## 进度TodoList

```
- [ ] 确认 /audios 和 /captions 目录存在
- [ ] 提取音频
- [ ] 检查字幕流
- [ ] 提取/生成字幕
- [ ] 纠正字幕（可选）
- [ ] 报告结果
```

## 输出文件

```
/audios/001.mp3       # 提取的音频
/captions/001.srt     # 字幕文件
```

## 常见问题

### Q1: 音频提取失败
- 检查视频文件是否完整
- 确认FFmpeg已安装

### Q2: 字幕时间不准确
- Whisper时间戳可能有偏差
- 使用更大模型（large-v3）提高准确度

### Q3: 字幕识别错误
- 使用原视频文案进行纠正
- 建立词典文件
