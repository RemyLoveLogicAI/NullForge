"""
Trinity Orchestrator
====================

The central command and control system managing workflow transitions
between Genspark, AOL-CLI, and Clawdpoke.a0 platforms.
"""

from tri_core.orchestrator.trinity import TrinityOrchestrator
from tri_core.orchestrator.router import AgentRouter
from tri_core.orchestrator.executor import CLIExecutor
from tri_core.orchestrator.game_manager import GameStateManager
from tri_core.orchestrator.interface_selector import InterfaceSelector

__all__ = [
    "TrinityOrchestrator",
    "AgentRouter",
    "CLIExecutor", 
    "GameStateManager",
    "InterfaceSelector",
]
