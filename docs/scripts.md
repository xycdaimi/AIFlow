# AIFlow 服务管理脚本

本目录包含用于管理 AIFlow 服务的脚本文件。

## 📁 文件说明

### Windows 脚本 (.bat)

| 文件名 | 说明 |
|--------|------|
| `start_all_services.bat` | 启动所有服务（Windows） |
| `stop_all_services.bat` | 停止所有服务（Windows） |
| `restart_all_services.bat` | 重启所有服务（Windows） |

### Linux/Ubuntu 脚本 (.sh)

| 文件名 | 说明 |
|--------|------|
| `start_all_services.sh` | 启动所有服务（Linux/Ubuntu） |
| `stop_all_services.sh` | 停止所有服务（Linux/Ubuntu） |
| `restart_all_services.sh` | 重启所有服务（Linux/Ubuntu） |

### 数据库脚本

| 文件名 | 说明 |
|--------|------|
| `init_database.py` | 初始化 PostgreSQL 数据库表结构 |
| `init_database.sql` | 数据库表结构 SQL 文件 |

---

## 🚀 使用方法

### Windows 系统

#### 启动所有服务
```cmd
scripts\start_all_services.bat
```

#### 停止所有服务
```cmd
scripts\stop_all_services.bat
```

#### 重启所有服务
```cmd
scripts\restart_all_services.bat
```

### Linux/Ubuntu 系统

#### 首次使用 - 添加执行权限
```bash
chmod +x scripts/*.sh
```

#### 启动所有服务
```bash
./scripts/start_all_services.sh
```

#### 停止所有服务
```bash
./scripts/stop_all_services.sh
```

#### 重启所有服务
```bash
./scripts/restart_all_services.sh
```

---

## 📋 服务启动顺序

脚本会按照以下顺序启动服务：

1. **Log Service** (端口 8002) - 日志收集服务
2. **Model Forwarder** (端口 8001) - 模型推理转发服务
3. **Task Scheduler** (后台) - 任务调度服务
4. **API Gateway** (端口 8000) - API 网关服务

---

## 🔍 服务管理

### Windows

- 每个服务会在独立的命令行窗口中运行
- 关闭窗口或按 `Ctrl+C` 可停止单个服务
- 使用 `stop_all_services.bat` 可一次性停止所有服务

### Linux/Ubuntu

- 所有服务以后台进程方式运行
- 进程 PID 保存在 `logs/pids/` 目录
- 日志文件保存在 `logs/` 目录
- 使用 `stop_all_services.sh` 可一次性停止所有服务

### 查看日志（Linux）

```bash
# 实时查看 API Gateway 日志
tail -f logs/api_gateway.log

# 实时查看 Model Forwarder 日志
tail -f logs/model_forwarder.log

# 实时查看 Task Scheduler 日志
tail -f logs/task_scheduler.log

# 实时查看 Log Service 日志
tail -f logs/log_service.log
```

### 检查服务状态（Linux）

```bash
# 查看所有 Python 服务进程
ps aux | grep "services\."

# 查看特定服务进程
ps aux | grep "services.api_gateway"
```

---

## 🔧 初始化数据库

在首次运行服务之前，需要初始化 PostgreSQL 数据库：

```bash
# Windows
python scripts\init_database.py

# Linux/Ubuntu
python3 scripts/init_database.py
```

---

## ⚙️ 配置要求

### 环境变量

脚本会自动检查 `.env` 文件：
- 如果不存在，会从 `.env.example` 复制
- 请确保配置以下连接信息：
  - Redis 连接
  - RabbitMQ 连接
  - PostgreSQL 连接
  - Consul 连接
  - MinIO 连接

### 系统要求

- **Python**: 3.8+
- **操作系统**: Windows 10+ 或 Ubuntu 18.04+

---

## 🌐 服务访问地址

启动成功后，可以通过以下地址访问服务：

| 服务 | URL |
|------|-----|
| API Gateway | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| Model Forwarder | http://localhost:8001 |
| Log Service | http://localhost:8002 |

### 健康检查

| 服务 | Health Check URL |
|------|------------------|
| API Gateway | http://localhost:8000/health |
| Model Forwarder | http://localhost:8001/health |
| Log Service | http://localhost:8002/health |

---

## ❗ 常见问题

### 1. 端口被占用

如果启动失败，可能是端口被占用。检查端口占用情况：

**Windows:**
```cmd
netstat -ano | findstr :8000
netstat -ano | findstr :8001
netstat -ano | findstr :8002
```

**Linux:**
```bash
lsof -i :8000
lsof -i :8001
lsof -i :8002
```

### 2. 服务无法停止（Linux）

如果 `stop_all_services.sh` 无法停止服务，可以手动强制停止：

```bash
# 查找所有 AIFlow 相关进程
ps aux | grep "services\."

# 强制停止进程（替换 <PID> 为实际进程 ID）
kill -9 <PID>
```

### 3. 权限问题（Linux）

如果遇到权限错误：

```bash
# 添加执行权限
chmod +x scripts/*.sh

# 如果需要，清理 PID 文件
rm -rf logs/pids/*
```

---

## 📝 注意事项

1. **首次运行**: 确保已配置 `.env` 文件和初始化数据库
2. **依赖服务**: 确保 Redis、RabbitMQ、PostgreSQL、Consul、MinIO 已启动
3. **日志文件**: 定期清理 `logs/` 目录下的日志文件
4. **进程管理**: Linux 下建议使用 systemd 或 supervisor 进行生产环境部署

---

## 🔗 相关文档

- [项目 README](../README.md)
- [API 文档](http://localhost:8000/docs)
- [配置说明](../.env.example)

