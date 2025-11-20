#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: 测试 Consul 连接
"""

import asyncio
from core.utils import ConsulClient

async def test_consul():
    print("Testing Consul connection...")
    
    client = ConsulClient()
    
    try:
        await client.connect()
        print("✓ Consul connection successful")
        
        # 测试服务注册
        await client.register_service(
            service_name="test-service",
            service_id="test-001",
            host="127.0.0.1",
            port=9999,
            tags=["test"],
            meta={"version": "1.0.0"}
        )
        print("✓ Service registration successful")
        
        # 测试服务发现
        services = await client.discover_service("test-service")
        print(f"✓ Service discovery successful: {services}")
        
        # 注销服务
        await client.deregister_service("test-001")
        print("✓ Service deregistration successful")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Consul test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_consul())

