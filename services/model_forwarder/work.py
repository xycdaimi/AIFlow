#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: Model Forwarder Worker - 推理协程
"""

import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from core.protocols import LogMessage, LogLevel
from core.utils import RabbitMQClient
from core.config import settings
from .infer import infer


async def inference_worker(
    task_queue: asyncio.Queue,
    result_queue: asyncio.Queue,
    rabbitmq_client: RabbitMQClient
):
    """
    推理协程 - 从任务队列获取任务，调用模型 API 推理，将结果放入结果队列

    Args:
        task_queue: 任务队列（主进程 -> 推理协程）
        result_queue: 结果队列（推理协程 -> 主进程）
        rabbitmq_client: RabbitMQ 客户端用于发送日志
    """
    print("Inference worker started")

    while True:
        try:
            # 从任务队列获取任务
            task_data = await task_queue.get()

            task_id = task_data.get("task_id", "unknown")
            task_type = task_data.get("task_type", "unknown")
            model_spec = task_data.get("model_spec", {})
            payload = task_data.get("payload", {})
            inference_params = task_data.get("inference_params", {})

            print(f"Inference worker processing task {task_id} of type {task_type}")

            # 发送日志：开始推理
            await _send_log(
                rabbitmq_client,
                task_id,
                LogLevel.INFO,
                "inference.started",
                f"Started inference for task {task_id}",
                {"task_type": task_type, "model": model_spec.get("name")}
            )

            try:
                # TODO: 调用实际的模型 API
                result = infer(task_id, task_type, model_spec, payload, inference_params)

                print(f"Inference completed for task {task_id}")

                # 将结果放入结果队列
                await result_queue.put(result)

            except Exception as e:
                print(f"Inference failed for task {task_id}: {e}")

                # 发送日志：推理失败
                await _send_log(
                    rabbitmq_client,
                    task_id,
                    LogLevel.ERROR,
                    "inference.failed",
                    f"Inference failed for task {task_id}: {str(e)}"
                )

                # 将错误结果放入结果队列
                error_result = {
                    "task_id": task_id,
                    "status": "FAILED",
                    "error": str(e)
                }
                await result_queue.put(error_result)

            finally:
                task_queue.task_done()

        except Exception as e:
            print(f"Error in inference worker: {e}")
            await asyncio.sleep(1)


async def _send_log(
    rabbitmq_client: RabbitMQClient,
    task_id: str,
    level: LogLevel,
    event: str,
    message: str,
    context: Dict[str, Any] = None
):
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

        await rabbitmq_client.publish_log(log_data)
    except Exception as e:
        print(f"Failed to send log: {e}")
