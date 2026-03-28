"""
Tri-Core Data Models
====================

Pydantic models for type-safe, validated data structures
across the entire Tri-Core architecture.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List, Dict, Callable
from pydantic import BaseModel, Field
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class Platform(str, Enum):
    """Supported platforms in the Tri-Core architecture."""
    GENSPARK = "genspark"
    AOL_CLI = "aol-cli"
    CLAWDPOKE = "clawdpoke"
    TRINITY = "trinity"  # Orchestrator itself


class EventPriority(str, Enum):
    """Event priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskType(str, Enum):
    """Task type classifications for routing."""
    CREATIVE = "creative"
    TECHNICAL = "technical"
    INTERACTIVE = "interactive"
    HYBRID = "hybrid"


class TaskStatus(str, Enum):
    """Status of a task in the pipeline."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InterfaceType(str, Enum):
    """Available interface types."""
    SPARKPAGE_UI = "SparkpageUI"
    TERMINAL_TUI = "TerminalTUI"
    GAME_ENGINE = "GameEngine"
    MULTI_VIEW = "MultiView"


class SkillCategory(str, Enum):
    """Skill categories in the game system."""
    COMBAT = "combat"
    EXPLORATION = "exploration"
    CRAFTING = "crafting"
    SOCIAL = "social"
    MAGIC = "magic"
    TECHNICAL = "technical"


# =============================================================================
# EVENT MODELS
# =============================================================================

class TriCoreEvent(BaseModel):
    """
    Standardized event format for cross-platform communication.
    
    All events flowing through the Unified Event Bus use this format
    to ensure consistent data structures regardless of source/destination.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: Platform
    target: Optional[Platform] = None
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class EventSubscription(BaseModel):
    """Subscription to an event topic."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    platform: Optional[Platform] = None
    callback_id: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# MESSAGE MODELS
# =============================================================================

class MessageSource(BaseModel):
    """Source information for a message."""
    platform: Platform
    component: str
    id: Optional[str] = None


class MessageTarget(BaseModel):
    """Target information for a message."""
    platform: Platform
    component: str
    id: Optional[str] = None


class MessageMetadata(BaseModel):
    """Metadata for message routing and tracking."""
    priority: EventPriority = EventPriority.NORMAL
    timeout: int = 300000  # 5 minutes in ms
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    retry_count: int = 0
    max_retries: int = 3


class IntegrationMessage(BaseModel):
    """
    Full integration message format as per spec.
    Used for complex cross-platform task execution.
    """
    message_type: str
    source: MessageSource
    target: MessageTarget
    payload: Dict[str, Any]
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)


# =============================================================================
# AGENT MODELS
# =============================================================================

class AgentCapability(BaseModel):
    """Capability of a Genspark agent."""
    name: str
    description: str
    skill_level: int = Field(ge=1, le=10)
    specializations: List[str] = Field(default_factory=list)


class AgentRequest(BaseModel):
    """Request to a Genspark agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    context: Dict[str, Any] = Field(default_factory=dict)
    required_capabilities: List[str] = Field(default_factory=list)
    priority: EventPriority = EventPriority.NORMAL
    timeout: int = 300  # seconds


class AgentResponse(BaseModel):
    """Response from a Genspark agent."""
    request_id: str
    agent_id: str
    agent_name: str
    result: Any
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time: float
    success: bool
    error: Optional[str] = None


# =============================================================================
# CLI MODELS
# =============================================================================

class CLICommand(BaseModel):
    """AOL-CLI command specification."""
    command: str
    args: List[str] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    working_directory: Optional[str] = None
    timeout: int = 60


class CommandResult(BaseModel):
    """Result from AOL-CLI command execution."""
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    execution_time: float
    success: bool


# =============================================================================
# GAME MODELS
# =============================================================================

