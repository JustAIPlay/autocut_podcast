---
name: comfyui:生图
description: 调用ComfyUI API生成图片。触发词：生图、生成封面、生成配图
---

# ComfyUI生图

> 基于原视频文案调用ComfyUI API生成配图

## 快速使用

```
用户: 生图，脚本号001
用户: 生成配图，文案是"一个美丽的风景"
```

## 前置条件

- ComfyUI服务运行在 `http://127.0.0.1:8188`
- 已配置好文生图工作流：`/workflow/wst_workflow.json`
- 需要原视频文案作为提示词来源

## 流程

```
1. 分析原视频文案，生成生图提示词
    ↓
2. 读取工作流模板
    ↓
3. 替换正向提示词
    ↓
4. 调整图片尺寸（适配1080x1920视频）
    ↓
5. 提交到ComfyUI API
    ↓
6. 获取生成的图片并保存
```

## ComfyUI API

### 获取工作流历史（prompt_id）

```bash
POST http://127.0.0.1:8188/prompt
Content-Type: application/json

{
  "prompt": {工作流JSON},
  "client_id": "客户端ID"
}
```

### 获取生成的图片

```bash
GET http://127.0.0.1:8188/view?filename={filename}&subfolder={subfolder}&type={type}
```

### WebSocket监听（可选）

```
ws://127.0.0.1:8188/ws?clientId={client_id}
```

## 工作流修改

基于 `/workflow/wst_workflow.json`，需要修改：

### 1. 替换正向提示词（节点2）

```json
"2": {
  "inputs": {
    "text": "{生成的提示词}",  // 替换这里
    "clip": ["16", 0]
  },
  "class_type": "CLIPTextEncode"
}
```

### 2. 调整图片尺寸（节点5）

适配1080x1920竖屏，建议生成576x1024：

```json
"5": {
  "inputs": {
    "width": 576,    // 或其他比例
    "height": 1024,
    "batch_size": 1
  },
  "class_type": "EmptyLatentImage"
}
```

## 提示词生成

基于原视频文案生成适配的提示词：

| 原视频文案 | 生成的提示词 |
|-----------|-------------|
| "介绍一个美丽的公园" | "a beautiful park landscape, high quality, 8k" |
| "展示美食制作过程" | "delicious food cooking process, cinematic lighting, 8k" |
| "科技产品评测" | "modern technology product, sleek design, professional photography" |

### 提示词生成原则

1. 翻译成英文
2. 添加质量词："high quality, 8k, detailed"
3. 根据内容添加场景描述
4. 保持简洁，避免过长

## 输出

```
/images/001.png
```

## 进度TodoList

```
- [ ] 确认 /images 目录存在
- [ ] 分析原视频文案，生成提示词
- [ ] 读取并修改工作流JSON
- [ ] 提交到ComfyUI API
- [ ] 等待生成完成
- [ ] 下载并保存图片
- [ ] 报告结果
```

## Python实现示例

```python
import json
import requests
import time

COMFYUI_API = "http://127.0.0.1:8188"

def generate_image(script_no, original_text, prompt_override=None):
    # 1. 生成提示词
    if not prompt_override:
        prompt = generate_prompt_from_text(original_text)
    else:
        prompt = prompt_override

    # 2. 读取工作流
    with open("workflow/wst_workflow.json", "r", encoding="utf-8") as f:
        workflow = json.load(f)

    # 3. 修改提示词
    workflow["2"]["inputs"]["text"] = prompt

    # 4. 调整尺寸（576x1024适配竖屏）
    workflow["5"]["inputs"]["width"] = 576
    workflow["5"]["inputs"]["height"] = 1024

    # 5. 提交任务
    response = requests.post(f"{COMFYUI_API}/prompt", json={"prompt": workflow})
    prompt_id = response.json()["prompt_id"]

    # 6. 等待完成并获取图片
    # ... (WebSocket监听或轮询)

    return f"/images/{script_no}.png"
```

## 常见问题

### Q1: ComfyUI连接失败
- 确认ComfyUI服务正在运行
- 检查端口8188是否被占用

### Q2: 生成图片失败
- 检查工作流JSON格式
- 确认模型文件存在

### Q3: 提示词不合适
- 用户可以手动提供提示词
- 建立提示词模板库
