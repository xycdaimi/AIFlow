"""Model Forwarder Routes - 处理任务接收和状态查询"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from core.protocols import TaskMessage, LogMessage, LogLevel
from core.utils import RabbitMQClient
from core.config import settings
import httpx
from services.model_forwarder.infer import get_registered_task_types

router = APIRouter(tags=["forwarder"])

# 全局变量
task_queue = None  # 任务队列（主进程 -> 推理协程）
result_queue = None  # 结果队列（推理协程 -> 主进程）
current_task: Optional[Dict[str, Any]] = None  # 当前正在处理的任务
current_callback: Optional[Dict[str, Any]] = None  # 当前任务的回调配置
rabbitmq_client: Optional[RabbitMQClient] = None
http_client: Optional[httpx.AsyncClient] = None
shutting_down = False  # 优雅关闭标志


def set_queues(task_q, result_q):
    """设置共享队列"""
    global task_queue, result_queue
    task_queue = task_q
    result_queue = result_q


def set_current_task(task: Optional[Dict[str, Any]]):
    """设置当前任务"""
    global current_task
    current_task = task


def set_rabbitmq_client(client: RabbitMQClient):
    """设置 RabbitMQ 客户端"""
    global rabbitmq_client
    rabbitmq_client = client


def set_http_client(client: httpx.AsyncClient):
    """设置 HTTP 客户端"""
    global http_client
    http_client = client


def set_shutting_down(value: bool):
    """设置关闭标志"""
    global shutting_down
    shutting_down = value


def is_shutting_down() -> bool:
    """检查是否正在关闭"""
    global shutting_down
    return shutting_down


@router.get("/status")
async def get_status():
    """
    查询当前推理状态

    Returns:
        - busy: 是否正在推理
        - current_task: 当前任务信息（如果有）
    """
    return {
        "busy": current_task is not None,
        "current_task": current_task,
        "pending_tasks_count": task_queue.qsize()
    }


@router.get("/api/v1/supported-tasks")
async def get_supported_tasks():
    """
    获取所有已注册的 task_type（支持的推理服务）

    Returns:
        - task_types: 已注册的 task_type 列表
        - count: 注册的服务数量
    """
    task_types = get_registered_task_types()
    return {
        "task_types": task_types,
        "count": len(task_types),
        "service": "model-forwarder",
        "instance_id": settings.forwarder_instance_id
    }


@router.post("/api/v1/tasks")
async def receive_task(task_data: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    接收来自 Task Scheduler 的任务

    Args:
        task_data: 任务数据，包含 task_id, task_type, model_spec, payload, inference_params, callback

    Returns:
        任务接收确认
    """
    global current_task, current_callback, task_queue, shutting_down

    # 检查是否正在关闭
    if shutting_down:
        raise HTTPException(status_code=503, detail="Forwarder is shutting down, not accepting new tasks")

    # 检查是否正在处理任务
    if current_task is not None:
        raise HTTPException(status_code=503, detail="Forwarder is busy processing another task")

    # 验证必需字段
    required_fields = ["task_id", "task_type", "model_spec", "payload", "callback"]
    for field in required_fields:
        if field not in task_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    task_id = task_data["task_id"]

    # 发送日志：任务接收
    await _send_log(
        task_id,
        LogLevel.INFO,
        "task.received",
        f"Model Forwarder received task {task_id}",
        {"task_type": task_data["task_type"]}
    )

    # 保存回调配置（不传给协程）
    current_callback = task_data.pop("callback")

    # 设置当前任务
    current_task = {
        "task_id": task_id,
        "task_type": task_data["task_type"],
        "started_at": datetime.now(timezone.utc).isoformat()
    }

    # 将任务放入队列，传递给推理协程（不包含 callback）
    await task_queue.put(task_data)

    # 在后台处理结果回调
    background_tasks.add_task(process_result_callback)

    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Task accepted and queued for inference"
    }