class Skill(BaseModel):
    """A skill in the Clawdpoke.a0 system."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: SkillCategory
    level: int = Field(ge=1, le=100, default=1)
    experience: int = Field(ge=0, default=0)
    description: str = ""
    effects: Dict[str, Any] = Field(default_factory=dict)
    requirements: Dict[str, int] = Field(default_factory=dict)  # skill_id: level required


class PlayerState(BaseModel):
    """Current state of a player in the game."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    level: int = Field(ge=1, default=1)
    experience: int = Field(ge=0, default=0)
    health: int = Field(ge=0, default=100)
    max_health: int = Field(ge=1, default=100)
    skills: Dict[str, Skill] = Field(default_factory=dict)
    inventory: List[Dict[str, Any]] = Field(default_factory=list)
    location: str = "start"
    flags: Dict[str, bool] = Field(default_factory=dict)
    stats: Dict[str, int] = Field(default_factory=dict)


class NarrativeChoice(BaseModel):
    """A choice in a narrative branch."""
    choice_id: str
    text: str
    required_skills: List[Dict[str, Any]] = Field(default_factory=list)
    consequences: Dict[str, Any] = Field(default_factory=dict)


class NarrativeBranch(BaseModel):
    """A branch point in the narrative."""
    branch_id: str
    narrative_text: str
    choices: List[NarrativeChoice]
    location: Optional[str] = None
    requirements: Dict[str, Any] = Field(default_factory=dict)


class GameAction(BaseModel):
    """An action in the game."""
    action_type: str
    player_id: str
    target: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GameStateUpdate(BaseModel):
    """Update to the game state."""
    update_type: str
    player_state: Optional[PlayerState] = None
    narrative: Optional[NarrativeBranch] = None
    world_changes: Dict[str, Any] = Field(default_factory=dict)
    events_triggered: List[str] = Field(default_factory=list)


# =============================================================================
# WORKFLOW MODELS
# =============================================================================

class WorkflowStep(BaseModel):
    """A step in a workflow."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    platform: Platform
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)  # step ids
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None


class Workflow(BaseModel):
    """A complete workflow definition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    steps: List[WorkflowStep] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class Task(BaseModel):
    """A task to be processed by the system."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    task_type: TaskType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    assigned_platform: Optional[Platform] = None
    assigned_interface: Optional[InterfaceType] = None


# =============================================================================
# CAPABILITY MAPPING
# =============================================================================

class CapabilityMapping(BaseModel):
    """Maps a capability to a system and component."""
    capability: str
    system: Platform
    component: str
    agent: Optional[str] = None
    node: Optional[str] = None


# Default capability mappings as per the spec
DEFAULT_CAPABILITY_MAP: Dict[str, CapabilityMapping] = {
    # Genspark specializations
    "creative_design": CapabilityMapping(
        capability="creative_design",
        system=Platform.GENSPARK,
        component="Agent",
        agent="AIDesigner"
    ),
    "narrative_creation": CapabilityMapping(
        capability="narrative_creation",
        system=Platform.GENSPARK,
        component="Agent",
        agent="AIDoc"
    ),
    "asset_generation": CapabilityMapping(
        capability="asset_generation",
        system=Platform.GENSPARK,
        component="Agent",
        agent="AIImage"
    ),
    
    # AOL-CLI specializations
    "code_generation": CapabilityMapping(
        capability="code_generation",
        system=Platform.AOL_CLI,
        component="Executor",
        node="Executor"
    ),
    "system_integration": CapabilityMapping(
        capability="system_integration",
        system=Platform.AOL_CLI,
        component="Executor",
        node="Executor"
    ),
    "deployment": CapabilityMapping(
        capability="deployment",
        system=Platform.AOL_CLI,
        component="Reporter",
        node="Reporter"
    ),
    
    # Clawdpoke.a0 specializations
    "game_mechanics": CapabilityMapping(
        capability="game_mechanics",
        system=Platform.CLAWDPOKE,
        component="GameSkill"
    ),
    "player_experience": CapabilityMapping(
        capability="player_experience",
        system=Platform.CLAWDPOKE,
        component="NarrativeBranch"
    ),
    "skill_progression": CapabilityMapping(
        capability="skill_progression",
        system=Platform.CLAWDPOKE,
        component="SkillTransfer"
    ),
}
