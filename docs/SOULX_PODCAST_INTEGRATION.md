# SoulX-Podcast 集成说明

## 📋 概述

本项目已成功集成 SoulX-Podcast 用于播客音频生成。系统会自动将 `[S1]`/`[S2]` 格式的播客文案转换为 SoulX-Podcast 需要的 JSON 格式。

## ✨ 主要功能

### 1. 自动格式转换

**输入格式**（`copys/{id}_podcast.txt`）：
```
[S1] 说话人1的内容
[S2] 说话人2的内容
[S1] 说话人1继续说话
```

**输出格式**（自动生成的 JSON）：
```json
{
  "speakers": {
    "S1": {
      "prompt_audio": "D:/AI/SoulX-Podcast/voices/speaker1.wav",
      "prompt_text": "说话人1的第一句话（自动提取）"
    },
    "S2": {
      "prompt_audio": "D:/AI/SoulX-Podcast/voices/speaker2.wav",
      "prompt_text": "说话人2的第一句话（自动提取）"
    }
  },
  "text": [
    ["S1", "说话人1的内容"],
    ["S2", "说话人2的内容"],
    ["S1", "说话人1继续说话"]
  ]
}
```

### 2. 智能参考文本提取

- 脚本会自动从对话中提取每个说话人的第一句话作为参考文本
- 也可以在 `.env` 中手动指定参考文本：
  ```bash
  SOULX_PROMPT_TEXT_S1=这是说话人1的参考文本
  SOULX_PROMPT_TEXT_S2=这是说话人2的参考文本
  ```

### 3. 完整的错误检查

- 验证输入文件格式
- 检查参考音频文件是否存在
- 解析对话并统计条数
- 显示详细的执行日志

## 🔧 配置要求

### 必需配置（`.env` 文件）

```bash
# SoulX-Podcast 安装目录
SOULX_PODCAST_PATH=D:/AI/SoulX-Podcast

# 模型路径（相对于 SOULX_PODCAST_PATH）
SOULX_MODEL_PATH=pretrained_models/SoulX-Podcast-1.7B

# 说话人1参考音频（5-30秒，WAV 格式推荐）
SOULX_VOICE_S1=D:/AI/SoulX-Podcast/voices/speaker1.wav

# 说话人2参考音频（5-30秒，WAV 格式推荐）
SOULX_VOICE_S2=D:/AI/SoulX-Podcast/voices/speaker2.wav
```

### 可选配置

```bash
# 说话人1参考文本（不设置则自动从对话中提取）
SOULX_PROMPT_TEXT_S1=这是说话人1的参考文本

# 说话人2参考文本（不设置则自动从对话中提取）
SOULX_PROMPT_TEXT_S2=这是说话人2的参考文本
```

## 📝 播客文案格式要求

为了获得最佳的 TTS 效果，播客文案需要遵循以下规则：

### ✅ 正确示例

```
[S1] 今天我们来聊聊关于睡眠质量的话题。
[S1] 这个问题困扰着很多人，尤其是现代人。
[S2] 是的，我发现现在失眠的人越来越多。
[S2] 尤其是中老年人群，这个问题特别突出。
[S1] 其实改善睡眠有很多简单的方法。
```

**要点**：
- ✅ 每行长度 50-150 字符
- ✅ 长段落拆分成多个短句
- ✅ 保持自然的对话节奏
- ✅ 同一说话人可以连续多行

### ❌ 错误示例

```
[S1] 今天我们来聊聊关于睡眠质量的话题，这个问题困扰着很多人，尤其是现代人，我发现现在失眠的人越来越多，尤其是中老年人群，这个问题特别突出，其实改善睡眠有很多简单的方法，不一定需要依赖药物。
```

**问题**：
- ❌ 单行过长（超过 200 字符）
- ❌ 缺乏自然的语气停顿
- ❌ 不符合播客对话习惯

## 🚀 使用方法

### 1. 生成播客音频

```bash
python .claude/skills/auto_edit_video/scripts/generate_podcast_tts.py HFlyx000418
```

### 2. 脚本执行流程

1. 读取 `raw_materials/copys/HFlyx000418_podcast.txt`
2. 解析 `[S1]`/`[S2]` 格式的对话
3. 提取参考文本（或使用环境变量中的配置）
4. 生成 JSON 输入文件：`raw_materials/audios/HFlyx000418_soulx_input.json`
5. 调用 SoulX-Podcast 生成音频
6. 输出：`raw_materials/audios/HFlyx000418_podcast.mp3`

### 3. 测试格式转换

```bash
python .claude/skills/auto_edit_video/scripts/test_podcast_json.py
```

这会运行测试脚本，验证格式转换功能是否正常。

## 📂 文件说明

### 核心脚本

- **`generate_podcast_tts.py`**: 主脚本，负责格式转换和调用 SoulX-Podcast
- **`test_podcast_json.py`**: 测试脚本，验证格式转换功能

