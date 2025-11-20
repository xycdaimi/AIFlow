# Model Services - 模型服务接口

这个目录用于存放各种模型服务的调用接口。

## 目录结构

```
configs/model_services/
├── README.md                  # 本文件
├── text_generation.py         # 文本生成模型服务（示例）
├── image_generation.py        # 图像生成模型服务（示例）
├── openai_gpt5.py            # OpenAI GPT-5 模型服务（文本生成 + 多模态）
├── gpt_image_1.py            # GPT Image-1 模型服务（图像编辑）
└── your_custom_service.py     # 你的自定义模型服务
```

## 如何添加新的模型服务

### 1. 创建新的 Python 文件

在 `configs/model_services/` 目录下创建一个新的 `.py` 文件，例如 `audio_generation.py`。

### 2. 导入注册装饰器

```python
from services.model_forwarder.infer import register_inference_function
```

### 3. 使用装饰器注册推理函数

```python
@register_inference_function("audio-generation")
def audio_generation_inference(task_id, task_type, model_spec, payload, inference_params):
    """
    音频生成推理函数
    
    Args:
        task_id: 任务 ID
        task_type: 任务类型
        model_spec: 模型规格配置
        payload: 推理输入数据
        inference_params: 推理参数
    
    Returns:
        推理结果（output 字段的内容）
    """
    # 你的推理逻辑
    # 调用模型 API
    # 返回结果
    
    return {
        "audio_url": "https://example.com/audio.mp3",
        "duration": 10.5
    }
```

### 4. 参数说明

#### `task_id` (str)
- 任务的唯一标识符

#### `task_type` (str)
- 任务类型，与装饰器中注册的类型一致
- 例如：`"text-generation"`, `"image-generation"`, `"audio-generation"`

#### `model_spec` (Dict[str, Any])
- 模型规格配置，包含：
  - `name`: 模型名称
  - `provider`: 模型提供商
  - `endpoint`: API 端点 URL
  - `api_key`: API 密钥
  - 其他自定义配置

#### `payload` (Dict[str, Any])
- 推理输入数据，根据任务类型不同而不同
- 文本生成：`prompt`, `messages`
- 图像生成：`prompt`, `negative_prompt`
- 音频生成：`text`, `voice`

#### `inference_params` (Dict[str, Any])
- 推理参数，根据任务类型不同而不同
- 文本生成：`temperature`, `max_tokens`, `top_p`
- 图像生成：`width`, `height`, `steps`, `guidance_scale`
- 音频生成：`speed`, `pitch`

### 5. 返回值

推理函数应该返回推理结果（output 字段的内容），可以是：
- 字符串：简单的文本结果
- 字典：复杂的结构化结果
- 列表：多个结果

**注意**：不需要返回完整的响应结构（包含 `task_id`, `status`, `result` 等），`infer()` 函数会自动包装。

### 6. 示例：完整的模型服务文件

```python
"""Custom Model Service - 自定义模型服务接口"""

import httpx
from typing import Dict, Any
from services.model_forwarder.infer import register_inference_function


@register_inference_function("custom-task")
def custom_inference(task_id: str, task_type: str, model_spec: Dict[str, Any], 
                    payload: Dict[str, Any], inference_params: Dict[str, Any]) -> Any:
    """自定义推理函数"""
    
    # 获取配置
    endpoint = model_spec.get("endpoint")
    api_key = model_spec.get("api_key")
    
    # 调用 API
    with httpx.Client() as client:
        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "input": payload,
                "params": inference_params
            },
            timeout=60.0
        )
        result = response.json()
    
    # 返回结果
    return result["output"]
```

## 自动加载机制

当 Model Forwarder 服务启动时，会自动：
1. 扫描 `configs/model_services/` 目录
2. 加载所有 `.py` 文件（跳过 `_` 开头的文件）
3. 执行文件中的代码，注册所有使用 `@register_inference_function` 装饰的函数
4. 将函数注册到 `INFERENCE_REGISTRY` 哈希桶中

