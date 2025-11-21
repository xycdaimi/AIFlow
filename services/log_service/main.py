#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: Log Service - 从 RabbitMQ 消费日志并统一写入 PostgreSQL
"""

import uvicorn
import asyncio
import asyncpg
import json
import os
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import Optional, List
from aio_pika import IncomingMessage
from core.config import settings
from core.utils import RabbitMQClient
from core.protocols import LogMessage
from core.exception_handlers import register_exception_handlers
from core.errors import ErrorCode


# 全局数据库连接池
db_pool: Optional[asyncpg.Pool] = None

# RabbitMQ 客户端
rabbitmq_client = RabbitMQClient()

# 日志批处理
log_batch: List[LogMessage] = []
batch_lock = asyncio.Lock()

# 备份日志文件路径
BACKUP_LOG_DIR = Path("logs/backup")
BACKUP_LOG_DIR.mkdir(parents=True, exist_ok=True)


async def _process_log_message(message: IncomingMessage):
    """
    处理从 RabbitMQ 接收到的日志消息

    错误恢复策略：
    1. 解析错误：拒绝消息，不重新入队（数据格式错误）
    2. 数据库错误：拒绝消息，重新入队（可恢复错误）
    3. 其他错误：写入备份文件，确认消息（避免阻塞队列）

    Args:
        message: RabbitMQ 消息
    """
    try:
        # 解析日志消息
        log_data = json.loads(message.body.decode())
        log_message = LogMessage(**log_data)

        # 打印日志到终端
        _print_log_to_terminal(log_message)

        # 添加到批处理队列
        async with batch_lock:
            log_batch.append(log_message)

            # 如果批次已满，立即刷新
            if len(log_batch) >= settings.log_batch_size:
                flush_success = await _flush_batch()

                # 如果刷新失败，拒绝消息并重新入队
                if not flush_success:
                    print(f"⚠️  Batch flush failed, rejecting message for requeue")
                    await message.reject(requeue=True)
                    return

        # 成功处理，确认消息
        await message.ack()

    except (json.JSONDecodeError, ValueError) as e:
        # 数据格式错误，无法恢复，拒绝消息不重新入队
        print(f"❌ Invalid log message format: {e}")
        await message.reject(requeue=False)

    except Exception as e:
        # 其他未知错误，写入备份文件并确认消息（避免阻塞队列）
        print(f"❌ Error processing log message: {e}")
        try:
            await _write_to_backup_file(message.body.decode())
            print(f"✓ Log message written to backup file")
            await message.ack()
        except Exception as backup_error:
            print(f"❌ Failed to write backup file: {backup_error}")
            # 最后的手段：拒绝消息并重新入队
            await message.reject(requeue=True)


async def _batch_processor():
    """定期刷新日志批次"""
    while True:
        await asyncio.sleep(settings.log_batch_timeout)

        async with batch_lock:
            if log_batch:
                await _flush_batch()


async def _flush_batch() -> bool:
    """
    将日志批次写入数据库，带重试机制

    Returns:
        bool: 成功返回 True，失败返回 False
    """
    global log_batch

    if not log_batch:
        return True

    if not db_pool:
        print(f"❌ Database pool not available, cannot flush logs")
        # 写入备份文件
        await _write_batch_to_backup_file(log_batch)
        log_batch = []
        return False

    # 重试配置
    max_retries = 3
    retry_delay = 1  # 秒

    for attempt in range(1, max_retries + 1):
        try:
            # 准备批量插入数据
            records = [
                (
                    log.timestamp,
                    log.task_id,
                    log.service_name,
                    log.service_instance,
                    log.level.value,
                    log.event,
                    log.message,
                    json.dumps(log.context) if log.context else None
                )
                for log in log_batch
            ]

            # 批量插入
            async with db_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO logs (timestamp, task_id, service_name, service_instance, level, event, message, context)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                    """,
                    records
                )

            print(f"✓ Flushed {len(log_batch)} logs to database (attempt {attempt}/{max_retries})")
            log_batch = []
            return True

        except asyncpg.PostgresConnectionError as e:
            # 数据库连接错误，可以重试
            error_msg = f"Database connection error (attempt {attempt}/{max_retries}): {str(e)}"
            print(f"⚠️  {error_msg}")
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                # 所有重试都失败，写入备份文件
                print(f"❌ All retries failed, writing {len(log_batch)} logs to backup file")
                print(f"   Error code: {ErrorCode.POSTGRES_CONNECTION_FAILED}")
                await _write_batch_to_backup_file(log_batch)
                log_batch = []
                return False

        except Exception as e:
            # 其他错误（如数据格式错误），不重试
            error_msg = f"Error flushing logs to database: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"   Error code: {ErrorCode.LOG_WRITE_FAILED}")
            # 写入备份文件
            await _write_batch_to_backup_file(log_batch)
            log_batch = []
            return False

    return False


