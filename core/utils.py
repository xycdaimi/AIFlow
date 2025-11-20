#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: Utility modules for AIFlow platform
"""

import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import redis.asyncio as aioredis
from aio_pika import connect_robust, Message, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange
import consul.aio
from core.config import settings
from core.protocols import TaskDetail, TaskStatus, LogMessage

class RedisClient:
    """Redis client wrapper."""
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        self.client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        # Close Redis connection
        if self.client:
            await self.client.close()


    async def set_task(self, task_id: str, task_data: TaskDetail, ttl: Optional[int] = None):
        """
        将任务数据存入 Redis，用于后续任务失败需要重试

        Args:
            task_id: 任务 ID
            task_data: 任务详情数据
            ttl: 过期时间（秒），None 表示不过期
        """
        key = f"task:{task_id}"
        value = task_data.model_dump_json()

        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)

    async def get_task(self, task_id: str) -> Optional[TaskDetail]:
        """
        从 Redis 中获取任务数据

        Args:
            task_id: 任务 ID

        Returns:
            TaskDetail 对象，如果不存在则返回 None
        """
        key = f"task:{task_id}"
        value = await self.client.get(key)

        if not value:
            return None

        task_dict = json.loads(value)
        return TaskDetail(**task_dict)

    async def delete_task(self, task_id: str) -> bool:
        """
        从 Redis 中删除任务数据

        Args:
            task_id: 任务 ID

        Returns:
            bool: 删除成功返回 True，任务不存在返回 False
        """
        key = f"task:{task_id}"
        result = await self.client.delete(key)
        return result > 0

class RabbitMQClient:
    """RabbitMQ client wrapper."""

    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.task_exchange: Optional[AbstractExchange] = None
        self.log_exchange: Optional[AbstractExchange] = None
    
    async def connect(self):
        """Connect to RabbitMQ."""
        self.connection = await connect_robust(settings.rabbitmq_url)
        self.channel = await self.connection.channel()

        # Declare task exchange
        self.task_exchange = await self.channel.declare_exchange(
            "task_exchange",
            ExchangeType.TOPIC,
            durable=True
        )

        # Declare task queue and bind to exchange
        task_queue = await self.channel.declare_queue(
            "task_queue",
            durable=True
        )
        await task_queue.bind(self.task_exchange, routing_key="#")

        # Declare log exchange (DIRECT type)
        self.log_exchange = await self.channel.declare_exchange(
            "log_exchange",
            ExchangeType.DIRECT,
            durable=True
        )

        # Declare log queue and bind to exchange
        log_queue = await self.channel.declare_queue(
            "log_queue",
            durable=True
        )
        await log_queue.bind(self.log_exchange, routing_key="log")
    
    async def disconnect(self):
        """Disconnect from RabbitMQ."""
        if self.connection:
            await self.connection.close()
    
    async def publish_task(self, task_id: str, task_type: str, task_detail: Dict[str, Any] = None):
        message_payload = {
            "task_id": task_id,
            "task_type": task_type
        }

        # Include complete task data in message
        if task_detail:
            message_payload.update(task_detail)

        message_body = json.dumps(message_payload)
        message = Message(
            body=message_body.encode(),
            content_type="application/json",
            delivery_mode=2  # Persistent
        )

        await self.task_exchange.publish(
            message,
            routing_key=task_type
        )

    async def consume_tasks(self, callback):
        """
        消费任务队列

        Args:
            callback: 消息处理回调函数
        """
        # 设置 prefetch count，一次只处理一个任务
        await self.channel.set_qos(prefetch_count=1)

        # 获取已声明的任务队列
        queue = await self.channel.declare_queue(
            "task_queue",
            durable=True
        )

        # 开始消费
        await queue.consume(callback)

    async def consume_logs(self, callback):
        """
        消费日志队列

        Args:
            callback: 消息处理回调函数
        """
        # 设置 prefetch count
        await self.channel.set_qos(prefetch_count=10)

        # 获取已声明的日志队列
        queue = await self.channel.declare_queue(
            "log_queue",
            durable=True
        )

        # 开始消费
        await queue.consume(callback)

    async def publish_log(self, log_message: LogMessage):
        """
        Publish log message to RabbitMQ.

        Args:
            log_message: Log message to publish
        """
        message_body = log_message.model_dump_json()
        message = Message(
            body=message_body.encode(),
            content_type="application/json",
            delivery_mode=2  # Persistent
        )

        await self.log_exchange.publish(
            message,
            routing_key="log"
        )

    async def remove_task_from_queue(self, task_id: str, queue_name: str = "task_queue") -> bool:
        """
        从队列中删除指定的任务

        实现原理：
        1. 临时消费队列中的所有消息（不确认）
        2. 过滤掉要删除的任务
        3. 将其他消息重新发布回队列
        4. 确认所有原始消息

        注意：此操作会暂时清空队列，可能影响其他消费者

        Args:
            task_id: 要删除的任务 ID
            queue_name: 队列名称，默认为 "task_queue"

        Returns:
            bool: 是否成功删除任务（True 表示找到并删除，False 表示未找到）
        """
        try:
            # 获取队列
            queue = await self.channel.declare_queue(queue_name, durable=True)

            # 获取队列中的消息数量
            queue_info = await queue.declare()
            message_count = queue_info.message_count

            if message_count == 0:
                print(f"Queue '{queue_name}' is empty, task {task_id} not found")
                return False

            print(f"Scanning {message_count} messages in queue '{queue_name}' to find task {task_id}...")

            # 临时存储要保留的消息
            messages_to_keep = []
            found_task = False

            # 创建临时消费者，获取所有消息
            async def temp_consumer(message):
                nonlocal found_task
                try:
                    # 解析消息
                    message_data = json.loads(message.body.decode())
                    msg_task_id = message_data.get('task_id', '')

                    if msg_task_id == task_id:
                        # 找到要删除的任务
                        found_task = True
                        print(f"✓ Found task {task_id}, marking for deletion")
                        # 确认消息（删除）
                        await message.ack()
                    else:
                        # 保留其他消息
                        messages_to_keep.append({
                            'body': message.body,
                            'headers': message.headers,
                            'routing_key': message_data.get('task_type', 'unknown')
                        })
                        # 确认消息（从队列中移除）
                        await message.ack()
                except Exception as e:
                    print(f"Error processing message: {e}")
                    # 出错时拒绝消息，重新入队
                    await message.reject(requeue=True)

            # 设置 prefetch，一次获取所有消息
            await self.channel.set_qos(prefetch_count=message_count)

            # 开始消费
            consumer_tag = await queue.consume(temp_consumer, no_ack=False)

            # 等待所有消息被处理（最多等待 5 秒）
            import asyncio
            for _ in range(50):  # 50 * 0.1s = 5s
                current_count = (await queue.declare()).message_count
                if current_count == 0:
                    break
                await asyncio.sleep(0.1)

            # 取消消费者
            await queue.cancel(consumer_tag)

            # 将保留的消息重新发布回队列
            if messages_to_keep:
                print(f"Re-publishing {len(messages_to_keep)} messages back to queue...")
                for msg_data in messages_to_keep:
                    message = Message(
                        body=msg_data['body'],
                        headers=msg_data['headers'],
                        content_type="application/json",
                        delivery_mode=2  # Persistent
                    )
                    await self.task_exchange.publish(
                        message,
                        routing_key=msg_data['routing_key']
                    )

            # 恢复原始 prefetch 设置
            await self.channel.set_qos(prefetch_count=1)

            if found_task:
                print(f"✓ Task {task_id} successfully removed from queue '{queue_name}'")
            else:
                print(f"✗ Task {task_id} not found in queue '{queue_name}'")

            return found_task

        except Exception as e:
            print(f"Error removing task {task_id} from queue: {e}")
            # 恢复 prefetch 设置
            try:
                await self.channel.set_qos(prefetch_count=1)
            except:
                pass
            return False

class ConsulClient:
    """Consul client wrapper for service discovery."""
    def __init__(self):
        self.client = consul.aio.Consul(
            host=settings.consul_host,
            port=settings.consul_port
        )

    async def connect(self):
        """Connect to Consul and verify the connection."""
        try:
            # 验证连接：获取 Consul 的 leader 信息
            leader = await self.client.status.leader()
            if leader:
                print(f"Connected to Consul successfully. Leader: {leader}")
            else:
                print("Warning: Connected to Consul but no leader found")
        except Exception as e:
            print(f"Failed to connect to Consul: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Consul and cleanup resources."""
        await self.close()

    async def close(self):
        """Close the Consul client and cleanup resources."""
        if self.client and hasattr(self.client, 'http') and hasattr(self.client.http, '_session'):
            # Close the aiohttp session
            await self.client.http._session.close()
    
    async def register_service(
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: Optional[list] = None,
        check_http: Optional[str] = None,
        check_interval: str = "10s"
    ):
        """Register a service with Consul."""
        check = None
        if check_http:
            check = consul.Check.http(check_http, check_interval)

        await self.client.agent.service.register(
            name=service_name,
            service_id=service_id,
            address=address,
            port=port,
            tags=tags or [],
            check=check
        )

    async def deregister_service(self, service_id: str):
        """Deregister a service from Consul."""
        await self.client.agent.service.deregister(service_id)

    async def discover_service(self, service_name: str) -> list:
        """
        Discover healthy service instances.

        Args:
            service_name: Name of the service to discover

        Returns:
            List of service instances
        """
        _, services = await self.client.health.service(service_name, passing=True)
        return services