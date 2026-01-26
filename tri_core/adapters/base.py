"""
Base Adapter
============

Abstract base class for all platform adapters in the Tri-Core architecture.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from tri_core.models import Platform, TriCoreEvent

logger = logging.getLogger(__name__)


@dataclass
class AdapterConfig:
    """Base configuration for adapters."""
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    enable_logging: bool = True
    enable_metrics: bool = True


@dataclass
class AdapterMetrics:
    """Metrics collected by adapters."""
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    total_latency_ms: float = 0
    last_request_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.requests_total == 0:
            return 0.0
        return self.requests_success / self.requests_total
    
    @property
    def average_latency_ms(self) -> float:
        if self.requests_success == 0:
            return 0.0
        return self.total_latency_ms / self.requests_success


class BaseAdapter(ABC):
    """
    🔌 Base Adapter
    
    Abstract base class providing common functionality for all platform adapters.
    
    Features:
    - Async execution support
    - Error handling and retries
    - Metrics collection
    - Event publishing
    - Health checking
    
    Subclasses must implement:
    - platform: Property returning the Platform enum
    - _execute_impl: Core execution logic
    - health_check: Platform-specific health check
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """Initialize the adapter."""
        self.config = config or AdapterConfig()
        self._metrics = AdapterMetrics()
        self._event_callbacks: List[Callable[[TriCoreEvent], None]] = []
        self._is_connected = False
        
        logger.info(f"🔌 {self.__class__.__name__} initialized")
    
    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Return the platform this adapter connects to."""
        pass
    
    @abstractmethod
    async def _execute_impl(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Internal implementation of execution.
        
        Args:
            action: Action to perform
            params: Action parameters
            
        Returns:
            Execution result
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the platform is healthy and accessible.
        
        Returns:
            True if healthy
        """
        pass
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    async def execute(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute an action on the platform.
        
        Args:
            action: Action to perform
            params: Action parameters
            timeout: Optional timeout override
            
        Returns:
            Execution result
        """
        params = params or {}
        timeout = timeout or self.config.timeout
        
        self._metrics.requests_total += 1
        self._metrics.last_request_at = datetime.utcnow()
        
        start_time = datetime.utcnow()
        
        try:
            # Execute with retries
            result = await self._execute_with_retry(action, params)
            
            # Record success
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._metrics.requests_success += 1
            self._metrics.total_latency_ms += latency
            
            # Publish event
            self._publish_event(
                event_type=f"{action}_completed",
                payload={"action": action, "result": result, "latency_ms": latency},
            )
            
            return result
            
        except Exception as e:
            self._metrics.requests_failed += 1
            
            # Publish error event
            self._publish_event(
                event_type=f"{action}_failed",
                payload={"action": action, "error": str(e)},
            )
            
            logger.error(f"❌ {self.platform} adapter error: {e}")
            raise
    
    async def _execute_with_retry(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute with retry logic."""
        import asyncio
        
        last_error = None
        
        for attempt in range(self.config.retry_count):
            try:
                return await self._execute_impl(action, params)
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_count - 1:
                    logger.warning(
                        f"Retry {attempt + 1}/{self.config.retry_count} for {action}: {e}"
                    )
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        raise last_error or RuntimeError("Execution failed")
    
    async def connect(self) -> bool:
        """
        Establish connection to the platform.
        
        Returns:
            True if connected successfully
        """
        try:
            if await self.health_check():
                self._is_connected = True
                logger.info(f"✅ Connected to {self.platform}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to {self.platform}: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the platform."""
        self._is_connected = False
        logger.info(f"🔌 Disconnected from {self.platform}")
    
    @property
    def is_connected(self) -> bool:
        """Check if adapter is connected."""
        return self._is_connected
    
    # =========================================================================
    # EVENTS
    # =========================================================================
    
    def on_event(self, callback: Callable[[TriCoreEvent], None]) -> None:
        """Register an event callback."""
        self._event_callbacks.append(callback)
    
    def _publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Publish an event to all registered callbacks."""
        event = TriCoreEvent(
            source=self.platform,
            event_type=event_type,
            payload=payload,
        )
        
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
    
    # =========================================================================
    # METRICS
    # =========================================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get adapter metrics."""
        return {
            "platform": self.platform.value,
            "requests_total": self._metrics.requests_total,
            "requests_success": self._metrics.requests_success,
            "requests_failed": self._metrics.requests_failed,
            "success_rate": self._metrics.success_rate,
            "average_latency_ms": self._metrics.average_latency_ms,
            "last_request_at": self._metrics.last_request_at.isoformat() if self._metrics.last_request_at else None,
            "is_connected": self._is_connected,
        }
    
    def reset_metrics(self) -> None:
        """Reset adapter metrics."""
        self._metrics = AdapterMetrics()
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"platform={self.platform.value}, "
            f"connected={self._is_connected}, "
            f"success_rate={self._metrics.success_rate:.2f})"
        )