async def _write_to_backup_file(log_json: str):
    """
    将单条日志写入备份文件

    Args:
        log_json: 日志的 JSON 字符串
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    backup_file = BACKUP_LOG_DIR / f"logs_backup_{timestamp}.jsonl"

    # 异步写入文件
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: backup_file.open("a", encoding="utf-8").write(log_json + "\n")
    )


async def _write_batch_to_backup_file(logs: List[LogMessage]):
    """
    将日志批次写入备份文件

    Args:
        logs: 日志消息列表
    """
    if not logs:
        return

    timestamp = datetime.now().strftime("%Y%m%d")
    backup_file = BACKUP_LOG_DIR / f"logs_backup_{timestamp}.jsonl"

    # 准备写入内容
    lines = []
    for log in logs:
        log_dict = {
            "timestamp": log.timestamp.isoformat(),
            "task_id": log.task_id,
            "service_name": log.service_name,
            "service_instance": log.service_instance,
            "level": log.level.value,
            "event": log.event,
            "message": log.message,
            "context": log.context
        }
        lines.append(json.dumps(log_dict, ensure_ascii=False))

    content = "\n".join(lines) + "\n"

    # 异步写入文件
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: backup_file.open("a", encoding="utf-8").write(content)
    )

    print(f"✓ Wrote {len(logs)} logs to backup file: {backup_file}")


def _print_log_to_terminal(log: LogMessage):
    """打印日志到终端"""
    level_colors = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m"  # Magenta
    }
    reset = "\033[0m"

    color = level_colors.get(log.level.value, "")
    timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    print(f"{color}[{timestamp}] [{log.level.value}] [{log.service_name}/{log.service_instance}] "
          f"[{log.task_id}] {log.event}: {log.message}{reset}")


async def _init_database():
    """初始化数据库表结构"""
    print("Checking database schema...")

    async with db_pool.acquire() as conn:
        # 检查 logs 表是否存在
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'logs'
            )
        """)

        if not table_exists:
            print("Creating logs table...")

            # 创建表
            await conn.execute("""
                CREATE TABLE logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    task_id VARCHAR(255),
                    service_name VARCHAR(100) NOT NULL,
                    service_instance VARCHAR(100),
                    level VARCHAR(20) NOT NULL,
                    event VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    context JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✓ Created table: logs")

            # 创建索引
            indexes = [
                ("idx_logs_timestamp", "timestamp"),
                ("idx_logs_task_id", "task_id"),
                ("idx_logs_service_name", "service_name"),
                ("idx_logs_level", "level"),
                ("idx_logs_event", "event"),
                ("idx_logs_created_at", "created_at"),
                ("idx_logs_task_service", "task_id, service_name"),
                ("idx_logs_timestamp_level", "timestamp, level"),
            ]

            for idx_name, columns in indexes:
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} ON logs({columns})
                """)
                print(f"✓ Created index: {idx_name}")

            print("✓ Database schema initialized")
        else:
            print("✓ Database schema already exists")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db_pool

    # 启动时连接数据库
    db_pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
        min_size=5,
        max_size=20
    )
    print(f"Connected to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}")

    # 初始化数据库表结构
    await _init_database()

    # 连接到 RabbitMQ
    await rabbitmq_client.connect()

    # 设置 RabbitMQ 消费者
    await rabbitmq_client.consume_logs(callback=_process_log_message)
    print("Started consuming logs from RabbitMQ")

    # 启动批处理任务
    batch_task = asyncio.create_task(_batch_processor())

    print(f"Log Service started on {settings.log_service_host}:{settings.log_service_port}")

    yield

    # 关闭时清理
    batch_task.cancel()

    # 刷新剩余日志
    async with batch_lock:
        await _flush_batch()

    await rabbitmq_client.disconnect()

    if db_pool:
        await db_pool.close()

    print("Log Service stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI Route Log Service",
    description="Centralized log collection service from RabbitMQ",
    version="1.0.0",
    lifespan=lifespan
)

# 注册全局异常处理器
register_exception_handlers(app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Route Log Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "log-service"}


def main():
    """运行 Log Service"""
    uvicorn.run(
        "services.log_service.main:app",
        host=settings.log_service_host,
        port=settings.log_service_port,
        reload=False
    )


if __name__ == "__main__":
    main()

