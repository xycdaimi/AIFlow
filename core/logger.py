"""Structured logging utilities for AI Route platform."""

import structlog
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from .protocols import LogLevel, LogMessage


def setup_logging(service_name: str, service_instance: str, log_level: str = "INFO"):
    """
    Setup structured logging for a service.
    
    Args:
        service_name: Name of the service
        service_instance: Instance identifier of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class TaskLogger:
    """Logger for task-related events."""
    
    def __init__(self, service_name: str, service_instance: str):
        """
        Initialize task logger.
        
        Args:
            service_name: Name of the service
            service_instance: Instance identifier of the service
        """
        self.service_name = service_name
        self.service_instance = service_instance
        self.logger = structlog.get_logger()
    
    def create_log_message(
        self,
        task_id: str,
        level: LogLevel,
        event: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LogMessage:
        """
        Create a structured log message.
        
        Args:
            task_id: Task identifier
            level: Log level
            event: Event identifier
            message: Human-readable message
            context: Additional context information
            
        Returns:
            LogMessage instance
        """
        return LogMessage(
            timestamp=datetime.now(timezone.utc),
            task_id=task_id,
            service_name=self.service_name,
            service_instance=self.service_instance,
            level=level,
            event=event,
            message=message,
            context=context or {}
        )
    
    def log(
        self,
        task_id: str,
        level: LogLevel,
        event: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log a message locally.
        
        Args:
            task_id: Task identifier
            level: Log level
            event: Event identifier
            message: Human-readable message
            context: Additional context information
        """
        log_data = {
            "task_id": task_id,
            "service_name": self.service_name,
            "service_instance": self.service_instance,
            "event": event,
            "message": message,
        }
        
        if context:
            log_data["context"] = context
        
        log_method = getattr(self.logger, level.lower())
        log_method(**log_data)
    
    def debug(self, task_id: str, event: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self.log(task_id, LogLevel.DEBUG, event, message, context)
    
    def info(self, task_id: str, event: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self.log(task_id, LogLevel.INFO, event, message, context)
    
    def warning(self, task_id: str, event: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self.log(task_id, LogLevel.WARNING, event, message, context)
    
    def error(self, task_id: str, event: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Log error message."""
        self.log(task_id, LogLevel.ERROR, event, message, context)

