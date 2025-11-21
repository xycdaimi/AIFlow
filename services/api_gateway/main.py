#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: API Gateway main application
"""

import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.config import settings
from core.exception_handlers import register_exception_handlers
from .routes import router
from .dependencies import redis_client, rabbitmq_client, minio_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""

    # Startup
    print(f"🚀 Starting API Gateway...")

    # 连接 Redis
    print("📦 Connecting to Redis...")
    await redis_client.connect()

    # 连接 RabbitMQ
    print("🐰 Connecting to RabbitMQ...")
    await rabbitmq_client.connect()

    # 连接 MinIO 并验证
    print("📁 Connecting to MinIO...")
    await minio_store.connect()  # 如果失败会抛出异常，导致服务启动失败

    print(f"✓ API Gateway started on {settings.api_gateway_host}:{settings.api_gateway_port}")
    print(f"✓ Task Monitor started (check interval: {settings.task_monitor_interval}s)")

    yield

    # Shutdown
    print("🛑 Shutting down API Gateway...")
    await redis_client.disconnect()
    await rabbitmq_client.disconnect()
    print("✓ API Gateway stopped")


# Create FastAPI application
app = FastAPI(
    title="AI Route API Gateway",
    description="Unified API Gateway for AI task scheduling platform",
    version="1.0.0",
    lifespan=lifespan
)

# Register global exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint with dependency status."""
    health_status = {
        "status": "healthy",
        "service": "api-gateway",
        "dependencies": {
            "redis": "unknown",
            "rabbitmq": "unknown",
            "minio": "unknown"
        }
    }

    # 检查 Redis
    try:
        await redis_client.client.ping()
        health_status["dependencies"]["redis"] = "healthy"
    except Exception:
        health_status["dependencies"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"

    # 检查 RabbitMQ
    try:
        if rabbitmq_client.connection and not rabbitmq_client.connection.is_closed:
            health_status["dependencies"]["rabbitmq"] = "healthy"
        else:
            health_status["dependencies"]["rabbitmq"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception:
        health_status["dependencies"]["rabbitmq"] = "unhealthy"
        health_status["status"] = "degraded"

    # 检查 MinIO
    try:
        if minio_store._connected:
            # 尝试列出 buckets 来验证连接
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: minio_store.client.list_buckets())
            health_status["dependencies"]["minio"] = "healthy"
        else:
            health_status["dependencies"]["minio"] = "not_connected"
            health_status["status"] = "degraded"
    except Exception:
        health_status["dependencies"]["minio"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Route API Gateway",
        "version": "1.0.0",
        "docs": "/docs"
    }


def main():
    """Run the API Gateway service."""
    uvicorn.run(
        "services.api_gateway.main:app",
        host=settings.api_gateway_host,
        port=settings.api_gateway_port,
        reload=False
    )


if __name__ == "__main__":
    main()

