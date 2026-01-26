"""
Unified Event Bus
=================

The central nervous system of the Tri-Core architecture.
Handles all cross-platform communication via pub/sub messaging.
"""

from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
import uuid

from tri_core.models import (
    TriCoreEvent,
    Platform,
    EventPriority,
    EventSubscription,
)

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionInfo:
    """Internal subscription tracking."""
    id: str
    topic: str
    callback: Callable[[TriCoreEvent], Any]
    filters: Dict[str, Any] = field(default_factory=dict)
    platform_filter: Optional[Platform] = None
    priority_filter: Optional[Set[EventPriority]] = None
    is_async: bool = False
    
    def matches(self, event: TriCoreEvent) -> bool:
        """Check if event matches subscription filters."""
        # Platform filter
        if self.platform_filter and event.source != self.platform_filter:
            return False
            
        # Priority filter
        if self.priority_filter and event.priority not in self.priority_filter:
            return False
            
        # Custom filters
        for key, value in self.filters.items():
            if key in event.payload:
                if event.payload[key] != value:
                    return False
            elif key in event.metadata:
                if event.metadata[key] != value:
                    return False
                    
        return True


class UnifiedEventBus:
    """
    🚌 Unified Event Bus
    
    The central communication hub for the Tri-Core architecture.
    Enables seamless, event-driven messaging between:
    - Genspark (Multi-Agent Orchestration)
    - AOL-CLI (Terminal Engine)
    - Clawdpoke.a0 (Game Framework)
    
    Features:
    - Topic-based pub/sub with filtering
    - Async and sync callback support
    - State synchronization
    - Event history and replay
    - Dead letter queue for failed events
    - Correlation ID tracking
    """
    
    _instance: Optional[UnifiedEventBus] = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global event bus access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, enable_history: bool = True, max_history: int = 1000):
        """Initialize the event bus."""
        if self._initialized:
            return
            
        self._subscriptions: Dict[str, List[SubscriptionInfo]] = defaultdict(list)
        self._state: Dict[str, Any] = {}
        self._state_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: List[TriCoreEvent] = []
        self._dead_letter_queue: List[TriCoreEvent] = []
        self._enable_history = enable_history
        self._max_history = max_history
        self._correlation_map: Dict[str, List[TriCoreEvent]] = defaultdict(list)
        self._metrics = {
            "events_published": 0,
            "events_delivered": 0,
            "events_failed": 0,
            "subscriptions_active": 0,
        }
        self._lock = asyncio.Lock()
        self._initialized = True
        
        logger.info("🚌 Unified Event Bus initialized")
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton for testing."""
        cls._instance = None
    
    # =========================================================================
    # SUBSCRIPTION METHODS
    # =========================================================================
    
    def subscribe(
        self,
        topic: str,
        callback: Callable[[TriCoreEvent], Any],
        *,
        filters: Optional[Dict[str, Any]] = None,
        platform_filter: Optional[Platform] = None,
        priority_filter: Optional[Set[EventPriority]] = None,
    ) -> str:
        """
        Subscribe to events on a topic.
        
        Args:
            topic: Topic pattern (supports wildcards: 'game.*', '*')
            callback: Function to call when matching event received
            filters: Additional filters on payload/metadata
            platform_filter: Only receive events from specific platform
            priority_filter: Only receive events with specific priorities
            
        Returns:
            Subscription ID for unsubscribing
        """
        sub_id = str(uuid.uuid4())
        is_async = asyncio.iscoroutinefunction(callback)
        
        subscription = SubscriptionInfo(
            id=sub_id,
            topic=topic,
            callback=callback,
            filters=filters or {},
            platform_filter=platform_filter,
            priority_filter=priority_filter,
            is_async=is_async,
        )
        
        self._subscriptions[topic].append(subscription)
        self._metrics["subscriptions_active"] += 1
        
        logger.debug(f"📬 New subscription: {sub_id} on topic '{topic}'")
        return sub_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID."""
        for topic, subs in self._subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    self._metrics["subscriptions_active"] -= 1
                    logger.debug(f"📭 Unsubscribed: {subscription_id}")
                    return True
        return False
    
    def _match_topic(self, pattern: str, topic: str) -> bool:
        """Match topic against pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern == topic:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix + ".")
        if "*" in pattern:
            # Simple wildcard matching
            parts = pattern.split("*")
            if len(parts) == 2:
                return topic.startswith(parts[0]) and topic.endswith(parts[1])
        return False
    
    # =========================================================================
    # PUBLISH METHODS
    # =========================================================================
    
    def publish(self, topic: str, event: TriCoreEvent) -> int:
        """
        Publish an event to a topic (synchronous).
        
        Args:
            topic: Topic to publish to
            event: Event to publish
            
        Returns:
            Number of subscribers notified
        """
        # Always use sync publish for synchronous calls to avoid nested loop issues
        return self._publish_sync(topic, event)
    
    def _publish_sync(self, topic: str, event: TriCoreEvent) -> int:
        """Synchronous publish implementation."""
        self._metrics["events_published"] += 1
        
        # Store in history
        if self._enable_history:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
        
        # Track correlation
        self._correlation_map[event.correlation_id].append(event)
        
        # Find matching subscribers
        delivered = 0
        for pattern, subs in self._subscriptions.items():
            if self._match_topic(pattern, topic):
                for sub in subs:
                    if sub.matches(event):
                        try:
                            if sub.is_async:
                                # Can't run async in sync context
                                logger.warning(f"Skipping async callback in sync publish")
                                continue
                            sub.callback(event)
                            delivered += 1
                            self._metrics["events_delivered"] += 1
                        except Exception as e:
                            logger.error(f"❌ Error delivering event: {e}")
                            self._dead_letter_queue.append(event)
                            self._metrics["events_failed"] += 1
        
        logger.debug(f"📤 Published '{topic}': delivered to {delivered} subscribers")
        return delivered
    
    async def publish_async(self, topic: str, event: TriCoreEvent) -> int:
        """
        Publish an event asynchronously.
        
        Args:
            topic: Topic to publish to
            event: Event to publish
            
        Returns:
            Number of subscribers notified
        """
        async with self._lock:
            self._metrics["events_published"] += 1
            
            # Store in history
            if self._enable_history:
                self._event_history.append(event)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)
            
            # Track correlation
            self._correlation_map[event.correlation_id].append(event)
        
        # Find matching subscribers
        delivered = 0
        tasks = []
        
        for pattern, subs in self._subscriptions.items():
            if self._match_topic(pattern, topic):
                for sub in subs:
                    if sub.matches(event):
                        if sub.is_async:
                            tasks.append(self._deliver_async(sub, event))
                        else:
                            try:
                                sub.callback(event)
                                delivered += 1
                                self._metrics["events_delivered"] += 1
                            except Exception as e:
                                logger.error(f"❌ Error delivering event: {e}")
                                self._dead_letter_queue.append(event)
                                self._metrics["events_failed"] += 1
        
        # Run async callbacks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    self._metrics["events_failed"] += 1
                else:
                    delivered += 1
                    self._metrics["events_delivered"] += 1
        
        logger.debug(f"📤 Published '{topic}': delivered to {delivered} subscribers")
        return delivered
    
    async def _deliver_async(self, sub: SubscriptionInfo, event: TriCoreEvent):
        """Deliver event to async callback."""
        try:
            await sub.callback(event)
        except Exception as e:
            logger.error(f"❌ Async delivery error: {e}")
            self._dead_letter_queue.append(event)
            raise
    
    # =========================================================================
    # STATE SYNC METHODS
    # =========================================================================
    
    def sync_state(self, key: str, state: Any, source: Platform) -> None:
        """
        Synchronize state across all platforms.
        
        Args:
            key: State key
            state: State value
            source: Platform that updated the state
        """
        self._state[key] = {
            "value": state,
            "source": source,
            "updated_at": datetime.utcnow(),
        }
        
        # Notify state subscribers
        for callback in self._state_subscribers.get(key, []):
            try:
                callback(key, state, source)
            except Exception as e:
                logger.error(f"State sync callback error: {e}")
        
        # Also publish as event
        event = TriCoreEvent(
            source=source,
            event_type="state_sync",
            payload={"key": key, "value": state},
        )
        self._publish_sync(f"state.{key}", event)
        
        logger.debug(f"🔄 State synced: {key} from {source}")
    
    def get_state(self, key: str) -> Optional[Any]:
        """Get current state value."""
        entry = self._state.get(key)
        return entry["value"] if entry else None
    
    def subscribe_state(self, key: str, callback: Callable[[str, Any, Platform], None]) -> None:
        """Subscribe to state changes for a specific key."""
        self._state_subscribers[key].append(callback)
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get all current state."""
        return {k: v["value"] for k, v in self._state.items()}
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_event_history(
        self,
        topic: Optional[str] = None,
        source: Optional[Platform] = None,
        limit: int = 100,
    ) -> List[TriCoreEvent]:
        """Get event history with optional filters."""
        events = self._event_history
        
        if source:
            events = [e for e in events if e.source == source]
        
        return events[-limit:]
    
    def get_correlated_events(self, correlation_id: str) -> List[TriCoreEvent]:
        """Get all events with the same correlation ID."""
        return self._correlation_map.get(correlation_id, [])
    
    def get_dead_letters(self) -> List[TriCoreEvent]:
        """Get events that failed delivery."""
        return self._dead_letter_queue.copy()
    
    def clear_dead_letters(self) -> int:
        """Clear and return count of dead letters."""
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return count
    
    def get_metrics(self) -> Dict[str, int]:
        """Get event bus metrics."""
        return self._metrics.copy()
    
    def __repr__(self) -> str:
        return (
            f"UnifiedEventBus("
            f"subscriptions={self._metrics['subscriptions_active']}, "
            f"published={self._metrics['events_published']}, "
            f"delivered={self._metrics['events_delivered']})"
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_event_bus() -> UnifiedEventBus:
    """Get the global event bus instance."""
    return UnifiedEventBus()


def emit(
    topic: str,
    event_type: str,
    payload: Dict[str, Any],
    source: Platform = Platform.TRINITY,
    priority: EventPriority = EventPriority.NORMAL,
) -> int:
    """
    Convenience function to emit an event.
    
    Args:
        topic: Topic to publish to
        event_type: Type of event
        payload: Event payload
        source: Source platform
        priority: Event priority
        
    Returns:
        Number of subscribers notified
    """
    event = TriCoreEvent(
        source=source,
        event_type=event_type,
        payload=payload,
        priority=priority,
    )
    return get_event_bus().publish(topic, event)
