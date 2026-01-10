"""
NullForge Self-Improving Agent System

State of the Art reflection and continuous self-improvement.
"""

from .self_improve import (
    ReflectionType,
    ImprovementType,
    ExecutionRecord,
    ReflectionResult,
    Improvement,
    PerformanceTracker,
    ReflectionEngine,
    SelfImprovingAgent,
    get_self_improving_agent
)

__all__ = [
    "ReflectionType",
    "ImprovementType",
    "ExecutionRecord",
    "ReflectionResult",
    "Improvement",
    "PerformanceTracker",
    "ReflectionEngine",
    "SelfImprovingAgent",
    "get_self_improving_agent"
]