## 查看已注册的任务类型

```python
from services.model_forwarder.infer import get_registered_task_types

print(get_registered_task_types())
# 输出: ['text-generation', 'image-generation', 'audio-generation', ...]
```

## 已实现的模型服务

### 1. OpenAI GPT-5 (`openai-gpt5`)

调用 OpenAI 的 GPT-5 模型进行文本生成，支持多模态输入（文本 + 图片）。

#### **示例 1: 使用完整的 messages 格式**

```json
{
  "task_type": "openai-gpt5",
  "model_spec": {
    "name": "gpt-5",
    "api_key": "sk-..."
  },
  "payload": {
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ]
  },
  "inference_params": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

#### **示例 2: 使用系统提示词和用户提示词**

```json
{
  "task_type": "openai-gpt5",
  "model_spec": {
    "name": "gpt-5",
    "api_key": "sk-..."
  },
  "payload": {
    "system_prompt": "You are a creative writer.",
    "prompt": "Write a poem about AI"
  },
  "inference_params": {
    "temperature": 0.9,
    "max_tokens": 500
  }
}
```

#### **示例 3: 单图片输入（URL 格式）**

```json
{
  "task_type": "openai-gpt5",
  "model_spec": {
    "name": "gpt-5",
    "api_key": "sk-..."
  },
  "payload": {
    "prompt": "What's in this image?",
    "images": [
      "https://example.com/image.jpg"
    ]
  },
  "inference_params": {
    "max_tokens": 300
  }
}
```

#### **示例 4: 多图片输入（混合格式）**

```json
{
  "task_type": "openai-gpt5",
  "model_spec": {
    "name": "gpt-5",
    "api_key": "sk-..."
  },
  "payload": {
    "system_prompt": "You are an image analysis expert.",
    "prompt": "Compare these images and describe the differences.",
    "images": [
      "https://example.com/image1.jpg",
      "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
      {
        "url": "https://example.com/image2.jpg",
        "detail": "high"
      }
    ]
  },
  "inference_params": {
    "temperature": 0.5,
    "max_tokens": 1000
  }
}
```

#### **示例 5: 仅图片输入（无文本提示）**

```json
{
  "task_type": "openai-gpt5",
  "model_spec": {
    "name": "gpt-5",
    "api_key": "sk-..."
  },
  "payload": {
    "images": [
      "https://example.com/diagram.png"
    ]
  },
  "inference_params": {
    "max_tokens": 500
  }
}
```

#### **图片格式说明**

`images` 字段支持以下三种格式：

1. **URL 字符串**:
   ```json
   "images": ["https://example.com/image.jpg"]
   ```

2. **Base64 字符串**:
   ```json
   "images": ["data:image/jpeg;base64,/9j/4AAQSkZJRg..."]
   ```
   或直接 base64 编码（自动添加前缀）:
   ```json
   "images": ["/9j/4AAQSkZJRg..."]
   ```

3. **字典格式**（支持 detail 参数）:
   ```json
   "images": [
     {
       "url": "https://example.com/image.jpg",
       "detail": "high"
     }
   ]
   ```
   - `detail` 参数可选值:
     - `"auto"`: 自动选择（默认）
     - `"low"`: 低分辨率（更快，更便宜）
     - `"high"`: 高分辨率（更详细，更贵）

#### **流式输出示例**

```json
{
  "task_type": "openai-gpt5",
  "model_spec": {
    "name": "gpt-5",
    "api_key": "sk-..."
  },
  "payload": {
    "system_prompt": "You are a storyteller.",
    "prompt": "Tell me a long story about space exploration"
  },
  "inference_params": {
    "temperature": 0.8,
    "max_tokens": 2000,
    "stream": true
  }
}
```

**返回结果（非流式）**：

```json
{
  "text": "生成的文本内容...",
  "model": "gpt-5",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  },
  "finish_reason": "stop",
  "stream": false
}
```

**返回结果（流式）**：

```json
{
  "text": "完整的生成文本内容（所有流式块拼接后的结果）...",
  "model": "gpt-5",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  },
  "finish_reason": "stop",
  "stream": true
}
```

---

### 2. GPT Image-1 (`gpt-image-1`)

调用 OpenAI 的 GPT Image-1 模型进行图像编辑，**支持批量多图编辑**。

#### **示例 1: 单图编辑（统一提示词）**

```json
{
  "task_type": "gpt-image-1",
  "model_spec": {
    "name": "gpt-image-1",
    "api_key": "sk-..."
  },
  "payload": {
    "images": ["https://example.com/photo.png"],
    "prompt": "Add a red hat to the person in the image"
  },
  "inference_params": {
    "n": 1,
    "size": "1024x1024"
  }
}
```

#### **示例 2: 多图编辑（统一提示词）**

```json
{
  "task_type": "gpt-image-1",
  "model_spec": {
    "name": "gpt-image-1",
    "api_key": "sk-..."
  },
  "payload": {
    "images": [
      "https://example.com/photo1.png",
      "https://example.com/photo2.png",
      "https://example.com/photo3.png"
    ],
    "prompt": "Add sunglasses to the person"
  },
  "inference_params": {
    "n": 2,
    "size": "1024x1024"
  }
}
```

#### **示例 3: 多图编辑（独立提示词）**

```json
{
  "task_type": "gpt-image-1",
  "model_spec": {
    "name": "gpt-image-1",
    "api_key": "sk-..."
  },
  "payload": {
    "images": [
      "https://example.com/room1.png",
      "https://example.com/room2.png",
      "https://example.com/room3.png"
    ],
    "prompts": [
      "Redesign this room in modern minimalist style",
      "Convert this room to a cozy library",
      "Transform this room into a home office"
    ]
  },
  "inference_params": {
    "n": 1,
    "size": "1024x1024"
  }
}
```

#### **示例 4: 多图编辑 + 遮罩（局部编辑）**

```json
{
  "task_type": "gpt-image-1",
  "model_spec": {
    "name": "gpt-image-1",
    "api_key": "sk-..."
  },
  "payload": {
    "images": [
      "https://example.com/photo1.png",
      "https://example.com/photo2.png"
    ],
    "masks": [
      "https://example.com/mask1.png",
      "https://example.com/mask2.png"
    ],
    "prompts": [
      "Replace the masked area with a beautiful garden",
      "Fill the masked area with a modern sculpture"
    ]
  },
  "inference_params": {
    "n": 1,
    "size": "1024x1024"
  }
}
```

#### **示例 5: 使用 base64 格式（批量）**

```json
{
  "task_type": "gpt-image-1",
  "model_spec": {
    "name": "gpt-image-1",
    "api_key": "sk-..."
  },
  "payload": {
    "images": [
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    ],
    "prompt": "Change the background to a sunset scene"
  },
  "inference_params": {
    "n": 1,
    "size": "512x512",
    "response_format": "b64_json"
  }
}
```

#### **参数说明**

**payload 参数**:
- `images` (必需): 原始图片列表
  - 格式: `["url1", "url2", ...]`
  - 每个元素可以是:
    - URL: `"https://example.com/image.png"`
    - base64: `"data:image/png;base64,..."` 或直接 base64 编码
- `masks` (可选): 遮罩图片列表
  - 格式: `["mask1", "mask2", ...]`
  - 长度必须与 `images` 相同
  - PNG 格式，透明区域表示要编辑的部分
- `prompt` (可选): 统一的编辑指令
  - 应用于所有图片
  - 如果提供了 `prompts`，则忽略此参数
- `prompts` (可选): 每张图片的独立编辑指令
  - 格式: `["prompt1", "prompt2", ...]`
  - 长度必须与 `images` 相同
  - 优先级高于 `prompt`

**inference_params 参数**:
- `n`: 每张图片生成的变体数量 (1-10, 默认 1)
- `size`: 图片尺寸 (默认 "1024x1024")
  - 可选: `"256x256"`, `"512x512"`, `"1024x1024"`
- `response_format`: 返回格式 (默认 "url")
  - `"url"`: 返回图片 URL（有效期有限）
  - `"b64_json"`: 返回 base64 编码

#### **返回结果（单图）**

```json
{
  "results": [
    {
      "original_index": 0,
      "prompt": "Add a red hat to the person",
      "edited_images": [
        {
          "url": "https://oaidalleapiprodscus.blob.core.windows.net/...",
          "revised_prompt": "A person wearing a stylish red fedora hat..."
        }
      ],
      "created": 1234567890
    }
  ],
  "model": "gpt-image-1",
  "total_images": 1,
  "images_per_edit": 1
}
```

#### **返回结果（多图，每图生成 2 个变体）**

```json
{
  "results": [
    {
      "original_index": 0,
      "prompt": "Add sunglasses",
      "edited_images": [
        {
          "url": "https://oaidalleapiprodscus.blob.core.windows.net/variant1...",
          "revised_prompt": "A person wearing stylish sunglasses..."
        },
        {
          "url": "https://oaidalleapiprodscus.blob.core.windows.net/variant2...",
          "revised_prompt": "A person wearing aviator sunglasses..."
        }
      ],
      "created": 1234567890
    },
    {
      "original_index": 1,
      "prompt": "Add sunglasses",
      "edited_images": [
        {
          "url": "https://oaidalleapiprodscus.blob.core.windows.net/variant1...",
          "revised_prompt": "Another person with sunglasses..."
        },
        {
          "url": "https://oaidalleapiprodscus.blob.core.windows.net/variant2...",
          "revised_prompt": "Another person with different sunglasses..."
        }
      ],
      "created": 1234567891
    }
  ],
  "model": "gpt-image-1",
  "total_images": 2,
  "images_per_edit": 2
}
```

#### **遮罩图片要求**

- **格式**: PNG 格式（支持透明度）
- **尺寸**: 必须与原始图片相同
- **透明区域**: 完全透明（alpha = 0）的区域将被编辑
- **不透明区域**: 不透明的区域将保持不变

#### **使用场景**

1. **批量添加元素**: 为多张照片统一添加相同元素
   ```json
   {
     "images": ["photo1.png", "photo2.png", "photo3.png"],
     "prompt": "Add sunglasses to the person"
   }
   ```

2. **批量风格转换**: 将多张图片转换为相同风格
   ```json
   {
     "images": ["img1.png", "img2.png"],
     "prompt": "Convert to watercolor painting style"
   }
   ```

3. **个性化编辑**: 为每张图片应用不同的编辑
   ```json
   {
     "images": ["room1.png", "room2.png"],
     "prompts": [
       "Add a modern sofa",
       "Add a vintage bookshelf"
     ]
   }
   ```

4. **局部批量修改**: 使用遮罩对多张图片进行精确编辑
   ```json
   {
     "images": ["photo1.png", "photo2.png"],
     "masks": ["mask1.png", "mask2.png"],
     "prompt": "Replace the masked area with flowers"
   }
   ```

5. **生成多个变体**: 为每张图片生成多个编辑版本
   ```json
   {
     "images": ["design.png"],
     "prompt": "Redesign in modern style",
     "inference_params": {"n": 4}
   }
   ```

---

## 注意事项

1. **task_type 必须唯一**：每个 task_type 只能注册一个推理函数
2. **文件名无要求**：文件名可以任意，只要是 `.py` 文件即可
3. **可以在一个文件中注册多个函数**：一个文件可以包含多个 `@register_inference_function` 装饰的函数
4. **异常处理**：推理函数中的异常会被 `infer()` 函数捕获并返回错误结果
5. **同步/异步**：目前推理函数是同步的，如果需要异步调用，请在函数内部使用 `asyncio.run()` 或其他方式
6. **API 密钥安全**：建议将 API 密钥存储在环境变量或配置文件中，不要硬编码在代码中

