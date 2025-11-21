#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-21
@Description: FastAPI 全局异常处理器
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import logging
from typing import Union

from core.errors import (
    AIRouteException,
    ErrorCode,
    create_error_response,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI):
    """
    注册全局异常处理器到 FastAPI 应用
    
    用法:
        app = FastAPI()
        register_exception_handlers(app)
    
    Args:
        app: FastAPI 应用实例
    """
    
    @app.exception_handler(AIRouteException)
    async def ai_route_exception_handler(request: Request, exc: AIRouteException):
        """处理 AIRouteException"""
        logger.warning(
            f"AIRouteException: {exc.error_code} - {exc.message}",
            extra={
                "error_code": exc.error_code.value,
                "path": request.url.path,
                "method": request.method,
                **exc.details
            }
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict()
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理 HTTPException"""
        # 如果 detail 已经是字典格式（标准错误响应），直接返回
        if isinstance(exc.detail, dict) and "error_code" in exc.detail:
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail
            )
        
        # 否则转换为标准错误响应格式
        error_code = _http_status_to_error_code(exc.status_code)
        error_response = create_error_response(
            error_code,
            message=str(exc.detail),
            details={"path": request.url.path}
        )
        
        logger.warning(
            f"HTTPException: {exc.status_code} - {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证错误"""
        # 提取验证错误详情
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        error_response = create_error_response(
            ErrorCode.INVALID_PARAMETER,
            message="Request validation failed",
            details={"validation_errors": errors}
        )
        
        logger.warning(
            f"Validation error: {errors}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": errors
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理所有未捕获的异常"""
        # 记录完整的异常堆栈
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
            },
            exc_info=True
        )
        
        # 打印堆栈跟踪（开发环境）
        traceback.print_exc()
        
        # 返回标准错误响应
        error_response = create_error_response(
            ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
            details={
                "exception_type": type(exc).__name__,
                "path": request.url.path
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )


def _http_status_to_error_code(status_code: int) -> ErrorCode:
    """
    将 HTTP 状态码映射到错误码
    
    Args:
        status_code: HTTP 状态码
    
    Returns:
        对应的错误码
    """
    mapping = {
        400: ErrorCode.INVALID_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        408: ErrorCode.TIMEOUT_ERROR,
        409: ErrorCode.TASK_ALREADY_EXISTS,
        413: ErrorCode.FILE_TOO_LARGE,
        500: ErrorCode.INTERNAL_ERROR,
        502: ErrorCode.MODEL_API_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }
    return mapping.get(status_code, ErrorCode.INTERNAL_ERROR)

