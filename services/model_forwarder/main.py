"""Model Forwarder - 模型推理转发服务"""

import uvicorn
import asyncio
import httpx
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.config import settings
from core.utils import ConsulClient, RabbitMQClient
from .routes import router, set_queues, set_rabbitmq_client, set_http_client, set_shutting_down
from .work import inference_worker

# 全局变量
task_queue = asyncio.Queue()  # 任务队列（主进程 -> 推理协程）
result_queue = asyncio.Queue()  # 结果队列（推理协程 -> 主进程）
consul_client = None
rabbitmq_client = RabbitMQClient()
http_client: httpx.AsyncClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global http_client, consul_client

    # 启动时
    print(f"Starting Model Forwarder on {settings.forwarder_service_host}:{settings.forwarder_service_port}")

    # 创建 HTTP 客户端
    mounts = {
        "http://127.0.0.1": httpx.AsyncHTTPTransport(proxy=None),
        "http://localhost": httpx.AsyncHTTPTransport(proxy=None),
        "http://192.168.": httpx.AsyncHTTPTransport(proxy=None),  # 内网 IP
        "http://10.": httpx.AsyncHTTPTransport(proxy=None),  # 内网 IP
    }
    http_client = httpx.AsyncClient(timeout=30.0, mounts=mounts)

    # 连接到 RabbitMQ
    await rabbitmq_client.connect()

    # 创建并连接到 Consul（必须在事件循环中创建）
    consul_client = ConsulClient()
    await consul_client.connect()

    # 注册到 Consul
    # 如果 FORWARDER_SERVICE_HOST 是 0.0.0.0，需要获取本机实际 IP
    if settings.forwarder_service_host == "0.0.0.0":
        import socket
        # 获取本机 IP（连接到 Consul 服务器来确定使用哪个网卡）
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((settings.consul_host, settings.consul_port))
            consul_address = s.getsockname()[0]
            s.close()
        except Exception:
            # 如果无法获取，回退到 127.0.0.1
            consul_address = "127.0.0.1"
            print("⚠️  Warning: Could not determine local IP, using 127.0.0.1")
    else:
        consul_address = settings.forwarder_service_host

    print(f"Registering to Consul: {settings.forwarder_instance_id} at {consul_address}:{settings.forwarder_service_port}")
    await consul_client.register_service(
        service_id=settings.forwarder_instance_id,
        service_name="model-forwarder",
        address=consul_address,
        port=settings.forwarder_service_port,
        tags=["model", "inference"],
        check_http=f"http://{consul_address}:{settings.forwarder_service_port}/health",
        check_interval="10s"
    )
    print(f"✓ Registered to Consul as {settings.forwarder_instance_id}")

    # 设置共享队列和客户端
    set_queues(task_queue, result_queue)
    set_rabbitmq_client(rabbitmq_client)
    set_http_client(http_client)

    # 启动推理协程
    inference_task = asyncio.create_task(inference_worker(task_queue, result_queue, rabbitmq_client))

    print("Model Forwarder started successfully")

    yield

    # 优雅关闭
    print("\n🛑 Shutting down Model Forwarder...")

    # 设置关闭标志，拒绝新任务
    set_shutting_down(True)
    print("⏸️  Rejecting new tasks...")

    # 等待当前任务完成（最多等待 10 秒）
    from .routes import current_task
    if current_task is not None:
        print("⏳ Waiting for current task to complete...")
        wait_time = 0
        max_wait = 10
        while current_task is not None and wait_time < max_wait:
            await asyncio.sleep(0.5)
            wait_time += 0.5

        if current_task is not None:
            print(f"⚠️  Task still processing after {max_wait}s, forcing shutdown...")
        else:
            print("✓ Current task completed")

    # 取消推理协程
    print("🛑 Stopping inference worker...")
    inference_task.cancel()
    try:
        await inference_task
    except asyncio.CancelledError:
        pass

    # 注销 Consul 服务
    print("📡 Deregistering from Consul...")
    await consul_client.deregister_service(settings.forwarder_instance_id)

    # 断开连接
    await rabbitmq_client.disconnect()
    await consul_client.disconnect()

    if http_client:
        await http_client.aclose()

    print("✓ Model Forwarder stopped gracefully")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI Route Model Forwarder",
    description="Model inference forwarding service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Route Model Forwarder",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "model-forwarder"}


# 注册路由
app.include_router(router)


def main():
    """启动服务"""
    uvicorn.run(
        "services.model_forwarder.main:app",
        host=settings.forwarder_service_host,
        port=settings.forwarder_service_port,
        reload=False
    )


if __name__ == "__main__":
    main()