async def process_result_callback():
    """处理推理结果并回调给 API Gateway（带重试机制）"""
    global current_task, current_callback, result_queue

    try:
        # 等待推理协程返回结果
        result_data = await result_queue.get()

        task_id = result_data.get("task_id", "unknown")

        if not current_callback:
            print(f"No callback config for task {task_id}")
            current_task = None
            current_callback = None
            return

        # 发送日志：推理完成
        await _send_log(
            task_id,
            LogLevel.INFO,
            "inference.completed",
            f"Inference completed for task {task_id}"
        )

        # 回调 API Gateway（带重试）
        callback_url = current_callback.get("url")
        callback_headers = current_callback.get("headers", {})

        success = await _execute_callback_with_retry(
            task_id,
            callback_url,
            callback_headers,
            result_data,
            max_retries=3
        )

        if not success:
            # 所有重试都失败，记录错误
            await _send_log(
                task_id,
                LogLevel.ERROR,
                "callback.all_retries_failed",
                f"All callback retries failed for task {task_id}"
            )

    except Exception as e:
        print(f"Error processing result callback: {e}")
        if current_task:
            await _send_log(
                current_task.get("task_id", "unknown"),
                LogLevel.ERROR,
                "callback.error",
                f"Error processing callback: {str(e)}"
            )

    finally:
        # 清除当前任务和回调配置
        current_task = None
        current_callback = None


async def _execute_callback_with_retry(
    task_id: str,
    callback_url: str,
    callback_headers: Dict[str, str],
    result_data: Dict[str, Any],
    max_retries: int = 3
) -> bool:
    """
    执行回调，带重试机制

    Args:
        task_id: 任务 ID
        callback_url: 回调 URL
        callback_headers: 回调请求头
        result_data: 结果数据
        max_retries: 最大重试次数（默认 3 次）

    Returns:
        bool: 回调成功返回 True，所有重试都失败返回 False
    """
    import asyncio

    retry_count = 0
    last_error = None

    while retry_count <= max_retries:
        try:
            # 发送回调请求
            response = await http_client.post(
                callback_url,
                json=result_data,
                headers=callback_headers,
                timeout=30.0
            )

            # 检查响应状态码
            if response.status_code == 200:
                # 成功
                await _send_log(
                    task_id,
                    LogLevel.INFO,
                    "callback.success",
                    f"✓ Successfully called back to API Gateway for task {task_id} (attempt {retry_count + 1}/{max_retries + 1})"
                )
                return True
            else:
                # HTTP 错误
                last_error = f"HTTP {response.status_code}: {response.text}"
                await _send_log(
                    task_id,
                    LogLevel.WARNING,
                    "callback.http_error",
                    f"⚠️  Callback failed for task {task_id}: {last_error} (attempt {retry_count + 1}/{max_retries + 1})"
                )

        except Exception as e:
            # 网络错误或其他异常
            last_error = str(e)
            await _send_log(
                task_id,
                LogLevel.WARNING,
                "callback.network_error",
                f"⚠️  Callback network error for task {task_id}: {last_error} (attempt {retry_count + 1}/{max_retries + 1})"
            )

        # 如果还有重试机会，等待后重试
        retry_count += 1
        if retry_count <= max_retries:
            # 指数退避：2s, 4s, 8s
            wait_time = min(2 ** retry_count, 30)
            print(f"⟳ Retrying callback for task {task_id} in {wait_time}s (attempt {retry_count + 1}/{max_retries + 1})")
            await asyncio.sleep(wait_time)

    # 所有重试都失败
    await _send_log(
        task_id,
        LogLevel.ERROR,
        "callback.failed",
        f"✗ All callback retries failed for task {task_id}: {last_error}"
    )
    return False


async def _send_log(task_id: str, level: LogLevel, event: str, message: str, context: Optional[Dict[str, Any]] = None):
    """发送日志到 RabbitMQ"""
    try:
        log_data = LogMessage(
            timestamp=datetime.now(timezone.utc),
            task_id=task_id,
            service_name="model-forwarder",
            service_instance=settings.forwarder_instance_id,
            level=level,
            event=event,
            message=message,
            context=context or {}
        )

        if rabbitmq_client:
            await rabbitmq_client.publish_log(log_data)
    except Exception as e:
        print(f"Failed to send log: {e}")
