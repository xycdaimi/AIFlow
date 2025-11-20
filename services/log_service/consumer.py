#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: Log consumer implementation
"""

import asyncio
import json
from typing import Optional, List
from datetime import datetime
from aio_pika import connect_robust, IncomingMessage, ExchangeType
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue
import asyncpg
from core.config import settings
from core.protocols import LogMessage


class LogConsumer:
    """Consumer that processes log messages and stores them in PostgreSQL."""
    
    def __init__(self, service_name: str, service_instance: str):
        """
        Initialize Log Consumer.
        
        Args:
            service_name: Name of the service
            service_instance: Instance identifier
        """
        self.service_name = service_name
        self.service_instance = service_instance
        
        # Database connection pool
        self.db_pool: Optional[asyncpg.Pool] = None
        
        # RabbitMQ connection
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None
        
        # Batch processing
        self.log_batch: List[LogMessage] = []
        self.batch_lock = asyncio.Lock()
        
        self.running = False
    
    async def start(self):
        """Start the log consumer."""
        self.running = True
        
        # Connect to PostgreSQL
        await self._connect_db()
        
        # Setup RabbitMQ consumer
        await self._setup_consumer()
        
        # Start batch processor
        asyncio.create_task(self._batch_processor())
        
        print(f"Log Consumer {self.service_instance} started and waiting for logs...")
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the log consumer."""
        self.running = False
        
        # Flush remaining logs
        await self._flush_batch()
        
        if self.connection:
            await self.connection.close()
        
        if self.db_pool:
            await self.db_pool.close()
    
    async def _connect_db(self):
        """Connect to PostgreSQL database."""
        self.db_pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            min_size=2,
            max_size=10
        )
        print("Connected to PostgreSQL")
    
    async def _setup_consumer(self):
        """Setup RabbitMQ consumer for log queue."""
        self.connection = await connect_robust(settings.rabbitmq_url)
        self.channel = await self.connection.channel()
        
        # Set prefetch count
        await self.channel.set_qos(prefetch_count=100)
        
        # Get log exchange (DIRECT type)
        log_exchange = await self.channel.declare_exchange(
            "log_exchange",
            ExchangeType.DIRECT,
            durable=True
        )
        
        # Declare queue and bind to log exchange
        self.queue = await self.channel.declare_queue(
            "log_queue",
            durable=True
        )
        
        await self.queue.bind(log_exchange, routing_key="log")
        
        # Start consuming
        await self.queue.consume(self._process_message)
        print("Subscribed to log queue")
    
    async def _process_message(self, message: IncomingMessage):
        """
        Process incoming log message.

        Args:
            message: Incoming RabbitMQ message
        """
        async with message.process():
            try:
                # Parse log message
                log_data = json.loads(message.body.decode())
                log_message = LogMessage(**log_data)

                # Print log to terminal for debugging
                self._print_log_to_terminal(log_message)

                # Add to batch
                async with self.batch_lock:
                    self.log_batch.append(log_message)

                    # Flush if batch is full
                    if len(self.log_batch) >= settings.log_batch_size:
                        await self._flush_batch()

            except Exception as e:
                print(f"Error processing log message: {e}")
    
    async def _batch_processor(self):
        """Periodically flush log batch based on timeout."""
        while self.running:
            await asyncio.sleep(settings.log_batch_timeout)
            
            async with self.batch_lock:
                if self.log_batch:
                    await self._flush_batch()
    
    def _print_log_to_terminal(self, log: LogMessage):
        """
        Print log message to terminal with formatting.

        Args:
            log: Log message to print
        """
        # Color codes for different log levels
        colors = {
            "DEBUG": "\033[36m",    # Cyan
            "INFO": "\033[32m",     # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
            "CRITICAL": "\033[35m"  # Magenta
        }
        reset = "\033[0m"

        # Get color for log level
        color = colors.get(log.level.value.upper(), "")

        # Format timestamp
        timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Build log line
        log_line = f"{color}[{timestamp}] [{log.level.value.upper()}] [{log.service_name}/{log.service_instance}]{reset}"

        if log.task_id:
            log_line += f" [Task: {log.task_id}]"

        if log.event:
            log_line += f" [{log.event}]"

        log_line += f" {log.message}"

        # Print context if available
        if log.context:
            context_str = json.dumps(log.context, ensure_ascii=False, indent=2)
            log_line += f"\n  Context: {context_str}"

        print(log_line)

    async def _flush_batch(self):
        """Flush current batch of logs to database."""
        if not self.log_batch:
            return

        try:
            # Prepare batch insert
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
                for log in self.log_batch
            ]

            # Insert into database
            async with self.db_pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO ai_task_logs
                    (timestamp, task_id, service_name, service_instance, level, event, message, context)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    records
                )

            print(f"\033[90m💾 Flushed {len(self.log_batch)} logs to database\033[0m")
            self.log_batch.clear()

        except Exception as e:
            print(f"\033[31m❌ Error flushing logs to database: {e}\033[0m")

