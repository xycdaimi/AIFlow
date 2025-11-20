<div align="center">

# 🚀 AIFlow

**智能 AI 任务调度与路由平台**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README_EN.md) | 简体中文

</div>

---

## 📖 目录

- [简介](#-简介)
- [核心特性](#-核心特性)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [API 使用指南](#-api-使用指南)
- [添加自定义模型](#-添加自定义模型)
- [配置说明](#-配置说明)
- [服务管理](#-服务管理)
- [开发指南](#-开发指南)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 🎯 简介

**AIFlow** 是一个高性能、可扩展的 AI 任务调度与路由平台，旨在简化多模型 AI 服务的集成与管理。通过统一的 API 网关，您可以轻松调用各种 AI 模型（文本生成、图像生成、语音识别等），平台会自动处理任务调度、负载均衡、服务发现和日志收集。

### 🌟 适用场景

- 🤖 **多模型 AI 应用** - 统一管理和调用多个 AI 模型服务
- 🔄 **异步任务处理** - 支持长时间运行的 AI 推理任务
- 📊 **负载均衡** - 自动分配任务到最优的模型实例
- 🔌 **服务编排** - 灵活的服务发现和动态扩展
- 📝 **集中式日志** - 统一收集和管理所有服务日志

---

## ✨ 核心特性

### 🎨 统一 API 网关
- ✅ RESTful API 接口，支持 JSON 和 multipart/form-data
- ✅ API Key 认证机制
- ✅ 自动文件上传到对象存储（MinIO）
- ✅ 任务状态查询和结果获取
- ✅ 支持同步和异步回调

### 🧠 智能任务调度
- ✅ 基于 RabbitMQ 的消息队列
- ✅ 自动服务发现（Consul）
- ✅ 负载感知的实例选择
- ✅ 任务超时和重试机制
- ✅ 优雅的失败处理

### 🔌 可扩展模型支持
- ✅ 插件化模型注册机制
- ✅ 支持文本生成（GPT-5 等）
- ✅ 支持图像生成（Stable Diffusion 等）
- ✅ 支持图像编辑（GPT Image-1 等）
- ✅ 轻松添加自定义模型服务

### 📊 完善的监控与日志
- ✅ 集中式日志收集（PostgreSQL）
- ✅ 实时任务状态追踪（Redis）
- ✅ 健康检查接口
- ✅ Swagger API 文档

### 🚀 高性能与可靠性
- ✅ 异步 I/O（FastAPI + asyncio）
- ✅ 水平扩展支持
- ✅ 共享内存优化（大文件传输）
- ✅ 优雅的启动和关闭

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户/客户端                          │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Request
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (8000)                        │
│  • API 认证  • 任务创建  • 状态查询  • 文件上传             │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ↓                  ↓                  ↓
   ┌────────┐      ┌──────────┐      ┌──────────┐
   │ Redis  │      │ RabbitMQ │      │  MinIO   │
   │ (状态) │      │ (队列)   │      │ (存储)   │
   └────────┘      └─────┬────┘      └──────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  Task Scheduler (后台)                       │
│  • 消费任务  • 服务发现  • 负载均衡  • 任务分配             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
                    ┌──────────┐
                    │  Consul  │
                    │ (服务发现)│
                    └─────┬────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Forwarder-1 │ │  Forwarder-2 │ │  Forwarder-N │
│   (8001)     │ │   (8002)     │ │   (800N)     │
│ • 模型推理   │ │ • 模型推理   │ │ • 模型推理   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │ 日志消息
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                   Log Service (9000)                         │
│  • 日志收集  • 日志存储  • 日志查询                         │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
                    ┌──────────┐
                    │PostgreSQL│
                    │ (日志库) │
                    └──────────┘
```

### 核心组件

| 组件 | 端口 | 职责 |
|------|------|------|
| **API Gateway** | 8000 | 统一入口，处理用户请求，管理任务生命周期 |
| **Task Scheduler** | - | 后台服务，负责任务调度和负载均衡 |
| **Model Forwarder** | 8001+ | 模型推理服务，可水平扩展多个实例 |
| **Log Service** | 9000 | 集中式日志收集和存储 |

### 外部依赖

| 服务 | 端口 | 用途 |
|------|------|------|
| **Redis** | 6379 | 任务状态存储和缓存 |
| **RabbitMQ** | 5672 | 任务队列和消息传递 |
| **PostgreSQL** | 5432 | 日志持久化存储 |
| **Consul** | 8500 | 服务注册与发现 |
| **MinIO** | 9000 | 对象存储（文件/图片） |

---

## 🚀 快速开始

### 前置要求

- **Python 3.8+**
- **Docker** (推荐用于运行外部服务)
- **Git**

### 1. 克隆项目

```bash
git clone https://github.com/xycdaimi/AIFlow.git
cd AIFlow
```

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 启动外部服务

使用 Docker Compose 快速启动所有外部依赖：

```bash
docker-compose up -d
```

或手动启动各个服务：

```bash
# Redis
docker run -d -p 6379:6379 --name redis redis:latest

# RabbitMQ
docker run -d -p 5672:5672 -p 15672:15672 --name rabbitmq rabbitmq:management

# PostgreSQL
docker run -d -p 5432:5432 --name postgres \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin \
  -e POSTGRES_DB=admin \
  postgres:latest

# Consul
docker run -d -p 8500:8500 --name consul consul:latest

# MinIO
docker run -d -p 9000:9000 -p 9001:9001 --name minio \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=adminadmin \
  minio/minio server /data --console-address ":9001"
```

### 4. 配置环境变量

```bash
# 复制配置文件模板
cp .env.example .env

# 编辑 .env 文件，修改为你的配置
# 主要配置项：
# - Redis/RabbitMQ/PostgreSQL/Consul/MinIO 连接信息
# - API Gateway API Keys
# - 服务端口和 URL
```

### 5. 初始化数据库

```bash
python scripts/init_database.py
```

### 6. 启动所有服务

**Windows:**
```bash
scripts\start_all_services.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/start_all_services.sh
./scripts/start_all_services.sh
```

### 7. 验证服务状态

访问以下 URL 检查服务是否正常运行：

- **API Gateway**: http://localhost:8000/health
- **API 文档**: http://localhost:8000/docs
- **Model Forwarder**: http://localhost:8001/health
- **Log Service**: http://localhost:8002/health

---

## 📚 API 使用指南

### 认证

所有 API 请求需要在 Header 中携带 API Key：

```bash
Authorization: Bearer your-api-key
```

在 `.env` 文件中配置允许的 API Keys：

```env
API_GATEWAY_API_KEYS=test-key-1,test-key-2,prod-key-abc123
```

### 创建任务

#### 方式 1: JSON 格式 (推荐)

```bash
curl -X POST "http://localhost:8000/api/v1/tasks_json" \
  -H "Authorization: Bearer test-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "openai-gpt5",
    "model_spec": {
      "name": "gpt-5",
      "api_key": "sk-your-openai-api-key",
      "endpoint": "https://api.openai.com/v1/chat/completions"
    },
    "payload": {
      "prompt": "你好，请介绍一下人工智能的发展历史"
    },
    "inference_params": {
      "temperature": 0.7,
      "max_tokens": 1000
    }
  }'
```

#### 方式 2: Multipart Form (支持文件上传)

```bash
curl -X POST "http://localhost:8000/api/v1/tasks_form" \
  -H "Authorization: Bearer test-key-1" \
  -F "task_type=image-generation" \
  -F 'model_spec={"name":"stable-diffusion","api_key":"your-key"}' \
  -F 'payload={"prompt":"a beautiful sunset over mountains"}' \
  -F 'inference_params={"width":1024,"height":768}' \
  -F "files=@/path/to/reference_image.jpg"
```

### 响应示例

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "created_at": "2025-11-20T10:30:00Z",
  "message": "Task created successfully"
}
```

### 查询任务状态

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Authorization: Bearer test-key-1"
```

### 响应示例

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "task_type": "openai-gpt5",
  "result": {
    "output": {
      "text": "人工智能的发展历史可以追溯到..."
    },
    "model": "gpt-5",
    "timestamp": "2025-11-20T10:30:15Z"
  },
  "created_at": "2025-11-20T10:30:00Z",
  "updated_at": "2025-11-20T10:30:15Z"
}
```

### 任务状态说明

| 状态 | 说明 |
|------|------|
| `PENDING` | 任务已创建，等待调度 |
| `PROCESSING` | 任务正在处理中 |
| `SUCCESS` | 任务成功完成 |
| `FAILED` | 任务执行失败 |
| `TIMEOUT` | 任务超时 |

### Python SDK 示例

```python
import httpx
import asyncio

async def create_task():
    api_gateway_url = "http://localhost:8000"
    api_key = "test-key-1"

    task_request = {
        "task_type": "openai-gpt5",
        "model_spec": {
            "name": "gpt-5",
            "api_key": "sk-your-openai-api-key"
        },
        "payload": {
            "prompt": "你好，请介绍一下人工智能"
        },
        "inference_params": {
            "temperature": 0.7
        }
    }

    async with httpx.AsyncClient() as client:
        # 创建任务
        response = await client.post(
            f"{api_gateway_url}/api/v1/tasks_json",
            json=task_request,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        task = response.json()
        task_id = task["task_id"]
        print(f"Task created: {task_id}")

        # 轮询任务状态
        while True:
            response = await client.get(
                f"{api_gateway_url}/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            task = response.json()

            if task["status"] in ["SUCCESS", "FAILED", "TIMEOUT"]:
                print(f"Task completed: {task['status']}")
                print(f"Result: {task.get('result')}")
                break

            await asyncio.sleep(2)

asyncio.run(create_task())
```

---

## 🔧 添加自定义模型

AIFlow 支持通过插件化机制轻松添加自定义模型服务。

### 步骤 1: 创建模型服务文件

在 `configs/model_services/` 目录下创建新的 Python 文件，例如 `my_custom_model.py`：

```python
"""My Custom Model Service"""

import httpx
from typing import Dict, Any
from services.model_forwarder.infer import register_inference_function


@register_inference_function("my-custom-model")
def my_custom_model_inference(
    model_spec: Dict[str, Any],
    payload: Dict[str, Any],
    inference_params: Dict[str, Any]
) -> Any:
    """
    自定义模型推理函数

    Args:
        model_spec: 模型配置
            - name: 模型名称
            - endpoint: API 端点
            - api_key: API 密钥
        payload: 输入数据
            - input_text: 输入文本
            - input_image: 输入图片 URL
        inference_params: 推理参数
            - param1: 参数1
            - param2: 参数2

    Returns:
        推理结果（任意格式）
    """
    # 获取配置
    endpoint = model_spec.get("endpoint")
    api_key = model_spec.get("api_key")

    # 获取输入
    input_text = payload.get("input_text")

    # 调用模型 API
    with httpx.Client() as client:
        response = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "input": input_text,
                **inference_params
            },
            timeout=60.0
        )
        result = response.json()

    # 返回结果
    return {
        "output": result["output"],
        "metadata": result.get("metadata", {})
    }
```

### 步骤 2: 重启 Model Forwarder 服务

```bash
# Windows
scripts\restart_all_services.bat

# Linux/Mac
./scripts/restart_all_services.sh
```

### 步骤 3: 使用新模型

```bash
curl -X POST "http://localhost:8000/api/v1/tasks_json" \
  -H "Authorization: Bearer test-key-1" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "my-custom-model",
    "model_spec": {
      "name": "my-model-v1",
      "endpoint": "https://api.example.com/inference",
      "api_key": "your-api-key"
    },
    "payload": {
      "input_text": "Hello, world!"
    },
    "inference_params": {
      "param1": "value1"
    }
  }'
```

### 已支持的模型

| 任务类型 | 说明 | 文件 |
|---------|------|------|
| `openai-gpt5` | OpenAI GPT-5 文本生成 | `openai_gpt5.py` |
| `text-generation` | 通用文本生成 | `text_generation.py` |
| `image-generation` | 图像生成 | `image_generation.py` |
| `gpt-image-1` | GPT Image-1 图像编辑 | `gpt_image_1.py` |

---

## ⚙️ 配置说明

### 环境变量配置 (`.env`)

```env
# ==================== Redis 配置 ====================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ==================== RabbitMQ 配置 ====================
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# ==================== PostgreSQL 配置 ====================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=admin

# ==================== Consul 配置 ====================
CONSUL_HOST=localhost
CONSUL_PORT=8500

# ==================== API Gateway 配置 ====================
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=8000
API_GATEWAY_URL=http://127.0.0.1:8000
API_GATEWAY_INTERNAL_KEY=your-secret-internal-key
API_GATEWAY_API_KEYS=test-key-1,test-key-2,prod-key-abc123

# ==================== Task Scheduler 配置 ====================
SCHEDULER_INSTANCE_ID=scheduler-001
SCHEDULER_MAX_PENDING_TASKS=2
SCHEDULER_RETRY_DELAY=2

# ==================== Model Forwarder 配置 ====================
FORWARDER_INSTANCE_ID=forwarder-001
FORWARDER_SERVICE_HOST=0.0.0.0
FORWARDER_SERVICE_PORT=8001
FORWARDER_SERVICE_URL=http://127.0.0.1:8001

# ==================== Log Service 配置 ====================
LOG_BATCH_SIZE=100
LOG_BATCH_TIMEOUT=5
LOG_SERVICE_HOST=0.0.0.0
LOG_SERVICE_PORT=8002

# ==================== 任务配置 ====================
TASK_TTL=86400              # 任务 TTL (24小时)
TASK_TIMEOUT=300            # 任务超时 (5分钟)
TASK_MAX_RETRIES=3          # 最大重试次数
TASK_MAX_WAIT_TIME=120      # 最大等待时间 (2分钟)
TASK_MONITOR_INTERVAL=30    # 监控间隔 (30秒)

# ==================== MinIO 配置 ====================
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=adminadmin
MINIO_SECURE=false
MINIO_BUCKET_INPUTS=ai-route-inputs
MINIO_BUCKET_OUTPUTS=ai-route-outputs

# ==================== 媒体处理配置 ====================
MEDIA_MAX_DOWNLOAD_SIZE=104857600  # 100MB
MEDIA_DOWNLOAD_TIMEOUT=60
MEDIA_MAX_FILE_SIZE=104857600      # 100MB
```

### 配置项说明

详细的配置说明请参考 [配置文档](docs/configuration.md)。

---

## 🛠️ 服务管理

### 启动所有服务

```bash
# Windows
scripts\start_all_services.bat

# Linux/Mac
./scripts/start_all_services.sh
```

### 停止所有服务

```bash
# Windows
scripts\stop_all_services.bat

# Linux/Mac
./scripts/stop_all_services.sh
```

### 重启所有服务

```bash
# Windows
scripts\restart_all_services.bat

# Linux/Mac
./scripts/restart_all_services.sh
```

### 单独启动服务

```bash
# API Gateway
python -m services.api_gateway.main

# Task Scheduler
python -m services.task_scheduler.main

# Model Forwarder
python -m services.model_forwarder.main

# Log Service
python -m services.log_service.main
```

### 查看服务日志

日志文件位于 `logs/` 目录：

```bash
# API Gateway 日志
tail -f logs/api_gateway.log

# Task Scheduler 日志
tail -f logs/task_scheduler.log

# Model Forwarder 日志
tail -f logs/model_forwarder.log

# Log Service 日志
tail -f logs/log_service.log
```

---

## 👨‍💻 开发指南

### 项目结构

```
AIFlow/
├── configs/                    # 配置文件
│   ├── model_services/         # 模型服务插件
│   └── workflows/              # 工作流配置
├── core/                       # 核心模块
│   ├── config.py               # 配置管理
│   ├── logger.py               # 日志工具
│   ├── protocols.py            # 协议定义
│   ├── utils.py                # 工具函数
│   └── storage/                # 存储客户端
├── services/                   # 服务模块
│   ├── api_gateway/            # API 网关
│   ├── task_scheduler/         # 任务调度器
│   ├── model_forwarder/        # 模型转发服务
│   └── log_service/            # 日志服务
├── scripts/                    # 脚本工具
│   ├── init_database.py        # 数据库初始化
│   ├── start_all_services.bat  # 启动脚本 (Windows)
│   └── start_all_services.sh   # 启动脚本 (Linux/Mac)
├── tests/                      # 测试文件
├── docs/                       # 文档
├── logs/                       # 日志目录
├── .env.example                # 环境变量模板
├── requirements.txt            # Python 依赖
├── docker-compose.yml          # Docker Compose 配置
└── README.md                   # 项目说明
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api_authentication.py

# 运行测试并生成覆盖率报告
pytest --cov=services --cov-report=html
```

### 代码规范

项目遵循 PEP 8 代码规范，使用以下工具进行代码检查：

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 代码格式化
black .

# 代码检查
flake8 .

# 类型检查
mypy .
```

---

## ❓ 常见问题

### 1. 服务启动失败

**问题**: 服务启动时报错 "Connection refused"

**解决方案**:
- 检查外部服务（Redis、RabbitMQ 等）是否正常运行
- 检查 `.env` 配置文件中的连接信息是否正确
- 检查端口是否被占用

### 2. 任务一直处于 PENDING 状态

**问题**: 提交的任务长时间处于 PENDING 状态

**解决方案**:
- 检查 Task Scheduler 服务是否正常运行
- 检查 Model Forwarder 服务是否已注册到 Consul
- 检查 RabbitMQ 队列是否有消息堆积

### 3. 模型推理失败

**问题**: 任务状态变为 FAILED

**解决方案**:
- 检查模型 API Key 是否正确
- 检查模型 API 端点是否可访问
- 查看 Model Forwarder 日志获取详细错误信息

### 4. 文件上传失败

**问题**: 上传文件时报错

**解决方案**:
- 检查 MinIO 服务是否正常运行
- 检查文件大小是否超过限制（默认 100MB）
- 检查 MinIO 存储桶是否已创建

更多问题请查看 [FAQ 文档](docs/faq.md) 或提交 [Issue](https://github.com/yourusername/AIFlow/issues)。

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

### 贡献类型

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- ✨ 添加新功能

### 开发流程

1. 确保所有测试通过
2. 遵循代码规范
3. 添加必要的测试用例
4. 更新相关文档

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Web 框架
- [RabbitMQ](https://www.rabbitmq.com/) - 消息队列
- [Redis](https://redis.io/) - 内存数据库
- [Consul](https://www.consul.io/) - 服务发现
- [MinIO](https://min.io/) - 对象存储
- [PostgreSQL](https://www.postgresql.org/) - 关系型数据库

---

## 📞 联系我们

- **项目主页**: https://github.com/xycdaimi/AIFlow
- **问题反馈**: https://github.com/xycdaimi/AIFlow/issues
- **邮箱**: xycdaimi@gmail.com

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！⭐**

Made with ❤️ by AIFlow Team

</div>
