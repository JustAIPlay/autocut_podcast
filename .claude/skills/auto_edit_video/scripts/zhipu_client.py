#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智谱 AI API 客户端
用于调用智谱平台的 AI 模型（兼容 OpenAI SDK 格式）
"""
import sys
import io
from openai import OpenAI
from typing import Optional
from utils import get_env


class ZhipuClient:
    """智谱 API 客户端（使用 OpenAI SDK 格式）"""

    def __init__(self):
        """初始化客户端"""
        self.api_key = get_env("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("❌ 请在 .env 中设置 ZHIPU_API_KEY")

        self.base_url = get_env("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        self.model_name = get_env("ZHIPU_MODEL", "glm-4-flash")

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 35000
    ) -> str:
        """
        调用智谱 API 进行对话（OpenAI SDK 格式）

        Args:
            prompt: 提示词
            model: 模型名称（如不指定则使用默认值）
            temperature: 温度参数
            max_tokens: 最大输出 token 数

        Returns:
            AI 返回的文本内容
        """
        bot_model = model or self.model_name

        try:
            print(f"🤖 正在调用智谱 API (model: {bot_model})...")

            response = self.client.chat.completions.create(
                model=bot_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            # 返回消息内容
            return response.choices[0].message.content

        except Exception as e:
            print(f"❌ 调用智谱 API 失败: {e}")
            raise


def test_zhipu_client():
    """测试智谱 API 客户端"""
    try:
        client = ZhipuClient()
        response = client.chat("你好，请用一句话介绍你自己。")
        print(f"✅ 测试成功！")
        print(f"响应: {response}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    test_zhipu_client()
