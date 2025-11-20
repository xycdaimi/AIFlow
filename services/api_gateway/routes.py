"""API routes for API Gateway."""

from fastapi import APIRouter, HTTPException, Request, status, UploadFile, Form, File, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Set, Tuple, List
from datetime import datetime, timezone
from pydantic import BaseModel
import httpx
import os
from core.protocols import (
    TaskRequest,
    TaskResponse,
    TaskDetail,
    TaskStatus,
    ModelSpec,
    CallbackConfig,
    LogLevel,
    generate_task_id
)
from core.config import settings
from core.protocols import LogMessage
from datetime import datetime, timezone
from .dependencies import redis_client, rabbitmq_client, minio_store
import json

router = APIRouter(tags=["tasks"])

# HTTP Bearer 认证（auto_error=False 允许在开发模式下不提供 token）
security = HTTPBearer(auto_error=False)

# MinIO storage is now imported from dependencies
import base64

import re
import mimetypes


async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    验证 API Key

    Args:
        credentials: HTTP Bearer 认证凭据（可选）

    Returns:
        验证通过的 API Key

    Raises:
        HTTPException: 如果 API Key 无效
    """
    # 获取允许的 API Keys 列表
    valid_api_keys = settings.api_gateway_api_keys

    # 如果没有配置 API Keys，则允许所有请求（开发模式）
    if not valid_api_keys:
        print("⚠️  Warning: No API keys configured, allowing all requests (development mode)")
        return "dev-mode"

    # 开发模式下不需要验证
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    api_key = credentials.credentials

    # 验证 API Key
    if api_key not in valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return api_key


async def _send_log(task_id: str, level: LogLevel, event: str, message: str, context: Optional[Dict[str, Any]] = None):
    """
    发送日志到 RabbitMQ

    Args:
        task_id: 任务 ID
        level: 日志级别
        event: 事件标识
        message: 日志消息
        context: 额外上下文
    """
    try:
        log_data = LogMessage(
            timestamp=datetime.now(timezone.utc),
            task_id=task_id,
            service_name="api-gateway",
            service_instance="",
            level=level,
            event=event,
            message=message,
            context=context or {}
        )

        await rabbitmq_client.publish_log(log_data)
    except Exception as e:
        # 日志发送失败不影响主流程，只打印错误
        print(f"Failed to send log: {e}")


async def _normalize_json_payload_to_minio(task_id: str, obj: Any) -> Any:
    """
    Scan JSON payload and convert base64/data-URI media into MinIO input URLs.
    HTTP(S) URLs are kept as-is.
    """
    bucket = settings.minio_bucket_inputs
    b64_re = re.compile(r"^[A-Za-z0-9+/=\r\n]+$")

    def _safe_path_hint(hint: str) -> str:
        return (hint or "data").replace("/", "_").replace("\\", "_").replace("..", ".").strip("._") or "data"

    def _default_mime_for_hint(hint: str) -> str:
        h = (hint or "").lower()
        if any(k in h for k in ("image", "img", "mask")):
            return "image/png"
        if "audio" in h:
            return "audio/mpeg"
        if "video" in h:
            return "video/mp4"
        return "application/octet-stream"

    async def _upload_bytes_from_base64(raw_b64: str, hint: str, mime_override: str | None = None) -> str:
        try:
            data = base64.b64decode(raw_b64, validate=False)
        except Exception:
            # Not valid base64; return original
            return raw_b64
        mime = mime_override or _default_mime_for_hint(hint)
        ext = mimetypes.guess_extension(mime) or ".bin"
        object_name = f"tasks/{task_id}/inputs/{_safe_path_hint(hint)}{ext}"
        url = await minio_store.upload_bytes(bucket, object_name, data, mime)
        return url

    async def _walk(x: Any, hint: str = "") -> Any:
        # Strings: check URL/data URI/base64
        if isinstance(x, str):
            s = x.strip()
            # Keep http(s) URL
            if s.startswith("http://") or s.startswith("https://"):
                return s
            # Data URI
            if s.startswith("data:") and ";base64," in s:
                try:
                    header, b64 = s.split(",", 1)
                    # header like: data:image/png;base64
                    mime = header[5: header.find(";")]
                    return await _upload_bytes_from_base64(b64, hint, mime_override=mime)
                except Exception:
                    return s
            # Heuristic base64 (long and looks like base64) on media-related fields
            if len(s) > 512 and b64_re.match(s) and any(k in (hint or "").lower() for k in ("image", "img", "mask", "audio", "video", "media", "file")):
                return await _upload_bytes_from_base64(s, hint)
            return s

        # Bytes-like
        if isinstance(x, (bytes, bytearray)):
            mime = _default_mime_for_hint(hint)
            ext = mimetypes.guess_extension(mime) or ".bin"
            object_name = f"tasks/{task_id}/inputs/{_safe_path_hint(hint)}{ext}"
            url = await minio_store.upload_bytes(bucket, object_name, bytes(x), mime)
            return url

        # Lists
        if isinstance(x, list):
            out = []
            for i, v in enumerate(x):
                out.append(await _walk(v, f"{hint}_{i}" if hint else str(i)))
            return out

        # Dicts
        if isinstance(x, dict):
            out: Dict[str, Any] = {}
            for k, v in x.items():
                child_hint = f"{hint}.{k}" if hint else k
                out[k] = await _walk(v, child_hint)
            return out

        # Other types: leave as-is
        return x

    return await _walk(obj)

# Internal callback data model
class TaskCallbackRequest(BaseModel):
    """Internal callback request from model_forwarder."""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/tasks_json", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_josn(
    _: str = Depends(verify_api_key),
    task_request: Optional[TaskRequest] = None
):
    """
    创建任务接口

    1. application/json:
        - task_request
            - task_type: 任务类型 (必填)
            - model_spec: 模型规格 (必填)
            - payload: 任务数据，图片/音频/视频可以使用 URL 或 base64 编码 (必填)
            - inference_params: 推理参数 (可选)
            - callback: 回调配置 (可选)
                base64 数据会自动上传到 MinIO 并转换为 URL
    
    Args:
        task_request: JSON 格式的任务请求（application/json）
    
    Returns:
        TaskResponse: 包含任务 ID 和状态的响应
    """
    try:
        task_id = generate_task_id()
        now = datetime.now(timezone.utc)

        # 记录任务创建日志
        await _send_log(task_id, LogLevel.INFO, "task.created", f"Task {task_id} created")
        if not task_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="task_request is required"
            )
        # 解析 JSON 请求
        final_task_type = task_request.task_type
        final_model_spec = task_request.model_spec
        final_payload = task_request.payload
        final_inference_params = task_request.inference_params
        final_callback = task_request.callback

        # 处理 payload 中的 base64/URL 数据，转换为 MinIO URL
        if final_payload:
            final_payload = await _normalize_json_payload_to_minio(task_id, final_payload)
        # 解析推理参数 (可选)
        # final_inference_params = None
        # if inference_params:
        #     try:
        #         final_inference_params = json.loads(inference_params)
        #     except Exception as e:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail=f"Invalid inference_params JSON: {str(e)}"
        #         )

        # # 解析回调配置 (可选)
        # final_callback = None
        # if callback:
        #     try:
        #         callback_dict = json.loads(callback)
        #         final_callback = CallbackConfig(**callback_dict)
        #     except Exception as e:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail=f"Invalid callback JSON: {str(e)}"
        #         )

        # 发布任务到 RabbitMQ
        # callback 是内部回调接口，用于 model_forwarder 完成任务后回调
        internal_callback_url = f"{settings.api_gateway_url}/api/v1/internal/task-callback"
        task_data = {
            "model_spec": final_model_spec.model_dump(),
            "payload": final_payload,
            "inference_params": final_inference_params,
            "callback": {
                "url": internal_callback_url,
                "headers": {
                    "Authorization": f"Bearer {settings.api_gateway_internal_key}"
                }
            },
        }
        await rabbitmq_client.publish_task(task_id, final_task_type, task_data)

        # 记录任务发布日志
        await _send_log(
            task_id,
            LogLevel.INFO,
            "task.published",
            f"Task {task_id} published to RabbitMQ",
            {"task_type": final_task_type}
        )

        # 创建任务详情
        task_detail = TaskDetail(
            task_id=task_id,
            task_type=final_task_type,
            model_spec=final_model_spec,
            payload=final_payload,
            inference_params=final_inference_params,
            callback=final_callback,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            retry_count=0,
            max_retries=settings.task_max_retries
        )

        # 保存任务到 Redis
        await redis_client.set_task(task_id, task_detail, settings.task_ttl)

        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Task created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录错误日志
        await _send_log(
            task_id if 'task_id' in locals() else "unknown",
            LogLevel.ERROR,
            "task.create_failed",
            f"Failed to create task: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )

@router.post("/tasks_form", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_form(
    _: str = Depends(verify_api_key),
    task_type: Optional[str] = None,
    model_spec: Optional[str] = None,
    payload: Optional[str] = None,
    inference_params: Optional[str] = None,
    callback: Optional[str] = None,
    files: Optional[List[UploadFile]] = None
):
    """
    创建任务接口

    1. multipart/form-data:
       - task_type: 任务类型 (必填)
       - model_spec: 模型规格 JSON 字符串 (必填)
       - payload: 任务数据 JSON 字符串 (可选)
       - inference_params: 推理参数 JSON 字符串 (可选)
       - callback: 回调配置 JSON 字符串 (可选)
       - files: 文件列表，会自动上传到 MinIO 并转换为 URL (可选)

    Args:
        task_type: 表单格式的任务类型（multipart/form-data）
        model_spec: 表单格式的模型规格（multipart/form-data）
        payload: 表单格式的任务数据（multipart/form-data）
        inference_params: 表单格式的推理参数（multipart/form-data）
        callback: 表单格式的回调配置（multipart/form-data）
        files: 上传的文件列表（multipart/form-data）

    Returns:
        TaskResponse: 包含任务 ID 和状态的响应
    """
    try:
        task_id = generate_task_id()
        now = datetime.now(timezone.utc)

        # 记录任务创建日志
        await _send_log(task_id, LogLevel.INFO, "task.created", f"Task {task_id} created")
        # 验证必填字段
        if not task_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="task_type is required for multipart/form-data requests"
            )
        if not model_spec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="model_spec is required for multipart/form-data requests"
            )

        # 解析表单数据
        final_task_type = task_type

        try:
            model_spec_dict = json.loads(model_spec)
            final_model_spec = ModelSpec(**model_spec_dict)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model_spec JSON: {str(e)}"
            )

        # 解析 payload (可选)
        final_payload = {}
        if payload:
            try:
                final_payload = json.loads(payload)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid payload JSON: {str(e)}"
                )

        # 处理上传的文件
        if files:
            bucket = settings.minio_bucket_inputs
            file_urls = []

            for idx, file in enumerate(files):
                # 读取文件内容
                file_content = await file.read()

                # 确定 MIME 类型
                content_type = file.content_type or "application/octet-stream"

                # 生成对象名称
                ext = mimetypes.guess_extension(content_type) or ""
                if not ext and file.filename:
                    # 从文件名获取扩展名
                    _, ext = os.path.splitext(file.filename)

                safe_filename = (file.filename or f"file_{idx}").replace("/", "_").replace("\\", "_")
                object_name = f"tasks/{task_id}/inputs/{safe_filename}"

                # 上传到 MinIO
                url = await minio_store.upload_bytes(bucket, object_name, file_content, content_type)
                file_urls.append({
                    "filename": file.filename,
                    "url": url,
                    "content_type": content_type,
                    "size": len(file_content)
                })

            # 将文件 URL 添加到 payload
            final_payload["files"] = file_urls

        # 处理 payload 中可能存在的 base64 数据
        if final_payload:
            final_payload = await _normalize_json_payload_to_minio(task_id, final_payload)

        # 解析推理参数 (可选)
        final_inference_params = None
        if inference_params:
            try:
                final_inference_params = json.loads(inference_params)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid inference_params JSON: {str(e)}"
                )

        # 解析回调配置 (可选)
        final_callback = None
        if callback:
            try:
                callback_dict = json.loads(callback)
                final_callback = CallbackConfig(**callback_dict)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid callback JSON: {str(e)}"
                )

        # 发布任务到 RabbitMQ
        # callback 是内部回调接口，用于 model_forwarder 完成任务后回调
        internal_callback_url = f"{settings.api_gateway_url}/api/v1/internal/task-callback"
        task_data = {
            "model_spec": final_model_spec.model_dump(),
            "payload": final_payload,
            "inference_params": final_inference_params,
            "callback": {
                "url": internal_callback_url,
                "headers": {
                    "Authorization": f"Bearer {settings.api_gateway_internal_key}"
                }
            },
        }
        await rabbitmq_client.publish_task(task_id, final_task_type, task_data)

        # 记录任务发布日志
        await _send_log(
            task_id,
            LogLevel.INFO,
            "task.published",
            f"Task {task_id} published to RabbitMQ",
            {"task_type": final_task_type}
        )

        # 创建任务详情
        task_detail = TaskDetail(
            task_id=task_id,
            task_type=final_task_type,
            model_spec=final_model_spec,
            payload=final_payload,
            inference_params=final_inference_params,
            callback=final_callback,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            retry_count=0,
            max_retries=settings.task_max_retries
        )

        # 保存任务到 Redis
        await redis_client.set_task(task_id, task_detail, settings.task_ttl)

        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Task created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录错误日志
        await _send_log(
            task_id if 'task_id' in locals() else "unknown",
            LogLevel.ERROR,
            "task.create_failed",
            f"Failed to create task: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )

@router.post("/internal/task-callback", status_code=status.HTTP_200_OK)
async def task_callback(request: Request, callback_request: TaskCallbackRequest):
    """
    内部回调接口：接收 model_forwarder 的任务完成通知，并按以下规则处理：
    - 成功：回调用户，删除 Redis 中的任务数据
    - 失败：检查超时和重试次数，决定是否重新提交到 RabbitMQ
    """
    # 检查api_key
    api_key = request.headers.get("Authorization")
    if api_key != f"Bearer {settings.api_gateway_internal_key}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    task_id = callback_request.task_id

    try:
        # 1. 从 Redis 获取任务数据
        task = await redis_client.get_task(task_id)

        if not task:
            # Redis 中没有找到任务，丢弃这个回调
            print(f"⚠️  Task {task_id} not found in Redis, discarding callback")
            await _send_log(
                task_id,
                LogLevel.WARNING,
                "callback.task_not_found",
                f"Task {task_id} not found in Redis, callback discarded"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found in Redis"
            )

        now = datetime.now(timezone.utc)

        # 2. 首先检查是否超时（不管成功还是失败）
        elapsed_seconds = (now - task.created_at).total_seconds()
        max_wait_time = getattr(settings, 'task_max_wait_time', 300)  # 默认 300 秒

        if elapsed_seconds > max_wait_time:
            # 超时，丢弃任务
            print(f"✗ Task {task_id} exceeded max wait time ({elapsed_seconds:.1f}s > {max_wait_time}s), discarding")

            # 标记为失败
            task.status = TaskStatus.FAILED
            task.error = f"Timeout after {elapsed_seconds:.1f}s"
            if callback_request.status == TaskStatus.FAILED:
                task.error += f": {callback_request.error}"
            task.updated_at = now

            # 删除 Redis 中的任务数据
            await redis_client.delete_task(task_id)

            # 发送超时日志
            await _send_log(
                task_id,
                LogLevel.ERROR,
                "task.timeout",
                f"Task {task_id} exceeded max wait time, discarded",
                {"elapsed_seconds": elapsed_seconds, "max_wait_time": max_wait_time}
            )

            # # 回调用户（如果提供了回调配置）
            # if task.callback and task.callback.url:
            #     await _execute_user_callback(
            #         task_id=task_id,
            #         callback_url=task.callback.url,
            #         callback_headers=task.callback.headers,
            #         status=TaskStatus.FAILED,
            #         result=None,
            #         error=task.error
            #     )

            return {
                "status": "timeout",
                "task_id": task_id,
                "message": f"Task exceeded max wait time ({elapsed_seconds:.1f}s), discarded"
            }

        # 3. 判断推理是否成功
        if callback_request.status == TaskStatus.SUCCESS:
            # ========== 成功场景 ==========
            print(f"✓ Task {task_id} completed successfully")

            # 更新任务状态
            task.status = TaskStatus.SUCCESS
            task.result = callback_request.result
            task.updated_at = now
            await redis_client.set_task(task_id, task, ttl=settings.task_ttl)

            # 发送成功日志
            await _send_log(
                task_id,
                LogLevel.INFO,
                "task.completed",
                f"Task {task_id} completed successfully",
                {"result_keys": list(callback_request.result.keys()) if callback_request.result else []}
            )

            # 回调用户（如果提供了回调配置）
            if task.callback and task.callback.url:
                print(f"Calling user callback for task {task_id}: {task.callback.url}")
                await _execute_user_callback(
                    task_id=task_id,
                    callback_url=task.callback.url,
                    callback_headers=task.callback.headers,
                    status=TaskStatus.SUCCESS,
                    result=callback_request.result,
                    error=None
                )

                # 删除 Redis 中的任务数据
                await redis_client.delete_task(task_id)

            return {
                "status": "success",
                "task_id": task_id,
                "message": "Task completed and user notified"
            }

        else:
            # ========== 失败场景 ==========
            print(f"✗ Task {task_id} failed: {callback_request.error}")

            # 检查是否超过重试次数
            if task.retry_count >= task.max_retries:
                print(f"✗ Task {task_id} exceeded max retries ({task.retry_count}/{task.max_retries})")

                # 超过重试次数，不再重试，丢弃任务
                task.status = TaskStatus.FAILED
                task.error = f"Max retries exceeded ({task.max_retries}): {callback_request.error}"
                task.last_error = callback_request.error
                task.updated_at = now
                await redis_client.set_task(task_id, task, ttl=settings.task_ttl)

                # 发送失败日志
                await _send_log(
                    task_id,
                    LogLevel.ERROR,
                    "task.max_retries_exceeded",
                    f"Task {task_id} exceeded max retries",
                    {"retry_count": task.retry_count, "error": callback_request.error}
                )

                # 回调用户
                if task.callback and task.callback.url:
                    await _execute_user_callback(
                        task_id=task_id,
                        callback_url=task.callback.url,
                        callback_headers=task.callback.headers,
                        status=TaskStatus.FAILED,
                        result=None,
                        error=task.error
                    )
                    # 删除 Redis 中的任务数据
                    await redis_client.delete_task(task_id)

                return {
                    "status": "failed",
                    "task_id": task_id,
                    "message": "Task failed after max retries"
                }

            # ========== 重试场景 ==========
            # 更新重试计数
            task.retry_count += 1
            task.last_error = callback_request.error
            task.updated_at = now

            # 保存到 Redis
            await redis_client.set_task(task_id, task, ttl=settings.task_ttl)

            print(f"⟳ Retrying task {task_id} (attempt {task.retry_count}/{task.max_retries})")

            # 发送重试日志
            await _send_log(
                task_id,
                LogLevel.WARNING,
                "task.retrying",
                f"Retrying task {task_id} (attempt {task.retry_count}/{task.max_retries})",
                {"retry_count": task.retry_count, "error": callback_request.error}
            )

            # 重新提交到 RabbitMQ
            task_data = {
                "model_spec": task.model_spec.model_dump(),
                "payload": task.payload,
                "inference_params": task.inference_params,
                "callback": {
                    "url": f"{settings.api_gateway_url}/api/v1/internal/task-callback",
                    "headers": {
                        "Authorization": f"Bearer {settings.api_gateway_internal_key}"
                    }
                }
            }
            await rabbitmq_client.publish_task(task_id, task.task_type, task_data)

            return {
                "status": "retrying",
                "task_id": task_id,
                "retry_count": task.retry_count,
                "message": f"Task resubmitted for retry (attempt {task.retry_count}/{task.max_retries})"
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing callback for task {task_id}: {e}")
        await _send_log(
            task_id,
            LogLevel.ERROR,
            "callback.error",
            f"Error processing callback for task {task_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process callback: {str(e)}"
        )

@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(task_id: str):
    """
    Get task details and status.

    Args:
        task_id: Task identifier

    Returns:
        TaskDetail with current status and result (if available)
    """
    try:
        task = await redis_client.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        return task

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task: {str(e)}"
        )


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Get task status only.

    Args:
        task_id: Task identifier

    Returns:
        Task status information
    """
    try:
        task = await redis_client.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        return {
            "task_id": task_id,
            "status": task.status,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """
    Get task result (only for completed tasks).

    Args:
        task_id: Task identifier

    Returns:
        Task result if task is completed successfully
    """
    try:
        task = await redis_client.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        if task.status == TaskStatus.PENDING or task.status == TaskStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail=f"Task is still {task.status.lower()}"
            )

        await redis_client.delete_task(task_id)

        if task.status == TaskStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Task failed: {task.error}"
            )

        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task result: {str(e)}"
        )


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a task and cleanup associated resources including shared memory.

    Args:
        task_id: Task identifier

    Returns:
        Deletion confirmation
    """
    try:
        task = await redis_client.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        # Cleanup shared memory if enabled
        await redis_client.cleanup_task_shared_memory(task_id)

        # Delete task from Redis
        await redis_client.client.delete(f"task:{task_id}")

        return {
            "task_id": task_id,
            "message": "Task deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        )

# # --- MinIO helpers ---
# async def _convert_minio_urls_to_base64(obj: Any) -> tuple[Any, Set[str]]:
#     """Recursively convert MinIO URLs in obj to base64 payloads.
#     Returns (converted_obj, encountered_minio_urls).
#     """
#     encountered: Set[str] = set()

