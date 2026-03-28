"""
Agent Router
============

Routes requests to appropriate Genspark agents based on
task requirements and agent specializations.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from tri_core.models import (
    Platform,
    AgentRequest,
    AgentResponse,
    AgentCapability,
    DEFAULT_CAPABILITY_MAP,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentProfile:
    """Profile of a Genspark agent."""
    id: str
    name: str
    capabilities: List[AgentCapability]
    specializations: List[str]
    current_load: int = 0
    max_concurrent: int = 5
    priority: int = 0  # Higher = more preferred
    
    @property
    def is_available(self) -> bool:
        """Check if agent can accept new tasks."""
        return self.current_load < self.max_concurrent
    
    def matches_capabilities(self, required: List[str]) -> float:
        """
        Calculate match score for required capabilities.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not required:
            return 1.0
        
        agent_caps = {cap.name for cap in self.capabilities}
        matches = sum(1 for r in required if r in agent_caps)
        return matches / len(required)


class AgentRouter:
    """
    🎯 Agent Router
    
    Intelligent routing of requests to Genspark agents.
    
    Features:
    - Capability-based routing
    - Load balancing
    - Specialization matching
    - Fallback strategies
    """
    
    # Default Genspark agents
    DEFAULT_AGENTS = [
        AgentProfile(
            id="super_agent",
            name="SuperAgent",
            capabilities=[
                AgentCapability(name="orchestration", description="Coordinate complex tasks", skill_level=10),
                AgentCapability(name="planning", description="Create execution plans", skill_level=9),
            ],
            specializations=["coordination", "planning", "delegation"],
            priority=10,
        ),
        AgentProfile(
            id="ai_designer",
            name="AIDesigner",
            capabilities=[
                AgentCapability(name="creative_design", description="Visual design and UI", skill_level=9),
                AgentCapability(name="asset_generation", description="Generate visual assets", skill_level=8),
            ],
            specializations=["ui", "visual", "graphics", "design"],
            priority=7,
        ),
        AgentProfile(
            id="ai_doc",
            name="AIDoc",
            capabilities=[
                AgentCapability(name="narrative_creation", description="Write stories and documentation", skill_level=9),
                AgentCapability(name="content_writing", description="Create written content", skill_level=9),
            ],
            specializations=["narrative", "documentation", "writing", "story"],
            priority=7,
        ),
        AgentProfile(
            id="ai_image",
            name="AIImage",
            capabilities=[
                AgentCapability(name="asset_generation", description="Generate images", skill_level=10),
                AgentCapability(name="image_editing", description="Edit and manipulate images", skill_level=8),
            ],
            specializations=["image", "sprite", "texture", "art"],
            priority=7,
        ),
        AgentProfile(
            id="ai_coder",
            name="AICoder",
            capabilities=[
                AgentCapability(name="code_generation", description="Write code", skill_level=10),
                AgentCapability(name="code_review", description="Review and improve code", skill_level=9),
                AgentCapability(name="debugging", description="Fix bugs", skill_level=9),
            ],
            specializations=["code", "programming", "development", "implementation"],
            priority=8,
        ),
        AgentProfile(
            id="ai_researcher",
            name="AIResearcher",
            capabilities=[
                AgentCapability(name="research", description="Research topics", skill_level=9),
                AgentCapability(name="analysis", description="Analyze information", skill_level=8),
            ],
            specializations=["research", "analysis", "investigation"],
            priority=6,
        ),
    ]
    
    def __init__(self):
        """Initialize the agent router."""
        self._agents: Dict[str, AgentProfile] = {}
        self._routing_history: List[Dict[str, Any]] = []
        
        # Register default agents
        for agent in self.DEFAULT_AGENTS:
            self.register_agent(agent)
        
        logger.info(f"🎯 Agent Router initialized with {len(self._agents)} agents")
    
    def register_agent(self, agent: AgentProfile) -> None:
        """Register an agent."""
        self._agents[agent.id] = agent
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
    
    def route(self, request: AgentRequest) -> str:
        """
        Route a request to the best available agent.
        
        Args:
            request: Agent request
            
        Returns:
            Selected agent ID
        """
        candidates = self._find_candidates(request)
        
        if not candidates:
            # Fallback to SuperAgent
            logger.warning("No suitable agents found, falling back to SuperAgent")
            return "super_agent"
        
        # Score and rank candidates
        scored = []
        for agent in candidates:
            score = self._calculate_score(agent, request)
            scored.append((score, agent))
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        selected = scored[0][1]
        
        # Record routing decision
        self._routing_history.append({
            "request_id": request.id,
            "selected_agent": selected.id,
            "score": scored[0][0],
            "candidates": [a.id for _, a in scored],
        })
        
        logger.info(f"🎯 Routed request {request.id} to {selected.name} (score: {scored[0][0]:.2f})")
        return selected.id
    
    def _find_candidates(self, request: AgentRequest) -> List[AgentProfile]:
        """Find candidate agents for a request."""
        candidates = []
        
        for agent in self._agents.values():
            # Must be available
            if not agent.is_available:
                continue
            
            # Check capability match
            if request.required_capabilities:
                match_score = agent.matches_capabilities(request.required_capabilities)
                if match_score > 0:
                    candidates.append(agent)
            else:
                candidates.append(agent)
        
        return candidates
    
    def _calculate_score(self, agent: AgentProfile, request: AgentRequest) -> float:
        """Calculate routing score for an agent."""
        score = 0.0
        
        # Capability match (0-40 points)
        cap_match = agent.matches_capabilities(request.required_capabilities)
        score += cap_match * 40
        
        # Specialization match (0-30 points)
        task_words = set(request.task.lower().split())
        spec_matches = sum(1 for spec in agent.specializations if spec in task_words)
        spec_score = min(spec_matches / max(len(agent.specializations), 1), 1.0)
        score += spec_score * 30
        
        # Load factor (0-15 points) - prefer less loaded agents
        load_factor = 1 - (agent.current_load / agent.max_concurrent)
        score += load_factor * 15
        
        # Priority (0-15 points)
        priority_score = agent.priority / 10
        score += priority_score * 15
        
        return score
    
    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[AgentProfile]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def get_routing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent routing decisions."""
        return self._routing_history[-limit:]
    
    def update_load(self, agent_id: str, delta: int) -> None:
        """Update agent load."""
        if agent_id in self._agents:
            self._agents[agent_id].current_load += delta
    
    def __repr__(self) -> str:
        available = sum(1 for a in self._agents.values() if a.is_available)
        return f"AgentRouter(agents={len(self._agents)}, available={available})"
