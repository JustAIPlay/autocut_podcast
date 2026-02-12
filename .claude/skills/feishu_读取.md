---
name: feishu:读取
description: 从飞书多维表格读取数据（脚本号、视频链接、原视频文案）。触发词：读取飞书、获取表格、飞书数据
---

# 飞书读取

> 从飞书多维表格读取视频二创所需的数据

## 快速使用

```
用户: 读取飞书表格
用户: 获取飞书数据
用户: 从飞书读取脚本信息
```

## 前置条件

需要以下信息（配置在 `.env.local` 中）：

| 参数 | 说明 | 获取方式 |
|------|------|----------|
| `app_id` | 飞书应用的 App ID | 飞书开放平台 → 创建应用 |
| `app_secret` | 飞书应用的 App Secret | 飞书开放平台 → 凭证与基础信息 |
| `app_token` | 多维表格的 ID（也叫 spreadsheet_token） | 表格链接中提取 |
| `table_id` | 数据表的 ID | 表格链接中提取 |

### 获取 app_token 和 table_id

从飞书多维表格链接中提取：

```
https://example.feishu.cn/base/{app_token}/objects/{table_id}?...
```

- `app_token`: base 后面的字符串
- `table_id`: objects 后面的字符串

### .env.local 配置示例

```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxx
FEISHU_APP_TOKEN=bascnxxxxxxxxxxxxxxxxxxxx
FEISHU_TABLE_ID=tblxxxxxxxxxxxxxxxxxxxx
```

## 数据结构

从飞书读取的数据包含以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| 脚本号 | 用于文件命名和素材关联 | `001`, `A001` |
| 视频链接 | 对标视频的URL | `https://xxx.com/video.mp4` |
| 原视频文案 | 用于字幕和生图提示词 | `这是一段介绍...` |

## 流程

```
1. 获取飞书访问令牌（tenant_access_token）
    ↓
2. 读取多维表格数据
    ↓
3. 解析所需字段（脚本号、视频链接、原视频文案）
    ↓
4. 返回数据列表
```

## 飞书API

### 1. 获取访问令牌

```bash
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
Content-Type: application/json

{
  "app_id": "cli_xxxxxxxxxxxxx",
  "app_secret": "xxxxxxxxxxxxxxxxxxxx"
}
```

响应：
```json
{
  "code": 0,
  "tenant_access_token": "t-xxxxxxxxxxxxxxxxxxxx",
  "expire": 7200
}
```

### 2. 读取多维表格记录

```bash
GET https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records
Authorization: Bearer {tenant_access_token}
```

响应：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "fields": {
          "脚本号": "001",
          "视频链接": "https://xxx.com/video.mp4",
          "原视频文案": "这是一段介绍..."
        }
      }
    ]
  }
}
```

## 输出

返回数据列表格式：

```json
[
  {
    "script_no": "001",
    "video_url": "https://xxx.com/video.mp4",
    "original_text": "这是一段介绍..."
  },
  {
    "script_no": "002",
    "video_url": "https://xxx.com/video2.mp4",
    "original_text": "另一段文案..."
  }
]
```

## 使用示例

读取后，可以继续执行其他Skills：

```
用户: 读取飞书表格
[返回数据列表]

用户: 下载第一条的视频
[调用 video:下载]
```

## 注意事项

- 飞书API有调用频率限制
- 确保应用有足够的权限读取多维表格
- 视频链接需要是可访问的URL（支持 http/https）
