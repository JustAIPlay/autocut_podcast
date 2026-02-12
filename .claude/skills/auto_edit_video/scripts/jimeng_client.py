#!/usr/bin/env python3
"""
即梦 API 客户端
支持文生图、图生图（参考图替换）、视频生成
"""

import os
import json
import re
import time
import base64
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any

# 使用统一的环境变量管理
try:
    from utils import get_env
    _USE_UTILS = True
except ImportError:
    _USE_UTILS = False


class JimengClient:
    """即梦 API 客户端"""

    def __init__(self, base_url: str = "http://101.33.249.64:8001", config_path: Optional[str] = None):
        """
        初始化客户端
        Args:
            base_url: API 基础 URL
            config_path: 配置文件路径（已废弃，保留用于兼容性）
        """
        self.base_url = base_url.rstrip("/")
        self.session_id = self._load_session_id()

    def _load_session_id(self) -> str:
        """从环境变量加载 session_id（使用统一的配置管理）"""
        if _USE_UTILS:
            # 使用统一的环境变量管理
            return get_env("JIMENG_SESSION_ID", "")
        else:
            # 降级方案：直接读取环境变量
            return os.environ.get("JIMENG_SESSION_ID", "")

    def _download_file(self, url: str, output_dir: str, filename: Optional[str] = None) -> str:
        """下载文件到本地，包含重试机制"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = url.split("/")[-1].split("?")[0]
            if not filename or len(filename) > 100:
                filename = f"jimeng_{int(time.time())}{Path(url).suffix}"

        filepath = output_path / filename
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, stream=True, timeout=60)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return str(filepath)
            except (requests.exceptions.RequestException, Exception) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 下载失败 (第 {attempt+1} 次): {e}，正在重试...")
                    time.sleep(2)  # 等待 2 秒后重试
                else:
                    print(f"❌ 下载最终失败: {url}")
                    raise e
        
        return str(filepath)

    def _file_to_base64(self, file_path: str) -> str:
        """将本地文件转换为 base64 字符串"""
        with open(file_path, "rb") as f:
            data = f.read()
            mime_type = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"
            base64_str = base64.b64encode(data).decode("utf-8")
            return f"data:{mime_type};base64,{base64_str}"

    def _get_env_value(self, key: str, default: str) -> str:
        """统一的环境变量获取方法"""
        if _USE_UTILS:
            return get_env(key, default)
        else:
            return os.environ.get(key, default)

    def text_to_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        sample_strength: float = 0.5,
        output_dir: Optional[str] = None,
        filename_prefix: str = "text2img",
        reference_image: Optional[str] = None,
        is_local_image: bool = True
    ) -> List[Dict[str, Any]]:
        """
        文生图（支持参考图替换）

        Args:
            prompt: 提示词
            model: 模型名称
            ratio: 图片比例
            resolution: 分辨率
            sample_strength: 采样强度
            output_dir: 输出目录
            filename_prefix: 文件名前缀
            reference_image: 参考图片路径（可选，传入时使用图生图替换模式）
            is_local_image: 参考图是否为本地图片（True=本地路径，False=网络URL），默认True

        Returns:
            生成的图片信息列表
        """
        # 优先级：参数传入 > 环境变量 > 默认值 (4:3, 2k)
        model = model or self._get_env_value("JIMENG_MODEL", "jimeng-4.0")
        ratio = ratio or self._get_env_value("JIMENG_RATIO", "4:3")
        resolution = resolution or self._get_env_value("JIMENG_RESOLUTION", "2k")
        # 如果未传入 output_dir，则默认使用当前目录下的 output/images
        output_dir = output_dir or "./output/images"

        # 如果有参考图，使用替换策略
        if reference_image:
            print(f"📎 检测到参考图，使用替换策略: {reference_image}")

            # 步骤1: 只用提示词生成临时图片
            print("🔄 步骤1: 用提示词生成临时图片...")
            # 如果参考图是 URL，不下载临时图片；如果是本地文件，需要下载
            temp_images = self._generate_temp_image(
                prompt=prompt,
                model=model,
                ratio=ratio,
                resolution=resolution,
                sample_strength=sample_strength,
                download=is_local_image  # 本地参考图需要下载，URL 参考图不需要
            )

            if not temp_images:
                raise Exception("临时图片生成失败")

            # 步骤2: 用临时图片 + 参考图进行替换
            print("🔄 步骤2: 执行图片替换...")
            return self._replace_book_in_image(
                temp_image=temp_images[0],
                reference_image=reference_image,
                is_local_ref=is_local_image,
                model=model,
                ratio=ratio,
                resolution=resolution,
                sample_strength=sample_strength,
                output_dir=output_dir,
                filename_prefix=filename_prefix
            )
        else:
            # 无参考图，直接生成（原有逻辑）
            return self._generate_direct_image(
                prompt=prompt,
                model=model,
                ratio=ratio,
                resolution=resolution,
                sample_strength=sample_strength,
                output_dir=output_dir,
                filename_prefix=filename_prefix
            )

    def _generate_direct_image(
        self,
        prompt: str,
        model: str,
        ratio: str,
        resolution: str,
        sample_strength: float,
        output_dir: str,
        filename_prefix: str
    ) -> List[Dict[str, Any]]:
        """
        直接文生图（无参考图，保留原有逻辑）
        """
        url = f"{self.base_url}/v1/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.session_id}"
        }

        data = {
            "model": model,
            "prompt": prompt,
            "ratio": ratio,
            "resolution": resolution,
            "sample_strength": sample_strength,
        }

        max_retries = 2
        result = {}
        for attempt in range(max_retries):
            try:
                # 增加到 300 秒超时，给 2K 生成留足时间
                response = requests.post(url, headers=headers, json=data, timeout=300)
                response.raise_for_status()
                result = response.json()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 生成请求失败 (第 {attempt+1} 次): {e}，正在重试...")
                    time.sleep(5)
                else:
                    raise e

        # 只取第一张图片
        output_files = []
        data_list = result.get("data", [])
        
        if data_list and len(data_list) > 0:
            # 只处理第一张图片
            item = data_list[0]
            img_url = item.get("url")
            if img_url:
                # 使用新的命名规则：filename_prefix.png（不加 _0 后缀）
                local_path = self._download_file(img_url, output_dir, f"{filename_prefix}.png")
                output_files.append({
                    "url": img_url,
                    "local_path": local_path,
                    "revised_prompt": item.get("revised_prompt", prompt)
                })

        return output_files

    def _generate_temp_image(
        self,
        prompt: str,
        model: str,
        ratio: str,
        resolution: str,
        sample_strength: float,
        output_dir: Optional[str] = None,
        filename_prefix: str = "temp",
        download: bool = True
    ) -> List[Dict[str, Any]]:
        """
        生成临时图片（内部方法，用于参考图替换流程）

        Args:
            prompt: 提示词
            model: 模型名称
            ratio: 图片比例
            resolution: 分辨率
            sample_strength: 采样强度
            output_dir: 输出目录
            filename_prefix: 文件名前缀
            download: 是否下载到本地（True=下载并返回 local_path，False=只返回 URL）
        """
        url = f"{self.base_url}/v1/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.session_id}"
        }

        data = {
            "model": model,
            "prompt": prompt,
            "ratio": ratio,
            "resolution": resolution,
            "sample_strength": sample_strength,
        }

        max_retries = 2
        result = {}
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=300)
                response.raise_for_status()
                result = response.json()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 生成请求失败 (第 {attempt+1} 次): {e}，正在重试...")
                    time.sleep(5)
                else:
                    raise e

        output_files = []
        data_list = result.get("data", [])
        for i, item in enumerate(data_list):
            img_url = item.get("url")
            if img_url:
                if download:
                    # 如果未传入 output_dir，则使用 cache 目录
                    if output_dir is None:
                        if _USE_UTILS:
                            from utils import get_project_root
                            project_root = get_project_root()
                        else:
                            project_root = Path(__file__).parent.parent.parent.parent.parent
                        output_dir = str(project_root / "raw_materials" / "cache")
                    local_path = self._download_file(img_url, output_dir, f"{filename_prefix}_{i}.png")
                    output_files.append({
                        "url": img_url,
                        "local_path": local_path,
                        "revised_prompt": item.get("revised_prompt", prompt)
                    })
                else:
                    # 不下载，只返回 URL
                    output_files.append({
                        "url": img_url,
                        "revised_prompt": item.get("revised_prompt", prompt)
                    })
                # 只处理第一张
                break

        return output_files

    def _replace_book_in_image(
        self,
        temp_image: Dict[str, Any],
        reference_image: str,
        is_local_ref: bool,
        model: str,
        ratio: str,
        resolution: str,
        sample_strength: float,
        output_dir: str,
        filename_prefix: str
    ) -> List[Dict[str, Any]]:
        """
        用图生图替换书籍（内部方法）

        Args:
            temp_image: 临时生成的图片信息（字典，包含 url 和可能的 local_path）
            reference_image: 参考图路径
            is_local_ref: 参考图是否为本地文件
            model: 模型名称
            ratio: 图片比例
            resolution: 分辨率
            sample_strength: 采样强度
            output_dir: 输出目录
            filename_prefix: 文件名前缀
        """
        api_url = f"{self.base_url}/v1/images/compositions"
        headers = {
            "Authorization": f"Bearer {self.session_id}"
        }

        # 固定替换提示词
        replace_prompt = "请将图1中的书，替换成图2的书"

        # 判断使用 URL 模式还是 base64 模式
        # 如果临时图片有 local_path 且参考图是本地文件，使用 base64
        use_base64 = "local_path" in temp_image and is_local_ref

        if use_base64:
            # Base64 模式：两个都是本地文件
            headers["Content-Type"] = "application/json"
            temp_base64 = self._file_to_base64(temp_image["local_path"])
            ref_base64 = self._file_to_base64(reference_image)
            images = [temp_base64, ref_base64]
            print(f"📎 使用 Base64 模式（本地文件）")
        else:
            # URL 模式：至少有一个是 URL
            headers["Content-Type"] = "application/json"
            # 临时图片使用 URL
            temp_url = temp_image["url"]
            # 参考图：本地文件转 base64，URL 直接使用
            if is_local_ref:
                ref_base64 = self._file_to_base64(reference_image)
                images = [temp_url, ref_base64]
            else:
                images = [temp_url, reference_image]
            print(f"📎 使用 URL 模式（无需下载临时图片）")

        data = {
            "model": model,
            "prompt": replace_prompt,
            "images": images,
            "ratio": ratio,
            "resolution": resolution,
            "sample_strength": sample_strength,
        }

        max_retries = 2
        result = {}
        for attempt in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=data, timeout=300)
                response.raise_for_status()
                result = response.json()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 替换请求失败 (第 {attempt+1} 次): {e}，正在重试...")
                    time.sleep(5)
                else:
                    raise e

        output_files = []
        for i, item in enumerate(result.get("data", [])):
            img_url = item.get("url")
            if img_url:
                # 使用新的命名规则：filename_prefix.png（不加 _0 后缀，与直接生成保持一致）
                local_path = self._download_file(img_url, output_dir, f"{filename_prefix}.png")
                output_files.append({
                    "url": img_url,
                    "local_path": local_path,
                    "revised_prompt": item.get("revised_prompt", replace_prompt)
                })
                # 只取第一张
                break

        return output_files

    def generate_video(
        self,
        prompt: str,
        model: Optional[str] = None,
        ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        duration: int = 5,
        file_paths: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
        filename_prefix: str = "video",
        is_local_file: bool = True
    ) -> List[Dict[str, Any]]:
        """
        视频生成

        Args:
            prompt: 视频描述
            model: 模型名称
            ratio: 宽高比
            resolution: 分辨率 (480p, 720p, 1080p)
            duration: 时长 (5 或 10 秒)
            file_paths: 首帧/尾帧图片 URL 或本地路径
            output_dir: 输出目录
            filename_prefix: 文件名前缀
            is_local_file: file_paths 是否为本地文件（True=本地路径，False=网络URL），默认True

        Returns:
            包含生成结果的列表
        """
        # 优先级：参数传入 > 环境变量 > 默认值
        model = model or self._get_env_value("JIMENG_VIDEO_MODEL", "jimeng-video-3.5-pro")
        ratio = ratio or self._get_env_value("JIMENG_RATIO", "16:9")
        resolution = resolution or self._get_env_value("JIMENG_VIDEO_RESOLUTION", "720p")
        output_dir = output_dir or "./output/videos"

        url = f"{self.base_url}/v1/videos/generations"
        headers = {
            "Authorization": f"Bearer {self.session_id}"
        }

        # 检查是否有 file_paths
        has_file_paths = file_paths and len(file_paths) > 0

        if has_file_paths:
            # 根据 is_local_file 判断处理方式
            if is_local_file:
                # 使用 multipart/form-data
                files = []
                form_data = {
                    "model": model,
                    "prompt": prompt,
                    "ratio": ratio,
                    "resolution": resolution,
                    "duration": str(duration),
                }
                for f in file_paths:
                    if os.path.exists(f):
                        mime_type = "image/png" if f.lower().endswith(".png") else "image/jpeg"
                        files.append(("file_paths", (os.path.basename(f), open(f, "rb"), mime_type)))
                    else:
                        # 混合模式：有些是本地文件，有些是 URL
                        form_data.setdefault("file_urls", []).append(f)

                response = requests.post(url, headers=headers, data=form_data, files=files, timeout=180)
                for _, file_info in files:
                    file_info[1].close()
            else:
                # 纯 JSON 模式
                headers["Content-Type"] = "application/json"
                data = {
                    "model": model,
                    "prompt": prompt,
                    "ratio": ratio,
                    "resolution": resolution,
                    "duration": duration,
                    "file_paths": file_paths,
                }
                response = requests.post(url, headers=headers, json=data, timeout=180)
        else:
            # 纯 JSON 模式
            headers["Content-Type"] = "application/json"
            data = {
                "model": model,
                "prompt": prompt,
                "ratio": ratio,
                "resolution": resolution,
                "duration": duration,
            }
            response = requests.post(url, headers=headers, json=data, timeout=180)

        response.raise_for_status()
        result = response.json()

        if not isinstance(result, dict) or result.get("data") is None:
            error_msg = result.get("error", "未知错误") if isinstance(result, dict) else "响应格式错误"
            print(f"API 错误: {error_msg}")
            if isinstance(result, dict) and "message" in result:
                print(f"详细信息: {result['message']}")
            return []

        output_files = []
        data_list = result.get("data", [])
        if not isinstance(data_list, list):
            return []

        for i, item in enumerate(data_list):
            video_url = item.get("url")
            if video_url:
                local_path = self._download_file(video_url, output_dir, f"{filename_prefix}_{i}.mp4")
                output_files.append({
                    "url": video_url,
                    "local_path": local_path,
                    "revised_prompt": item.get("revised_prompt", prompt)
                })

        return output_files