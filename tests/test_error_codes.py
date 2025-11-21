#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-21
@Description: 错误码系统测试
"""

import pytest
from fastapi import status
from core.errors import (
    ErrorCode,
    AIRouteException,
    raise_error,
    raise_unauthorized,
    raise_invalid_api_key,
    raise_task_not_found,
    raise_invalid_parameter,
    raise_missing_parameter,
    create_error_response,
    ERROR_CODE_TO_HTTP_STATUS,
    ERROR_CODE_TO_MESSAGE,
)


def test_error_code_enum():
    """测试错误码枚举"""
    assert ErrorCode.UNAUTHORIZED == "E2000001"
    assert ErrorCode.TASK_NOT_FOUND == "E3000001"
    assert ErrorCode.INTERNAL_ERROR == "E1000099"


def test_error_code_to_http_status_mapping():
    """测试错误码到 HTTP 状态码的映射"""
    assert ERROR_CODE_TO_HTTP_STATUS[ErrorCode.UNAUTHORIZED] == status.HTTP_401_UNAUTHORIZED
    assert ERROR_CODE_TO_HTTP_STATUS[ErrorCode.TASK_NOT_FOUND] == status.HTTP_404_NOT_FOUND
    assert ERROR_CODE_TO_HTTP_STATUS[ErrorCode.INTERNAL_ERROR] == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_error_code_to_message_mapping():
    """测试错误码到错误消息的映射"""
    assert ERROR_CODE_TO_MESSAGE[ErrorCode.UNAUTHORIZED] == "Unauthorized"
    assert ERROR_CODE_TO_MESSAGE[ErrorCode.TASK_NOT_FOUND] == "Task not found"


def test_ai_route_exception():
    """测试 AIRouteException"""
    exc = AIRouteException(
        ErrorCode.TASK_NOT_FOUND,
        message="Task abc-123 not found",
        details={"task_id": "abc-123"}
    )
    
    assert exc.error_code == ErrorCode.TASK_NOT_FOUND
    assert exc.message == "Task abc-123 not found"
    assert exc.details == {"task_id": "abc-123"}
    assert exc.http_status == status.HTTP_404_NOT_FOUND


def test_ai_route_exception_to_dict():
    """测试 AIRouteException.to_dict()"""
    exc = AIRouteException(
        ErrorCode.INVALID_PARAMETER,
        message="Invalid temperature value",
        details={"parameter": "temperature", "value": 2.5}
    )
    
    result = exc.to_dict()
    
    assert result["error_code"] == "E1000002"
    assert result["message"] == "Invalid temperature value"
    assert result["details"]["parameter"] == "temperature"
    assert result["details"]["value"] == 2.5


def test_ai_route_exception_to_http_exception():
    """测试 AIRouteException.to_http_exception()"""
    exc = AIRouteException(ErrorCode.UNAUTHORIZED)
    http_exc = exc.to_http_exception()
    
    assert http_exc.status_code == status.HTTP_401_UNAUTHORIZED
    assert http_exc.detail["error_code"] == "E2000001"
    assert http_exc.detail["message"] == "Unauthorized"


def test_raise_unauthorized():
    """测试 raise_unauthorized()"""
    with pytest.raises(Exception) as exc_info:
        raise_unauthorized("Missing API key")
    
    # 应该抛出 HTTPException
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error_code"] == "E2000001"


def test_raise_invalid_api_key():
    """测试 raise_invalid_api_key()"""
    with pytest.raises(Exception) as exc_info:
        raise_invalid_api_key()
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail["error_code"] == "E2000002"


def test_raise_task_not_found():
    """测试 raise_task_not_found()"""
    with pytest.raises(Exception) as exc_info:
        raise_task_not_found("task-123")
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail["error_code"] == "E3000001"
    assert "task-123" in exc_info.value.detail["message"]


def test_raise_invalid_parameter():
    """测试 raise_invalid_parameter()"""
    with pytest.raises(Exception) as exc_info:
        raise_invalid_parameter("temperature", "Must be between 0 and 1")
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail["error_code"] == "E1000002"
    assert exc_info.value.detail["details"]["parameter"] == "temperature"


def test_raise_missing_parameter():
    """测试 raise_missing_parameter()"""
    with pytest.raises(Exception) as exc_info:
        raise_missing_parameter("model_spec")
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc_info.value.detail["error_code"] == "E1000003"
    assert "model_spec" in exc_info.value.detail["message"]


def test_create_error_response():
    """测试 create_error_response()"""
    response = create_error_response(
        ErrorCode.TASK_FAILED,
        message="Task execution failed",
        details={"task_id": "task-123", "error": "Timeout"}
    )
    
    assert response["error_code"] == "E3000008"
    assert response["message"] == "Task execution failed"
    assert response["details"]["task_id"] == "task-123"
    assert response["details"]["error"] == "Timeout"


def test_raise_error_with_custom_message():
    """测试 raise_error() 自定义消息"""
    with pytest.raises(Exception) as exc_info:
        raise_error(
            ErrorCode.REDIS_OPERATION_FAILED,
            message="Failed to get task from Redis",
            details={"task_id": "task-123", "error": "Connection timeout"}
        )
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail["error_code"] == "E9000002"
    assert "Redis" in exc_info.value.detail["message"]


def test_all_error_codes_have_http_status():
    """测试所有错误码都有 HTTP 状态码映射"""
    for error_code in ErrorCode:
        assert error_code in ERROR_CODE_TO_HTTP_STATUS, f"Missing HTTP status for {error_code}"


def test_all_error_codes_have_message():
    """测试所有错误码都有错误消息"""
    for error_code in ErrorCode:
        assert error_code in ERROR_CODE_TO_MESSAGE, f"Missing message for {error_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

