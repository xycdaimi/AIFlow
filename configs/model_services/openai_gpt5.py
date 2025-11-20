"""OpenAI GPT-5 Model Service - OpenAI GPT-5 模型服务接口"""

import httpx
from typing import Dict, Any


# 导入注册装饰器
from services.model_forwarder.infer import register_inference_function


@register_inference_function("openai-gpt5")
def openai_gpt5_inference(model_spec: Dict[str, Any],
                          payload: Dict[str, Any],
                          inference_params: Dict[str, Any]) -> Any:
    """
    OpenAI GPT-5 推理函数

    Args:
        model_spec: 模型规格配置
            - name: 模型名称 (例如 "gpt-5", "gpt-5-turbo")
            - endpoint: API 端点 (默认 "https://api.openai.com/v1/chat/completions")
            - api_key: OpenAI API 密钥
        payload: 推理输入数据
            - messages: 完整的消息列表（优先使用）
            - prompt: 用户提示词（文本）
            - system_prompt: 系统提示词
            - images: 图片列表，支持以下格式：
                * URL 字符串: "https://example.com/image.jpg"
                * base64 字符串: "data:image/jpeg;base64,..." 或直接 base64 编码
                * 字典: {"url": "...", "detail": "high"}  # detail 可选: "auto", "low", "high"
        inference_params: 推理参数
            - temperature: 温度参数 (0.0-2.0, 默认 0.7)
            - max_tokens: 最大生成 token 数 (默认 1000)
            - top_p: 核采样参数 (0.0-1.0, 默认 1.0)
            - frequency_penalty: 频率惩罚 (-2.0-2.0, 默认 0.0)
            - presence_penalty: 存在惩罚 (-2.0-2.0, 默认 0.0)
            - stream: 是否流式输出 (默认 False)
            ...

    Returns:
        推理结果（生成的文本内容）
    """
    # 获取模型配置
    model_name = model_spec.get("name", "gpt-5")
    endpoint = model_spec.get("endpoint", "https://api.openai.com/v1/chat/completions")
    api_key = model_spec.get("api_key")
    
    if not api_key:
        raise ValueError("OpenAI API key is required in model_spec.api_key")
    
    # 获取输入数据
    messages = payload.get("messages")
    prompt = payload.get("prompt")
    system_prompt = payload.get("system_prompt")
    images = payload.get("images", [])  # 图片列表，可以是 URL 或 base64

    # 构建 messages
    if not messages:
        # 如果没有提供 messages，从 prompt/system_prompt/images 构建
        messages = []

        # 添加系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加用户提示词（可能包含图片）
        if prompt or images:
            user_content = []

            # 添加文本内容
            if prompt:
                user_content.append({
                    "type": "text",
                    "text": prompt
                })

            # 添加图片内容
            for image in images:
                if isinstance(image, str):
                    # 判断是 URL 还是 base64
                    if image.startswith("http://") or image.startswith("https://"):
                        # URL 格式
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image
                            }
                        })
                    else:
                        # base64 格式
                        # 如果没有 data URI 前缀，添加默认前缀
                        if not image.startswith("data:"):
                            image = f"data:image/jpeg;base64,{image}"
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image
                            }
                        })
                elif isinstance(image, dict):
                    # 字典格式，可能包含 url 和 detail 参数
                    image_url_obj = {
                        "url": image.get("url")
                    }
                    if "detail" in image:
                        image_url_obj["detail"] = image["detail"]  # "auto", "low", "high"

                    user_content.append({
                        "type": "image_url",
                        "image_url": image_url_obj
                    })

            if user_content:
                messages.append({
                    "role": "user",
                    "content": user_content
                })

        if not messages:
            raise ValueError("Must provide either 'messages', 'prompt', 'system_prompt', or 'images' in payload")
    else:
        # 添加用户提示词（可能包含图片）
        if prompt or images:
            user_content = []

            # 添加文本内容
            if prompt:
                user_content.append({
                    "type": "text",
                    "text": prompt
                })

            # 添加图片内容
            for image in images:
                if isinstance(image, str):
                    # 判断是 URL 还是 base64
                    if image.startswith("http://") or image.startswith("https://"):
                        # URL 格式
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image
                            }
                        })
                    else:
                        # base64 格式
                        # 如果没有 data URI 前缀，添加默认前缀
                        if not image.startswith("data:"):
                            image = f"data:image/jpeg;base64,{image}"
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image
                            }
                        })
                elif isinstance(image, dict):
                    # 字典格式，可能包含 url 和 detail 参数
                    image_url_obj = {
                        "url": image.get("url")
                    }
                    if "detail" in image:
                        image_url_obj["detail"] = image["detail"]  # "auto", "low", "high"

                    user_content.append({
                        "type": "image_url",
                        "image_url": image_url_obj
                    })

            if user_content:
                messages.append({
                    "role": "user",
                    "content": user_content
                })

        if not messages:
            raise ValueError("Must provide either 'messages', 'prompt', 'system_prompt', or 'images' in payload")
    
    # 构建请求数据
    request_data = {
        "model": model_name,
        "messages": messages
    }
    
    # 动态添加所有推理参数到请求数据中
    if inference_params:
        request_data.update(inference_params)
    
    # 获取 stream 参数（用于后续判断）
    stream = inference_params.get("stream", False)
    
    # 调用 OpenAI API
    if stream:
        # 流式输出
        full_text = ""
        usage_info = {}
        finish_reason = None

        with httpx.Client() as client:
            with client.stream(
                "POST",
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=request_data,
                timeout=120.0
            ) as response:
                # 检查响应状态
                if response.status_code != 200:
                    error_detail = response.text
                    raise Exception(f"OpenAI API error (status {response.status_code}): {error_detail}")

                # 逐行读取流式响应
                for line in response.iter_lines():
                    if not line:
                        continue

                    # 移除 "data: " 前缀
                    if line.startswith("data: "):
                        line = line[6:]

                    # 检查是否是结束标记
                    if line == "[DONE]":
                        break

                    try:
                        import json
                        chunk = json.loads(line)

                        # 提取增量内容
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            full_text += content

                            # 获取 finish_reason
                            if chunk["choices"][0].get("finish_reason"):
                                finish_reason = chunk["choices"][0]["finish_reason"]

                        # 获取 usage 信息（通常在最后一个 chunk）
                        if "usage" in chunk:
                            usage_info = chunk["usage"]

                    except json.JSONDecodeError:
                        continue

        # 返回流式结果
        return {
            "text": full_text,
            "model": model_name,
            "usage": usage_info,
            "finish_reason": finish_reason,
            "stream": True
        }

    else:
        # 非流式输出
        with httpx.Client() as client:
            response = client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=request_data,
                timeout=120.0
            )

            # 检查响应状态
            if response.status_code != 200:
                error_detail = response.text
                raise Exception(f"OpenAI API error (status {response.status_code}): {error_detail}")

            result = response.json()

        # 提取生成的文本
        if "choices" not in result or len(result["choices"]) == 0:
            raise Exception("No choices returned from OpenAI API")

        generated_text = result["choices"][0]["message"]["content"]

        # 返回结果（可以返回更多信息）
        return {
            "text": generated_text,
            "model": model_name,
            "usage": result.get("usage", {}),
            "finish_reason": result["choices"][0].get("finish_reason"),
            "stream": False
        }

