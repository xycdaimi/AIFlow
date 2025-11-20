"""初始化 PostgreSQL 数据库表结构"""

import asyncio
import asyncpg
from pathlib import Path
from core.config import settings

async def init_database():
    """初始化数据库表结构"""
    print("=" * 60)
    print("AI Router - Database Initialization")
    print("=" * 60)
    print()
    
    # 连接信息
    print(f"Connecting to PostgreSQL...")
    print(f"  Host: {settings.postgres_host}")
    print(f"  Port: {settings.postgres_port}")
    print(f"  Database: {settings.postgres_db}")
    print(f"  User: {settings.postgres_user}")
    print()
    
    try:
        # 连接到数据库
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db
        )
        print("✓ Connected to PostgreSQL")
        print()
        
        # 读取 SQL 脚本
        sql_file = Path(__file__).parent / "init_database.sql"
        if not sql_file.exists():
            print(f"❌ SQL file not found: {sql_file}")
            return
        
        sql_content = sql_file.read_text(encoding='utf-8')
        
        # 分割 SQL 语句（按分号分割，忽略注释）
        statements = []
        for line in sql_content.split('\n'):
            line = line.strip()
            # 跳过注释和空行
            if line.startswith('--') or not line:
                continue
            # 跳过 psql 特殊命令
            if line.startswith('\\'):
                continue
            statements.append(line)
        
        sql = ' '.join(statements)
        
        # 执行 SQL 语句
        print("Executing SQL statements...")
        
        # 创建表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                task_id VARCHAR(255),
                service_name VARCHAR(100) NOT NULL,
                service_instance VARCHAR(100),
                level VARCHAR(20) NOT NULL,
                event VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                context JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ Created table: logs")
        
        # 创建索引
        indexes = [
            ("idx_logs_timestamp", "timestamp"),
            ("idx_logs_task_id", "task_id"),
            ("idx_logs_service_name", "service_name"),
            ("idx_logs_level", "level"),
            ("idx_logs_event", "event"),
            ("idx_logs_created_at", "created_at"),
        ]
        
        for idx_name, column in indexes:
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name} ON logs({column})
            """)
            print(f"✓ Created index: {idx_name}")
        
        # 创建复合索引
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_task_service ON logs(task_id, service_name)
        """)
        print("✓ Created index: idx_logs_task_service")
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp_level ON logs(timestamp, level)
        """)
        print("✓ Created index: idx_logs_timestamp_level")
        
        print()
        
        # 查询表结构
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'logs'
            ORDER BY ordinal_position
        """)
        
        print("Table structure:")
        print("-" * 60)
        print(f"{'Column':<20} {'Type':<25} {'Nullable':<10}")
        print("-" * 60)
        for col in columns:
            print(f"{col['column_name']:<20} {col['data_type']:<25} {col['is_nullable']:<10}")
        print("-" * 60)
        print()
        
        # 查询索引
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'logs'
            ORDER BY indexname
        """)
        
        print(f"Indexes ({len(indexes)}):")
        print("-" * 60)
        for idx in indexes:
            print(f"  - {idx['indexname']}")
        print("-" * 60)
        print()
        
        # 关闭连接
        await conn.close()
        
        print("=" * 60)
        print("✓ Database initialization completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(init_database())

