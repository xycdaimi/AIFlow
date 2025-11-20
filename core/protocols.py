"""Data protocols and schemas for AI Route platform."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ModelSpec(BaseModel):
    """Model specification."""
    name: str = Field(..., description="Model name")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    api_key: Optional[str] = Field(None, description="API key for authentication")
    version: Optional[str] = Field(None, description="Model version")


class CallbackConfig(BaseModel):
    """Callback configuration."""
    url: str = Field(..., description="Callback URL")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers for callback")


class TaskRequest(BaseModel):
    """Task request schema."""
    task_type: str = Field(..., description="Task type identifier, e.g., 'text:generation', 'image:classification'")
    model_spec: ModelSpec = Field(..., description="Model specification")
    payload: Dict[str, Any] = Field(..., description="Task input data")
    inference_params: Optional[Dict[str, Any]] = Field(None, description="Model inference parameters")
    callback: Optional[CallbackConfig] = Field(None, description="Callback configuration")


class TaskResponse(BaseModel):
    """Task response schema."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Task status")
    message: str = Field(default="Task created successfully", description="Response message")


class TaskDetail(BaseModel):
    """Task detail schema."""
    task_id: str
    task_type: str
    model_spec: ModelSpec
    payload: Dict[str, Any]
    inference_params: Optional[Dict[str, Any]] = None
    callback: Optional[CallbackConfig] = None
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retries allowed")
    last_error: Optional[str] = Field(None, description="Last error message from failed attempt")


class TaskMessage(BaseModel):
    """Task message for RabbitMQ."""
    task_id: str
    task_type: str
    model_spec: ModelSpec
    payload: Dict[str, Any]
    inference_params: Optional[Dict[str, Any]] = None
    callback: Optional[CallbackConfig] = None


class LogMessage(BaseModel):
    """Structured log message schema."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="ISO 8601 UTC timestamp")
    task_id: str = Field(..., description="Associated task ID")
    service_name: str = Field(..., description="Service name that generated the log")
    service_instance: str = Field(..., description="Service instance identifier")
    level: LogLevel = Field(..., description="Log level")
    event: str = Field(..., description="Machine-readable event identifier")
    message: str = Field(..., description="Human-readable message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ModelServiceInfo(BaseModel):
    """Model service information for service discovery."""
    service_id: str
    service_name: str
    address: str
    port: int
    tags: List[str] = []
    meta: Dict[str, str] = {}
    
    @property
    def url(self) -> str:
        """Get service URL."""
        return f"http://{self.address}:{self.port}"


class ModelInferenceRequest(BaseModel):
    """Model inference request schema."""
    task_id: str
    payload: Dict[str, Any]
    inference_params: Optional[Dict[str, Any]] = None


class ModelInferenceResponse(BaseModel):
    """Model inference response schema."""
    task_id: str
    result: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


def generate_task_id() -> str:
    """Generate a unique task ID."""
    return str(uuid.uuid4())

