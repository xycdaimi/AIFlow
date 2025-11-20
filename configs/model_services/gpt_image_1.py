"""GPT Image-1 Model Service - GPT Image-1 图像编辑服务接口"""

import httpx
from typing import Dict, Any


# 导入注册装饰器
from services.model_forwarder.infer import register_inference_function


@register_inference_function("gpt-image-1")
def gpt_image_1_inference(model_spec: Dict[str, Any],
                          payload: Dict[str, Any],
                          inference_params: Dict[str, Any]) -> Any:
    """
    GPT Image-1 图像编辑推理函数（支持多图编辑）

    Args:
        model_spec: 模型规格配置
            - name: 模型名称 (默认 "gpt-image-1")
            - endpoint: API 端点 (默认 "https://api.openai.com/v1/images/edits")
            - api_key: OpenAI API 密钥
        payload: 推理输入数据
            - images: 原始图片列表（必需，支持多张图片）
                * 列表格式: ["url1", "url2", ...]
                * 每个元素可以是:
                  - URL: "https://example.com/image.png"
                  - base64: "data:image/png;base64,..." 或直接 base64 编码
            - masks: 遮罩图片列表（可选，与 images 一一对应）
                * 列表格式: ["mask_url1", "mask_url2", ...]
                * 如果提供，长度必须与 images 相同
            - prompt: 统一的编辑指令（可选，与 prompts 二选一）
                * 例如: "Add a red hat to the person in each image"
                * 应用于所有图片
            - prompts: 每张图片的独立编辑指令（可选，与 prompt 二选一）
                * 列表格式: ["prompt1", "prompt2", ...]
                * 如果提供，长度必须与 images 相同
                * 优先级高于 prompt
                * 注意: prompt 和 prompts 必须提供其中一个
        inference_params: 推理参数
            - n: 每张图片生成的变体数量 (1-10, 默认 1)
            - size: 图片尺寸 (默认 "1024x1024")
                * 可选: "256x256", "512x512", "1024x1024"
            - response_format: 返回格式 (默认 "url")
                * "url": 返回图片 URL
                * "b64_json": 返回 base64 编码

    Returns:
        推理结果（编辑后的图片列表）
    """
    # 获取模型配置
    model_name = model_spec.get("name", "gpt-image-1")
    endpoint = model_spec.get("endpoint", "https://api.openai.com/v1/images/edits")
    api_key = model_spec.get("api_key")

    if not api_key:
        raise ValueError("OpenAI API key is required in model_spec.api_key")

    # 获取输入数据
    images = payload.get("images", [])
    masks = payload.get("masks", [])
    prompt = payload.get("prompt")
    prompts = payload.get("prompts", [])

    # 验证输入
    if not images:
        raise ValueError("'images' list is required in payload")

    # 如果提供了 prompts，长度必须与 images 相同
    if prompts and len(prompts) != len(images):
        raise ValueError(f"Length of 'prompts' ({len(prompts)}) must match 'images' ({len(images)})")

    # 如果提供了 masks，长度必须与 images 相同
    if masks and len(masks) != len(images):
        raise ValueError(f"Length of 'masks' ({len(masks)}) must match 'images' ({len(images)})")

    # 如果没有提供 prompts，使用统一的 prompt
    if not prompts:
        if not prompt:
            raise ValueError("Either 'prompt' or 'prompts' must be provided in payload")
        prompts = [prompt] * len(images)

    # 获取推理参数
    n = inference_params.get("n", 1)
    size = inference_params.get("size", "1024x1024")
    response_format = inference_params.get("response_format", "url")

    # 处理每张图片
    all_results = []

    for idx, image_source in enumerate(images):
        # 准备请求数据（使用 multipart/form-data）
        files = {}
        data = {
            "prompt": prompts[idx],
            "n": n,
            "size": size,
            "response_format": response_format,
            "model": model_name
        }

        # 处理图片（需要下载或解码为文件）
        image_bytes = _get_image_bytes(image_source)
        files["image"] = ("image.png", image_bytes, "image/png")

        # 处理遮罩（如果提供）
        if masks and idx < len(masks):
            mask_bytes = _get_image_bytes(masks[idx])
            files["mask"] = ("mask.png", mask_bytes, "image/png")

        # 调用 OpenAI API
        with httpx.Client() as client:
            response = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}"
                },
                data=data,
                files=files,
                timeout=120.0
            )

            # 检查响应状态
            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"OpenAI API error for image {idx} (status {response.status_code}): {error_detail}")

            result = response.json()

        # 提取生成的图片
        if "data" not in result or len(result["data"]) == 0:
            raise Exception(f"No images returned from OpenAI API for image {idx}")

        # 收集结果
        image_results = []
        for item in result["data"]:
            if response_format == "url":
                image_results.append({
                    "url": item.get("url"),
                    "revised_prompt": item.get("revised_prompt")
                })
            else:  # b64_json
                image_results.append({
                    "b64_json": item.get("b64_json"),
                    "revised_prompt": item.get("revised_prompt")
                })

        all_results.append({
            "original_index": idx,
            "prompt": prompts[idx],
            "edited_images": image_results,
            "created": result.get("created")
        })

    # 返回所有结果
    return {
        "results": all_results,
        "model": model_name,
        "total_images": len(images),
        "images_per_edit": n
    }


def _get_image_bytes(image_source: str) -> bytes:
    """
    从 URL 或 base64 获取图片字节数据
    
    Args:
        image_source: 图片来源（URL 或 base64）
    
    Returns:
        图片字节数据
    """
    import base64
    
    # 判断是 URL 还是 base64
    if image_source.startswith("http://") or image_source.startswith("https://"):
        # 从 URL 下载
        with httpx.Client() as client:
            response = client.get(image_source, timeout=30.0)
            if response.status_code != 200:
                raise Exception(f"Failed to download image from {image_source}")
            return response.content
    else:
        # base64 解码
        # 移除 data URI 前缀（如果有）
        if image_source.startswith("data:"):
            # 格式: data:image/png;base64,xxxxx
            image_source = image_source.split(",", 1)[1]
        
        return base64.b64decode(image_source)

