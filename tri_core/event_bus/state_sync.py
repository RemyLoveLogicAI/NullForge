"""
State Synchronization
=====================

Real-time state synchronization across all platforms in the Tri-Core architecture.
Maintains consistent context throughout complex multi-platform operations.
"""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
import copy

from tri_core.models import Platform

logger = logging.getLogger(__name__)


@dataclass
class StateEntry:
    """A single state entry with metadata."""
    value: Any
    source: Platform
    version: int
    updated_at: datetime
    expires_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    
    def is_expired(self) -> bool:
        """Check if state entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class StateChange:
    """Record of a state change for history tracking."""
    key: str
    old_value: Any
    new_value: Any
    source: Platform
    version: int
    timestamp: datetime


class StateSync:
    """
    🔄 State Synchronization Manager
    
    Maintains consistent state across all three platforms:
    - Genspark agent context
    - AOL-CLI execution state
    - Clawdpoke.a0 game state
    
    Features:
    - Version-controlled state
    - Conflict resolution
    - State expiration
    - Change history
    - Selective synchronization
    - Snapshot and restore
    """
    
    def __init__(
        self,
        max_history: int = 100,
        enable_snapshots: bool = True,
    ):
        """Initialize state sync manager."""
        self._state: Dict[str, StateEntry] = {}
        self._history: List[StateChange] = []
        self._max_history = max_history
        self._snapshots: Dict[str, Dict[str, StateEntry]] = {}
        self._enable_snapshots = enable_snapshots
        self._listeners: Dict[str, List[Callable]] = {}
        self._global_listeners: List[Callable] = []
        self._platform_versions: Dict[Platform, int] = {
            Platform.GENSPARK: 0,
            Platform.AOL_CLI: 0,
            Platform.CLAWDPOKE: 0,
            Platform.TRINITY: 0,
        }
        self._lock = asyncio.Lock()
        
        logger.info("🔄 State Sync Manager initialized")
    
    # =========================================================================
    # STATE OPERATIONS
    # =========================================================================
    
    def set(
        self,
        key: str,
        value: Any,
        source: Platform,
        *,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
    ) -> int:
        """
        Set a state value.
        
        Args:
            key: State key
            value: State value (will be deep copied)
            source: Platform setting the state
            ttl: Time to live in seconds (optional)
            tags: Tags for grouping/filtering
            
        Returns:
            New version number
        """
        now = datetime.utcnow()
        old_entry = self._state.get(key)
        old_value = old_entry.value if old_entry else None
        
        # Increment version
        version = (old_entry.version + 1) if old_entry else 1
        self._platform_versions[source] = max(
            self._platform_versions[source], version
        )
        
        # Create new entry
        entry = StateEntry(
            value=copy.deepcopy(value),
            source=source,
            version=version,
            updated_at=now,
            expires_at=now + timedelta(seconds=ttl) if ttl else None,
            tags=tags or set(),
        )
        
        self._state[key] = entry
        
        # Record history
        change = StateChange(
            key=key,
            old_value=old_value,
            new_value=value,
            source=source,
            version=version,
            timestamp=now,
        )
        self._history.append(change)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        # Notify listeners
        self._notify_listeners(key, value, source, version)
        
        logger.debug(f"🔄 State set: {key} v{version} by {source}")
        return version
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value.
        
        Args:
            key: State key
            default: Default value if not found
            
        Returns:
            State value or default
        """
        entry = self._state.get(key)
        if entry is None:
            return default
        if entry.is_expired():
            del self._state[key]
            return default
        return copy.deepcopy(entry.value)
    
    def get_with_metadata(self, key: str) -> Optional[StateEntry]:
        """Get state entry with full metadata."""
        entry = self._state.get(key)
        if entry and entry.is_expired():
            del self._state[key]
            return None
        return entry
    
    def delete(self, key: str, source: Platform) -> bool:
        """Delete a state key."""
        if key in self._state:
            old_value = self._state[key].value
            del self._state[key]
            
            change = StateChange(
                key=key,
                old_value=old_value,
                new_value=None,
                source=source,
                version=-1,
                timestamp=datetime.utcnow(),
            )
            self._history.append(change)
            
            logger.debug(f"🗑️ State deleted: {key} by {source}")
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if a state key exists and is not expired."""
        entry = self._state.get(key)
        if entry is None:
            return False
        if entry.is_expired():
            del self._state[key]
            return False
        return True
    
    def keys(self, pattern: Optional[str] = None, tag: Optional[str] = None) -> List[str]:
        """
        Get all keys, optionally filtered by pattern or tag.
        
        Args:
            pattern: Glob pattern (e.g., 'game.*')
            tag: Filter by tag
        """
        # Clean expired entries
        self._clean_expired()
        
        keys = list(self._state.keys())
        
        if pattern:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                keys = [k for k in keys if k.startswith(prefix)]
            elif "*" in pattern:
                import fnmatch
                keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
        
        if tag:
            keys = [k for k in keys if tag in self._state[k].tags]
        
        return keys
    
    def _clean_expired(self) -> int:
        """Remove expired entries."""
        expired = [k for k, v in self._state.items() if v.is_expired()]
        for key in expired:
            del self._state[key]
        return len(expired)
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def set_many(
        self,
        items: Dict[str, Any],
        source: Platform,
        **kwargs,
    ) -> Dict[str, int]:
        """Set multiple state values at once."""
        return {
            key: self.set(key, value, source, **kwargs)
            for key, value in items.items()
        }
    
    def get_many(self, keys: List[str], default: Any = None) -> Dict[str, Any]:
        """Get multiple state values at once."""
        return {key: self.get(key, default) for key in keys}
    
    def get_by_tag(self, tag: str) -> Dict[str, Any]:
        """Get all state entries with a specific tag."""
        self._clean_expired()
        return {
            key: entry.value
            for key, entry in self._state.items()
            if tag in entry.tags
        }
    
    def get_by_source(self, source: Platform) -> Dict[str, Any]:
        """Get all state entries from a specific platform."""
        self._clean_expired()
        return {
            key: entry.value
            for key, entry in self._state.items()
            if entry.source == source
        }
    
    # =========================================================================
    # LISTENERS
    # =========================================================================
    
    def on_change(
        self,
        key: str,
        callback: Callable[[str, Any, Platform, int], None],
    ) -> None:
        """
        Register a listener for state changes on a specific key.
        
        Args:
            key: State key to watch
            callback: Function(key, value, source, version)
        """
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)
    
    def on_any_change(
        self,
        callback: Callable[[str, Any, Platform, int], None],
    ) -> None:
        """Register a global listener for all state changes."""
        self._global_listeners.append(callback)
    
    def _notify_listeners(
        self,
        key: str,
        value: Any,
        source: Platform,
        version: int,
    ) -> None:
        """Notify all relevant listeners of a state change."""
        # Key-specific listeners
        for callback in self._listeners.get(key, []):
            try:
                callback(key, value, source, version)
            except Exception as e:
                logger.error(f"Listener error for {key}: {e}")
        
        # Pattern-matching listeners (e.g., 'game.*')
        for pattern, callbacks in self._listeners.items():
            if pattern.endswith("*") and key.startswith(pattern[:-1]):
                for callback in callbacks:
                    try:
                        callback(key, value, source, version)
                    except Exception as e:
                        logger.error(f"Pattern listener error: {e}")
        
        # Global listeners
        for callback in self._global_listeners:
            try:
                callback(key, value, source, version)
            except Exception as e:
                logger.error(f"Global listener error: {e}")
    
    # =========================================================================
    # SNAPSHOTS
    # =========================================================================
    
    def create_snapshot(self, name: str) -> str:
        """
        Create a snapshot of current state.
        
        Args:
            name: Snapshot name
            
        Returns:
            Snapshot ID (name)
        """
        if not self._enable_snapshots:
            raise RuntimeError("Snapshots are disabled")
        
        self._snapshots[name] = {
            key: StateEntry(
                value=copy.deepcopy(entry.value),
                source=entry.source,
                version=entry.version,
                updated_at=entry.updated_at,
                expires_at=entry.expires_at,
                tags=entry.tags.copy(),
            )
            for key, entry in self._state.items()
        }
        
        logger.info(f"📸 Snapshot created: {name}")
        return name
    
    def restore_snapshot(self, name: str) -> bool:
        """
        Restore state from a snapshot.
        
        Args:
            name: Snapshot name
            
        Returns:
            Success status
        """
        if name not in self._snapshots:
            return False
        
        self._state = {
            key: StateEntry(
                value=copy.deepcopy(entry.value),
                source=entry.source,
                version=entry.version,
                updated_at=entry.updated_at,
                expires_at=entry.expires_at,
                tags=entry.tags.copy(),
            )
            for key, entry in self._snapshots[name].items()
        }
        
        logger.info(f"🔄 Snapshot restored: {name}")
        return True
    
    def list_snapshots(self) -> List[str]:
        """List all snapshot names."""
        return list(self._snapshots.keys())
    
    def delete_snapshot(self, name: str) -> bool:
        """Delete a snapshot."""
        if name in self._snapshots:
            del self._snapshots[name]
            return True
        return False
    
    # =========================================================================
    # HISTORY
    # =========================================================================
    
    def get_history(
        self,
        key: Optional[str] = None,
        source: Optional[Platform] = None,
        limit: int = 50,
    ) -> List[StateChange]:
        """
        Get state change history.
        
        Args:
            key: Filter by key
            source: Filter by source platform
            limit: Maximum entries to return
        """
        history = self._history
        
        if key:
            history = [h for h in history if h.key == key]
        if source:
            history = [h for h in history if h.source == source]
        
        return history[-limit:]
    
    def get_version(self, key: str) -> int:
        """Get current version of a state key."""
        entry = self._state.get(key)
        return entry.version if entry else 0
    
    def get_platform_version(self, platform: Platform) -> int:
        """Get the highest version number from a platform."""
        return self._platform_versions.get(platform, 0)
    
    # =========================================================================
    # CONFLICT RESOLUTION
    # =========================================================================
    
    def merge(
        self,
        key: str,
        value: Any,
        source: Platform,
        strategy: str = "latest",
    ) -> int:
        """
        Merge a value with conflict resolution.
        
        Args:
            key: State key
            value: New value
            source: Source platform
            strategy: Conflict resolution strategy
                - 'latest': Most recent wins
                - 'highest_version': Highest version wins
                - 'source_priority': Priority by source platform
                
        Returns:
            Resulting version number
        """
        existing = self._state.get(key)
        
        if existing is None:
            return self.set(key, value, source)
        
        should_update = False
        
        if strategy == "latest":
            should_update = True
        elif strategy == "highest_version":
            # Compare version numbers
            incoming_version = self._platform_versions[source]
            should_update = incoming_version >= existing.version
        elif strategy == "source_priority":
            # Priority: CLAWDPOKE > AOL_CLI > GENSPARK > TRINITY
            priority = {
                Platform.CLAWDPOKE: 4,
                Platform.AOL_CLI: 3,
                Platform.GENSPARK: 2,
                Platform.TRINITY: 1,
            }
            should_update = priority.get(source, 0) >= priority.get(existing.source, 0)
        
        if should_update:
            return self.set(key, value, source)
        
        return existing.version
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def clear(self, source: Optional[Platform] = None) -> int:
        """
        Clear all state or state from a specific source.
        
        Args:
            source: If provided, only clear state from this platform
            
        Returns:
            Number of entries cleared
        """
        if source is None:
            count = len(self._state)
            self._state.clear()
            return count
        
        keys_to_delete = [
            k for k, v in self._state.items()
            if v.source == source
        ]
        for key in keys_to_delete:
            del self._state[key]
        return len(keys_to_delete)
    
    def stats(self) -> Dict[str, Any]:
        """Get state synchronization statistics."""
        self._clean_expired()
        
        by_source = {}
        for entry in self._state.values():
            source = entry.source.value if hasattr(entry.source, 'value') else str(entry.source)
            by_source[source] = by_source.get(source, 0) + 1
        
        return {
            "total_entries": len(self._state),
            "by_source": by_source,
            "history_size": len(self._history),
            "snapshots": len(self._snapshots),
            "platform_versions": {
                k.value if hasattr(k, 'value') else str(k): v 
                for k, v in self._platform_versions.items()
            },
        }
    
    def __repr__(self) -> str:
        stats = self.stats()
        return f"StateSync(entries={stats['total_entries']}, history={stats['history_size']})"
