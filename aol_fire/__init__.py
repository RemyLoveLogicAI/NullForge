"""
AOL-CLI Fire Edition 🔥
=======================

The Ultimate AI Agent Command Line Interface

Features:
- Multi-agent orchestration with specialized agents
- Semantic memory and conversation persistence
- Advanced tool system with web search, code analysis
- Beautiful TUI with live streaming
- Plugin/extension architecture
- Code execution sandbox
- Git-aware project understanding

Usage:
    fire run "Build a full-stack app with React and FastAPI"
    fire chat  # Interactive mode with memory
    fire analyze ./project  # Deep code analysis
"""

__version__ = "2.0.0"
__codename__ = "Fire Edition"

from aol_fire.core import FireAgent, FireConfig
from aol_fire.models import AgentState, Task, Plan, Memory

__all__ = [
    "FireAgent",
    "FireConfig", 
    "AgentState",
    "Task",
    "Plan",
    "Memory",
    "__version__",
    "__codename__",
]
