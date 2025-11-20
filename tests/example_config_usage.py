#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: 示例：如何使用 EnvConfig 配置类

这个示例展示了如何使用 core.config 模块中的 EnvConfig 类来：
1. 读取 .env 文件配置
2. 自动监控文件变化并更新配置
3. 使用不同的数据类型获取配置值
"""

import time
from core.config import config, get_config, reload_config


def main():
    print("=" * 60)
    print("EnvConfig 配置类使用示例")
    print("=" * 60)
    
    # 方法 1: 使用全局 config 实例
    print("\n1. 使用全局 config 实例获取配置:")
    print(f"   Redis Host: {config.get('REDIS_HOST', 'localhost')}")
    print(f"   Redis Port: {config.get_int('REDIS_PORT', 6379)}")
    print(f"   Redis DB: {config.get_int('REDIS_DB', 0)}")
    print(f"   Redis Password: {config.get('REDIS_PASSWORD', '')}")
    
    # 方法 2: 使用便捷函数
    print("\n2. 使用便捷函数获取配置:")
    print(f"   RabbitMQ Host: {get_config('RABBITMQ_HOST', 'localhost')}")
    print(f"   RabbitMQ Port: {get_config('RABBITMQ_PORT', '5672')}")
    
    # 方法 3: 获取不同类型的配置
    print("\n3. 获取不同类型的配置值:")
    print(f"   API Gateway Port (int): {config.get_int('API_GATEWAY_PORT', 8000)}")
    print(f"   MinIO Secure (bool): {config.get_bool('MINIO_SECURE', False)}")
    print(f"   Forwarder Workers (int): {config.get_int('FORWARDER_WORKERS', 4)}")
    
    # 方法 4: 字典式访问
    print("\n4. 字典式访问配置:")
    if 'CONSUL_HOST' in config:
        print(f"   Consul Host: {config['CONSUL_HOST']}")
    else:
        print("   Consul Host 未配置")
    
    # 方法 5: 获取所有配置
    print("\n5. 获取所有配置:")
    all_config = config.get_all()
    print(f"   总共有 {len(all_config)} 个配置项")
    
    # 显示配置对象信息
    print(f"\n6. 配置对象信息:")
    print(f"   {config}")
    
    # 演示自动重载功能
    print("\n7. 自动重载演示:")
    print("   配置类会自动监控 .env 文件的变化")
    print("   当文件被修改时，配置会自动更新")
    print("   你可以尝试修改 .env 文件，然后观察配置的变化")
    print("\n   监控中... (按 Ctrl+C 退出)")
    
    try:
        # 持续监控配置变化
        last_mtime = config._last_mtime
        while True:
            time.sleep(2)
            current_mtime = config._last_mtime
            if current_mtime != last_mtime:
                print(f"\n   ✓ 检测到配置文件更新！")
                print(f"   Redis Host: {config.get('REDIS_HOST', 'localhost')}")
                last_mtime = current_mtime
    except KeyboardInterrupt:
        print("\n\n8. 停止监控:")
        config.stop_monitor()
        print("   监控已停止")
    
    print("\n" + "=" * 60)
    print("示例结束")
    print("=" * 60)


if __name__ == "__main__":
    main()