#     async def _convert(x: Any) -> Any:
#         # String URL case
#         if isinstance(x, str):
#             parsed = minio_store.parse_url(x)
#             if parsed:
#                 bucket, object_name = parsed
#                 try:
#                     data, content_type = await minio_store.get_bytes(bucket, object_name)
#                     encountered.add(x)
#                     return {
#                         "mime_type": content_type or "application/octet-stream",
#                         "data": base64.b64encode(data).decode("utf-8"),
#                     }
#                 except Exception:
#                     # If download fails, keep original URL
#                     return x
#             return x
#         # List case
#         if isinstance(x, list):
#             return [await _convert(i) for i in x]
#         # Dict case
#         if isinstance(x, dict):
#             out = {}
#             for k, v in x.items():
#                 out[k] = await _convert(v)
#             return out
#         # Primitive or unknown
#         return x

#     converted = await _convert(obj)
#     return converted, encountered


# def _collect_minio_urls(obj: Any) -> Set[str]:
#     """Collect all MinIO URLs from a nested object."""
#     urls: Set[str] = set()

#     def _walk(x: Any):
#         if isinstance(x, str):
#             parsed = minio_store.parse_url(x)
#             if parsed:
#                 urls.add(x)
#             return
#         if isinstance(x, list):
#             for i in x:
#                 _walk(i)
#             return
#         if isinstance(x, dict):
#             for v in x.values():
#                 _walk(v)
#             return

