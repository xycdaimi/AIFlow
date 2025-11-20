# AI Router 启动脚本

本目录包含用于快速启动、停止和重启 AI Router 所有服务的批处理脚本。

---

## 📁 脚本列表

| 脚本文件 | 功能 | 说明 |
|---------|------|------|
| `start_all_services.bat` | 启动所有服务 | 按正确顺序启动所有服务 |
| `stop_all_services.bat` | 停止所有服务 | 停止所有正在运行的服务 |
| `restart_all_services.bat` | 重启所有服务 | 先停止再启动所有服务 |

---

## 🚀 使用方法

### 1. 启动所有服务

在项目根目录双击运行：

```
scripts\start_all_services.bat
```

或在命令行中执行：

```bash
cd d:\py\AI_Router
scripts\start_all_services.bat
```

**启动顺序**：
1. Log Service (端口 8002)
2. Model Forwarder (端口 8001)
3. Task Scheduler (后台服务)
4. API Gateway (端口 8000)

每个服务会在独立的命令行窗口中启动，方便查看日志。

---

### 2. 停止所有服务

双击运行：

```
scripts\stop_all_services.bat
```

或在命令行中执行：

```bash
scripts\stop_all_services.bat
```

脚本会自动查找并停止所有 AI Router 服务进程。

---

### 3. 重启所有服务

双击运行：

```
scripts\restart_all_services.bat
```

或在命令行中执行：

```bash
scripts\restart_all_services.bat
```

脚本会先停止所有服务，等待 3 秒后重新启动。

---

## ⚙️ 前置要求

### 1. Python 环境

确保已安装 Python 3.8 或更高版本：

```bash
python --version
```

### 2. 依赖安装

在项目根目录安装所有依赖：

```bash
pip install -r requirements.txt
```

### 3. 配置文件

确保 `.env` 文件存在并配置正确。如果不存在，脚本会提示从 `.env.example` 复制。

**必需的配置项**：
- Redis 连接信息
- RabbitMQ 连接信息
- PostgreSQL 连接信息
- Consul 连接信息
- MinIO 连接信息

### 4. 外部服务

确保以下外部服务已启动：
- ✅ Redis (默认端口 6379)
- ✅ RabbitMQ (默认端口 5672)
- ✅ PostgreSQL (默认端口 5432)
- ✅ Consul (默认端口 8500)
- ✅ MinIO (默认端口 9000)

---

## 🔍 验证服务状态

### 1. 检查服务是否启动

访问健康检查接口：

```bash
# API Gateway
curl http://localhost:8000/health

# Model Forwarder
curl http://localhost:8001/health

# Log Service
curl http://localhost:8002/health
```

### 2. 查看 API 文档

访问 Swagger UI：

```
http://localhost:8000/docs
```

### 3. 查看服务窗口

每个服务都在独立的命令行窗口中运行，窗口标题为：
- `AI Router - API Gateway`
- `AI Router - Model Forwarder`
- `AI Router - Task Scheduler`
- `AI Router - Log Service`

---

## 🛠️ 故障排查

### 问题 1: 脚本提示"请在项目根目录运行"

**原因**：脚本不在项目根目录执行

**解决**：
```bash
cd d:\py\AI_Router
scripts\start_all_services.bat
```

---

### 问题 2: 服务启动失败

**可能原因**：
1. 外部服务未启动（Redis、RabbitMQ 等）
2. 端口被占用
3. 配置文件错误

**解决步骤**：
1. 检查外部服务是否运行
2. 检查端口是否被占用：
   ```bash
   netstat -ano | findstr "8000"
   netstat -ano | findstr "8001"
   netstat -ano | findstr "8002"
   ```
3. 检查 `.env` 配置是否正确

---

### 问题 3: 停止脚本无法停止服务

**原因**：服务窗口标题不匹配

**解决**：手动关闭服务窗口，或使用任务管理器结束 Python 进程

---

## 📝 手动启动服务（调试用）

如果需要单独启动某个服务进行调试：

```bash
# 启动 Log Service
python -m services.log_service.main

# 启动 Model Forwarder
python -m services.model_forwarder.main

# 启动 Task Scheduler
python -m services.task_scheduler.main

# 启动 API Gateway
python -m services.api_gateway.main
```

---

## 🔧 自定义配置

### 修改启动延迟

编辑 `start_all_services.bat`，修改 `timeout` 命令的延迟时间：

```batch
timeout /t 3 /nobreak >nul  REM 改为其他秒数
```

### 修改服务端口

编辑 `.env` 文件中的端口配置：

```bash
API_GATEWAY_PORT=8000
FORWARDER_SERVICE_PORT=8001
LOG_SERVICE_PORT=8002
```

---

## 📊 服务架构

```
┌─────────────────┐
│   API Gateway   │ ← 用户请求入口 (8000)
│   (端口 8000)   │
└────────┬────────┘
         │
         ├─→ Redis (任务状态)
         ├─→ RabbitMQ (任务队列)
         └─→ MinIO (文件存储)
              │
              ↓
┌─────────────────┐
│ Task Scheduler  │ ← 任务调度器
│   (后台服务)    │
└────────┬────────┘
         │
         ├─→ RabbitMQ (消费任务)
         ├─→ Consul (服务发现)
         └─→ Redis (更新状态)
              │
              ↓
┌─────────────────┐
│ Model Forwarder │ ← 模型推理服务 (8001)
│   (端口 8001)   │
└────────┬────────┘
         │
         ├─→ Consul (注册服务)
         ├─→ RabbitMQ (发送日志)
         └─→ API Gateway (回调)
              │
              ↓
┌─────────────────┐
│  Log Service    │ ← 日志收集服务 (8002)
│   (端口 8002)   │
└────────┬────────┘
         │
         ├─→ RabbitMQ (消费日志)
         └─→ PostgreSQL (存储日志)
```

---

## ⚡ 快速测试

启动所有服务后，可以使用以下命令快速测试：

```bash
# 创建一个测试任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer test-key-1" \
  -H "Content-Type: application/json" \
  -d "{\"task_type\":\"text-generation\",\"model_spec\":{\"provider\":\"openai\",\"model_name\":\"gpt-5\",\"api_key\":\"sk-test\"},\"payload\":{\"prompt\":\"Hello!\"}}"
```

---

## 📞 支持

如有问题，请查看：
- 项目文档：`docs/` 目录
- 服务日志：各个服务窗口的输出
- 健康检查：`http://localhost:8000/health`

