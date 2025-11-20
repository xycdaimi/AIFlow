#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: 测试 API Gateway 的 API Key 认证功能
"""

import requests
import json

# API Gateway 地址
API_GATEWAY_URL = "http://localhost:8000/api/v1"

# 测试用的 API Keys
VALID_API_KEY = "test-key-1"
INVALID_API_KEY = "invalid-key-xxx"


def test_create_task_with_valid_api_key():
    """测试使用有效的 API Key 创建任务"""
    print("\n" + "="*60)
    print("测试 1: 使用有效的 API Key 创建任务")
    print("="*60)
    
    url = f"{API_GATEWAY_URL}/tasks"
    headers = {
        "Authorization": f"Bearer {VALID_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "task_type": "text-generation",
        "model_spec": {
            "provider": "openai",
            "model_name": "gpt-5",
            "api_key": "sk-test"
        },
        "payload": {
            "prompt": "Hello, world!"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 201:
            print("✅ 测试通过：成功创建任务")
        else:
            print("❌ 测试失败：期望状态码 201")
    except Exception as e:
        print(f"❌ 测试失败：{e}")


def test_create_task_with_invalid_api_key():
    """测试使用无效的 API Key 创建任务"""
    print("\n" + "="*60)
    print("测试 2: 使用无效的 API Key 创建任务")
    print("="*60)
    
    url = f"{API_GATEWAY_URL}/tasks"
    headers = {
        "Authorization": f"Bearer {INVALID_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "task_type": "text-generation",
        "model_spec": {
            "provider": "openai",
            "model_name": "gpt-5",
            "api_key": "sk-test"
        },
        "payload": {
            "prompt": "Hello, world!"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 401:
            print("✅ 测试通过：正确拒绝无效的 API Key")
        else:
            print("❌ 测试失败：期望状态码 401")
    except Exception as e:
        print(f"❌ 测试失败：{e}")


def test_create_task_without_api_key():
    """测试不提供 API Key 创建任务"""
    print("\n" + "="*60)
    print("测试 3: 不提供 API Key 创建任务")
    print("="*60)
    
    url = f"{API_GATEWAY_URL}/tasks"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "task_type": "text-generation",
        "model_spec": {
            "provider": "openai",
            "model_name": "gpt-5",
            "api_key": "sk-test"
        },
        "payload": {
            "prompt": "Hello, world!"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 403:
            print("✅ 测试通过：正确拒绝缺少 API Key 的请求")
        else:
            print("❌ 测试失败：期望状态码 403")
    except Exception as e:
        print(f"❌ 测试失败：{e}")


def test_create_task_with_multipart_form():
    """测试使用 multipart/form-data 格式和 API Key 创建任务"""
    print("\n" + "="*60)
    print("测试 4: 使用 multipart/form-data 格式创建任务")
    print("="*60)
    
    url = f"{API_GATEWAY_URL}/tasks"
    headers = {
        "Authorization": f"Bearer {VALID_API_KEY}"
    }
    data = {
        "task_type": "text-generation",
        "model_spec": json.dumps({
            "provider": "openai",
            "model_name": "gpt-5",
            "api_key": "sk-test"
        }),
        "payload": json.dumps({
            "prompt": "Hello, world!"
        })
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 201:
            print("✅ 测试通过：成功创建任务（multipart/form-data）")
        else:
            print("❌ 测试失败：期望状态码 201")
    except Exception as e:
        print(f"❌ 测试失败：{e}")


if __name__ == "__main__":
    print("\n🚀 开始测试 API Gateway 认证功能")
    print("请确保：")
    print("1. API Gateway 正在运行（http://localhost:8000）")
    print("2. .env 文件中配置了 API_GATEWAY_API_KEYS=test-key-1,test-key-2")
    
    input("\n按 Enter 键开始测试...")
    
    test_create_task_with_valid_api_key()
    test_create_task_with_invalid_api_key()
    test_create_task_without_api_key()
    test_create_task_with_multipart_form()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60)

