"""
NullForge API Schemas
=====================
Pydantic models for API request/response validation.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a synthesis task."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubtaskStatus(str, Enum):
    """Status of individual subtasks."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProviderType(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    VENICE = "venice"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"
    TOGETHER = "together"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    provider: ProviderType = Field(
        default=ProviderType.VENICE,
        description="The LLM provider to use"
    )
    model: str = Field(
        default="llama-3.1-405b",
        description="Model identifier"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key (uses environment variable if not provided)"
    )
    api_base: Optional[str] = Field(
        default=None,
        description="Custom API base URL"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=4096,
        ge=256,
        le=32768,
        description="Maximum tokens in response"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider": "venice",
                "model": "llama-3.1-405b",
                "temperature": 0.7,
                "max_tokens": 4096
            }
        }


class ToolConfig(BaseModel):
    """Tool configuration."""
    enable_shell: bool = Field(
        default=True,
        description="Enable shell command execution"
    )
    enable_file_ops: bool = Field(
        default=True,
        description="Enable file read/write operations"
    )
    enable_web_search: bool = Field(
        default=False,
        description="Enable web search capability"
    )
    enable_git: bool = Field(
        default=True,
        description="Enable git operations"
    )
    workspace: str = Field(
        default="./workspace",
        description="Working directory for file operations"
    )
    allowed_paths: List[str] = Field(
        default_factory=list,
        description="Allowed paths for file operations (empty = workspace only)"
    )
    blocked_commands: List[str] = Field(
        default_factory=lambda: ["rm -rf /", "sudo rm", "mkfs", "> /dev/"],
        description="Blocked shell commands"
    )


class SynthesisRequest(BaseModel):
    """Request to synthesize code from natural language."""
    goal: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Natural language description of the task"
    )
    provider_config: Optional[ProviderConfig] = Field(
        default=None,
        description="LLM provider configuration"
    )
    tool_config: Optional[ToolConfig] = Field(
        default=None,
        description="Tool configuration"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for the synthesis"
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for status updates"
    )
    async_mode: bool = Field(
        default=False,
        description="Run synthesis asynchronously"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "goal": "Build a REST API for a todo application with user authentication using JWT, CRUD operations, and SQLite database",
                "provider_config": {
                    "provider": "venice",
                    "model": "llama-3.1-405b",
                    "temperature": 0.7
                },
                "tool_config": {
                    "enable_shell": True,
                    "enable_file_ops": True,
                    "workspace": "./my_project"
                },
                "async_mode": False
            }
        }


class Subtask(BaseModel):
    """A subtask in the execution plan."""
    id: str = Field(..., description="Unique subtask identifier")
    title: str = Field(..., description="Subtask title")
    description: str = Field(..., description="Detailed description")
    status: SubtaskStatus = Field(
        default=SubtaskStatus.PENDING,
        description="Current status"
    )
    output: Optional[str] = Field(
        default=None,
        description="Output/result of the subtask"
    )
    files_created: List[str] = Field(
        default_factory=list,
        description="Files created by this subtask"
    )
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error: Optional[str] = Field(default=None)


class PlanResponse(BaseModel):
    """Execution plan for a synthesis task."""
    task_id: str = Field(..., description="Task identifier")
    goal: str = Field(..., description="Original goal")
    subtasks: List[Subtask] = Field(..., description="List of subtasks")
    total_steps: int = Field(..., description="Total number of steps")
    estimated_time_seconds: Optional[int] = Field(
        default=None,
        description="Estimated completion time"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FileOutput(BaseModel):
    """Generated file output."""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    language: Optional[str] = Field(
        default=None,
        description="Programming language"
    )
    size_bytes: int = Field(..., description="File size in bytes")
    is_new: bool = Field(default=True, description="Whether file is newly created")
    checksum: Optional[str] = Field(default=None, description="SHA256 checksum")


class TokenUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    estimated_cost_usd: Optional[float] = Field(default=None)


class SynthesisResponse(BaseModel):
    """Response from a synthesis operation."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    goal: str = Field(..., description="Original goal")
    plan: Optional[PlanResponse] = Field(
        default=None,
        description="Execution plan"
    )
    files: List[FileOutput] = Field(
        default_factory=list,
        description="Generated files"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Summary of accomplishments"
    )
    token_usage: Optional[TokenUsage] = Field(
        default=None,
        description="Token usage statistics"
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Total execution time"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "synth_abc123",
                "status": "completed",
                "goal": "Build a REST API...",
                "files": [
                    {
                        "path": "main.py",
                        "content": "from fastapi import FastAPI...",
                        "language": "python",
                        "size_bytes": 1234,
                        "is_new": True
                    }
                ],
                "summary": "Successfully created REST API with 5 endpoints...",
                "duration_seconds": 45.2
            }
        }


class TaskListResponse(BaseModel):
    """List of synthesis tasks."""
    tasks: List[SynthesisResponse] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    per_page: int = Field(default=20)


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = Field(default="healthy")
    version: str = Field(default="1.0.0")
    uptime_seconds: float = Field(default=0.0)
    providers_available: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None)
    task_id: Optional[str] = Field(default=None)


class ProviderListResponse(BaseModel):
    """List of available providers."""
    providers: List[Dict[str, Any]] = Field(default_factory=list)


class PresetResponse(BaseModel):
    """Provider preset configuration."""
    name: str
    provider: str
    model: str
    description: Optional[str] = None
    is_uncensored: bool = False


class PresetsListResponse(BaseModel):
    """List of available presets."""
    presets: List[PresetResponse] = Field(default_factory=list)


# WebSocket message schemas
class WSMessage(BaseModel):
    """WebSocket message."""
    type: str = Field(..., description="Message type")
    task_id: str = Field(..., description="Task identifier")
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamChunk(BaseModel):
    """Streaming response chunk."""
    task_id: str
    chunk_type: str  # 'plan', 'output', 'file', 'status', 'error'
    content: str
    metadata: Optional[Dict[str, Any]] = None
