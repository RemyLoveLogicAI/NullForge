"""
Platform Adapters
=================

Adapters for integrating with each platform in the Tri-Core architecture:
- Genspark: Multi-agent orchestration
- AOL-CLI: Terminal engine
- Clawdpoke.a0: Game framework
"""

from tri_core.adapters.base import BaseAdapter
from tri_core.adapters.genspark import GensparkAdapter
from tri_core.adapters.aol_cli import AOLCLIAdapter
from tri_core.adapters.clawdpoke import ClawdpokeAdapter

__all__ = [
    "BaseAdapter",
    "GensparkAdapter",
    "AOLCLIAdapter",
    "ClawdpokeAdapter",
]
