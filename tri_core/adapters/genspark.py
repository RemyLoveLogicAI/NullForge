"""
Genspark Adapter
================

Adapter for integrating with Genspark's multi-agent orchestration system.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from tri_core.models import Platform, AgentCapability
from tri_core.adapters.base import BaseAdapter, AdapterConfig

logger = logging.getLogger(__name__)


@dataclass
class GensparkConfig(AdapterConfig):
    """Configuration for Genspark adapter."""
    api_endpoint: str = "https://api.genspark.ai/v1"
    api_key: Optional[str] = None
    default_agent: str = "SuperAgent"
    enable_sparkpages: bool = True
    enable_inbox: bool = True


@dataclass
class AgentInfo:
    """Information about a Genspark agent."""
    id: str
    name: str
    description: str
    capabilities: List[AgentCapability]
    is_available: bool = True


class GensparkAdapter(BaseAdapter):
    """
    🌟 Genspark Adapter
    
    Connects to Genspark's multi-agent orchestration platform.
    
    Features:
    - Agent orchestration
    - Sparkpages document access
    - AI Inbox integration
    - Multi-agent coordination
    
    Supported Actions:
    - call_agent: Execute task with specific agent
    - list_agents: Get available agents
    - create_sparkpage: Create a Sparkpage document
    - send_inbox: Send message to AI Inbox
    - orchestrate: Multi-agent task orchestration
    """
    
    # Available Genspark agents
    AGENTS = {
        "SuperAgent": AgentInfo(
            id="super_agent",
            name="SuperAgent",
            description="Master orchestrator that coordinates all other agents",
            capabilities=[
                AgentCapability(name="orchestration", description="Coordinate complex tasks", skill_level=10),
                AgentCapability(name="planning", description="Create execution plans", skill_level=9),
                AgentCapability(name="delegation", description="Delegate to specialized agents", skill_level=10),
            ],
        ),
        "AIDesigner": AgentInfo(
            id="ai_designer",
            name="AIDesigner",
            description="Expert in visual design and UI/UX",
            capabilities=[
                AgentCapability(name="creative_design", description="Create visual designs", skill_level=9),
                AgentCapability(name="ui_design", description="Design user interfaces", skill_level=9),
                AgentCapability(name="branding", description="Brand identity design", skill_level=8),
            ],
        ),
        "AIDoc": AgentInfo(
            id="ai_doc",
            name="AIDoc",
            description="Expert in documentation and narrative writing",
            capabilities=[
                AgentCapability(name="narrative_creation", description="Write compelling narratives", skill_level=9),
                AgentCapability(name="documentation", description="Technical documentation", skill_level=9),
                AgentCapability(name="copywriting", description="Marketing and copy", skill_level=8),
            ],
        ),
        "AIImage": AgentInfo(
            id="ai_image",
            name="AIImage",
            description="Expert in image generation and manipulation",
            capabilities=[
                AgentCapability(name="asset_generation", description="Generate visual assets", skill_level=10),
                AgentCapability(name="image_editing", description="Edit and enhance images", skill_level=8),
                AgentCapability(name="style_transfer", description="Apply artistic styles", skill_level=8),
            ],
        ),
        "AICoder": AgentInfo(
            id="ai_coder",
            name="AICoder",
            description="Expert in code generation and software development",
            capabilities=[
                AgentCapability(name="code_generation", description="Generate code", skill_level=10),
                AgentCapability(name="debugging", description="Find and fix bugs", skill_level=9),
                AgentCapability(name="code_review", description="Review code quality", skill_level=9),
            ],
        ),
        "AIResearcher": AgentInfo(
            id="ai_researcher",
            name="AIResearcher",
            description="Expert in research and information gathering",
            capabilities=[
                AgentCapability(name="research", description="Research topics thoroughly", skill_level=9),
                AgentCapability(name="analysis", description="Analyze information", skill_level=8),
                AgentCapability(name="summarization", description="Summarize findings", skill_level=9),
            ],
        ),
        "GameDesigner": AgentInfo(
            id="game_designer",
            name="GameDesigner",
            description="Expert in game design and mechanics",
            capabilities=[
                AgentCapability(name="game_design", description="Design game systems", skill_level=9),
                AgentCapability(name="level_design", description="Design game levels", skill_level=8),
                AgentCapability(name="balancing", description="Balance game mechanics", skill_level=8),
            ],
        ),
        "NarrativeWriter": AgentInfo(
            id="narrative_writer",
            name="NarrativeWriter",
            description="Expert in game narratives and dialogue",
            capabilities=[
                AgentCapability(name="narrative_creation", description="Create game stories", skill_level=10),
                AgentCapability(name="dialogue_writing", description="Write character dialogue", skill_level=9),
                AgentCapability(name="world_building", description="Build game worlds", skill_level=8),
            ],
        ),
    }
    
    def __init__(self, config: Optional[GensparkConfig] = None):
        """Initialize the Genspark adapter."""
        super().__init__(config or GensparkConfig())
        self.genspark_config: GensparkConfig = self.config  # type: ignore
        
        # Agent registry
        self._agents = self.AGENTS.copy()
        
        # Sparkpages storage (simulated)
        self._sparkpages: Dict[str, Dict[str, Any]] = {}
        
        # Inbox messages (simulated)
        self._inbox: List[Dict[str, Any]] = []
    
    @property
    def platform(self) -> Platform:
        return Platform.GENSPARK
    
    async def _execute_impl(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a Genspark action."""
        
        if action == "call_agent":
            return await self._call_agent(params)
        elif action == "list_agents":
            return await self._list_agents(params)
        elif action == "create_sparkpage":
            return await self._create_sparkpage(params)
        elif action == "send_inbox":
            return await self._send_inbox(params)
        elif action == "orchestrate":
            return await self._orchestrate(params)
        elif action == "get_sparkpage":
            return await self._get_sparkpage(params)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def health_check(self) -> bool:
        """Check Genspark API health."""
        # Simulated health check
        return True
    
    # =========================================================================
    # AGENT OPERATIONS
    # =========================================================================
    
    async def _call_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a specific Genspark agent.
        
        Params:
            agent: Agent name
            task: Task description
            context: Additional context
        """
        agent_name = params.get("agent", self.genspark_config.default_agent)
        task = params.get("task", "")
        context = params.get("context", {})
        
        if agent_name not in self._agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        agent = self._agents[agent_name]
        
        logger.info(f"🌟 Calling {agent_name} with task: {task[:50]}...")
        
        # Simulate agent execution
        await asyncio.sleep(0.1)  # Simulated latency
        
        # Generate response based on agent capabilities
        response = {
            "agent": agent_name,
            "agent_id": agent.id,
            "task": task,
            "status": "completed",
            "result": self._generate_agent_response(agent, task, context),
            "artifacts": [],
        }
        
        # If agent creates documents, add sparkpage
        if agent_name in ["AIDoc", "NarrativeWriter", "GameDesigner"]:
            sparkpage_id = f"sp_{len(self._sparkpages)}"
            self._sparkpages[sparkpage_id] = {
                "id": sparkpage_id,
                "title": f"Output: {task[:30]}",
                "content": response["result"],
                "created_by": agent_name,
            }
            response["artifacts"].append({
                "type": "sparkpage",
                "id": sparkpage_id,
            })
        
        return response
    
    def _generate_agent_response(
        self,
        agent: AgentInfo,
        task: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a response based on agent type."""
        task_lower = task.lower()
        
        if agent.name == "SuperAgent":
            return {
                "type": "orchestration_plan",
                "steps": [
                    {"agent": "AIResearcher", "task": "Research requirements"},
                    {"agent": "AICoder", "task": "Implement solution"},
                    {"agent": "AIDoc", "task": "Document results"},
                ],
                "summary": f"Orchestrated plan for: {task}",
            }
        
        elif agent.name == "AIDesigner":
            return {
                "type": "design",
                "elements": ["layout", "colors", "typography"],
                "recommendations": [
                    "Use a clean, modern layout",
                    "Implement consistent color scheme",
                    "Ensure accessibility standards",
                ],
            }
        
        elif agent.name == "AIDoc":
            return {
                "type": "documentation",
                "sections": ["overview", "details", "examples"],
                "content": f"# Documentation\n\n## Overview\n\n{task}\n\n## Details\n\nGenerated documentation content...",
            }
        
        elif agent.name == "AICoder":
            return {
                "type": "code",
                "language": context.get("language", "python"),
                "files": [
                    {
                        "path": "main.py",
                        "content": f"# Generated code for: {task}\n\ndef main():\n    pass\n",
                    }
                ],
            }
        
        elif agent.name == "GameDesigner":
            return {
                "type": "game_design",
                "mechanics": ["core_loop", "progression", "rewards"],
                "document": {
                    "title": "Game Design Document",
                    "concept": task,
                    "features": [],
                },
            }
        
        elif agent.name == "NarrativeWriter":
            return {
                "type": "narrative",
                "elements": ["characters", "plot", "world"],
                "story": {
                    "title": "Generated Story",
                    "synopsis": task,
                    "chapters": [],
                },
            }
        
        else:
            return {
                "type": "generic",
                "result": f"Completed: {task}",
            }
    
    async def _list_agents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available agents."""
        include_capabilities = params.get("include_capabilities", False)
        
        agents = []
        for name, agent in self._agents.items():
            info = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "is_available": agent.is_available,
            }
            if include_capabilities:
                info["capabilities"] = [
                    {"name": c.name, "level": c.skill_level}
                    for c in agent.capabilities
                ]
            agents.append(info)
        
        return {"agents": agents}
    
    # =========================================================================
    # SPARKPAGE OPERATIONS
    # =========================================================================
    
    async def _create_sparkpage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Sparkpage document."""
        title = params.get("title", "Untitled")
        content = params.get("content", "")
        template = params.get("template")
        
        sparkpage_id = f"sp_{len(self._sparkpages)}"
        
        self._sparkpages[sparkpage_id] = {
            "id": sparkpage_id,
            "title": title,
            "content": content,
            "template": template,
            "created_at": "2024-01-01T00:00:00Z",
        }
        
        logger.info(f"📄 Created Sparkpage: {title}")
        
        return {
            "id": sparkpage_id,
            "title": title,
            "url": f"https://genspark.ai/sparkpage/{sparkpage_id}",
        }
    
    async def _get_sparkpage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a Sparkpage by ID."""
        sparkpage_id = params.get("id")
        
        if sparkpage_id not in self._sparkpages:
            raise ValueError(f"Sparkpage not found: {sparkpage_id}")
        
        return self._sparkpages[sparkpage_id]
    
    # =========================================================================
    # INBOX OPERATIONS
    # =========================================================================
    
    async def _send_inbox(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to AI Inbox."""
        message = params.get("message", "")
        priority = params.get("priority", "normal")
        
        inbox_item = {
            "id": f"inbox_{len(self._inbox)}",
            "message": message,
            "priority": priority,
            "status": "pending",
        }
        
        self._inbox.append(inbox_item)
        
        logger.info(f"📬 Sent to inbox: {message[:50]}...")
        
        return inbox_item
    
    # =========================================================================
    # ORCHESTRATION
    # =========================================================================
    
    async def _orchestrate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate a complex multi-agent task.
        
        Params:
            goal: High-level goal
            agents: Optional list of agents to use
            strategy: Orchestration strategy
        """
        goal = params.get("goal", "")
        agents = params.get("agents", ["SuperAgent"])
        strategy = params.get("strategy", "sequential")
        
        logger.info(f"🎭 Orchestrating: {goal}")
        
        # First, call SuperAgent to create a plan
        plan_result = await self._call_agent({
            "agent": "SuperAgent",
            "task": goal,
            "context": {"strategy": strategy},
        })
        
        results = [plan_result]
        
        # Execute the plan steps
        if "steps" in plan_result.get("result", {}):
            for step in plan_result["result"]["steps"]:
                step_result = await self._call_agent({
                    "agent": step["agent"],
                    "task": step["task"],
                    "context": {"parent_goal": goal},
                })
                results.append(step_result)
        
        return {
            "goal": goal,
            "strategy": strategy,
            "steps_completed": len(results),
            "results": results,
        }
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def register_agent(self, agent: AgentInfo) -> None:
        """Register a custom agent."""
        self._agents[agent.name] = agent
    
    def get_sparkpages(self) -> Dict[str, Dict[str, Any]]:
        """Get all Sparkpages."""
        return self._sparkpages.copy()
    
    def get_inbox(self) -> List[Dict[str, Any]]:
        """Get inbox messages."""
        return self._inbox.copy()
