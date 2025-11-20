import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import dotenv_values


class EnvConfig:
    """
    公共配置类，用于读取和自动更新 .env 文件配置

    特性:
    1. 自动加载 .env 文件
    2. 监控文件变化并自动更新配置
    3. 线程安全的配置访问
    4. 支持类型转换和默认值

    使用示例:
        config = EnvConfig()
        redis_host = config.get('REDIS_HOST', 'localhost')
        redis_port = config.get_int('REDIS_PORT', 6379)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, env_file: str = '.env', auto_reload: bool = True, check_interval: int = 5):
        """单例模式，确保全局只有一个配置实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, env_file: str = '.env', auto_reload: bool = True, check_interval: int = 5):
        """
        初始化配置类

        Args:
            env_file: .env 文件路径，默认为项目根目录下的 .env
            auto_reload: 是否自动重载配置，默认为 True
            check_interval: 检查文件变化的间隔时间（秒），默认为 5 秒
        """
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        self.env_file = Path(env_file)
        self.auto_reload = auto_reload
        self.check_interval = check_interval

        # 配置数据和文件修改时间
        self._config: Dict[str, Optional[str]] = {}
        self._last_mtime: Optional[float] = None
        self._config_lock = threading.RLock()

        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()

        # 加载初始配置
        self._load_config()

        # 启动自动重载监控
        if self.auto_reload:
            self._start_monitor()

        self._initialized = True

    def _load_config(self) -> None:
        """加载或重载 .env 文件配置"""
        if not self.env_file.exists():
            print(f"警告: 配置文件 {self.env_file} 不存在")
            return

        try:
            # 获取文件修改时间
            current_mtime = self.env_file.stat().st_mtime

            # 如果文件没有变化，跳过加载
            if self._last_mtime is not None and current_mtime == self._last_mtime:
                return

            # 读取配置
            new_config = dotenv_values(self.env_file)

            # 线程安全地更新配置
            with self._config_lock:
                self._config = new_config
                self._last_mtime = current_mtime

            print(f"配置已加载/更新: {self.env_file} (修改时间: {time.ctime(current_mtime)})")

        except Exception as e:
            print(f"加载配置文件失败: {e}")

    def _monitor_file_changes(self) -> None:
        """监控文件变化的后台线程"""
        while not self._stop_monitor.is_set():
            try:
                self._load_config()
            except Exception as e:
                print(f"监控配置文件时出错: {e}")

            # 等待指定的检查间隔
            self._stop_monitor.wait(self.check_interval)

    def _start_monitor(self) -> None:
        """启动文件监控线程"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_monitor.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_file_changes,
                daemon=True,
                name="EnvConfigMonitor"
            )
            self._monitor_thread.start()
            print(f"配置文件监控已启动，检查间隔: {self.check_interval} 秒")

    def stop_monitor(self) -> None:
        """停止文件监控线程"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop_monitor.set()
            self._monitor_thread.join(timeout=self.check_interval + 1)
            print("配置文件监控已停止")

    def reload(self) -> None:
        """手动重载配置"""
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值或默认值
        """
        with self._config_lock:
            return self._config.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """
        获取整数类型的配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            整数配置值或默认值
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            print(f"警告: 配置 {key}={value} 无法转换为整数，使用默认值 {default}")
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        获取浮点数类型的配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            浮点数配置值或默认值
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            print(f"警告: 配置 {key}={value} 无法转换为浮点数，使用默认值 {default}")
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        获取布尔类型的配置值

        支持的真值: true, yes, 1, on (不区分大小写)
        支持的假值: false, no, 0, off (不区分大小写)

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            布尔配置值或默认值
        """
        value = self.get(key)
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        value_lower = str(value).lower().strip()
        if value_lower in ('true', 'yes', '1', 'on'):
            return True
        elif value_lower in ('false', 'no', '0', 'off'):
            return False
        else:
            print(f"警告: 配置 {key}={value} 无法转换为布尔值，使用默认值 {default}")
            return default

    def get_list(self, key: str, separator: str = ',', default: Optional[list] = None) -> list:
        """
        获取列表类型的配置值

        Args:
            key: 配置键名
            separator: 分隔符，默认为逗号
            default: 默认值

        Returns:
            列表配置值或默认值
        """
        value = self.get(key)
        if value is None:
            return default or []

        try:
            return [item.strip() for item in str(value).split(separator) if item.strip()]
        except Exception as e:
            print(f"警告: 配置 {key}={value} 无法转换为列表，使用默认值 {default}")
            return default or []

    def get_all(self) -> Dict[str, Optional[str]]:
        """
        获取所有配置

        Returns:
            配置字典的副本
        """
        with self._config_lock:
            return self._config.copy()

    def __getitem__(self, key: str) -> Any:
        """支持字典式访问: config['KEY']"""
        value = self.get(key)
        if value is None:
            raise KeyError(f"配置键 '{key}' 不存在")
        return value

    def __contains__(self, key: str) -> bool:
        """支持 in 操作符: 'KEY' in config"""
        with self._config_lock:
            return key in self._config

    def __repr__(self) -> str:
        """字符串表示"""
        with self._config_lock:
            return f"EnvConfig(file={self.env_file}, keys={len(self._config)})"


# 全局配置实例
config = EnvConfig()


# 便捷函数
def get_config(key: str, default: Any = None, value_type: str = 'str') -> Any:
    """
    获取配置值的便捷函数
    
    Args:
        key: 配置键名
        default: 默认值
        value_type: 值类型，支持 'str', 'int', 'float', 'bool', 'list'
    
    Returns:
        根据指定类型转换后的配置值或默认值
    """
    if value_type == 'int':
        return config.get_int(key, default if default is not None else 0)
    elif value_type == 'float':
        return config.get_float(key, default if default is not None else 0.0)
    elif value_type == 'bool':
        return config.get_bool(key, default if default is not None else False)
    elif value_type == 'list':
        return config.get_list(key, default=default)
    else:  # 'str' or default
        return config.get(key, default)


def reload_config() -> None:
    """重载配置的便捷函数"""
    config.reload()


class Settings:
    """
    应用配置类，提供业务友好的配置访问接口

    这个类从 EnvConfig 读取原始配置，并提供：
    1. 类型安全的配置属性
    2. 解析后的复合配置（如 URL、连接字符串等）
    3. 配置验证和默认值
    4. 业务逻辑相关的配置组织

    使用示例:
        settings = Settings()
        redis_url = settings.redis_url
        rabbitmq_url = settings.rabbitmq_url
    """

    def __init__(self, env_config: EnvConfig = None):
        """
        初始化配置类

        Args:
            env_config: EnvConfig 实例，默认使用全局 config 实例
        """
        self._config = env_config or config

    # ==================== Redis 配置 ====================

    @property
    def redis_host(self) -> str:
        """Redis 主机地址"""
        return self._config.get('REDIS_HOST', 'localhost')

    @property
    def redis_port(self) -> int:
        """Redis 端口"""
        return self._config.get_int('REDIS_PORT', 6379)

    @property
    def redis_db(self) -> int:
        """Redis 数据库编号"""
        return self._config.get_int('REDIS_DB', 0)

    @property
    def redis_password(self) -> str:
        """Redis 密码"""
        return self._config.get('REDIS_PASSWORD', '')

    @property
    def redis_url(self) -> str:
        """Redis 连接 URL"""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ==================== RabbitMQ 配置 ====================

    @property
    def rabbitmq_host(self) -> str:
        """RabbitMQ 主机地址"""
        return self._config.get('RABBITMQ_HOST', 'localhost')

    @property
    def rabbitmq_port(self) -> int:
        """RabbitMQ 端口"""
        return self._config.get_int('RABBITMQ_PORT', 5672)

    @property
    def rabbitmq_user(self) -> str:
        """RabbitMQ 用户名"""
        return self._config.get('RABBITMQ_USER', 'guest')

    @property
    def rabbitmq_password(self) -> str:
        """RabbitMQ 密码"""
        return self._config.get('RABBITMQ_PASSWORD', 'guest')

    @property
    def rabbitmq_vhost(self) -> str:
        """RabbitMQ 虚拟主机"""
        return self._config.get('RABBITMQ_VHOST', '/')

    @property
    def rabbitmq_url(self) -> str:
        """RabbitMQ 连接 URL (AMQP)"""
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}{self.rabbitmq_vhost}"

    # ==================== PostgreSQL 配置 ====================

    @property
    def postgres_host(self) -> str:
        """PostgreSQL 主机地址"""
        return self._config.get('POSTGRES_HOST', 'localhost')

    @property
    def postgres_port(self) -> int:
        """PostgreSQL 端口"""
        return self._config.get_int('POSTGRES_PORT', 5432)

    @property
    def postgres_user(self) -> str:
        """PostgreSQL 用户名"""
        return self._config.get('POSTGRES_USER', 'postgres')

    @property
    def postgres_password(self) -> str:
        """PostgreSQL 密码"""
        return self._config.get('POSTGRES_PASSWORD', '')

    @property
    def postgres_db(self) -> str:
        """PostgreSQL 数据库名"""
        return self._config.get('POSTGRES_DB', 'postgres')

    @property
    def postgres_url(self) -> str:
        """PostgreSQL 连接 URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postgres_async_url(self) -> str:
        """PostgreSQL 异步连接 URL (asyncpg)"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # ==================== Consul 配置 ====================

    @property
    def consul_host(self) -> str:
        """Consul 主机地址"""
        return self._config.get('CONSUL_HOST', 'localhost')

    @property
    def consul_port(self) -> int:
        """Consul 端口"""
        return self._config.get_int('CONSUL_PORT', 8500)

    @property
    def consul_url(self) -> str:
        """Consul HTTP API URL"""
        return f"http://{self.consul_host}:{self.consul_port}"

    # ==================== API Gateway 配置 ====================

    @property
    def api_gateway_host(self) -> str:
        """API Gateway 主机地址"""
        return self._config.get('API_GATEWAY_HOST', '0.0.0.0')

    @property
    def api_gateway_port(self) -> int:
        """API Gateway 端口"""
        return self._config.get_int('API_GATEWAY_PORT', 8000)

    @property
    def api_gateway_url(self) -> str:
        """API Gateway 完整 URL"""
        return self._config.get('API_GATEWAY_URL', f'http://127.0.0.1:{self.api_gateway_port}')

    @property
    def api_gateway_internal_key(self) -> str:
        """API Gateway 内部接口访问密钥"""
        return self._config.get('API_GATEWAY_INTERNAL_KEY', 'internal-key')

    @property
    def api_gateway_api_keys(self) -> list:
        """API Gateway 允许的 API Keys 列表"""
        keys_str = self._config.get('API_GATEWAY_API_KEYS', '')
        if not keys_str:
            return []
        return [key.strip() for key in keys_str.split(',') if key.strip()]

    # ==================== Task Scheduler 配置 ====================

    @property
    def scheduler_instance_id(self) -> str:
        """Task Scheduler 实例 ID"""
        return self._config.get('SCHEDULER_INSTANCE_ID', 'scheduler-001')
    
    @property
    def scheduler_task_max_count(self) -> int:
        """任务最大等待数量"""
        return self._config.get_int('SCHEDULER_MAX_PENDING_TASKS', 2)
    
    @property
    def scheduler_retry_delay(self) -> int:
        """任务重试延迟时间（秒）"""
        return self._config.get_int('SCHEDULER_RETRY_DELAY', 5)

    # ==================== Model Forwarder 配置 ====================
    @property
    def forwarder_instance_id(self) -> str:
        """Model Forwarder 实例 ID"""
        return self._config.get('FORWARDER_INSTANCE_ID', 'forwarder-001')

    @property
    def forwarder_service_host(self) -> str:
        """Model Forwarder 主机地址"""
        return self._config.get('FORWARDER_SERVICE_HOST', '0.0.0.0')

    @property
    def forwarder_service_port(self) -> int:
        """Model Forwarder 端口"""
        return self._config.get_int('FORWARDER_SERVICE_PORT', 8001)

    @property
    def forwarder_service_url(self) -> str:
        """Model Forwarder 完整 URL"""
        return self._config.get('FORWARDER_SERVICE_URL', f'http://127.0.0.1:{self.forwarder_service_port}')

    # ==================== Log Service 配置 ====================

    @property
    def log_service_host(self) -> str:
        """Log Service 主机地址"""
        return self._config.get('LOG_SERVICE_HOST', '0.0.0.0')

    @property
    def log_service_port(self) -> int:
        """Log Service 端口"""
        return self._config.get_int('LOG_SERVICE_PORT', 8002)

    @property
    def log_service_url(self) -> str:
        """Log Service 完整 URL"""
        return self._config.get('LOG_SERVICE_URL', f'http://127.0.0.1:{self.log_service_port}')

    @property
    def log_batch_size(self) -> int:
        """日志批处理大小"""
        return self._config.get_int('LOG_BATCH_SIZE', 100)

    @property
    def log_batch_timeout(self) -> int:
        """日志批处理超时时间（秒）"""
        return self._config.get_int('LOG_BATCH_TIMEOUT', 5)

    # ==================== Task 配置 ====================

    @property
    def task_ttl(self) -> int:
        """任务 TTL（秒）"""
        return self._config.get_int('TASK_TTL', 86400)

    @property
    def task_timeout(self) -> int:
        """任务处理超时时间（秒）"""
        return self._config.get_int('TASK_TIMEOUT', 300)

    @property
    def task_max_retries(self) -> int:
        """任务最大重试次数"""
        return self._config.get_int('TASK_MAX_RETRIES', 3)

    @property
    def task_max_wait_time(self) -> int:
        """任务最大等待时间（秒）"""
        return self._config.get_int('TASK_MAX_WAIT_TIME', 120)

    @property
    def task_monitor_interval(self) -> int:
        """任务监控检查间隔（秒）"""
        return self._config.get_int('TASK_MONITOR_INTERVAL', 30)

    # ==================== Shared Memory 配置 ====================

    @property
    def shared_memory_enabled(self) -> bool:
        """是否启用共享内存"""
        return self._config.get_bool('SHARED_MEMORY_ENABLED', True)

    @property
    def shared_memory_threshold(self) -> int:
        """共享内存阈值（字节）"""
        return self._config.get_int('SHARED_MEMORY_THRESHOLD', 10240)

    @property
    def shared_memory_cleanup_interval(self) -> int:
        """共享内存清理间隔（秒）"""
        return self._config.get_int('SHARED_MEMORY_CLEANUP_INTERVAL', 300)

    @property
    def shared_memory_max_age(self) -> int:
        """共享内存最大存活时间（秒）"""
        return self._config.get_int('SHARED_MEMORY_MAX_AGE', 3600)

    # ==================== Media Processing 配置 ====================

    @property
    def media_max_download_size(self) -> int:
        """媒体文件最大下载大小（字节）"""
        return self._config.get_int('MEDIA_MAX_DOWNLOAD_SIZE', 104857600)

    @property
    def media_download_timeout(self) -> int:
        """媒体文件下载超时时间（秒）"""
        return self._config.get_int('MEDIA_DOWNLOAD_TIMEOUT', 60)

    @property
    def media_max_file_size(self) -> int:
        """媒体文件最大大小（字节）"""
        return self._config.get_int('MEDIA_MAX_FILE_SIZE', 104857600)

    # ==================== MinIO 配置 ====================

    @property
    def minio_endpoint(self) -> str:
        """MinIO 端点地址"""
        return self._config.get('MINIO_ENDPOINT', 'localhost:9000')

    @property
    def minio_access_key(self) -> str:
        """MinIO 访问密钥"""
        return self._config.get('MINIO_ACCESS_KEY', 'minioadmin')

    @property
    def minio_secret_key(self) -> str:
        """MinIO 密钥"""
        return self._config.get('MINIO_SECRET_KEY', 'minioadmin')

    @property
    def minio_secure(self) -> bool:
        """MinIO 是否使用 HTTPS"""
        return self._config.get_bool('MINIO_SECURE', False)

    @property
    def minio_bucket_inputs(self) -> str:
        """MinIO 输入文件桶名"""
        return self._config.get('MINIO_BUCKET_INPUTS', 'ai-route-inputs')

    @property
    def minio_bucket_outputs(self) -> str:
        """MinIO 输出文件桶名"""
        return self._config.get('MINIO_BUCKET_OUTPUTS', 'ai-route-outputs')

    @property
    def minio_url(self) -> str:
        """MinIO HTTP URL"""
        scheme = "https" if self.minio_secure else "http"
        return f"{scheme}://{self.minio_endpoint}"

    # ==================== 工具方法 ====================

    def get_raw(self, key: str, default: Any = None) -> Any:
        """获取原始配置值"""
        return self._config.get(key, default)

    def reload(self) -> None:
        """重载配置"""
        self._config.reload()

    def __repr__(self) -> str:
        """字符串表示"""
        return f"Settings(config={self._config})"


# 全局 Settings 实例
settings = Settings()


# 便捷函数
def get_settings() -> Settings:
    """获取全局 Settings 实例"""
    return settings