### 示例文件

- **`raw_materials/audios/example_soulx_input.json`**: SoulX-Podcast 输入格式示例

### 提示词

- **`PROMPTS/prompt_podcast_recreate.md`**: 播客二创提示词（已优化，包含句子长度控制）

## 🔍 参考音频要求

为了获得最佳的声音克隆效果，参考音频需要满足：

- **时长**: 5-30 秒
- **格式**: WAV（推荐）或 MP3
- **采样率**: 16kHz 或更高
- **内容**: 清晰的单人语音
- **质量**: 无背景噪音，发音清晰
- **建议**: 音频内容最好包含参考文本的内容

## 🎭 副语言标签功能

### 可用标签

SoulX-Podcast 支持以下副语言标签，让播客更生动自然：

| 标签 | 效果 | 使用场景 |
|------|------|----------|
| `<|laughter|>` | 笑声 | 轻松、幽默的时刻 |
| `<|sigh|>` | 叹气 | 感慨、无奈的时刻 |
| `<|breathing|>` | 呼吸声 | 停顿、思考的时刻 |
| `<|coughing|>` | 咳嗽 | 需要清嗓的时刻 |
| `<|throat_clearing|>` | 清嗓 | 转换话题前 |

### 使用方法

**在文本中添加标签**：
```json
{
  "text": [
    ["S1", "大家好！欢迎收听节目 `<|laughter|>` 我是主持人"],
    ["S2", "很高兴来到这里 `<|sigh|>` 让我们开始今天的话题"],
    ["S1", "有些事情真的让人... `<|breathing|>` 不知道从何说起"]
  ]
}
```

**使用原则**：
- ✅ 标签放在句子中间或末尾，用空格分隔
- ✅ 在合适的情感节点添加
- ❌ 不要过度使用，保持自然（建议 20-30% 的对话添加）

### 自动添加标签

使用 `add_paralanguage_tags.py` 脚本为现有 JSON 文件添加标签：

**自动模式**（智能识别关键词）：
```bash
# 使用默认概率 (30%)
python .claude/skills/auto_edit_video/scripts/add_paralanguage_tags.py raw_materials/audios/HFlyx000418_soulx_input.json

# 指定输出文件和概率 (20%)
python .claude/skills/auto_edit_video/scripts/add_paralanguage_tags.py \
  raw_materials/audios/HFlyx000418_soulx_input.json \
  raw_materials/audios/HFlyx000418_soulx_input_tagged.json \
  0.2
```

**手动模式**（逐条选择）：
```bash
python .claude/skills/auto_edit_video/scripts/add_paralanguage_tags.py \
  raw_materials/audios/HFlyx000418_soulx_input.json \
  --manual
```

### 在二创时自动生成

播客二创提示词已经包含副语言标签的说明，AI 会在生成文案时自动添加合适的标签。

**提示词中的说明**：
- 在轻松、幽默的时刻添加 `<|laughter|>`
- 在感慨、无奈的时刻添加 `<|sigh|>`
- 在停顿、思考的时刻添加 `<|breathing|>`

## ⚠️ 注意事项

1. **SoulX-Podcast 路径**: 确保 `SOULX_PODCAST_PATH` 指向正确的安装目录
2. **模型路径**: 确保模型文件已下载到 `pretrained_models/SoulX-Podcast-1.7B`
3. **参考音频**: 确保参考音频文件存在且路径正确
4. **API 调用**: 脚本中的 `inference.py` 可能需要根据实际的 SoulX-Podcast API 调整

## 🐛 故障排除

### 问题：找不到参考音频文件

```
❌ 找不到参考音频文件: D:/AI/SoulX-Podcast/voices/speaker1.wav
```

**解决方案**：
- 检查 `.env` 中的路径是否正确
- 确保参考音频文件存在

### 问题：无法解析播客脚本

```
❌ 无法解析播客脚本，请检查格式
```

**解决方案**：
- 确保文件使用 `[S1]`/`[S2]` 格式
- 检查是否有空行或格式错误
- 运行测试脚本验证格式

### 问题：SoulX-Podcast 执行失败

```
❌ SoulX-Podcast 执行失败
```

**解决方案**：
- 检查 SoulX-Podcast 是否正确安装
- 查看详细的错误输出
- 确认 `inference.py` 文件名是否正确（可能是 `run.py` 或 `main.py`）

## 📚 相关文档

- **CLAUDE.md**: 项目概述和快速开始
- **PROMPTS/prompt_podcast_recreate.md**: 播客二创提示词（包含格式要求）
- **.env.example.txt**: 环境变量配置示例

## 🎯 下一步

1. 准备好参考音频文件（speaker1.wav 和 speaker2.wav）
2. 配置 `.env` 文件
3. 运行测试脚本验证功能
4. 生成播客音频

---

**更新日期**: 2026-02-05
**版本**: 1.0.0
