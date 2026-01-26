"""
Trinity Orchestrator
====================

The central command and control system for the Tri-Core architecture.
Manages workflow transitions between all three platforms while maintaining
consistent context throughout complex multi-platform operations.
"""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

from tri_core.models import (
    Platform,
    TaskType,
    TaskStatus,
    InterfaceType,
    EventPriority,
    Task,
    Workflow,
    WorkflowStep,
    AgentRequest,
    AgentResponse,
    CLICommand,
    CommandResult,
    GameAction,
    GameStateUpdate,
    TriCoreEvent,
    DEFAULT_CAPABILITY_MAP,
    CapabilityMapping,
)
from tri_core.event_bus.bus import UnifiedEventBus, get_event_bus
from tri_core.event_bus.state_sync import StateSync
from tri_core.event_bus.event_bridge import EventBridge

if TYPE_CHECKING:
    from tri_core.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for the Trinity Orchestrator."""
    max_concurrent_tasks: int = 10
    default_timeout: int = 300  # seconds
    enable_auto_routing: bool = True
    enable_context_sync: bool = True
    retry_failed_tasks: bool = True
    max_retries: int = 3


@dataclass
class ExecutionContext:
    """Context maintained across platform transitions."""
    workflow_id: str
    current_step: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_platform: Optional[Platform] = None


class TrinityOrchestrator:
    """
    🔱 Trinity Orchestrator
    
    The brain of the Tri-Core Integration Architecture.
    Coordinates all operations between Genspark, AOL-CLI, and Clawdpoke.a0.
    
    Core Capabilities:
    - Agent Router: Directs requests to appropriate Genspark agents
    - CLI Executor: Translates decisions into AOL-CLI commands
    - Game State Manager: Maps actions to Clawdpoke game mechanics
    - Context Sync: Maintains continuity across platform transitions
    - Skill Mapper: Translates skills between platforms
    - Interface Selector: Dynamically selects optimal interface
    
    Usage:
        orchestrator = TrinityOrchestrator()
        result = await orchestrator.execute_task(task)
    """
    
    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        event_bus: Optional[UnifiedEventBus] = None,
    ):
        """Initialize the Trinity Orchestrator."""
        self.config = config or OrchestratorConfig()
        self.event_bus = event_bus or get_event_bus()
        self.state_sync = StateSync()
        self.event_bridge = EventBridge()
        
        # Adapters for each platform
        self._adapters: Dict[Platform, BaseAdapter] = {}
        
        # Capability mapping
        self._capability_map = DEFAULT_CAPABILITY_MAP.copy()
        
        # Active contexts
        self._contexts: Dict[str, ExecutionContext] = {}
        
        # Task queue
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Dict[str, Task] = {}
        
        # Workflow registry
        self._workflow_templates: Dict[str, Workflow] = {}
        
        # Statistics
        self._stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "workflows_completed": 0,
            "platform_calls": {
                Platform.GENSPARK: 0,
                Platform.AOL_CLI: 0,
                Platform.CLAWDPOKE: 0,
            },
        }
        
        # Subscribe to events
        self._setup_event_subscriptions()
        
        logger.info("🔱 Trinity Orchestrator initialized")
    
    def _setup_event_subscriptions(self) -> None:
        """Set up event bus subscriptions."""
        # Listen for task requests
        self.event_bus.subscribe(
            "task.*",
            self._handle_task_event,
        )
        
        # Listen for platform responses
        self.event_bus.subscribe(
            "response.*",
            self._handle_response_event,
        )
        
        # Listen for state changes
        self.state_sync.on_any_change(self._handle_state_change)
    
    # =========================================================================
    # ADAPTER MANAGEMENT
    # =========================================================================
    
    def register_adapter(self, platform: Platform, adapter: BaseAdapter) -> None:
        """Register an adapter for a platform."""
        self._adapters[platform] = adapter
        logger.info(f"📌 Registered adapter for {platform}")
    
    def get_adapter(self, platform: Platform) -> Optional[BaseAdapter]:
        """Get the adapter for a platform."""
        return self._adapters.get(platform)
    
    # =========================================================================
    # AGENT ROUTING (Genspark)
    # =========================================================================
    
    async def route_to_agent(self, request: AgentRequest) -> AgentResponse:
        """
        Route a request to the appropriate Genspark agent.
        
        Analyzes the request and selects the best agent based on:
        - Required capabilities
        - Agent specializations
        - Current workload
        
        Args:
            request: Agent request
            
        Returns:
            Agent response
        """
        logger.info(f"🎯 Routing request {request.id} to Genspark agent")
        
        # Find matching capability
        selected_agent = None
        for capability in request.required_capabilities:
            if capability in self._capability_map:
                mapping = self._capability_map[capability]
                if mapping.system == Platform.GENSPARK:
                    selected_agent = mapping.agent
                    break
        
        if not selected_agent:
            # Default to orchestrator agent
            selected_agent = "SuperAgent"
        
        # Get Genspark adapter
        adapter = self._adapters.get(Platform.GENSPARK)
        if not adapter:
            raise RuntimeError("Genspark adapter not registered")
        
        # Execute through adapter
        self._stats["platform_calls"][Platform.GENSPARK] += 1
        
        start_time = datetime.utcnow()
        result = await adapter.execute(
            action="call_agent",
            params={
                "agent": selected_agent,
                "task": request.task,
                "context": request.context,
            }
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Sync state
        if self.config.enable_context_sync:
            self.state_sync.set(
                f"agent.{request.id}.result",
                result,
                Platform.GENSPARK,
            )
        
        # Publish event
        await self.event_bus.publish_async(
            "response.genspark",
            TriCoreEvent(
                source=Platform.GENSPARK,
                event_type="agent_response",
                payload={"request_id": request.id, "result": result},
            )
        )
        
        return AgentResponse(
            request_id=request.id,
            agent_id=selected_agent,
            agent_name=selected_agent,
            result=result,
            execution_time=execution_time,
            success=True,
        )
    
    # =========================================================================
    # CLI EXECUTION (AOL-CLI)
    # =========================================================================
    
    async def execute_cli_command(
        self,
        command: str,
        params: Optional[List[Any]] = None,
        working_directory: Optional[str] = None,
    ) -> CommandResult:
        """
        Execute a command via AOL-CLI.
        
        Translates high-level agent decisions into executable
        AOL-CLI commands using LangGraph workflows.
        
        Args:
            command: Command to execute
            params: Command parameters
            working_directory: Working directory for execution
            
        Returns:
            Command execution result
        """
        logger.info(f"⚡ Executing CLI command: {command}")
        
        cli_command = CLICommand(
            command=command,
            args=params or [],
            working_directory=working_directory,
        )
        
        # Get AOL-CLI adapter
        adapter = self._adapters.get(Platform.AOL_CLI)
        if not adapter:
            raise RuntimeError("AOL-CLI adapter not registered")
        
        # Execute through adapter
        self._stats["platform_calls"][Platform.AOL_CLI] += 1
        
        start_time = datetime.utcnow()
        result = await adapter.execute(
            action="run_command",
            params={
                "command": cli_command.command,
                "args": cli_command.args,
                "kwargs": cli_command.kwargs,
                "working_directory": cli_command.working_directory,
            }
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Parse result
        success = result.get("exit_code", 1) == 0
        
        # Sync state
        if self.config.enable_context_sync:
            self.state_sync.set(
                f"cli.last_command",
                {"command": command, "result": result},
                Platform.AOL_CLI,
            )
        
        # Publish event
        await self.event_bus.publish_async(
            "response.aol-cli",
            TriCoreEvent(
                source=Platform.AOL_CLI,
                event_type="command_result",
                payload={"command": command, "result": result},
            )
        )
        
        return CommandResult(
            command=command,
            exit_code=result.get("exit_code", 1),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            execution_time=execution_time,
            success=success,
        )
    
    # =========================================================================
    # GAME STATE MANAGEMENT (Clawdpoke.a0)
    # =========================================================================
    
    async def update_game_state(self, action: GameAction) -> GameStateUpdate:
        """
        Update game state in Clawdpoke.a0.
        
        Maps agent actions to game mechanics and updates
        the game state accordingly.
        
        Args:
            action: Game action to perform
            
        Returns:
            Game state update result
        """
        logger.info(f"🎮 Updating game state: {action.action_type}")
        
        # Get Clawdpoke adapter
        adapter = self._adapters.get(Platform.CLAWDPOKE)
        if not adapter:
            raise RuntimeError("Clawdpoke adapter not registered")
        
        # Execute through adapter
        self._stats["platform_calls"][Platform.CLAWDPOKE] += 1
        
        result = await adapter.execute(
            action="update_state",
            params={
                "action_type": action.action_type,
                "player_id": action.player_id,
                "target": action.target,
                "parameters": action.parameters,
            }
        )
        
        # Sync state
        if self.config.enable_context_sync:
            self.state_sync.set(
                f"game.player.{action.player_id}",
                result.get("player_state"),
                Platform.CLAWDPOKE,
            )
        
        # Publish event
        await self.event_bus.publish_async(
            "response.clawdpoke",
            TriCoreEvent(
                source=Platform.CLAWDPOKE,
                event_type="state_update",
                payload={"action": action.action_type, "result": result},
            )
        )
        
        return GameStateUpdate(
            update_type=action.action_type,
            player_state=result.get("player_state"),
            narrative=result.get("narrative"),
            world_changes=result.get("world_changes", {}),
            events_triggered=result.get("events_triggered", []),
        )
    
    # =========================================================================
    # INTERFACE SELECTION
    # =========================================================================
    
    def select_interface(self, task: Task) -> InterfaceType:
        """
        Dynamically select the optimal interface based on task characteristics.
        
        Args:
            task: Task to analyze
            
        Returns:
            Selected interface type
        """
        task_type = task.task_type
        
        if task_type == TaskType.CREATIVE:
            # Creative tasks -> Genspark visual interface
            interface = InterfaceType.SPARKPAGE_UI
        elif task_type == TaskType.TECHNICAL:
            # Development tasks -> AOL-CLI terminal
            interface = InterfaceType.TERMINAL_TUI
        elif task_type == TaskType.INTERACTIVE:
            # Gameplay -> Clawdpoke game engine
            interface = InterfaceType.GAME_ENGINE
        elif task_type == TaskType.HYBRID:
            # Complex tasks -> split view
            interface = InterfaceType.MULTI_VIEW
        else:
            # Default to last used or terminal
            last_interface = self.state_sync.get("interface.last_used")
            interface = InterfaceType(last_interface) if last_interface else InterfaceType.TERMINAL_TUI
        
        # Update task
        task.assigned_interface = interface
        
        # Store selection
        self.state_sync.set("interface.last_used", interface.value, Platform.TRINITY)
        
        logger.info(f"🖥️ Selected interface: {interface} for task type: {task_type}")
        return interface
    
    # =========================================================================
    # TASK EXECUTION
    # =========================================================================
    
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        Execute a task using the appropriate platform(s).
        
        Args:
            task: Task to execute
            
        Returns:
            Execution result
        """
        logger.info(f"📋 Executing task: {task.name}")
        
        task.status = TaskStatus.IN_PROGRESS
        self._active_tasks[task.id] = task
        
        # Select interface
        interface = self.select_interface(task)
        
        # Determine platform based on task type
        if task.task_type == TaskType.CREATIVE:
            platform = Platform.GENSPARK
        elif task.task_type == TaskType.TECHNICAL:
            platform = Platform.AOL_CLI
        elif task.task_type == TaskType.INTERACTIVE:
            platform = Platform.CLAWDPOKE
        else:
            # Hybrid - use orchestrator logic
            platform = self._determine_platform(task)
        
        task.assigned_platform = platform
        
        try:
            # Route to appropriate handler
            if platform == Platform.GENSPARK:
                request = AgentRequest(
                    task=task.description,
                    context=task.parameters,
                    required_capabilities=self._extract_capabilities(task),
                )
                response = await self.route_to_agent(request)
                result = {"agent_response": response.result}
                
            elif platform == Platform.AOL_CLI:
                command = task.parameters.get("command", task.description)
                response = await self.execute_cli_command(command)
                result = {
                    "exit_code": response.exit_code,
                    "stdout": response.stdout,
                    "stderr": response.stderr,
                }
                
            elif platform == Platform.CLAWDPOKE:
                action = GameAction(
                    action_type=task.parameters.get("action_type", "generic"),
                    player_id=task.parameters.get("player_id", "default"),
                    parameters=task.parameters,
                )
                response = await self.update_game_state(action)
                result = {
                    "update_type": response.update_type,
                    "events": response.events_triggered,
                }
            else:
                result = {"error": "Unknown platform"}
            
            task.status = TaskStatus.COMPLETED
            self._stats["tasks_completed"] += 1
            
            # Publish completion event
            await self.event_bus.publish_async(
                "task.completed",
                TriCoreEvent(
                    source=Platform.TRINITY,
                    event_type="task_completed",
                    payload={"task_id": task.id, "result": result},
                )
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task.status = TaskStatus.FAILED
            self._stats["tasks_failed"] += 1
            
            if self.config.retry_failed_tasks:
                # Could implement retry logic here
                pass
            
            raise
        finally:
            del self._active_tasks[task.id]
    
    def _determine_platform(self, task: Task) -> Platform:
        """Determine the best platform for a hybrid task."""
        # Analyze task parameters and description
        description = task.description.lower()
        
        if any(word in description for word in ["design", "create", "generate", "write"]):
            return Platform.GENSPARK
        elif any(word in description for word in ["build", "compile", "run", "execute", "code"]):
            return Platform.AOL_CLI
        elif any(word in description for word in ["play", "game", "skill", "character"]):
            return Platform.CLAWDPOKE
        else:
            # Default to Genspark for high-level orchestration
            return Platform.GENSPARK
    
    def _extract_capabilities(self, task: Task) -> List[str]:
        """Extract required capabilities from a task."""
        capabilities = []
        description = task.description.lower()
        
        capability_keywords = {
            "creative_design": ["design", "visual", "ui", "interface"],
            "narrative_creation": ["story", "narrative", "write", "dialogue"],
            "asset_generation": ["asset", "image", "sprite", "texture"],
            "code_generation": ["code", "implement", "build", "develop"],
            "system_integration": ["integrate", "connect", "api", "deploy"],
            "game_mechanics": ["mechanic", "gameplay", "rule", "system"],
            "player_experience": ["player", "experience", "ux", "interaction"],
            "skill_progression": ["skill", "level", "progression", "upgrade"],
        }
        
        for capability, keywords in capability_keywords.items():
            if any(keyword in description for keyword in keywords):
                capabilities.append(capability)
        
        return capabilities or ["code_generation"]  # Default capability
    
    # =========================================================================
    # WORKFLOW EXECUTION
    # =========================================================================
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow template."""
        self._workflow_templates[workflow.id] = workflow
        logger.info(f"📝 Registered workflow: {workflow.name}")
    
    async def execute_workflow(self, workflow_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a registered workflow.
        
        Args:
            workflow_id: ID of the workflow template
            context: Initial context variables
            
        Returns:
            Workflow execution results
        """
        if workflow_id not in self._workflow_templates:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        # Clone the template
        import copy
        workflow = copy.deepcopy(self._workflow_templates[workflow_id])
        workflow.context = context or {}
        workflow.status = TaskStatus.IN_PROGRESS
        
        # Create execution context
        exec_context = ExecutionContext(
            workflow_id=workflow.id,
            variables=context or {},
        )
        self._contexts[workflow.id] = exec_context
        
        logger.info(f"🚀 Starting workflow: {workflow.name}")
        
        results = {}
        
        try:
            for i, step in enumerate(workflow.steps):
                exec_context.current_step = i
                
                # Check dependencies
                for dep_id in step.dependencies:
                    dep_step = next((s for s in workflow.steps if s.id == dep_id), None)
                    if dep_step and dep_step.status != TaskStatus.COMPLETED:
                        raise RuntimeError(f"Dependency not met: {dep_id}")
                
                # Execute step
                step.status = TaskStatus.IN_PROGRESS
                logger.info(f"  Step {i+1}/{len(workflow.steps)}: {step.name}")
                
                # Create task from step
                task = Task(
                    name=step.name,
                    description=step.action,
                    task_type=self._get_task_type_for_platform(step.platform),
                    parameters={**step.parameters, **exec_context.variables},
                    assigned_platform=step.platform,
                )
                
                # Execute
                result = await self.execute_task(task)
                step.result = result
                step.status = TaskStatus.COMPLETED
                results[step.id] = result
                
                # Update context with result
                exec_context.variables[f"step_{step.id}_result"] = result
                exec_context.history.append({
                    "step": step.name,
                    "platform": step.platform.value if hasattr(step.platform, 'value') else str(step.platform),
                    "result": result,
                })
                
                # Sync state
                self.state_sync.set(
                    f"workflow.{workflow.id}.step.{step.id}",
                    result,
                    step.platform,
                )
            
            workflow.status = TaskStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self._stats["workflows_completed"] += 1
            
            logger.info(f"✅ Workflow completed: {workflow.name}")
            
            return {
                "workflow_id": workflow.id,
                "status": "completed",
                "steps": results,
                "context": exec_context.variables,
            }
            
        except Exception as e:
            workflow.status = TaskStatus.FAILED
            exec_context.errors.append(str(e))
            logger.error(f"❌ Workflow failed: {e}")
            raise
        finally:
            del self._contexts[workflow.id]
    
    def _get_task_type_for_platform(self, platform: Platform) -> TaskType:
        """Map platform to task type."""
        mapping = {
            Platform.GENSPARK: TaskType.CREATIVE,
            Platform.AOL_CLI: TaskType.TECHNICAL,
            Platform.CLAWDPOKE: TaskType.INTERACTIVE,
            Platform.TRINITY: TaskType.HYBRID,
        }
        return mapping.get(platform, TaskType.HYBRID)
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _handle_task_event(self, event: TriCoreEvent) -> None:
        """Handle incoming task events."""
        logger.debug(f"📥 Task event: {event.event_type}")
        # Queue task for processing
        if "task" in event.payload:
            asyncio.create_task(
                self._task_queue.put(event.payload["task"])
            )
    
    def _handle_response_event(self, event: TriCoreEvent) -> None:
        """Handle response events from platforms."""
        logger.debug(f"📥 Response event from {event.source}: {event.event_type}")
    
    def _handle_state_change(
        self,
        key: str,
        value: Any,
        source: Platform,
        version: int,
    ) -> None:
        """Handle state changes from any platform."""
        logger.debug(f"🔄 State change: {key} from {source} (v{version})")
    
    # =========================================================================
    # SKILL MAPPING
    # =========================================================================
    
    def map_skill_to_capability(self, skill_id: str) -> Optional[str]:
        """
        Map a Clawdpoke skill to a Genspark agent capability.
        
        Args:
            skill_id: Clawdpoke skill ID
            
        Returns:
            Corresponding capability name
        """
        # Skill to capability mapping
        skill_map = {
            "archaeology": "narrative_creation",
            "combat": "game_mechanics",
            "programming": "code_generation",
            "design": "creative_design",
            "crafting": "asset_generation",
        }
        return skill_map.get(skill_id)
    
    def map_capability_to_skill(self, capability: str) -> Optional[str]:
        """
        Map a Genspark capability to a Clawdpoke skill.
        
        Args:
            capability: Genspark capability name
            
        Returns:
            Corresponding skill ID
        """
        # Reverse mapping
        capability_map = {
            "narrative_creation": "archaeology",
            "game_mechanics": "combat",
            "code_generation": "programming",
            "creative_design": "design",
            "asset_generation": "crafting",
        }
        return capability_map.get(capability)
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self._stats,
            "active_tasks": len(self._active_tasks),
            "registered_workflows": len(self._workflow_templates),
            "state_entries": self.state_sync.stats()["total_entries"],
        }
    
    def get_active_contexts(self) -> Dict[str, ExecutionContext]:
        """Get all active execution contexts."""
        return self._contexts.copy()
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"TrinityOrchestrator("
            f"tasks={stats['tasks_completed']}, "
            f"workflows={stats['workflows_completed']}, "
            f"active={stats['active_tasks']})"
        )
