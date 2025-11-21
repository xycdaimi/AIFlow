# AI Router 错误码规范

## 📋 目录

- [错误码格式](#错误码格式)
- [错误响应格式](#错误响应格式)
- [错误码列表](#错误码列表)
- [使用示例](#使用示例)

---

## 错误码格式

错误码采用统一格式: **EXXXYYYY**

- **E**: Error 前缀
- **XXX**: 模块代码 (3位数字)
- **YYYY**: 具体错误代码 (4位数字)

### 模块代码分配

| 模块代码 | 模块名称 | 说明 |
|---------|---------|------|
| 100 | 通用错误 | 通用的请求和参数错误 |
| 200 | 认证和授权 | API Key、权限相关错误 |
| 300 | 任务管理 | 任务创建、查询、状态相关错误 |
| 400 | 模型推理 | 模型推理、Forwarder 相关错误 |
| 500 | 存储服务 | MinIO、文件存储相关错误 |
| 600 | 消息队列 | RabbitMQ 相关错误 |
| 700 | 服务发现 | Consul 服务注册和发现错误 |
| 800 | 日志服务 | 日志收集和查询错误 |
| 900 | 系统错误 | Redis、数据库、网络等系统级错误 |

---

## 错误响应格式

所有错误响应遵循统一的 JSON 格式:

```json
{
  "error_code": "E3000001",
  "message": "Task not found",
  "details": {
    "task_id": "abc-123-def"
  }
}
```

### 字段说明

- **error_code** (string, 必需): 错误码
- **message** (string, 必需): 人类可读的错误消息
- **details** (object, 可选): 额外的错误详情

---

## 错误码列表

### 1. 通用错误 (E100XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E1000001 | 400 | 无效的请求 | 请求格式不正确 |
| E1000002 | 400 | 无效的参数 | 参数值不符合要求 |
| E1000003 | 400 | 缺少必需参数 | 缺少必填字段 |
| E1000004 | 400 | 无效的 JSON 格式 | JSON 解析失败 |
| E1000005 | 404 | 资源不存在 | 请求的资源未找到 |
| E1000099 | 500 | 内部错误 | 服务器内部错误 |

### 2. 认证和授权 (E200XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E2000001 | 401 | 未认证 | 未提供认证信息 |
| E2000002 | 401 | 无效的 API Key | API Key 不正确 |
| E2000003 | 401 | 缺少 API Key | 请求头中缺少 API Key |
| E2000004 | 403 | 无权限访问 | 没有访问该资源的权限 |
| E2000005 | 401 | 无效的内部服务密钥 | 内部服务间调用密钥错误 |

### 3. 任务管理 (E300XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E3000001 | 404 | 任务不存在 | 查询的任务 ID 不存在 |
| E3000002 | 500 | 任务创建失败 | 创建任务时发生错误 |
| E3000003 | 408 | 任务超时 | 任务执行超过最大等待时间 |
| E3000004 | 500 | 任务超过最大重试次数 | 任务失败重试次数达到上限 |
| E3000005 | 409 | 任务已存在 | 任务 ID 冲突 |
| E3000006 | 400 | 任务状态无效 | 任务状态不符合预期 |
| E3000007 | 202 | 任务处理中 | 任务仍在处理中 |
| E3000008 | 500 | 任务失败 | 任务执行失败 |
| E3000009 | 400 | 无效的任务类型 | 不支持的任务类型 |
| E3000010 | 400 | 无效的模型规格 | model_spec 格式错误 |
| E3000011 | 400 | 无效的任务数据 | payload 格式错误 |
| E3000012 | 400 | 无效的回调配置 | callback 配置错误 |

### 4. 模型推理 (E400XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E4000001 | 500 | 推理失败 | 模型推理过程中出错 |
| E4000002 | 404 | 模型不存在 | 请求的模型未注册 |
| E4000003 | 503 | 模型不可用 | 模型服务暂时不可用 |
| E4000004 | 503 | 推理服务繁忙 | Forwarder 正在处理其他任务 |
| E4000005 | 404 | 推理服务不存在 | 没有可用的 Forwarder 实例 |
| E4000006 | 400 | 无效的推理参数 | inference_params 格式错误 |
| E4000007 | 502 | 模型 API 错误 | 调用外部模型 API 失败 |

### 5. 存储服务 (E500XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E5000001 | 500 | 存储错误 | 通用存储错误 |
| E5000002 | 503 | MinIO 连接失败 | 无法连接到 MinIO 服务 |
| E5000003 | 500 | MinIO 上传失败 | 文件上传到 MinIO 失败 |
| E5000004 | 500 | MinIO 下载失败 | 从 MinIO 下载文件失败 |
| E5000005 | 500 | MinIO 删除失败 | 删除 MinIO 文件失败 |
| E5000006 | 404 | MinIO 存储桶不存在 | 指定的 bucket 不存在 |
| E5000007 | 413 | 文件过大 | 文件大小超过限制 |
| E5000008 | 400 | 无效的文件格式 | 文件格式不支持 |

### 6. 消息队列 (E600XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E6000001 | 503 | RabbitMQ 连接失败 | 无法连接到 RabbitMQ |
| E6000002 | 500 | RabbitMQ 发布失败 | 消息发布到队列失败 |
| E6000003 | 500 | RabbitMQ 消费失败 | 消息消费失败 |
| E6000004 | 404 | 队列不存在 | 指定的队列不存在 |
| E6000005 | 400 | 消息格式无效 | 消息格式不正确 |

### 7. 服务发现 (E700XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E7000001 | 503 | Consul 连接失败 | 无法连接到 Consul |
| E7000002 | 500 | 服务注册失败 | 服务注册到 Consul 失败 |
| E7000003 | 404 | 服务不存在 | 在 Consul 中未找到服务 |
| E7000004 | 503 | 服务不可用 | 服务暂时不可用 |

### 8. 日志服务 (E800XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E8000001 | 500 | 日志写入失败 | 日志写入数据库失败 |
| E8000002 | 500 | 日志查询失败 | 日志查询失败 |
| E8000003 | 503 | PostgreSQL 连接失败 | 无法连接到 PostgreSQL |

### 9. 系统错误 (E900XXXX)

| 错误码 | HTTP状态码 | 说明 | 示例场景 |
|--------|-----------|------|---------|
| E9000001 | 503 | Redis 连接失败 | 无法连接到 Redis |
| E9000002 | 500 | Redis 操作失败 | Redis 操作执行失败 |
| E9000003 | 500 | 数据库错误 | 数据库操作失败 |
| E9000004 | 503 | 网络错误 | 网络连接失败 |
| E9000005 | 408 | 超时错误 | 请求超时 |
| E9000006 | 500 | 配置错误 | 配置文件错误 |
| E9000007 | 503 | 服务关闭中 | 服务正在关闭 |

---

## 使用示例

### Python 代码示例

#### 1. 抛出标准错误

```python
from core.errors import raise_task_not_found, raise_invalid_parameter

# 任务不存在
raise_task_not_found("task-123")

# 无效参数
raise_invalid_parameter("temperature", "Temperature must be between 0 and 1")
```

#### 2. 使用错误码抛出自定义错误

```python
from core.errors import raise_error, ErrorCode

raise_error(
    ErrorCode.TASK_TIMEOUT,
    message="Task execution timeout after 120 seconds",
    details={
        "task_id": "task-123",
        "elapsed_time": 120,
        "max_wait_time": 120
    }
)
```

#### 3. 使用异常处理装饰器

```python
from core.errors import handle_errors
from fastapi import APIRouter

router = APIRouter()

@router.get("/tasks/{task_id}")
@handle_errors
async def get_task(task_id: str):
    # 自动处理异常并转换为标准错误响应
    task = await get_task_from_db(task_id)
    if not task:
        raise_task_not_found(task_id)
    return task
```

#### 4. 创建错误响应（不抛出异常）

```python
from core.errors import create_error_response, ErrorCode

# 创建错误响应字典
error_response = create_error_response(
    ErrorCode.MODEL_UNAVAILABLE,
    message="Model gpt-4 is temporarily unavailable",
    details={"model": "gpt-4", "retry_after": 60}
)

# 返回:
# {
#     "error_code": "E4000003",
#     "message": "Model gpt-4 is temporarily unavailable",
#     "details": {
#         "model": "gpt-4",
#         "retry_after": 60
#     }
# }
```

#### 5. 捕获和处理 AIRouteException

```python
from core.errors import AIRouteException, ErrorCode

try:
    # 某些操作
    process_task(task_id)
except AIRouteException as e:
    # 记录错误
    logger.error(f"Error: {e.error_code} - {e.message}", extra=e.details)
    # 转换为 HTTP 异常
    raise e.to_http_exception()
```

### API 响应示例

#### 成功响应

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "task_id": "task-123",
  "status": "SUCCESS",
  "result": {
    "output": "Hello, world!"
  }
}
```

#### 错误响应示例 1: 任务不存在

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error_code": "E3000001",
  "message": "Task task-123 not found",
  "details": {
    "task_id": "task-123"
  }
}
```

#### 错误响应示例 2: 无效的 API Key

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error_code": "E2000002",
  "message": "Invalid API key",
  "details": {}
}
```

#### 错误响应示例 3: 模型服务繁忙

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "error_code": "E4000004",
  "message": "Model forwarder is busy",
  "details": {
    "forwarder_id": "forwarder-001",
    "current_task": "task-456",
    "retry_after": 30
  }
}
```

#### 错误响应示例 4: 参数验证失败

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error_code": "E1000002",
  "message": "Invalid parameter: temperature",
  "details": {
    "parameter": "temperature",
    "value": 2.5,
    "expected": "Value between 0 and 1"
  }
}
```

---

## 最佳实践

### 1. 选择合适的错误码

- 优先使用已定义的错误码
- 如果没有合适的错误码，使用最接近的通用错误码
- 需要新错误码时，在 `core/errors.py` 中添加

### 2. 提供有用的错误详情

```python
# ❌ 不好的做法
raise_error(ErrorCode.TASK_FAILED)

# ✅ 好的做法
raise_error(
    ErrorCode.TASK_FAILED,
    message="Task failed due to model API timeout",
    details={
        "task_id": task_id,
        "model": "gpt-4",
        "error": "Connection timeout after 30s",
        "retry_count": 3
    }
)
```

### 3. 使用便捷函数

```python
# ❌ 不推荐
raise HTTPException(status_code=404, detail="Task not found")

# ✅ 推荐
raise_task_not_found(task_id)
```

### 4. 统一异常处理

```python
# 在路由中使用装饰器
@router.post("/tasks")
@handle_errors
async def create_task(request: TaskRequest):
    # 所有异常会自动转换为标准错误响应
    return await task_service.create(request)
```

### 5. 记录错误日志

```python
from core.errors import AIRouteException
import logging

logger = logging.getLogger(__name__)

try:
    result = await process_task(task_id)
except AIRouteException as e:
    logger.error(
        f"Task processing failed: {e.error_code}",
        extra={
            "error_code": e.error_code.value,
            "task_id": task_id,
            **e.details
        }
    )
    raise
```

---

## 错误码扩展指南

如果需要添加新的错误码:

1. **在 `core/errors.py` 中添加错误码**

```python
class ErrorCode(str, Enum):
    # ... 现有错误码 ...

    # 新增错误码
    NEW_ERROR = "E3000013"  # 新的任务相关错误
```

2. **添加 HTTP 状态码映射**

```python
ERROR_CODE_TO_HTTP_STATUS = {
    # ... 现有映射 ...
    ErrorCode.NEW_ERROR: status.HTTP_400_BAD_REQUEST,
}
```

3. **添加错误消息**

```python
ERROR_CODE_TO_MESSAGE = {
    # ... 现有消息 ...
    ErrorCode.NEW_ERROR: "New error description",
}
```

4. **（可选）添加便捷函数**

```python
def raise_new_error(param: str, message: Optional[str] = None):
    """抛出新错误"""
    raise_error(
        ErrorCode.NEW_ERROR,
        message or f"New error for {param}",
        {"param": param}
    )
```

5. **更新文档**

在本文档中添加新错误码的说明。

---

## 常见问题

### Q: 如何处理第三方库的异常?

A: 在异常处理装饰器中捕获并转换:

```python
try:
    await redis_client.set(key, value)
except redis.ConnectionError:
    raise_error(ErrorCode.REDIS_CONNECTION_FAILED)
except redis.TimeoutError:
    raise_error(ErrorCode.TIMEOUT_ERROR)
```

### Q: 如何在回调中返回错误?

A: 使用 `create_error_response` 创建错误字典:

```python
error_response = create_error_response(
    ErrorCode.TASK_FAILED,
    message="Task execution failed",
    details={"reason": "Model API error"}
)

# 发送到回调 URL
await send_callback(callback_url, error_response)
```

### Q: 如何处理多语言错误消息?

A: 可以扩展 `ERROR_CODE_TO_MESSAGE` 支持多语言:

```python
# 在 core/errors.py 中
ERROR_MESSAGES_I18N = {
    "en": {
        ErrorCode.TASK_NOT_FOUND: "Task not found",
    },
    "zh": {
        ErrorCode.TASK_NOT_FOUND: "任务不存在",
    }
}

def get_error_message(error_code: ErrorCode, lang: str = "en") -> str:
    return ERROR_MESSAGES_I18N.get(lang, {}).get(
        error_code,
        ERROR_CODE_TO_MESSAGE[error_code]
    )
```

---

## 版本历史

- **v1.0.0** (2025-11-21): 初始版本，定义基础错误码体系


