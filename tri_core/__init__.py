"""
🔥 Tri-Core Integration Architecture
=====================================

Genspark + AOL-CLI + Clawdpoke.a0

A unified platform combining three powerful systems:
- Genspark: Multi-agent orchestration & creative AI
- AOL-CLI: LangGraph terminal engine & code execution  
- Clawdpoke.a0: Game framework with skill system

Built for hackathons. Built for production.
"""

__version__ = "1.0.0"
__author__ = "Tri-Core Contributors"

from tri_core.event_bus.bus import UnifiedEventBus, TriCoreEvent
from tri_core.orchestrator.trinity import TrinityOrchestrator
from tri_core.adapters.base import BaseAdapter
from tri_core.clawdpoke.game_engine import ClawdpokeEngine
from tri_core.workflows.pipeline import GameDevPipeline

__all__ = [
    "UnifiedEventBus",
    "TriCoreEvent", 
    "TrinityOrchestrator",
    "BaseAdapter",
    "ClawdpokeEngine",
    "GameDevPipeline",
    "__version__",
]
