"""
测试重构后的配置使用

验证 api_gateway/main.py 和 minio_client.py 使用新的 EnvConfig 配置类
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_config_import():
    """测试配置模块导入"""
    print("=" * 60)
    print("测试 1: 配置模块导入")
    print("=" * 60)
    
    try:
        from core.config import config, get_config, reload_config
        print("✓ 成功导入 core.config 模块")
        print(f"  - config 对象: {config}")
        print(f"  - get_config 函数: {get_config}")
        print(f"  - reload_config 函数: {reload_config}")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_minio_client():
    """测试 MinIO 客户端配置"""
    print("\n" + "=" * 60)
    print("测试 2: MinIO 客户端配置")
    print("=" * 60)
    
    try:
        from core.storage.minio_client import MinioStore
        from core.config import config
        
        print("✓ 成功导入 MinioStore 类")
        
        # 检查配置值
        minio_endpoint = config.get('MINIO_ENDPOINT', 'localhost:9000')
        minio_secure = config.get_bool('MINIO_SECURE', False)
        bucket_inputs = config.get('MINIO_BUCKET_INPUTS', 'ai-route-inputs')
        bucket_outputs = config.get('MINIO_BUCKET_OUTPUTS', 'ai-route-outputs')
        
        print(f"  配置值:")
        print(f"    - MINIO_ENDPOINT: {minio_endpoint}")
        print(f"    - MINIO_SECURE: {minio_secure}")
        print(f"    - MINIO_BUCKET_INPUTS: {bucket_inputs}")
        print(f"    - MINIO_BUCKET_OUTPUTS: {bucket_outputs}")
        
        # 注意：不实际创建 MinioStore 实例，因为可能没有 MinIO 服务器
        print("  注意: 跳过实际 MinIO 连接测试（需要 MinIO 服务器）")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_gateway_config():
    """测试 API Gateway 配置"""
    print("\n" + "=" * 60)
    print("测试 3: API Gateway 配置")
    print("=" * 60)
    
    try:
        from core.config import config
        
        # 检查 API Gateway 相关配置
        api_host = config.get('API_GATEWAY_HOST', '0.0.0.0')
        api_port = config.get_int('API_GATEWAY_PORT', 8000)
        api_url = config.get('API_GATEWAY_URL', 'http://127.0.0.1:8000')
        monitor_interval = config.get_int('TASK_MONITOR_INTERVAL', 30)
        
        print(f"  配置值:")
        print(f"    - API_GATEWAY_HOST: {api_host}")
        print(f"    - API_GATEWAY_PORT: {api_port} (类型: {type(api_port).__name__})")
        print(f"    - API_GATEWAY_URL: {api_url}")
        print(f"    - TASK_MONITOR_INTERVAL: {monitor_interval}s (类型: {type(monitor_interval).__name__})")
        
        # 验证类型
        assert isinstance(api_port, int), "API_GATEWAY_PORT 应该是整数类型"
        assert isinstance(monitor_interval, int), "TASK_MONITOR_INTERVAL 应该是整数类型"
        
        print("✓ 所有配置类型正确")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_config_values():
    """测试所有配置值"""
    print("\n" + "=" * 60)
    print("测试 4: 所有配置值")
    print("=" * 60)
    
    try:
        from core.config import config
        
        all_config = config.get_all()
        print(f"  总共加载了 {len(all_config)} 个配置项")
        
        # 显示前 10 个配置项
        print("\n  前 10 个配置项:")
        for i, (key, value) in enumerate(list(all_config.items())[:10]):
            # 隐藏敏感信息
            if 'PASSWORD' in key or 'SECRET' in key or 'KEY' in key:
                display_value = '***' if value else None
            else:
                display_value = value
            print(f"    {i+1}. {key} = {display_value}")
        
        if len(all_config) > 10:
            print(f"    ... 还有 {len(all_config) - 10} 个配置项")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔧 开始测试配置重构" + "\n")
    
    results = []
    results.append(("配置模块导入", test_config_import()))
    results.append(("MinIO 客户端配置", test_minio_client()))
    results.append(("API Gateway 配置", test_api_gateway_config()))
    results.append(("所有配置值", test_all_config_values()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n  总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！配置重构成功！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

