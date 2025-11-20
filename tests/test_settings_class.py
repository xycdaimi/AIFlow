"""
测试新的 Settings 配置类

验证 Settings 类提供业务友好的配置访问接口
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_settings_import():
    """测试 Settings 类导入"""
    print("=" * 60)
    print("测试 1: Settings 类导入")
    print("=" * 60)
    
    try:
        from core.config import settings, Settings, get_settings
        print("✓ 成功导入 Settings 相关模块")
        print(f"  - settings 实例: {settings}")
        print(f"  - Settings 类: {Settings}")
        print(f"  - get_settings 函数: {get_settings}")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_config():
    """测试 Redis 配置"""
    print("\n" + "=" * 60)
    print("测试 2: Redis 配置")
    print("=" * 60)
    
    try:
        from core.config import settings
        
        print(f"  Redis 配置:")
        print(f"    - Host: {settings.redis_host}")
        print(f"    - Port: {settings.redis_port} (类型: {type(settings.redis_port).__name__})")
        print(f"    - DB: {settings.redis_db}")
        print(f"    - Password: {'***' if settings.redis_password else '(空)'}")
        print(f"    - URL: {settings.redis_url}")
        
        assert isinstance(settings.redis_port, int), "redis_port 应该是整数"
        assert isinstance(settings.redis_db, int), "redis_db 应该是整数"
        assert settings.redis_url.startswith('redis://'), "redis_url 应该以 redis:// 开头"
        
        print("✓ Redis 配置验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rabbitmq_config():
    """测试 RabbitMQ 配置"""
    print("\n" + "=" * 60)
    print("测试 3: RabbitMQ 配置")
    print("=" * 60)
    
    try:
        from core.config import settings
        
        print(f"  RabbitMQ 配置:")
        print(f"    - Host: {settings.rabbitmq_host}")
        print(f"    - Port: {settings.rabbitmq_port}")
        print(f"    - User: {settings.rabbitmq_user}")
        print(f"    - Password: {'***' if settings.rabbitmq_password else '(空)'}")
        print(f"    - VHost: {settings.rabbitmq_vhost}")
        print(f"    - URL: {settings.rabbitmq_url}")
        
        assert isinstance(settings.rabbitmq_port, int), "rabbitmq_port 应该是整数"
        assert settings.rabbitmq_url.startswith('amqp://'), "rabbitmq_url 应该以 amqp:// 开头"
        
        print("✓ RabbitMQ 配置验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_postgres_config():
    """测试 PostgreSQL 配置"""
    print("\n" + "=" * 60)
    print("测试 4: PostgreSQL 配置")
    print("=" * 60)
    
    try:
        from core.config import settings
        
        print(f"  PostgreSQL 配置:")
        print(f"    - Host: {settings.postgres_host}")
        print(f"    - Port: {settings.postgres_port}")
        print(f"    - User: {settings.postgres_user}")
        print(f"    - Database: {settings.postgres_db}")
        print(f"    - URL: {settings.postgres_url}")
        print(f"    - Async URL: {settings.postgres_async_url}")
        
        assert isinstance(settings.postgres_port, int), "postgres_port 应该是整数"
        assert settings.postgres_url.startswith('postgresql://'), "postgres_url 应该以 postgresql:// 开头"
        assert settings.postgres_async_url.startswith('postgresql+asyncpg://'), "postgres_async_url 应该以 postgresql+asyncpg:// 开头"
        
        print("✓ PostgreSQL 配置验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_minio_config():
    """测试 MinIO 配置"""
    print("\n" + "=" * 60)
    print("测试 5: MinIO 配置")
    print("=" * 60)
    
    try:
        from core.config import settings
        
        print(f"  MinIO 配置:")
        print(f"    - Endpoint: {settings.minio_endpoint}")
        print(f"    - Secure: {settings.minio_secure}")
        print(f"    - Bucket Inputs: {settings.minio_bucket_inputs}")
        print(f"    - Bucket Outputs: {settings.minio_bucket_outputs}")
        print(f"    - URL: {settings.minio_url}")
        
        assert isinstance(settings.minio_secure, bool), "minio_secure 应该是布尔值"
        
        print("✓ MinIO 配置验证通过")
        return True
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔧 开始测试 Settings 配置类" + "\n")
    
    results = []
    results.append(("Settings 类导入", test_settings_import()))
    results.append(("Redis 配置", test_redis_config()))
    results.append(("RabbitMQ 配置", test_rabbitmq_config()))
    results.append(("PostgreSQL 配置", test_postgres_config()))
    results.append(("MinIO 配置", test_minio_config()))
    
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
        print("\n🎉 所有测试通过！Settings 类工作正常！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

