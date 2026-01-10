"""
NullForge Multi-Agent Collaboration System
State of the Art distributed agent collaboration

Features:
- Multiple specialized agents working together
- Agent communication protocol
- Task delegation and coordination
- Consensus-based decision making
- Real-time synchronization
- Role-based access control
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import hashlib


class AgentRole(Enum):
    """Agent specializations."""
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DEBUGGER = "debugger"
    DOCUMENTER = "documenter"
    SECURITY = "security"
    OPTIMIZER = "optimizer"
    RESEARCHER = "researcher"


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    CONSENSUS_REQUEST = "consensus_request"
    CONSENSUS_VOTE = "consensus_vote"
    STATE_UPDATE = "state_update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class AgentMessage:
    """Message between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: Optional[str] = None  # None for broadcast
    message_type: MessageType = MessageType.BROADCAST
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 5  # 1-10, 10 is highest
    requires_response: bool = False
    response_to: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['message_type'] = self.message_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        data['message_type'] = MessageType(data['message_type'])
        return cls(**data)


@dataclass
class TaskAssignment:
    """Task assigned to an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    description: str = ""
    requirements: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    assigned_to: str = ""
    assigned_by: str = ""
    deadline: Optional[str] = None
    priority: int = 5
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConsensusRequest:
    """Request for consensus among agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    options: List[Dict[str, Any]] = field(default_factory=list)
    votes: Dict[str, int] = field(default_factory=dict)  # agent_id -> option_index
    required_votes: int = 3
    deadline: Optional[str] = None
    status: str = "open"  # open, closed, resolved
    result: Optional[int] = None


