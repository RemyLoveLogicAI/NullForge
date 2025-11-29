"""
Multi-agent system for AOL-CLI Fire Edition.

Specialized agents for different tasks:
- Orchestrator: Coordinates other agents
- Planner: Strategic planning
- Coder: Code generation/editing
- Researcher: Web search and analysis
- Reviewer: Code review and QA
- Debugger: Error analysis and fixing
"""

from aol_fire.agents.orchestrator import OrchestratorAgent
from aol_fire.agents.planner import PlannerAgent
from aol_fire.agents.coder import CoderAgent
from aol_fire.agents.prompts import AGENT_PROMPTS

__all__ = [
    "OrchestratorAgent",
    "PlannerAgent",
    "CoderAgent",
    "AGENT_PROMPTS",
]
