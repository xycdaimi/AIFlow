-- AI Router 数据库初始化脚本
-- 创建日志表

-- 删除已存在的表（如果需要重新创建）
-- DROP TABLE IF EXISTS logs;

-- 创建日志表
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
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_task_id ON logs(task_id);
CREATE INDEX IF NOT EXISTS idx_logs_service_name ON logs(service_name);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_event ON logs(event);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_logs_task_service ON logs(task_id, service_name);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp_level ON logs(timestamp, level);

-- 显示表结构
\d logs

-- 显示索引
\di logs*

COMMENT ON TABLE logs IS 'AI Router 系统日志表';
COMMENT ON COLUMN logs.id IS '日志 ID（自增主键）';
COMMENT ON COLUMN logs.timestamp IS '日志时间戳';
COMMENT ON COLUMN logs.task_id IS '任务 ID';
COMMENT ON COLUMN logs.service_name IS '服务名称';
COMMENT ON COLUMN logs.service_instance IS '服务实例 ID';
COMMENT ON COLUMN logs.level IS '日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）';
COMMENT ON COLUMN logs.event IS '事件标识';
COMMENT ON COLUMN logs.message IS '日志消息';
COMMENT ON COLUMN logs.context IS '额外上下文（JSON 格式）';
COMMENT ON COLUMN logs.created_at IS '记录创建时间';

