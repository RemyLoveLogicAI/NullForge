"""
Unified Event Bus
=================

Event-driven messaging system creating a shared communication layer
between all three platforms (Genspark, AOL-CLI, Clawdpoke.a0).
"""

from tri_core.event_bus.bus import UnifiedEventBus, TriCoreEvent
from tri_core.event_bus.state_sync import StateSync
from tri_core.event_bus.event_bridge import EventBridge

__all__ = ["UnifiedEventBus", "TriCoreEvent", "StateSync", "EventBridge"]
