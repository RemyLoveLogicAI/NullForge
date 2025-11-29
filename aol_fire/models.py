"""
Enhanced Data Models for AOL-CLI Fire Edition.

This module provides comprehensive data structures for:
- Agent state management
- Task and plan tracking
- Memory and context
- Tool execution results
- Multi-agent coordination
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, field_validator, computed_field


# =============================================================================
# Enums
# =============================================================================

class TaskStatus(str, Enum):
    """Status of a task."""
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority level for tasks."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlanStatus(str, Enum):
    """Overall status of the execution plan."""
    PENDING = "pending"
    PLANNING = "planning"
    PLANNING_COMPLETE = "planning_complete"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRole(str, Enum):
    """Specialized agent roles."""
    ORCHESTRATOR = "orchestrator"  # Coordinates other agents
    PLANNER = "planner"            # Strategic planning
    CODER = "coder"                # Code generation/editing
    RESEARCHER = "researcher"      # Web search and analysis
    REVIEWER = "reviewer"          # Code review and QA
    DEVOPS = "devops"              # Infrastructure and deployment
    DEBUGGER = "debugger"          # Error analysis and fixing


class MemoryType(str, Enum):
    """Types of memory storage."""
    EPISODIC = "episodic"      # Conversation history
    SEMANTIC = "semantic"      # Knowledge/facts
    PROCEDURAL = "procedural"  # How-to knowledge
    WORKING = "working"        # Current context


# =============================================================================
# Core Models
# =============================================================================

class ToolCall(BaseModel):
    """Record of a tool invocation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        return self.error is None


class FileChange(BaseModel):
    """Record of a file modification."""
    path: str
    action: Literal["created", "modified", "deleted", "moved"]
    old_path: Optional[str] = None  # For moves/renames
    diff: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    """
    A single task in the execution plan.
    
    Tasks can have dependencies, subtasks, and rich metadata
    for tracking progress and results.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Execution details
    assigned_agent: Optional[AgentRole] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    file_changes: List[FileChange] = Field(default_factory=list)
    
    # Results
    output: Optional[str] = None
    error: Optional[str] = None
    
    # Relationships
    parent_id: Optional[str] = None
    subtasks: List["Task"] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # Task IDs
    blockers: List[str] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_mins: Optional[int] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    
    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def complete(self, output: str) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.output = output
        self.completed_at = datetime.now()
    
    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()
    
    def add_subtask(self, title: str, **kwargs) -> "Task":
        """Add a subtask."""
        subtask = Task(title=title, parent_id=self.id, **kwargs)
        self.subtasks.append(subtask)
        return subtask
    
    @computed_field
    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate execution duration."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None
    
    @property
    def is_blocked(self) -> bool:
        """Check if task is blocked by dependencies."""
        return len(self.blockers) > 0
    
    @property
    def progress(self) -> float:
        """Calculate progress based on subtasks."""
        if not self.subtasks:
            return 100.0 if self.status == TaskStatus.COMPLETED else 0.0
        completed = sum(1 for t in self.subtasks if t.status == TaskStatus.COMPLETED)
        return (completed / len(self.subtasks)) * 100


class Plan(BaseModel):
    """
    Execution plan containing tasks and metadata.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str
    reasoning: str = ""
    tasks: List[Task] = Field(default_factory=list)
    
    # Status tracking
    status: TaskStatus = TaskStatus.PENDING
    current_task_index: int = 0
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    estimated_total_mins: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    
    def add_task(self, title: str, **kwargs) -> Task:
        """Add a task to the plan."""
        task = Task(title=title, **kwargs)
        self.tasks.append(task)
        return task
    
    @property
    def pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]
    
    @property
    def completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]
    
    @property
    def failed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]
    
    @property
    def current_task(self) -> Optional[Task]:
        pending = self.pending_tasks
        return pending[0] if pending else None
    
    @property
    def is_complete(self) -> bool:
        return all(t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED) 
                   for t in self.tasks)
    
    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        return (len(self.completed_tasks) / len(self.tasks)) * 100
    
    @property
    def success_rate(self) -> float:
        completed = len(self.completed_tasks) + len(self.failed_tasks)
        if completed == 0:
            return 0.0
        return (len(self.completed_tasks) / completed) * 100


