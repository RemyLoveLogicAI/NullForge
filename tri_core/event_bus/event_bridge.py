"""
Event Bridge
============

Standardized message format converter and transformation layer
for cross-platform events in the Tri-Core architecture.
"""

from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass

from tri_core.models import (
    TriCoreEvent,
    Platform,
    EventPriority,
    IntegrationMessage,
    MessageSource,
    MessageTarget,
    MessageMetadata,
)

logger = logging.getLogger(__name__)


@dataclass
class TransformRule:
    """Rule for transforming data between platforms."""
    source_platform: Platform
    target_platform: Platform
    source_field: str
    target_field: str
    transformer: Optional[Callable[[Any], Any]] = None


class EventBridge:
    """
    🌉 Event Bridge
    
    Handles transformation and routing of events between platforms.
    Ensures data format compatibility and semantic consistency.
    
    Features:
    - Platform-specific format conversion
    - Field mapping and transformation
    - Protocol validation
    - Message serialization/deserialization
    - Route registration
    """
    
    # Standard field mappings between platforms
    GENSPARK_FIELD_MAP = {
        "agent_id": "source_agent",
        "task_id": "request_id",
        "result": "output",
        "artifacts": "generated_files",
    }
    
    AOL_CLI_FIELD_MAP = {
        "command": "cli_command",
        "exit_code": "status_code",
        "stdout": "output",
        "stderr": "error_output",
    }
    
    CLAWDPOKE_FIELD_MAP = {
        "player_state": "game_context",
        "action": "game_action",
        "skill_id": "ability_id",
        "narrative": "story_branch",
    }
    
    def __init__(self):
        """Initialize the event bridge."""
        self._transform_rules: List[TransformRule] = []
        self._routes: Dict[str, List[Platform]] = {}
        self._validators: Dict[Platform, Callable[[Dict], bool]] = {}
        self._interceptors: List[Callable[[TriCoreEvent], Optional[TriCoreEvent]]] = []
        
        # Register default transform rules
        self._register_default_rules()
        
        logger.info("🌉 Event Bridge initialized")
    
    def _register_default_rules(self) -> None:
        """Register default transformation rules."""
        # Genspark -> AOL-CLI
        self.add_transform_rule(TransformRule(
            source_platform=Platform.GENSPARK,
            target_platform=Platform.AOL_CLI,
            source_field="agent_result",
            target_field="task_input",
        ))
        
        # AOL-CLI -> Clawdpoke
        self.add_transform_rule(TransformRule(
            source_platform=Platform.AOL_CLI,
            target_platform=Platform.CLAWDPOKE,
            source_field="generated_code",
            target_field="game_script",
        ))
        
        # Clawdpoke -> Genspark
        self.add_transform_rule(TransformRule(
            source_platform=Platform.CLAWDPOKE,
            target_platform=Platform.GENSPARK,
            source_field="player_feedback",
            target_field="context_update",
        ))
    
    # =========================================================================
    # TRANSFORMATION
    # =========================================================================
    
    def add_transform_rule(self, rule: TransformRule) -> None:
        """Add a transformation rule."""
        self._transform_rules.append(rule)
    
    def transform(
        self,
        data: Dict[str, Any],
        source: Platform,
        target: Platform,
    ) -> Dict[str, Any]:
        """
        Transform data from source platform format to target platform format.
        
        Args:
            data: Source data
            source: Source platform
            target: Target platform
            
        Returns:
            Transformed data
        """
        result = data.copy()
        
        # Apply field mappings
        field_map = self._get_field_map(source, target)
        for source_field, target_field in field_map.items():
            if source_field in result:
                result[target_field] = result.pop(source_field)
        
        # Apply custom transform rules
        for rule in self._transform_rules:
            if rule.source_platform == source and rule.target_platform == target:
                if rule.source_field in result:
                    value = result[rule.source_field]
                    if rule.transformer:
                        value = rule.transformer(value)
                    result[rule.target_field] = value
        
        return result
    
    def _get_field_map(self, source: Platform, target: Platform) -> Dict[str, str]:
        """Get field mapping for source->target transformation."""
        # Get source field names
        if source == Platform.GENSPARK:
            source_map = self.GENSPARK_FIELD_MAP
        elif source == Platform.AOL_CLI:
            source_map = self.AOL_CLI_FIELD_MAP
        elif source == Platform.CLAWDPOKE:
            source_map = self.CLAWDPOKE_FIELD_MAP
        else:
            source_map = {}
        
        # Get target field names (inverse)
        if target == Platform.GENSPARK:
            target_map = {v: k for k, v in self.GENSPARK_FIELD_MAP.items()}
        elif target == Platform.AOL_CLI:
            target_map = {v: k for k, v in self.AOL_CLI_FIELD_MAP.items()}
        elif target == Platform.CLAWDPOKE:
            target_map = {v: k for k, v in self.CLAWDPOKE_FIELD_MAP.items()}
        else:
            target_map = {}
        
        # Combine: source canonical -> target native
        result = {}
        for src_native, canonical in source_map.items():
            if canonical in target_map:
                result[src_native] = target_map[canonical]
        
        return result
    
    # =========================================================================
    # MESSAGE CONVERSION
    # =========================================================================
    
    def event_to_message(self, event: TriCoreEvent) -> IntegrationMessage:
        """Convert a TriCoreEvent to an IntegrationMessage."""
        return IntegrationMessage(
            message_type=event.event_type,
            source=MessageSource(
                platform=event.source,
                component=event.metadata.get("component", "unknown"),
                id=event.id,
            ),
            target=MessageTarget(
                platform=event.target or Platform.TRINITY,
                component=event.metadata.get("target_component", "unknown"),
                id=event.metadata.get("target_id"),
            ),
            payload=event.payload,
            metadata=MessageMetadata(
                priority=event.priority,
                correlation_id=event.correlation_id,
            ),
        )
    
    def message_to_event(self, message: IntegrationMessage) -> TriCoreEvent:
        """Convert an IntegrationMessage to a TriCoreEvent."""
        return TriCoreEvent(
            source=message.source.platform,
            target=message.target.platform,
            event_type=message.message_type,
            payload=message.payload,
            correlation_id=message.metadata.correlation_id,
            priority=message.metadata.priority,
            metadata={
                "component": message.source.component,
                "source_id": message.source.id,
                "target_component": message.target.component,
                "target_id": message.target.id,
            },
        )
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def serialize_event(self, event: TriCoreEvent) -> str:
        """Serialize an event to JSON string."""
        data = {
            "id": event.id,
            "source": event.source.value if hasattr(event.source, 'value') else event.source,
            "target": event.target.value if event.target and hasattr(event.target, 'value') else event.target,
            "event_type": event.event_type,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
            "correlation_id": event.correlation_id,
            "priority": event.priority.value if hasattr(event.priority, 'value') else event.priority,
            "metadata": event.metadata,
        }
        return json.dumps(data, default=str)
    
    def deserialize_event(self, data: str) -> TriCoreEvent:
        """Deserialize a JSON string to an event."""
        parsed = json.loads(data)
        return TriCoreEvent(
            id=parsed.get("id"),
            source=Platform(parsed["source"]),
            target=Platform(parsed["target"]) if parsed.get("target") else None,
            event_type=parsed["event_type"],
            payload=parsed.get("payload", {}),
            timestamp=datetime.fromisoformat(parsed["timestamp"]) if parsed.get("timestamp") else datetime.utcnow(),
            correlation_id=parsed.get("correlation_id", ""),
            priority=EventPriority(parsed.get("priority", "normal")),
            metadata=parsed.get("metadata", {}),
        )
    
    def serialize_message(self, message: IntegrationMessage) -> str:
        """Serialize an integration message to JSON."""
        return message.model_dump_json()
    
    def deserialize_message(self, data: str) -> IntegrationMessage:
        """Deserialize a JSON string to an integration message."""
        return IntegrationMessage.model_validate_json(data)
    
    # =========================================================================
    # ROUTING
    # =========================================================================
    
    def register_route(self, event_type: str, targets: List[Platform]) -> None:
        """Register a route for an event type."""
        self._routes[event_type] = targets
    
    def get_routes(self, event_type: str) -> List[Platform]:
        """Get target platforms for an event type."""
        # Check exact match
        if event_type in self._routes:
            return self._routes[event_type]
        
        # Check wildcard patterns
        for pattern, targets in self._routes.items():
            if pattern.endswith("*") and event_type.startswith(pattern[:-1]):
                return targets
        
        # Default: broadcast to all
        return [Platform.GENSPARK, Platform.AOL_CLI, Platform.CLAWDPOKE]
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def register_validator(
        self,
        platform: Platform,
        validator: Callable[[Dict], bool],
    ) -> None:
        """Register a payload validator for a platform."""
        self._validators[platform] = validator
    
    def validate(self, event: TriCoreEvent, target: Platform) -> bool:
        """Validate an event payload for a target platform."""
        validator = self._validators.get(target)
        if validator is None:
            return True
        return validator(event.payload)
    
    # =========================================================================
    # INTERCEPTORS
    # =========================================================================
    
    def add_interceptor(
        self,
        interceptor: Callable[[TriCoreEvent], Optional[TriCoreEvent]],
    ) -> None:
        """
        Add an event interceptor.
        
        Interceptors can modify events or return None to drop them.
        """
        self._interceptors.append(interceptor)
    
    def intercept(self, event: TriCoreEvent) -> Optional[TriCoreEvent]:
        """Run event through all interceptors."""
        current = event
        for interceptor in self._interceptors:
            result = interceptor(current)
            if result is None:
                logger.debug(f"Event {event.id} dropped by interceptor")
                return None
            current = result
        return current
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def create_response_event(
        self,
        original: TriCoreEvent,
        response_type: str,
        payload: Dict[str, Any],
        source: Platform,
    ) -> TriCoreEvent:
        """Create a response event linked to an original event."""
        return TriCoreEvent(
            source=source,
            target=original.source,
            event_type=response_type,
            payload=payload,
            correlation_id=original.correlation_id,
            priority=original.priority,
            metadata={
                "in_reply_to": original.id,
                "original_type": original.event_type,
            },
        )
    
    def __repr__(self) -> str:
        return (
            f"EventBridge("
            f"rules={len(self._transform_rules)}, "
            f"routes={len(self._routes)}, "
            f"validators={len(self._validators)})"
        )
