#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: Task Scheduler - 智能任务调度器

职责：
1. 从 RabbitMQ 消费任务
2. 根据任务类型从 Consul 发现可用的 Model Forwarder 实例
3. 检查实例支持的任务类型和负载状态(是否正在调用模型推理)
4. 选择最优实例并分配任务
5. 如果没有空闲实例，让任务继续在队列中等待
"""

import asyncio
import json
import httpx
import signal
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from aio_pika import IncomingMessage
from core.config import settings
from core.utils import ConsulClient, RabbitMQClient, RedisClient
from core.protocols import LogMessage, LogLevel, TaskStatus


class TaskScheduler:
    """任务调度器，负责从 RabbitMQ 消费任务并分配给 Model Forwarder"""

    def __init__(self, instance_id: str = "scheduler-001"):
        """
        初始化任务调度器

        Args:
            instance_id: 调度器实例 ID
        """
        self.instance_id = instance_id

        # RabbitMQ 客户端
        self.rabbitmq_client = RabbitMQClient()

        # Consul 客户端（延迟创建，在 start() 中初始化）
        self.consul_client = None

        # Redis 客户端
        self.redis_client = RedisClient()

        # HTTP 客户端
        self.http_client: Optional[httpx.AsyncClient] = None

        # 运行状态
        self.running = False
        self.shutting_down = False  # 优雅关闭标志
        self.processing_task = False  # 是否正在处理任务

    async def _send_log(self, task_id: str, level: LogLevel, event: str, message: str, context: Optional[Dict[str, Any]] = None):
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
                service_name="task-scheduler",
                service_instance=self.instance_id,
                level=level,
                event=event,
                message=message,
                context=context or {}
            )

            await self.rabbitmq_client.publish_log(log_data)
        except Exception as e:
            # 日志发送失败不影响主流程，只打印错误
            print(f"Failed to send log: {e}")

    async def start(self):
        """启动任务调度器"""
        self.running = True
        print(f"Starting Task Scheduler {self.instance_id}...")

        # 创建 HTTP 客户端（本地地址不走代理，其他地址走系统代理）
        # 配置 mounts：本地地址使用不带代理的 transport
        mounts = {
            "http://127.0.0.1": httpx.AsyncHTTPTransport(proxy=None),
            "http://localhost": httpx.AsyncHTTPTransport(proxy=None),
            "http://192.168.": httpx.AsyncHTTPTransport(proxy=None),  # 内网 IP
            "http://10.": httpx.AsyncHTTPTransport(proxy=None),  # 内网 IP
        }
        self.http_client = httpx.AsyncClient(timeout=30.0, mounts=mounts)

        # 连接到 RabbitMQ
        await self.rabbitmq_client.connect()

        # 创建并连接到 Consul（必须在事件循环中创建）
        self.consul_client = ConsulClient()
        await self.consul_client.connect()

        # 连接到 Redis
        await self.redis_client.connect()

        # 设置 RabbitMQ 消费者
        await self._setup_consumer()

        print(f"Task Scheduler {self.instance_id} started and waiting for tasks...")

        # 发送启动日志
        await self._send_log("", LogLevel.INFO, "scheduler.started", f"Task Scheduler {self.instance_id} started")

        # 保持运行
        while self.running:
            await asyncio.sleep(1)

    async def stop(self):
        """优雅停止任务调度器"""
        print(f"\n🛑 Stopping Task Scheduler {self.instance_id}...")

        # 设置关闭标志，拒绝新任务
        self.shutting_down = True
        print("⏸️  Rejecting new tasks...")

        # 等待当前任务处理完成（最多等待 30 秒）
        if self.processing_task:
            print("⏳ Waiting for current task to complete...")
            wait_time = 0
            max_wait = 30
            while self.processing_task and wait_time < max_wait:
                await asyncio.sleep(0.5)
                wait_time += 0.5

            if self.processing_task:
                print(f"⚠️  Task still processing after {max_wait}s, forcing shutdown...")
            else:
                print("✓ Current task completed")

        # 停止运行循环
        self.running = False

        # 发送停止日志
        if self.http_client:
            await self._send_log("", LogLevel.INFO, "scheduler.stopped", f"Task Scheduler {self.instance_id} stopped")

        # 断开连接
        try:
            await self.rabbitmq_client.disconnect()
        except Exception as e:
            print(f"⚠️  Error disconnecting RabbitMQ: {e}")

        try:
            if self.http_client:
                await self.http_client.aclose()
        except Exception as e:
            print(f"⚠️  Error closing HTTP client: {e}")

        try:
            if self.consul_client:
                await self.consul_client.disconnect()
        except Exception as e:
            print(f"⚠️  Error disconnecting Consul: {e}")

        try:
            await self.redis_client.disconnect()
        except Exception as e:
            print(f"⚠️  Error disconnecting Redis: {e}")

        print(f"✓ Task Scheduler {self.instance_id} stopped gracefully")

    async def _setup_consumer(self):
        """设置 RabbitMQ 消费者"""
        # 使用 RabbitMQClient 消费任务
        # 队列已在 connect() 中声明并绑定
        await self.rabbitmq_client.consume_tasks(
            callback=self._process_task_message
        )
        print(f"Subscribed to task queue 'task_queue'")

    async def _process_task_message(self, message: IncomingMessage):
        """
        处理从 RabbitMQ 接收到的任务消息

        Args:
            message: RabbitMQ 消息
        """
        # 检查是否正在关闭
        if self.shutting_down:
            # 正在关闭，拒绝新任务并重新入队
            print("⚠️  Scheduler is shutting down, rejecting new task")
            await message.reject(requeue=True)
            return

        task_id = "unknown"
        try:
            # 标记正在处理任务
            self.processing_task = True

            # 解析任务消息
            task_data = json.loads(message.body.decode())
            task_id = task_data.get('task_id', 'unknown')
            task_type = task_data.get('task_type', 'unknown')

            print(f"Received task: {task_id} - {task_type}")

            # 发送接收任务日志
            await self._send_log(
                task_id,
                LogLevel.INFO,
                "task.received",
                f"Received task {task_id} of type {task_type}",
                {"task_type": task_type}
            )

            # 调度任务
            success = await self._schedule_task(task_data)
            if success:
                await message.ack()  # 成功分配，确认消息

                # 更新 Redis 中的任务状态为 PROCESSING
                try:
                    task = await self.redis_client.get_task(task_id)
                    if task:
                        task.status = TaskStatus.PROCESSING
                        task.updated_at = datetime.now(timezone.utc)
                        await self.redis_client.set_task(task_id, task, ttl=settings.task_ttl)
                        print(f"✓ Updated task {task_id} status to PROCESSING in Redis")
                    else:
                        print(f"⚠️  Task {task_id} not found in Redis, skipping status update")
                except Exception as e:
                    print(f"⚠️  Failed to update task {task_id} status in Redis: {e}")

            else:
                # 调度失败（可能原因：没有可用实例、Forwarder 返回 503 忙碌、网络错误等）
                # 延迟后拒绝消息并重新入队，延迟可以避免立即重试
                retry_delay = settings.scheduler_retry_delay  # 从配置读取延迟时间
                print(f"⏳ Task {task_id} scheduling failed, waiting {retry_delay}s before requeue...")
                await asyncio.sleep(retry_delay)
                await message.reject(requeue=True)
                print(f"🔄 Task {task_id} requeued, will retry scheduling...")

        except Exception as e:
            print(f"❌ Error processing task message: {e}")
            import traceback
            traceback.print_exc()
            # 发送错误日志
            await self._send_log(
                task_id,
                LogLevel.ERROR,
                "task.process_failed",
                f"Error processing task {task_id}: {str(e)}"
            )
            # 发生异常时也 reject 并重新入队
            await message.reject(requeue=True)
        finally:
            # 标记任务处理完成
            self.processing_task = False

    async def _discover_forwarders(self) -> List[Dict[str, Any]]:
        """
        从 Consul 发现所有健康的 Model Forwarder 实例

        Returns:
            Model Forwarder 实例列表
        """
        try:
            services = await self.consul_client.discover_service("model-forwarder")
            print(f"🔍 Consul returned {len(services)} service(s) for 'model-forwarder'")

            # 获取本机对外 IP（连接到 Consul 服务器时使用的 IP）
            local_ip = None
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect((settings.consul_host, settings.consul_port))
                local_ip = s.getsockname()[0]
                s.close()
                print(f"   Local IP: {local_ip}")
            except Exception as e:
                print(f"   ⚠️  Could not determine local IP: {e}")

            forwarders = []
            for service in services:
                service_info = service.get("Service", {})
                service_id = service_info.get("ID")
                address = service_info.get("Address")
                port = service_info.get("Port")

                # 如果 Model Forwarder 的 IP 和本机对外 IP 一致，改用 127.0.0.1
                if local_ip and address == local_ip:
                    actual_address = "127.0.0.1"
                    print(f"   - Service ID: {service_id}, Address: {address}:{port} → Using 127.0.0.1 (same machine)")
                else:
                    actual_address = address
                    print(f"   - Service ID: {service_id}, Address: {address}:{port}")

                forwarders.append({
                    "service_id": service_id,
                    "address": actual_address,
                    "port": port,
                    "url": f"http://{actual_address}:{port}"
                })

            return forwarders
        except Exception as e:
            print(f"❌ Error discovering forwarders from Consul: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _get_forwarder_status(self, forwarder_url: str) -> Tuple[bool, Optional[Dict]]:
        """
        获取 Model Forwarder 的状态

        Args:
            forwarder_url: Forwarder 的 URL

        Returns:
            (是否空闲, 当前任务信息)
        """
        try:
            response = await self.http_client.get(
                f"{forwarder_url}/status",
                timeout=5.0
            )

            if response.status_code == 200:
                status_data = response.json()
                is_idle = not status_data.get("busy", True)
                current_task = status_data.get("current_task")
                pending_tasks_count = status_data.get("pending_tasks_count", 0)
                return is_idle, current_task, pending_tasks_count
            else:
                return False, None, 0
        except Exception as e:
            print(f"Error getting forwarder status from {forwarder_url}: {e}")
            return False, None, 0

    async def _get_supported_tasks(self, forwarder_url: str) -> List[str]:
        """
        获取 Model Forwarder 支持的任务类型

        Args:
            forwarder_url: Forwarder 的 URL

        Returns:
            支持的任务类型列表
        """
        try:
            response = await self.http_client.get(
                f"{forwarder_url}/api/v1/supported-tasks",
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                task_types = data.get("task_types", [])
                print(f"   ✓ Forwarder supports: {task_types}")
                return task_types
            else:
                print(f"   ❌ Failed to get supported tasks: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"   ❌ Error getting supported tasks from {forwarder_url}: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _select_forwarder(self, task_type: str) -> Optional[str]:
        """
        选择合适的 Model Forwarder 实例

        选择策略：
        1. 从 Consul 发现所有健康的 Model Forwarder 实例
        2. 查询每个实例支持的任务类型
        3. 过滤出支持当前任务类型的实例
        4. 优先选择空闲的实例
        5. 如果没有空闲实例，选择 pending_tasks_count <= 2 的实例
        6. 如果都不满足，返回 None（任务继续在 RabbitMQ 等待）

        Args:
            task_type: 任务类型

        Returns:
            选中的 Forwarder URL，如果没有可用实例则返回 None
        """
        # 1. 从 Consul 发现所有 Model Forwarder 实例
        forwarders = await self._discover_forwarders()

        if not forwarders:
            print("No Model Forwarder instances found in Consul")
            return None

        print(f"Found {len(forwarders)} Model Forwarder instance(s)")

        # 用于存储候选实例
        idle_candidates = []  # 空闲实例
        low_load_candidates = []  # 低负载实例 (pending_tasks_count <= 2)

        # 2. 遍历每个实例，查询支持的任务类型和状态
        for forwarder in forwarders:
            forwarder_url = forwarder["url"]
            service_id = forwarder["service_id"]

            # 查询支持的任务类型
            supported_tasks = await self._get_supported_tasks(forwarder_url)

            # 检查是否支持当前任务类型
            if task_type not in supported_tasks:
                print(f"Forwarder {service_id} does not support task type '{task_type}'")
                continue

            # 检查状态和负载
            is_idle, current_task, pending_tasks_count = await self._get_forwarder_status(forwarder_url)

            if is_idle:
                # 空闲实例
                idle_candidates.append({
                    "url": forwarder_url,
                    "service_id": service_id,
                    "pending_tasks_count": pending_tasks_count
                })
                print(f"Forwarder {service_id} is idle (pending: {pending_tasks_count})")
            elif current_task:
                # 忙碌实例，检查 pending 队列
                print(f"Forwarder {service_id} is busy (current task: {current_task}, pending: {pending_tasks_count})")
                if pending_tasks_count <= settings.scheduler_task_max_count:
                    low_load_candidates.append({
                        "url": forwarder_url,
                        "service_id": service_id,
                        "pending_tasks_count": pending_tasks_count
                    })
            else:
                continue

        # 3. 选择策略：优先选择空闲实例
        if idle_candidates:
            # 选择 pending_tasks_count 最少的空闲实例
            selected = min(idle_candidates, key=lambda x: x["pending_tasks_count"])
            print(f"✓ Selected idle forwarder {selected['service_id']} at {selected['url']} (pending: {selected['pending_tasks_count']})")
            return selected["url"]

        # 4. 如果没有空闲实例，选择低负载实例
        if low_load_candidates:
            # 选择 pending_tasks_count 最少的低负载实例
            selected = min(low_load_candidates, key=lambda x: x["pending_tasks_count"])
            print(f"⚠ No idle forwarder, selected low-load forwarder {selected['service_id']} at {selected['url']} (pending: {selected['pending_tasks_count']})")
            return selected["url"]

        # 5. 没有找到可用实例，任务继续在 RabbitMQ 等待
        print(f"❌ No available forwarder found for task type '{task_type}' (all instances are overloaded)")
        return None

    async def _schedule_task(self, task_data: Dict):
        """
        调度任务到合适的 Model Forwarder 实例

        Args:
            task_data: 任务数据
        """
        task_id = task_data.get("task_id", "unknown")
        task_type = task_data.get("task_type", "unknown")

        print(f"Scheduling task {task_id} of type {task_type}")

        # 发送调度日志
        await self._send_log(
            task_id,
            LogLevel.INFO,
            "task.scheduling",
            f"Scheduling task {task_id} of type {task_type}",
            {"task_type": task_type}
        )

        try:
            # 选择合适的 Model Forwarder 实例
            forwarder_url = await self._select_forwarder(task_type)

            if not forwarder_url:
                # 没有可用的 Forwarder，拒绝消息让其重新入队
                print(f"No available forwarder for task {task_id}, rejecting message for requeue")
                await self._send_log(
                    task_id,
                    LogLevel.WARNING,
                    "task.no_forwarder",
                    f"No available forwarder for task {task_id}, will retry later",
                    {"task_type": task_type}
                )
                # 注意：这里需要在 _process_task_message 中处理拒绝逻辑
                # 暂时记录错误
                return False

            # 转发任务到 Model Forwarder
            response = await self.http_client.post(
                f"{forwarder_url}/api/v1/tasks",
                json=task_data,
                timeout=30.0
            )

            if response.status_code == 200 or response.status_code == 201:
                # 成功转发
                print(f"✓ Task {task_id} forwarded to Model Forwarder successfully")
                await self._send_log(
                    task_id,
                    LogLevel.INFO,
                    "task.forwarded",
                    f"Task {task_id} forwarded to Model Forwarder",
                    {"forwarder_url": forwarder_url}
                )
                return True

            elif response.status_code == 503:
                # Model Forwarder 忙碌（Service Unavailable）
                # 这是临时状态，任务应该重新入队等待
                print(f"⚠️  Model Forwarder is busy (503) for task {task_id}, will requeue")
                await self._send_log(
                    task_id,
                    LogLevel.WARNING,
                    "task.forwarder_busy",
                    f"Model Forwarder is busy for task {task_id}, will retry later",
                    {"forwarder_url": forwarder_url, "status_code": 503}
                )
                return False

            else:
                # 其他错误（4xx, 5xx）
                print(f"✗ Failed to forward task {task_id}: {response.status_code} - {response.text}")
                await self._send_log(
                    task_id,
                    LogLevel.ERROR,
                    "task.forward_failed",
                    f"Failed to forward task {task_id}: {response.status_code}",
                    {"status_code": response.status_code, "response": response.text, "forwarder_url": forwarder_url}
                )
                return False

        except Exception as e:
            print(f"Error scheduling task {task_id}: {e}")
            await self._send_log(
                task_id,
                LogLevel.ERROR,
                "task.schedule_failed",
                f"Error scheduling task {task_id}: {str(e)}"
            )
            return False


async def main():
    """主函数"""
    scheduler = TaskScheduler(instance_id=settings.scheduler_instance_id)

    # 设置信号处理器（用于优雅关闭）
    import platform
    if platform.system() != 'Windows':
        # Unix/Linux 系统使用 signal handler
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def signal_handler(sig):
            """处理 SIGTERM 和 SIGINT 信号"""
            print(f"\n📡 Received signal {sig.name}, initiating graceful shutdown...")
            shutdown_event.set()

        # 注册信号处理器
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

        try:
            # 启动调度器（非阻塞）
            start_task = asyncio.create_task(scheduler.start())

            # 等待关闭信号
            await shutdown_event.wait()

            # 收到关闭信号，停止调度器
            await scheduler.stop()

            # 取消启动任务
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

        except KeyboardInterrupt:
            print("\n⌨️  Received keyboard interrupt, shutting down...")
            await scheduler.stop()
        except Exception as e:
            print(f"❌ Error in main: {e}")
            await scheduler.stop()
    else:
        # Windows 系统直接运行，使用 Ctrl+C 停止
        try:
            await scheduler.start()
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n⌨️  Received keyboard interrupt, shutting down...")
        except Exception as e:
            print(f"❌ Error in main: {e}")
        finally:
            # 确保总是执行清理
            await scheduler.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Task Scheduler stopped")