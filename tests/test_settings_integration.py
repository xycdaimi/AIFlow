"""
测试 Settings 配置类在各个模块中的集成

验证所有模块都正确使用新的 Settings 配置类
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_api_gateway_main_import():
    """测试 API Gateway main.py 导入"""
    print("=" * 60)
    print("测试 1: API Gateway main.py 导入")
    print("=" * 60)
    
    try:
        # 导入 main 模块
        import services.api_gateway.main as main_module
        
        # 检查是否使用了 settings
        import inspect
        source = inspect.getsource(main_module)
        
        if 'from core.config import settings' in source:
            print("✓ main.py 正确导入 settings")
        else:
            print("✗ main.py 未导入 settings")
            return False
        
        if 'settings.api_gateway_host' in source and 'settings.api_gateway_port' in source:
            print("✓ main.py 正确使用 settings 属性")
        else:
            print("✗ main.py 未使用 settings 属性")
            return False
        
        print("✓ API Gateway main.py 集成验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_gateway_routes_import():
    """测试 API Gateway routes.py 导入"""
    print("\n" + "=" * 60)
    print("测试 2: API Gateway routes.py 导入")
    print("=" * 60)
    
    try:
        # 导入 routes 模块
        import services.api_gateway.routes as routes_module
        
        # 检查是否使用了 settings
        import inspect
        source = inspect.getsource(routes_module)
        
        if 'from core.config import settings' in source:
            print("✓ routes.py 正确导入 settings")
        else:
            print("✗ routes.py 未导入 settings")
            return False
        
        if 'settings.minio_bucket_inputs' in source or 'settings.task_ttl' in source:
            print("✓ routes.py 正确使用 settings 属性")
        else:
            print("✗ routes.py 未使用 settings 属性")
            return False
        
        print("✓ API Gateway routes.py 集成验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_minio_client_import():
    """测试 MinIO 客户端导入"""
    print("\n" + "=" * 60)
    print("测试 3: MinIO 客户端导入")
    print("=" * 60)
    
    try:
        # 导入 minio_client 模块
        import core.storage.minio_client as minio_module
        
        # 检查是否使用了 settings
        import inspect
        source = inspect.getsource(minio_module)
        
        if 'from core.config import settings' in source:
            print("✓ minio_client.py 正确导入 settings")
        else:
            print("✗ minio_client.py 未导入 settings")
            return False
        
        if 'settings.minio_endpoint' in source or 'settings.minio_bucket_inputs' in source:
            print("✓ minio_client.py 正确使用 settings 属性")
        else:
            print("✗ minio_client.py 未使用 settings 属性")
            return False
        
        print("✓ MinIO 客户端集成验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_settings_functionality():
    """测试 Settings 类功能"""
    print("\n" + "=" * 60)
    print("测试 4: Settings 类功能")
    print("=" * 60)
    
    try:
        from core.config import settings
        
        # 测试各种配置属性
        print(f"  API Gateway:")
        print(f"    - Host: {settings.api_gateway_host}")
        print(f"    - Port: {settings.api_gateway_port}")
        print(f"    - URL: {settings.api_gateway_url}")
        
        print(f"\n  MinIO:")
        print(f"    - Endpoint: {settings.minio_endpoint}")
        print(f"    - Bucket Inputs: {settings.minio_bucket_inputs}")
        print(f"    - Bucket Outputs: {settings.minio_bucket_outputs}")
        print(f"    - URL: {settings.minio_url}")
        
        print(f"\n  Task:")
        print(f"    - TTL: {settings.task_ttl}s")
        print(f"    - Timeout: {settings.task_timeout}s")
        print(f"    - Max Retries: {settings.task_max_retries}")
        print(f"    - Monitor Interval: {settings.task_monitor_interval}s")
        
        print("\n✓ Settings 类功能验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔧 开始测试 Settings 配置类集成" + "\n")
    
    results = []
    results.append(("API Gateway main.py", test_api_gateway_main_import()))
    results.append(("API Gateway routes.py", test_api_gateway_routes_import()))
    results.append(("MinIO 客户端", test_minio_client_import()))
    results.append(("Settings 类功能", test_settings_functionality()))
    
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
        print("\n🎉 所有集成测试通过！Settings 配置类已成功集成到各个模块！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

