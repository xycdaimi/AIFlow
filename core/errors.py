#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-21
@Description: 统一错误码和异常处理系统

错误码格式: EXXXYYYY
- E: Error 前缀
- XXX: 模块代码 (3位数字)
- YYYY: 具体错误代码 (4位数字)

模块代码分配:
- 100: 通用错误
- 200: 认证和授权
- 300: 任务管理
- 400: 模型推理
- 500: 存储服务
- 600: 消息队列
- 700: 服务发现
- 800: 日志服务
- 900: 系统错误
"""

from typing import Optional, Dict, Any
from enum import Enum
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """统一错误码枚举"""
    
    # ==================== 通用错误 (E100XXXX) ====================
    INVALID_REQUEST = "E1000001"           # 无效的请求
    INVALID_PARAMETER = "E1000002"         # 无效的参数
    MISSING_PARAMETER = "E1000003"         # 缺少必需参数
    INVALID_JSON = "E1000004"              # 无效的 JSON 格式
    RESOURCE_NOT_FOUND = "E1000005"        # 资源不存在
    INTERNAL_ERROR = "E1000099"            # 内部错误
    
    # ==================== 认证和授权 (E200XXXX) ====================
    UNAUTHORIZED = "E2000001"              # 未认证
    INVALID_API_KEY = "E2000002"           # 无效的 API Key
    MISSING_API_KEY = "E2000003"           # 缺少 API Key
    FORBIDDEN = "E2000004"                 # 无权限访问
    INVALID_INTERNAL_KEY = "E2000005"      # 无效的内部服务密钥
    
    # ==================== 任务管理 (E300XXXX) ====================
    TASK_NOT_FOUND = "E3000001"            # 任务不存在
    TASK_CREATE_FAILED = "E3000002"        # 任务创建失败
    TASK_TIMEOUT = "E3000003"              # 任务超时
    TASK_MAX_RETRIES = "E3000004"          # 任务超过最大重试次数
    TASK_ALREADY_EXISTS = "E3000005"       # 任务已存在
    TASK_INVALID_STATUS = "E3000006"       # 任务状态无效
    TASK_PROCESSING = "E3000007"           # 任务处理中
    TASK_FAILED = "E3000008"               # 任务失败
    INVALID_TASK_TYPE = "E3000009"         # 无效的任务类型
    INVALID_MODEL_SPEC = "E3000010"        # 无效的模型规格
    INVALID_PAYLOAD = "E3000011"           # 无效的任务数据
    INVALID_CALLBACK = "E3000012"          # 无效的回调配置
    
    # ==================== 模型推理 (E400XXXX) ====================
    INFERENCE_FAILED = "E4000001"          # 推理失败
    MODEL_NOT_FOUND = "E4000002"           # 模型不存在
    MODEL_UNAVAILABLE = "E4000003"         # 模型不可用
    FORWARDER_BUSY = "E4000004"            # 推理服务繁忙
    FORWARDER_NOT_FOUND = "E4000005"       # 推理服务不存在
    INVALID_INFERENCE_PARAMS = "E4000006"  # 无效的推理参数
    MODEL_API_ERROR = "E4000007"           # 模型 API 错误
    
    # ==================== 存储服务 (E500XXXX) ====================
    STORAGE_ERROR = "E5000001"             # 存储错误
    MINIO_CONNECTION_FAILED = "E5000002"   # MinIO 连接失败
    MINIO_UPLOAD_FAILED = "E5000003"      # MinIO 上传失败
    MINIO_DOWNLOAD_FAILED = "E5000004"    # MinIO 下载失败
    MINIO_DELETE_FAILED = "E5000005"      # MinIO 删除失败
    MINIO_BUCKET_NOT_FOUND = "E5000006"   # MinIO 存储桶不存在
    FILE_TOO_LARGE = "E5000007"           # 文件过大
    INVALID_FILE_FORMAT = "E5000008"      # 无效的文件格式
    
    # ==================== 消息队列 (E600XXXX) ====================
    RABBITMQ_CONNECTION_FAILED = "E6000001"  # RabbitMQ 连接失败
    RABBITMQ_PUBLISH_FAILED = "E6000002"     # RabbitMQ 发布失败
    RABBITMQ_CONSUME_FAILED = "E6000003"     # RabbitMQ 消费失败
    QUEUE_NOT_FOUND = "E6000004"             # 队列不存在
    MESSAGE_INVALID = "E6000005"             # 消息格式无效
    
    # ==================== 服务发现 (E700XXXX) ====================
    CONSUL_CONNECTION_FAILED = "E7000001"    # Consul 连接失败
    SERVICE_REGISTRATION_FAILED = "E7000002" # 服务注册失败
    SERVICE_NOT_FOUND = "E7000003"           # 服务不存在
    SERVICE_UNAVAILABLE = "E7000004"         # 服务不可用
    
    # ==================== 日志服务 (E800XXXX) ====================
    LOG_WRITE_FAILED = "E8000001"            # 日志写入失败
    LOG_QUERY_FAILED = "E8000002"            # 日志查询失败
    POSTGRES_CONNECTION_FAILED = "E8000003"  # PostgreSQL 连接失败
    
    # ==================== 系统错误 (E900XXXX) ====================
    REDIS_CONNECTION_FAILED = "E9000001"     # Redis 连接失败
    REDIS_OPERATION_FAILED = "E9000002"      # Redis 操作失败
    DATABASE_ERROR = "E9000003"              # 数据库错误
    NETWORK_ERROR = "E9000004"               # 网络错误
    TIMEOUT_ERROR = "E9000005"               # 超时错误
    CONFIGURATION_ERROR = "E9000006"         # 配置错误
    SERVICE_SHUTDOWN = "E9000007"            # 服务关闭中


# 错误码到 HTTP 状态码的映射
ERROR_CODE_TO_HTTP_STATUS = {
    # 通用错误
    ErrorCode.INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_PARAMETER: status.HTTP_400_BAD_REQUEST,
    ErrorCode.MISSING_PARAMETER: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_JSON: status.HTTP_400_BAD_REQUEST,
    ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # 认证和授权
    ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INVALID_API_KEY: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.MISSING_API_KEY: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.INVALID_INTERNAL_KEY: status.HTTP_401_UNAUTHORIZED,
    
    # 任务管理
    ErrorCode.TASK_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.TASK_CREATE_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.TASK_TIMEOUT: status.HTTP_408_REQUEST_TIMEOUT,
    ErrorCode.TASK_MAX_RETRIES: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.TASK_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.TASK_INVALID_STATUS: status.HTTP_400_BAD_REQUEST,
    ErrorCode.TASK_PROCESSING: status.HTTP_202_ACCEPTED,
    ErrorCode.TASK_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.INVALID_TASK_TYPE: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_MODEL_SPEC: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_PAYLOAD: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_CALLBACK: status.HTTP_400_BAD_REQUEST,

    # 模型推理
    ErrorCode.INFERENCE_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.MODEL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.MODEL_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.FORWARDER_BUSY: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.FORWARDER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.INVALID_INFERENCE_PARAMS: status.HTTP_400_BAD_REQUEST,
    ErrorCode.MODEL_API_ERROR: status.HTTP_502_BAD_GATEWAY,

    # 存储服务
    ErrorCode.STORAGE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.MINIO_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.MINIO_UPLOAD_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.MINIO_DOWNLOAD_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.MINIO_DELETE_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.MINIO_BUCKET_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.FILE_TOO_LARGE: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    ErrorCode.INVALID_FILE_FORMAT: status.HTTP_400_BAD_REQUEST,

    # 消息队列
    ErrorCode.RABBITMQ_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.RABBITMQ_PUBLISH_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.RABBITMQ_CONSUME_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.QUEUE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.MESSAGE_INVALID: status.HTTP_400_BAD_REQUEST,

    # 服务发现
    ErrorCode.CONSUL_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.SERVICE_REGISTRATION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.SERVICE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,

    # 日志服务
    ErrorCode.LOG_WRITE_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.LOG_QUERY_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.POSTGRES_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,

    # 系统错误
    ErrorCode.REDIS_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.REDIS_OPERATION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.NETWORK_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.TIMEOUT_ERROR: status.HTTP_408_REQUEST_TIMEOUT,
    ErrorCode.CONFIGURATION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.SERVICE_SHUTDOWN: status.HTTP_503_SERVICE_UNAVAILABLE,
}


# 错误码到错误消息的映射
ERROR_CODE_TO_MESSAGE = {
    # 通用错误
    ErrorCode.INVALID_REQUEST: "Invalid request",
    ErrorCode.INVALID_PARAMETER: "Invalid parameter",
    ErrorCode.MISSING_PARAMETER: "Missing required parameter",
    ErrorCode.INVALID_JSON: "Invalid JSON format",
    ErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
    ErrorCode.INTERNAL_ERROR: "Internal server error",

    # 认证和授权
    ErrorCode.UNAUTHORIZED: "Unauthorized",
    ErrorCode.INVALID_API_KEY: "Invalid API key",
    ErrorCode.MISSING_API_KEY: "Missing API key",
    ErrorCode.FORBIDDEN: "Forbidden",
    ErrorCode.INVALID_INTERNAL_KEY: "Invalid internal service key",

    # 任务管理
    ErrorCode.TASK_NOT_FOUND: "Task not found",
    ErrorCode.TASK_CREATE_FAILED: "Failed to create task",
    ErrorCode.TASK_TIMEOUT: "Task timeout",
    ErrorCode.TASK_MAX_RETRIES: "Task exceeded maximum retries",
    ErrorCode.TASK_ALREADY_EXISTS: "Task already exists",
    ErrorCode.TASK_INVALID_STATUS: "Invalid task status",
    ErrorCode.TASK_PROCESSING: "Task is still processing",
    ErrorCode.TASK_FAILED: "Task failed",
    ErrorCode.INVALID_TASK_TYPE: "Invalid task type",
    ErrorCode.INVALID_MODEL_SPEC: "Invalid model specification",
    ErrorCode.INVALID_PAYLOAD: "Invalid task payload",
    ErrorCode.INVALID_CALLBACK: "Invalid callback configuration",

    # 模型推理
    ErrorCode.INFERENCE_FAILED: "Model inference failed",
    ErrorCode.MODEL_NOT_FOUND: "Model not found",
    ErrorCode.MODEL_UNAVAILABLE: "Model unavailable",
    ErrorCode.FORWARDER_BUSY: "Model forwarder is busy",
    ErrorCode.FORWARDER_NOT_FOUND: "Model forwarder not found",
    ErrorCode.INVALID_INFERENCE_PARAMS: "Invalid inference parameters",
    ErrorCode.MODEL_API_ERROR: "Model API error",

    # 存储服务
    ErrorCode.STORAGE_ERROR: "Storage error",
    ErrorCode.MINIO_CONNECTION_FAILED: "Failed to connect to MinIO",
    ErrorCode.MINIO_UPLOAD_FAILED: "Failed to upload file to MinIO",
    ErrorCode.MINIO_DOWNLOAD_FAILED: "Failed to download file from MinIO",
    ErrorCode.MINIO_DELETE_FAILED: "Failed to delete file from MinIO",
    ErrorCode.MINIO_BUCKET_NOT_FOUND: "MinIO bucket not found",
    ErrorCode.FILE_TOO_LARGE: "File size exceeds limit",
    ErrorCode.INVALID_FILE_FORMAT: "Invalid file format",

    # 消息队列
    ErrorCode.RABBITMQ_CONNECTION_FAILED: "Failed to connect to RabbitMQ",
    ErrorCode.RABBITMQ_PUBLISH_FAILED: "Failed to publish message to RabbitMQ",
    ErrorCode.RABBITMQ_CONSUME_FAILED: "Failed to consume message from RabbitMQ",
    ErrorCode.QUEUE_NOT_FOUND: "Queue not found",
    ErrorCode.MESSAGE_INVALID: "Invalid message format",

    # 服务发现
    ErrorCode.CONSUL_CONNECTION_FAILED: "Failed to connect to Consul",
    ErrorCode.SERVICE_REGISTRATION_FAILED: "Failed to register service",
    ErrorCode.SERVICE_NOT_FOUND: "Service not found",
    ErrorCode.SERVICE_UNAVAILABLE: "Service unavailable",

    # 日志服务
    ErrorCode.LOG_WRITE_FAILED: "Failed to write log",
    ErrorCode.LOG_QUERY_FAILED: "Failed to query logs",
    ErrorCode.POSTGRES_CONNECTION_FAILED: "Failed to connect to PostgreSQL",

    # 系统错误
    ErrorCode.REDIS_CONNECTION_FAILED: "Failed to connect to Redis",
    ErrorCode.REDIS_OPERATION_FAILED: "Redis operation failed",
    ErrorCode.DATABASE_ERROR: "Database error",
    ErrorCode.NETWORK_ERROR: "Network error",
    ErrorCode.TIMEOUT_ERROR: "Request timeout",
    ErrorCode.CONFIGURATION_ERROR: "Configuration error",
    ErrorCode.SERVICE_SHUTDOWN: "Service is shutting down",
}


class AIRouteException(Exception):
    """AI Route 平台基础异常类"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        http_status: Optional[int] = None
    ):
        """
        初始化异常

        Args:
            error_code: 错误码
            message: 自定义错误消息（可选，默认使用错误码对应的消息）
            details: 额外的错误详情（可选）
            http_status: HTTP 状态码（可选，默认使用错误码对应的状态码）
        """
        self.error_code = error_code
        self.message = message or ERROR_CODE_TO_MESSAGE.get(error_code, "Unknown error")
        self.details = details or {}
        self.http_status = http_status or ERROR_CODE_TO_HTTP_STATUS.get(
            error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "error_code": self.error_code.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result

    def to_http_exception(self) -> HTTPException:
        """转换为 FastAPI HTTPException"""
        return HTTPException(
            status_code=self.http_status,
            detail=self.to_dict()
        )


# ==================== 便捷函数 ====================

def raise_error(
    error_code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    http_status: Optional[int] = None
):
    """
    抛出 AI Route 异常

    Args:
        error_code: 错误码
        message: 自定义错误消息
        details: 额外的错误详情
        http_status: HTTP 状态码

    Raises:
        HTTPException: FastAPI HTTP 异常
    """
    exc = AIRouteException(error_code, message, details, http_status)
    raise exc.to_http_exception()


def create_error_response(
    error_code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    创建错误响应字典（不抛出异常）

    Args:
        error_code: 错误码
        message: 自定义错误消息
        details: 额外的错误详情

    Returns:
        错误响应字典
    """
    exc = AIRouteException(error_code, message, details)
    return exc.to_dict()


# ==================== 特定错误的便捷函数 ====================

def raise_unauthorized(message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """抛出未认证错误"""
    raise_error(ErrorCode.UNAUTHORIZED, message, details)


def raise_invalid_api_key(message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """抛出无效 API Key 错误"""
    raise_error(ErrorCode.INVALID_API_KEY, message, details)


def raise_task_not_found(task_id: str, message: Optional[str] = None):
    """抛出任务不存在错误"""
    raise_error(
        ErrorCode.TASK_NOT_FOUND,
        message or f"Task {task_id} not found",
        {"task_id": task_id}
    )


def raise_invalid_parameter(param_name: str, message: Optional[str] = None):
    """抛出无效参数错误"""
    raise_error(
        ErrorCode.INVALID_PARAMETER,
        message or f"Invalid parameter: {param_name}",
        {"parameter": param_name}
    )


def raise_missing_parameter(param_name: str, message: Optional[str] = None):
    """抛出缺少参数错误"""
    raise_error(
        ErrorCode.MISSING_PARAMETER,
        message or f"Missing required parameter: {param_name}",
        {"parameter": param_name}
    )


def raise_internal_error(message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """抛出内部错误"""
    raise_error(ErrorCode.INTERNAL_ERROR, message, details)


def raise_service_unavailable(service_name: str, message: Optional[str] = None):
    """抛出服务不可用错误"""
    raise_error(
        ErrorCode.SERVICE_UNAVAILABLE,
        message or f"Service {service_name} is unavailable",
        {"service": service_name}
    )


# ==================== 异常处理装饰器 ====================

from functools import wraps
from typing import Callable
import traceback


def handle_errors(func: Callable) -> Callable:
    """
    异常处理装饰器，自动捕获并转换异常为标准错误响应

    用法:
        @handle_errors
        async def my_endpoint():
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # 已经是 HTTPException，直接抛出
            raise
        except AIRouteException as e:
            # AI Route 异常，转换为 HTTPException
            raise e.to_http_exception()
        except Exception as e:
            # 未知异常，记录并返回内部错误
            print(f"Unexpected error in {func.__name__}: {e}")
            traceback.print_exc()
            raise_internal_error(
                message=f"Unexpected error: {str(e)}",
                details={"function": func.__name__}
            )

    return wrapper


def handle_errors_sync(func: Callable) -> Callable:
    """
    同步函数的异常处理装饰器

    用法:
        @handle_errors_sync
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except AIRouteException as e:
            raise e.to_http_exception()
        except Exception as e:
            print(f"Unexpected error in {func.__name__}: {e}")
            traceback.print_exc()
            raise_internal_error(
                message=f"Unexpected error: {str(e)}",
                details={"function": func.__name__}
            )

    return wrapper