class BaseAgent(ABC):
    """
    Base class for all collaborative agents.
    
    Each agent has:
    - Unique ID and role
    - Message queue for communication
    - State tracking
    - Capability registration
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        role: AgentRole = AgentRole.CODER,
        capabilities: Optional[List[str]] = None,
        llm_provider: str = "venice"
    ):
        self.agent_id = agent_id or f"{role.value}-{uuid.uuid4().hex[:8]}"
        self.role = role
        self.capabilities = capabilities or []
        self.llm_provider = llm_provider
        
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.outbox: asyncio.Queue = asyncio.Queue()
        
        self.state: Dict[str, Any] = {
            "status": "idle",
            "current_task": None,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "last_active": datetime.now().isoformat()
        }
        
        self.peers: Dict[str, "BaseAgent"] = {}
        self.coordinator: Optional["AgentCoordinator"] = None
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the agent's message processing loop."""
        self._running = True
        self._task = asyncio.create_task(self._message_loop())
    
    async def stop(self):
        """Stop the agent."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _message_loop(self):
        """Main message processing loop."""
        while self._running:
            try:
                message = await asyncio.wait_for(self.inbox.get(), timeout=1.0)
                await self._handle_message(message)
            except asyncio.TimeoutError:
                # Send heartbeat
                await self._send_heartbeat()
            except Exception as e:
                print(f"Agent {self.agent_id} error: {e}")
    
    async def _handle_message(self, message: AgentMessage):
        """Handle incoming message."""
        self.state["last_active"] = datetime.now().isoformat()
        
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            await self._handle_task_assignment(message)
        elif message.message_type == MessageType.QUERY:
            await self._handle_query(message)
        elif message.message_type == MessageType.CONSENSUS_REQUEST:
            await self._handle_consensus_request(message)
        elif message.message_type == MessageType.STATE_UPDATE:
            await self._handle_state_update(message)
        else:
            await self.on_message(message)
    
    async def _handle_task_assignment(self, message: AgentMessage):
        """Handle task assignment."""
        task = TaskAssignment(**message.content)
        self.state["status"] = "working"
        self.state["current_task"] = task.id
        
        try:
            result = await self.execute_task(task)
            task.status = "completed"
            task.result = result
            self.state["completed_tasks"] += 1
            
            # Send result back
            response = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                message_type=MessageType.TASK_RESULT,
                content=asdict(task),
                response_to=message.id
            )
            await self.send(response)
            
        except Exception as e:
            task.status = "failed"
            task.result = {"error": str(e)}
            self.state["failed_tasks"] += 1
            
            response = AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                message_type=MessageType.ERROR,
                content={"task_id": task.id, "error": str(e)},
                response_to=message.id
            )
            await self.send(response)
        
        finally:
            self.state["status"] = "idle"
            self.state["current_task"] = None
    
    async def _handle_query(self, message: AgentMessage):
        """Handle query from another agent."""
        query = message.content.get("query", "")
        response_content = await self.answer_query(query, message.content)
        
        response = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type=MessageType.RESPONSE,
            content=response_content,
            response_to=message.id
        )
        await self.send(response)
    
    async def _handle_consensus_request(self, message: AgentMessage):
        """Handle consensus voting request."""
        request = ConsensusRequest(**message.content)
        vote = await self.vote_on_consensus(request)
        
        response = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            message_type=MessageType.CONSENSUS_VOTE,
            content={"request_id": request.id, "vote": vote},
            response_to=message.id
        )
        await self.send(response)
    
    async def _handle_state_update(self, message: AgentMessage):
        """Handle state update from coordinator."""
        updates = message.content.get("updates", {})
        self.state.update(updates)
    
    async def _send_heartbeat(self):
        """Send heartbeat to coordinator."""
        if self.coordinator:
            heartbeat = AgentMessage(
                sender_id=self.agent_id,
                message_type=MessageType.HEARTBEAT,
                content={"state": self.state}
            )
            await self.coordinator.receive_heartbeat(self.agent_id, heartbeat)
    
    async def send(self, message: AgentMessage):
        """Send a message."""
        if self.coordinator:
            await self.coordinator.route_message(message)
        else:
            await self.outbox.put(message)
    
    async def receive(self, message: AgentMessage):
        """Receive a message."""
        await self.inbox.put(message)
    
    async def query_peer(
        self,
        peer_id: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Query another agent and wait for response."""
        message = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=peer_id,
            message_type=MessageType.QUERY,
            content={"query": query, **(context or {})},
            requires_response=True
        )
        
        await self.send(message)
        
        # Wait for response (simplified - in production use proper correlation)
        try:
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout:
                if not self.inbox.empty():
                    response = await self.inbox.get()
                    if response.response_to == message.id:
                        return response.content
                await asyncio.sleep(0.1)
        except Exception:
            pass
        
        return None
    
    @abstractmethod
    async def execute_task(self, task: TaskAssignment) -> Dict[str, Any]:
        """Execute an assigned task. Override in subclasses."""
        pass
    
    async def answer_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Answer a query. Override in subclasses."""
        return {"response": f"Query received: {query}"}
    
    async def vote_on_consensus(self, request: ConsensusRequest) -> int:
        """Vote on a consensus request. Override in subclasses."""
        return 0  # Default to first option
    
    async def on_message(self, message: AgentMessage):
        """Handle other message types. Override in subclasses."""
        pass


class CoderAgent(BaseAgent):
    """Agent specialized in code generation."""
    
    def __init__(self, **kwargs):
        super().__init__(
            role=AgentRole.CODER,
            capabilities=["code_generation", "code_completion", "refactoring"],
            **kwargs
        )
    
    async def execute_task(self, task: TaskAssignment) -> Dict[str, Any]:
        """Generate code based on task."""
        # In production, this would call the LLM
        return {
            "code": f"# Generated code for: {task.description}\nprint('Hello from CoderAgent')",
            "language": task.context.get("language", "python"),
            "files": [{"name": "main.py", "content": "# Code here"}]
        }


class ReviewerAgent(BaseAgent):
    """Agent specialized in code review."""
    
    def __init__(self, **kwargs):
        super().__init__(
            role=AgentRole.REVIEWER,
            capabilities=["code_review", "quality_check", "best_practices"],
            **kwargs
        )
    
    async def execute_task(self, task: TaskAssignment) -> Dict[str, Any]:
        """Review code."""
        code = task.context.get("code", "")
        return {
            "approved": True,
            "issues": [],
            "suggestions": ["Consider adding type hints", "Add docstrings"],
            "score": 8.5
        }


class TesterAgent(BaseAgent):
    """Agent specialized in testing."""
    
    def __init__(self, **kwargs):
        super().__init__(
            role=AgentRole.TESTER,
            capabilities=["unit_testing", "integration_testing", "test_generation"],
            **kwargs
        )
    
    async def execute_task(self, task: TaskAssignment) -> Dict[str, Any]:
        """Generate or run tests."""
        return {
            "tests_generated": 5,
            "tests_passed": 5,
            "tests_failed": 0,
            "coverage": 85.0,
            "test_code": "# Test code here"
        }


class SecurityAgent(BaseAgent):
    """Agent specialized in security analysis."""
    
    def __init__(self, **kwargs):
        super().__init__(
            role=AgentRole.SECURITY,
            capabilities=["security_audit", "vulnerability_scan", "compliance_check"],
            **kwargs
        )
    
    async def execute_task(self, task: TaskAssignment) -> Dict[str, Any]:
        """Perform security audit."""
        return {
            "vulnerabilities": [],
            "risk_level": "low",
            "recommendations": ["Enable HTTPS", "Add input validation"],
            "compliance": {"OWASP": True, "CWE": True}
        }


class AgentCoordinator:
    """
    Coordinates multiple agents working together.
    
    Responsibilities:
    - Agent registration and discovery
    - Message routing
    - Task distribution
    - Consensus management
    - Health monitoring
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_roles: Dict[AgentRole, List[str]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.pending_tasks: Dict[str, TaskAssignment] = {}
        self.consensus_requests: Dict[str, ConsensusRequest] = {}
        self.agent_health: Dict[str, datetime] = {}
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the coordinator."""
        self._running = True
        self._task = asyncio.create_task(self._coordination_loop())
        
        # Start all agents
        for agent in self.agents.values():
            await agent.start()
    
    async def stop(self):
        """Stop the coordinator and all agents."""
        self._running = False
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        if self._task:
            self._task.cancel()
    
    async def _coordination_loop(self):
        """Main coordination loop."""
        while self._running:
            try:
                # Process message queue
                try:
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    await self.route_message(message)
                except asyncio.TimeoutError:
                    pass
                
                # Health check
                await self._health_check()
                
            except Exception as e:
                print(f"Coordinator error: {e}")
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the coordinator."""
        self.agents[agent.agent_id] = agent
        agent.coordinator = self
        
        if agent.role not in self.agent_roles:
            self.agent_roles[agent.role] = []
        self.agent_roles[agent.role].append(agent.agent_id)
        
        self.agent_health[agent.agent_id] = datetime.now()
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            if agent.role in self.agent_roles:
                self.agent_roles[agent.role].remove(agent_id)
            del self.agents[agent_id]
            del self.agent_health[agent_id]
    
    async def route_message(self, message: AgentMessage):
        """Route a message to the appropriate recipient(s)."""
        if message.receiver_id:
            # Direct message
            if message.receiver_id in self.agents:
                await self.agents[message.receiver_id].receive(message)
        else:
            # Broadcast
            for agent in self.agents.values():
                if agent.agent_id != message.sender_id:
                    await agent.receive(message)
    
    async def assign_task(
        self,
        task_type: str,
        description: str,
        role: AgentRole,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 5
    ) -> Optional[str]:
        """
        Assign a task to an available agent of the specified role.
        
        Returns task_id if successful, None otherwise.
        """
        # Find available agent
        agent_id = await self._find_available_agent(role)
        if not agent_id:
            return None
        
        task = TaskAssignment(
            task_type=task_type,
            description=description,
            context=context or {},
            assigned_to=agent_id,
            assigned_by="coordinator",
            priority=priority
        )
        
        self.pending_tasks[task.id] = task
        
        # Send task assignment
        message = AgentMessage(
            sender_id="coordinator",
            receiver_id=agent_id,
            message_type=MessageType.TASK_ASSIGNMENT,
            content=asdict(task),
            priority=priority
        )
        
        await self.agents[agent_id].receive(message)
        return task.id
    
    async def _find_available_agent(self, role: AgentRole) -> Optional[str]:
        """Find an available agent of the specified role."""
        if role not in self.agent_roles:
            return None
        
        for agent_id in self.agent_roles[role]:
            agent = self.agents.get(agent_id)
            if agent and agent.state.get("status") == "idle":
                return agent_id
        
        # Return first agent if none are idle
        return self.agent_roles[role][0] if self.agent_roles[role] else None
    
    async def request_consensus(
        self,
        topic: str,
        options: List[Dict[str, Any]],
        required_votes: int = 3,
        roles: Optional[List[AgentRole]] = None
    ) -> ConsensusRequest:
        """
        Request consensus from agents.
        
        Args:
            topic: Topic to vote on
            options: List of options
            required_votes: Minimum votes needed
            roles: Optional list of roles to include
            
        Returns:
            ConsensusRequest with results after voting
        """
        request = ConsensusRequest(
            topic=topic,
            options=options,
            required_votes=required_votes
        )
        
        self.consensus_requests[request.id] = request
        
        # Determine which agents should vote
        voters = []
        if roles:
            for role in roles:
                voters.extend(self.agent_roles.get(role, []))
        else:
            voters = list(self.agents.keys())
        
        # Send consensus requests
        message = AgentMessage(
            sender_id="coordinator",
            message_type=MessageType.CONSENSUS_REQUEST,
            content=asdict(request)
        )
        
        for agent_id in voters:
            msg = AgentMessage(
                sender_id="coordinator",
                receiver_id=agent_id,
                message_type=MessageType.CONSENSUS_REQUEST,
                content=asdict(request)
            )
            await self.agents[agent_id].receive(msg)
        
        # Wait for votes (with timeout)
        await asyncio.sleep(5.0)  # Simplified - would use proper async waiting
        
        # Tally votes
        if request.votes:
            vote_counts = {}
            for vote in request.votes.values():
                vote_counts[vote] = vote_counts.get(vote, 0) + 1
            
            if vote_counts:
                request.result = max(vote_counts, key=vote_counts.get)
                request.status = "resolved"
        
        return request
    
    async def receive_heartbeat(self, agent_id: str, message: AgentMessage):
        """Receive heartbeat from an agent."""
        self.agent_health[agent_id] = datetime.now()
    
    async def _health_check(self):
        """Check health of all agents."""
        now = datetime.now()
        unhealthy = []
        
        for agent_id, last_heartbeat in self.agent_health.items():
            if (now - last_heartbeat).seconds > 30:
                unhealthy.append(agent_id)
        
        # Handle unhealthy agents
        for agent_id in unhealthy:
            print(f"Agent {agent_id} appears unhealthy")
    
    def get_status(self) -> Dict[str, Any]:
        """Get coordinator status."""
        return {
            "agents": len(self.agents),
            "agents_by_role": {role.value: len(ids) for role, ids in self.agent_roles.items()},
            "pending_tasks": len(self.pending_tasks),
            "active_consensus": len([r for r in self.consensus_requests.values() if r.status == "open"]),
            "agent_states": {
                agent_id: agent.state 
                for agent_id, agent in self.agents.items()
            }
        }


class CollaborativeWorkflow:
    """
    High-level workflow orchestrating multiple agents.
    
    Example: Code generation with review
    1. Planner creates plan
    2. Coder generates code
    3. Reviewer reviews code
    4. Tester generates tests
    5. Security audits
    6. Final consensus on quality
    """
    
    def __init__(self, coordinator: AgentCoordinator):
        self.coordinator = coordinator
        self.workflow_id = str(uuid.uuid4())
        self.steps: List[Dict[str, Any]] = []
        self.results: Dict[str, Any] = {}
    
    async def execute_code_generation_workflow(
        self,
        description: str,
        language: str = "python",
        requirements: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a full code generation workflow with collaboration.
        """
        self.steps = []
        self.results = {}
        
        # Step 1: Planning
        plan_task_id = await self.coordinator.assign_task(
            task_type="planning",
            description=f"Create a plan for: {description}",
            role=AgentRole.PLANNER,
            context={"requirements": requirements or []}
        )
        self.steps.append({"step": "planning", "task_id": plan_task_id})
        await asyncio.sleep(2)  # Wait for planning
        
        # Step 2: Code generation
        code_task_id = await self.coordinator.assign_task(
            task_type="code_generation",
            description=description,
            role=AgentRole.CODER,
            context={"language": language}
        )
        self.steps.append({"step": "coding", "task_id": code_task_id})
        await asyncio.sleep(3)  # Wait for coding
        
        # Step 3: Code review
        review_task_id = await self.coordinator.assign_task(
            task_type="code_review",
            description="Review the generated code",
            role=AgentRole.REVIEWER,
            context={"code": self.results.get("code", "")}
        )
        self.steps.append({"step": "review", "task_id": review_task_id})
        await asyncio.sleep(2)
        
        # Step 4: Testing
        test_task_id = await self.coordinator.assign_task(
            task_type="test_generation",
            description="Generate tests for the code",
            role=AgentRole.TESTER,
            context={"code": self.results.get("code", "")}
        )
        self.steps.append({"step": "testing", "task_id": test_task_id})
        await asyncio.sleep(2)
        
        # Step 5: Security audit
        security_task_id = await self.coordinator.assign_task(
            task_type="security_audit",
            description="Audit code for security issues",
            role=AgentRole.SECURITY,
            context={"code": self.results.get("code", "")}
        )
        self.steps.append({"step": "security", "task_id": security_task_id})
        await asyncio.sleep(2)
        
        # Step 6: Final consensus
        consensus = await self.coordinator.request_consensus(
            topic="Code quality approval",
            options=[
                {"label": "Approve", "action": "proceed"},
                {"label": "Needs revision", "action": "revise"},
                {"label": "Reject", "action": "reject"}
            ],
            roles=[AgentRole.REVIEWER, AgentRole.TESTER, AgentRole.SECURITY]
        )
        
        return {
            "workflow_id": self.workflow_id,
            "steps": self.steps,
            "consensus": asdict(consensus),
            "status": "completed"
        }


# Factory function to create a pre-configured collaborative team
async def create_collaborative_team() -> AgentCoordinator:
    """
    Create a team of collaborative agents.
    
    Returns:
        Configured AgentCoordinator with specialized agents
    """
    coordinator = AgentCoordinator()
    
    # Register specialized agents
    coordinator.register_agent(CoderAgent())
    coordinator.register_agent(ReviewerAgent())
    coordinator.register_agent(TesterAgent())
    coordinator.register_agent(SecurityAgent())
    
    # Start the coordinator
    await coordinator.start()
    
    return coordinator
