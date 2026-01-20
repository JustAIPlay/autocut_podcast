---
name: video:合成
description: 合成视频。音频+字幕+图片 → 完整视频。触发词：合成视频、剪辑、生成视频
---

# 视频合成

> 将音频、字幕、图片合成为完整的竖屏视频

## 快速使用

```
用户: 合成视频，脚本号001
用户: 生成最终视频001
```

## 前置条件

需要先完成：
- `/audios/{脚本号}.mp3` - 音频文件
- `/captions/{脚本号}.srt` - 字幕文件
- `/images/{脚本号}.png` - 配图

## 流程

```
1. 确认所有素材文件存在
    ↓
2. 创建FFmpeg复杂滤镜（图片缩放+字幕烧录）
    ↓
3. 合成视频（音频时长）
    ↓
4. 输出到 /outputs
```

## 输出规格

| 参数 | 值 |
|------|-----|
| 分辨率 | 1080x1920（竖屏9:16） |
| 时长 | 依赖音频时长 |
| 字幕样式 | 白字、黑描边、底部居中 |
| 字体大小 | 24号（可调整） |
| 视频编码 | H.264 (libx264) |
| 音频编码 | AAC |
| 帧率 | 30fps |

## FFmpeg命令

### 方案一：字幕烧录到视频

```bash
ffmpeg -y \
  -loop 1 -i "images/{脚本号}.png" \
  -i "audios/{脚本号}.mp3" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2, \
       subtitles='captions/{脚本号}.srt':force_style='FontName=Microsoft YaHei,FontSize=24, \
       PrimaryColour=&Hffffff,OutlineColour=&H000000,Alignment=2,MarginV=50'" \
  -c:v libx264 -tune stillimage -preset medium -crf 23 \
  -c:a aac -b:a 128k \
  -shortest \
  -pix_fmt yuv420p \
  "outputs/{脚本号}_final.mp4"
```

### 方案二：使用drawtext滤镜（更灵活）

```bash
ffmpeg -y \
  -loop 1 -i "images/{脚本号}.png" \
  -i "audios/{脚本号}.mp3" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2, \
       drawtext=textfile='captions/{脚本号}.txt':reload=1:fontfile=/Windows/Fonts/msyh.ttc: \
       fontsize=36:fontcolor=white:x=(w-text_w)/2:y=h-150: \
       bordercolor=black:borderw=3:box=1:boxcolor=black@0.5:boxborderw=5" \
  -c:v libx264 -tune stillimage -preset medium -crf 23 \
  -c:a aac -b:a 128k \
  -shortest \
  -pix_fmt yuv420p \
  "outputs/{脚本号}_final.mp4"
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `-loop 1` | 循环图片 |
| `-shortest` | 以最短的流为准（通常是音频） |
| `-tune stillimage` | 优化静态图片视频 |
| `-pix_fmt yuv420p` | 兼容性最好的像素格式 |

## 字幕样式

### 默认样式

```
字体: Microsoft YaHei（微软雅黑）
大小: 24号
颜色: 白色
描边: 黑色，3px
位置: 底部居中，距离底部50px
```

### 字幕样式配置（force_style）

```
FontName=Microsoft YaHei      # 字体
FontSize=24                   # 字号
PrimaryColour=&Hffffff        # 白色 (BGR)
OutlineColour=&H000000        # 黑色描边
Alignment=2                   # 底部居中
MarginV=50                    # 底部边距
```

## 输出

```
/outputs/001_final.mp4
```

## 进度TodoList

```
- [ ] 确认 /outputs 目录存在
- [ ] 检查素材文件完整性
  - [ ] 音频文件存在
  - [ ] 字幕文件存在
  - [ ] 图片文件存在
- [ ] 构建FFmpeg命令
- [ ] 执行合成
- [ ] 验证输出视频
- [ ] 报告结果
```

## Python实现示例

```python
import subprocess
import os

def compose_video(script_no):
    # 检查文件
    audio = f"audios/{script_no}.mp3"
    caption = f"captions/{script_no}.srt"
    image = f"images/{script_no}.png"
    output = f"outputs/{script_no}_final.mp4"

    if not all(os.path.exists(f) for f in [audio, caption, image]):
        raise FileNotFoundError("素材文件不完整")

    # FFmpeg命令
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image,
        "-i", audio,
        "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,"
               f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
               f"subtitles='{caption}':force_style='FontName=Microsoft YaHei,"
               f"FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,"
               f"Alignment=2,MarginV=50'",
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        output
    ]

    subprocess.run(cmd, check=True)
    return output
```

## 常见问题

### Q1: 字幕显示乱码
- 检查字体路径是否正确
- 确认字幕文件编码是UTF-8

### Q2: 视频时长不对
- 使用 `-shortest` 参数确保时长匹配音频

### Q3: 图片变形
- 使用 `force_original_aspect_ratio=decrease` 保持比例
- 使用 `pad` 填充黑边

### Q4: 合成速度慢
- 调整 `-preset` 参数（ultrafast/fast/medium/slow）
- 静态图片可使用 `-tune stillimage`
