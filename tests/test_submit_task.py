#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: 测试提交任务到 API Gateway
"""

import httpx
import asyncio
from datetime import datetime


async def test_submit_gpt5_task():
    """测试提交 GPT-5 文本生成任务"""
    
    # API Gateway 配置
    api_gateway_url = "http://127.0.0.1:8000"
    api_key = "test-key-1"
    
    # 构建任务请求
    task_request = {
        "task_type": "openai-gpt5",  # 必须匹配 @register_inference_function("openai-gpt5")
        "model_spec": {
            "name": "gpt-5",  # 模型名称
            "api_key": "sk-Vyka3wGWN67eaLBqnGIlu6uFNmSoRoT9gB4MBSxeyDpll3Dw",  # 替换为真实的 OpenAI API Key
            "endpoint": "https://api2.aigcbest.top/v1/chat/completions"  # 可选，默认就是这个
        },
        "payload": {
            "prompt": "你好"  # 用户提示词
        },
        "inference_params": {
            "temperature": 0.7
        }
    }
    
    print("=" * 60)
    print("📤 提交任务到 API Gateway")
    print("=" * 60)
    print(f"URL: {api_gateway_url}/api/v1/tasks_json")
    print(f"API Key: {api_key}")
    print(f"Task Type: {task_request['task_type']}")
    print(f"Model: {task_request['model_spec']['name']}")
    print(f"Prompt: {task_request['payload']['prompt']}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 提交任务
            print("⏳ 发送请求...")
            response = await client.post(
                f"{api_gateway_url}/api/v1/tasks_json",
                json=task_request,
                headers={
                    "Authorization": f"Bearer {api_key}"
                }
            )
            
            print(f"📡 响应状态码: {response.status_code}")
            print()
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                task_id = result.get("task_id")
                status = result.get("status")
                message = result.get("message")
                
                print("✅ 任务提交成功！")
                print(f"   Task ID: {task_id}")
                print(f"   Status: {status}")
                print(f"   Message: {message}")
                print()
                
                # 查询任务状态
                print("=" * 60)
                print("🔍 查询任务状态")
                print("=" * 60)
                
                max_attempts = 30
                for attempt in range(1, max_attempts + 1):
                    print(f"[{attempt}/{max_attempts}] 查询任务状态...")
                    
                    status_response = await client.get(
                        f"{api_gateway_url}/api/v1/tasks/{task_id}",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    
                    if status_response.status_code == 200:
                        task_info = status_response.json()
                        current_status = task_info.get("status")
                        
                        print(f"   当前状态: {current_status}")
                        
                        if current_status == "SUCCESS":
                            print()
                            print("✅ 任务完成！")
                            print("=" * 60)
                            print("📊 任务结果")
                            print("=" * 60)
                            print(f"Task ID: {task_info.get('task_id')}")
                            print(f"Status: {task_info.get('status')}")
                            print(f"Result: {task_info.get('result')}")
                            print(f"Metadata: {task_info.get('metadata')}")
                            print()
                            return task_info
                        
                        elif current_status == "FAILED":
                            print()
                            print("❌ 任务失败！")
                            print(f"Error: {task_info.get('result')}")
                            print()
                            return task_info
                        
                        elif current_status in ["pending", "processing","PROCESSING"]:
                            # 继续等待
                            await asyncio.sleep(2)
                        else:
                            print(f"⚠️  未知状态: {current_status}")
                            await asyncio.sleep(2)
                    else:
                        print(f"❌ 查询失败: {status_response.status_code}")
                        print(f"   {status_response.text}")
                        await asyncio.sleep(2)
                
                print()
                print(f"⏱️  超时：任务在 {max_attempts * 2} 秒内未完成")
                
            else:
                print(f"❌ 任务提交失败！")
                print(f"   状态码: {response.status_code}")
                print(f"   响应: {response.text}")
                
    except httpx.ConnectError:
        print("❌ 连接失败！请确保 API Gateway 正在运行")
        print(f"   URL: {api_gateway_url}")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    print("🚀 AI Router - 任务提交测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    asyncio.run(test_submit_gpt5_task())