class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def access(self) -> None:
        """Record an access to this memory."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class Memory(BaseModel):
    """
    Agent memory system with multiple memory types.
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    entries: List[MemoryEntry] = Field(default_factory=list)
    
    # Conversation history (short-term)
    conversation: List[Dict[str, str]] = Field(default_factory=list)
    
    # Working context (current task context)
    working_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Project knowledge
    project_files: Dict[str, str] = Field(default_factory=dict)  # path -> summary
    project_structure: Optional[str] = None
    
    # Learned patterns
    patterns: List[str] = Field(default_factory=list)
    
    def add_entry(
        self, 
        content: str, 
        type: MemoryType = MemoryType.EPISODIC,
        importance: float = 0.5,
        **metadata
    ) -> MemoryEntry:
        """Add a memory entry."""
        entry = MemoryEntry(
            type=type,
            content=content,
            importance=importance,
            metadata=metadata
        )
        self.entries.append(entry)
        return entry
    
    def add_message(self, role: str, content: str) -> None:
        """Add a conversation message."""
        self.conversation.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_recent_conversation(self, limit: int = 20) -> List[Dict[str, str]]:
        """Get recent conversation history."""
        return self.conversation[-limit:]
    
    def search(
        self, 
        query: str, 
        type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memories (basic keyword search, can be enhanced with embeddings)."""
        results = []
        query_lower = query.lower()
        
        for entry in self.entries:
            if type and entry.type != type:
                continue
            if query_lower in entry.content.lower():
                results.append(entry)
                entry.access()
        
        # Sort by importance and recency
        results.sort(key=lambda e: (e.importance, e.timestamp), reverse=True)
        return results[:limit]
    
    def get_context_summary(self, max_tokens: int = 2000) -> str:
        """Generate a context summary for the LLM."""
        parts = []
        
        if self.project_structure:
            parts.append(f"## Project Structure\n{self.project_structure[:500]}")
        
        if self.working_context:
            parts.append(f"## Current Context\n{str(self.working_context)[:500]}")
        
        if self.patterns:
            parts.append(f"## Learned Patterns\n" + "\n".join(f"- {p}" for p in self.patterns[:5]))
        
        return "\n\n".join(parts)


class AgentMessage(BaseModel):
    """Message in agent communication."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_agent: AgentRole
    to_agent: Optional[AgentRole] = None  # None = broadcast
    content: str
    message_type: Literal["request", "response", "notification", "error"] = "notification"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentState(BaseModel):
    """
    Complete state for the Fire agent system.
    
    This is the primary state object that flows through the LangGraph workflow.
    """
    # Session info
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = Field(default_factory=datetime.now)
    
    # User input
    goal: str = ""
    user_messages: List[str] = Field(default_factory=list)
    
    # Planning
    plan: Optional[Plan] = None
    
    # Memory
    memory: Memory = Field(default_factory=Memory)
    
    # Execution tracking
    current_agent: AgentRole = AgentRole.ORCHESTRATOR
    iteration: int = 0
    max_iterations: int = 100
    
    # Multi-agent communication
    agent_messages: List[AgentMessage] = Field(default_factory=list)
    
    # Results
    file_changes: List[FileChange] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    
    # Output
    final_output: Optional[str] = None
    error: Optional[str] = None
    
    # Configuration reference
    config_hash: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if the agent has finished."""
        if self.error:
            return True
        if self.plan and self.plan.is_complete:
            return True
        if self.iteration >= self.max_iterations:
            return True
        return False
    
    @property
    def all_files_created(self) -> List[str]:
        """Get all files created in this session."""
        return [f.path for f in self.file_changes if f.action == "created"]
    
    @property
    def all_files_modified(self) -> List[str]:
        """Get all files modified in this session."""
        return [f.path for f in self.file_changes if f.action == "modified"]
    
    def send_message(
        self, 
        from_agent: AgentRole, 
        content: str,
        to_agent: Optional[AgentRole] = None,
        **metadata
    ) -> AgentMessage:
        """Send a message between agents."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            metadata=metadata
        )
        self.agent_messages.append(msg)
        return msg


class ProjectContext(BaseModel):
    """
    Context about the current project being worked on.
    """
    root_path: Path
    name: str = ""
    description: str = ""
    
    # Detected info
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    package_managers: List[str] = Field(default_factory=list)
    
    # File structure
    structure: Dict[str, Any] = Field(default_factory=dict)
    key_files: List[str] = Field(default_factory=list)
    
    # Git info
    git_initialized: bool = False
    git_branch: Optional[str] = None
    git_remote: Optional[str] = None
    has_uncommitted_changes: bool = False
    
    # Dependencies
    dependencies: Dict[str, str] = Field(default_factory=dict)
    dev_dependencies: Dict[str, str] = Field(default_factory=dict)
    
    # Documentation
    readme_content: Optional[str] = None
    has_docs: bool = False
    
    @field_validator('root_path', mode='before')
    @classmethod
    def validate_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v


class ExecutionMetrics(BaseModel):
    """Metrics for agent execution."""
    total_duration_ms: int = 0
    planning_duration_ms: int = 0
    execution_duration_ms: int = 0
    
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0
    
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    
    tokens_used: int = 0
    api_calls: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
    
    @property
    def tool_success_rate(self) -> float:
        if self.total_tool_calls == 0:
            return 0.0
        return (self.successful_tool_calls / self.total_tool_calls) * 100