#     _walk(obj)
#     return urls


# async def _cleanup_task_storage(task: TaskDetail, extra_urls: Optional[Set[str]] = None):
#     """Delete MinIO objects for inputs (from task.payload) and any extra output URLs."""
#     urls = _collect_minio_urls(task.payload or {})
#     if extra_urls:
#         urls.update(extra_urls)

#     # Delete all
#     for url in urls:
#         parsed = minio_store.parse_url(url)
#         if not parsed:
#             continue
#         bucket, object_name = parsed
#         try:
#             await minio_store.delete_object(bucket, object_name)
#         except Exception:
#             # Ignore delete errors
#             pass



async def _execute_user_callback(
    task_id: str,
    callback_url: str,
    callback_headers: Optional[Dict[str, str]],
    status: TaskStatus,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    max_retries: int = 3
):
    """
    异步回调用户的 callback URL

    Args:
        task_id: 任务 ID
        callback_url: 用户的回调 URL
        callback_headers: 回调请求头
        status: 任务状态
        result: 任务结果
        error: 错误信息
        max_retries: 最大重试次数
    """
    import asyncio

    retry_count = 0
    last_error = None

    # 构建回调数据
    callback_data = {
        "task_id": task_id,
        "status": status.value,  # 转换为字符串
    }

    if status == TaskStatus.SUCCESS:
        callback_data["result"] = result
    elif status == TaskStatus.FAILED:
        callback_data["error"] = error

    while retry_count <= max_retries:
        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                response = await client.post(
                    callback_url,
                    json=callback_data,
                    headers=callback_headers or {}
                )

                # 检查响应状态
                if response.status_code >= 200 and response.status_code < 300:
                    print(f"✓ Task {task_id} user callback successful (attempt {retry_count + 1}/{max_retries + 1})")

                    # 发送成功日志
                    await _send_log(
                        task_id,
                        LogLevel.INFO,
                        "callback.user_success",
                        f"User callback successful for task {task_id}"
                    )
                    return  # 成功，退出
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    print(f"⚠️  Task {task_id} user callback error (attempt {retry_count + 1}/{max_retries + 1}): {last_error}")

        except asyncio.TimeoutError:
            last_error = "Request timeout (30s)"
            print(f"⚠️  Task {task_id} user callback timeout (attempt {retry_count + 1}/{max_retries + 1})")

        except Exception as e:
            last_error = str(e)
            print(f"⚠️  Task {task_id} user callback failed (attempt {retry_count + 1}/{max_retries + 1}): {last_error}")

        # 重试前等待（指数退避）
        retry_count += 1
        if retry_count <= max_retries:
            wait_time = min(2 ** retry_count, 30)  # 2s, 4s, 8s, ... 最多 30s
            print(f"   Retrying user callback in {wait_time}s...")
            await asyncio.sleep(wait_time)

    # 所有重试都失败
    print(f"❌ Task {task_id} user callback failed after {max_retries + 1} attempts. Last error: {last_error}")

    # 发送失败日志
    await _send_log(
        task_id,
        LogLevel.ERROR,
        "callback.user_failed",
        f"User callback failed for task {task_id} after {max_retries + 1} attempts",
        {"last_error": last_error}
    )

