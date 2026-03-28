"""
Interface Selector
==================

Dynamically selects the optimal interface based on task characteristics.
Ensures users always interact through the most appropriate platform.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from tri_core.models import (
    Platform,
    TaskType,
    InterfaceType,
    Task,
)

logger = logging.getLogger(__name__)


@dataclass
class InterfaceProfile:
    """Profile of an interface."""
    interface_type: InterfaceType
    platform: Platform
    strengths: List[str]
    weaknesses: List[str]
    task_affinity: Dict[TaskType, float]  # 0.0 to 1.0
    is_available: bool = True
    priority: int = 5


@dataclass
class SelectionResult:
    """Result of interface selection."""
    interface: InterfaceType
    platform: Platform
    confidence: float
    reasoning: str
    alternatives: List[Tuple[InterfaceType, float]]


class InterfaceSelector:
    """
    🖥️ Interface Selector
    
    Intelligently selects the optimal interface for each task.
    
    Available Interfaces:
    - SparkpageUI: Genspark's visual interface for creative tasks
    - TerminalTUI: AOL-CLI's terminal for technical development
    - GameEngine: Clawdpoke.a0's engine for interactive experiences
    - MultiView: Combined split-view for hybrid tasks
    
    Selection Factors:
    - Task type and requirements
    - User preferences
    - Interface availability
    - Historical success rates
    """
    
    # Default interface profiles
    DEFAULT_PROFILES = [
        InterfaceProfile(
            interface_type=InterfaceType.SPARKPAGE_UI,
            platform=Platform.GENSPARK,
            strengths=["visual", "creative", "collaboration", "documentation"],
            weaknesses=["low-level control", "command-line operations"],
            task_affinity={
                TaskType.CREATIVE: 0.95,
                TaskType.TECHNICAL: 0.3,
                TaskType.INTERACTIVE: 0.4,
                TaskType.HYBRID: 0.6,
            },
            priority=7,
        ),
        InterfaceProfile(
            interface_type=InterfaceType.TERMINAL_TUI,
            platform=Platform.AOL_CLI,
            strengths=["code", "execution", "debugging", "automation", "efficiency"],
            weaknesses=["visual design", "non-technical users"],
            task_affinity={
                TaskType.CREATIVE: 0.2,
                TaskType.TECHNICAL: 0.95,
                TaskType.INTERACTIVE: 0.3,
                TaskType.HYBRID: 0.7,
            },
            priority=8,
        ),
        InterfaceProfile(
            interface_type=InterfaceType.GAME_ENGINE,
            platform=Platform.CLAWDPOKE,
            strengths=["interactive", "gameplay", "testing", "immersion"],
            weaknesses=["code editing", "documentation"],
            task_affinity={
                TaskType.CREATIVE: 0.5,
                TaskType.TECHNICAL: 0.2,
                TaskType.INTERACTIVE: 0.95,
                TaskType.HYBRID: 0.5,
            },
            priority=6,
        ),
        InterfaceProfile(
            interface_type=InterfaceType.MULTI_VIEW,
            platform=Platform.TRINITY,
            strengths=["complex tasks", "multi-platform", "comprehensive"],
            weaknesses=["screen real estate", "complexity"],
            task_affinity={
                TaskType.CREATIVE: 0.6,
                TaskType.TECHNICAL: 0.7,
                TaskType.INTERACTIVE: 0.6,
                TaskType.HYBRID: 0.95,
            },
            priority=5,
        ),
    ]
    
    def __init__(self):
        """Initialize the interface selector."""
        self._profiles: Dict[InterfaceType, InterfaceProfile] = {}
        self._selection_history: List[SelectionResult] = []
        self._user_preferences: Dict[str, InterfaceType] = {}
        self._success_rates: Dict[InterfaceType, Dict[str, int]] = {}
        
        # Register default profiles
        for profile in self.DEFAULT_PROFILES:
            self.register_profile(profile)
        
        # Initialize success tracking
        for interface in InterfaceType:
            self._success_rates[interface] = {"success": 0, "total": 0}
        
        logger.info("🖥️ Interface Selector initialized")
    
    def register_profile(self, profile: InterfaceProfile) -> None:
        """Register an interface profile."""
        self._profiles[profile.interface_type] = profile
    
    def select(
        self,
        task: Task,
        *,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> SelectionResult:
        """
        Select the optimal interface for a task.
        
        Args:
            task: Task to analyze
            user_id: Optional user ID for preference lookup
            context: Additional context for selection
            
        Returns:
            Selection result with reasoning
        """
        context = context or {}
        
        # Score each interface
        scores: List[Tuple[InterfaceType, float, str]] = []
        
        for interface_type, profile in self._profiles.items():
            if not profile.is_available:
                continue
            
            score, reasoning = self._calculate_score(task, profile, user_id, context)
            scores.append((interface_type, score, reasoning))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if not scores:
            # Fallback
            return SelectionResult(
                interface=InterfaceType.TERMINAL_TUI,
                platform=Platform.AOL_CLI,
                confidence=0.5,
                reasoning="No interfaces available, using fallback",
                alternatives=[],
            )
        
        # Select best
        best_interface, best_score, best_reasoning = scores[0]
        profile = self._profiles[best_interface]
        
        # Build alternatives
        alternatives = [(iface, score) for iface, score, _ in scores[1:4]]
        
        result = SelectionResult(
            interface=best_interface,
            platform=profile.platform,
            confidence=best_score,
            reasoning=best_reasoning,
            alternatives=alternatives,
        )
        
        # Record selection
        self._selection_history.append(result)
        
        logger.info(
            f"🖥️ Selected {best_interface.value} for task '{task.name}' "
            f"(confidence: {best_score:.2f})"
        )
        
        return result
    
    def _calculate_score(
        self,
        task: Task,
        profile: InterfaceProfile,
        user_id: Optional[str],
        context: Dict[str, Any],
    ) -> Tuple[float, str]:
        """Calculate selection score for an interface."""
        score = 0.0
        reasons = []
        
        # Task type affinity (0-40 points)
        affinity = profile.task_affinity.get(task.task_type, 0.5)
        score += affinity * 40
        reasons.append(f"Task affinity: {affinity:.2f}")
        
        # Keyword matching (0-25 points)
        task_text = f"{task.name} {task.description}".lower()
        strength_matches = sum(1 for s in profile.strengths if s in task_text)
        weakness_matches = sum(1 for w in profile.weaknesses if w in task_text)
        keyword_score = (strength_matches - weakness_matches * 0.5) / max(len(profile.strengths), 1)
        keyword_score = max(0, min(1, keyword_score))  # Clamp 0-1
        score += keyword_score * 25
        if strength_matches > 0:
            reasons.append(f"Matched strengths: {strength_matches}")
        
        # User preference (0-15 points)
        if user_id and user_id in self._user_preferences:
            if self._user_preferences[user_id] == profile.interface_type:
                score += 15
                reasons.append("User preference match")
        
        # Historical success rate (0-10 points)
        success_data = self._success_rates.get(profile.interface_type, {})
        if success_data.get("total", 0) > 0:
            success_rate = success_data["success"] / success_data["total"]
            score += success_rate * 10
            reasons.append(f"Success rate: {success_rate:.2f}")
        
        # Priority bonus (0-10 points)
        score += (profile.priority / 10) * 10
        
        # Normalize to 0-1
        final_score = score / 100
        
        reasoning = " | ".join(reasons)
        return final_score, reasoning
    
    def set_interface_availability(
        self,
        interface: InterfaceType,
        available: bool,
    ) -> None:
        """Set whether an interface is available."""
        if interface in self._profiles:
            self._profiles[interface].is_available = available
    
    def set_user_preference(
        self,
        user_id: str,
        interface: InterfaceType,
    ) -> None:
        """Set a user's preferred interface."""
        self._user_preferences[user_id] = interface
    
    def record_outcome(
        self,
        interface: InterfaceType,
        success: bool,
    ) -> None:
        """Record the outcome of using an interface."""
        if interface in self._success_rates:
            self._success_rates[interface]["total"] += 1
            if success:
                self._success_rates[interface]["success"] += 1
    
    def get_recommendation(
        self,
        task_type: TaskType,
    ) -> InterfaceType:
        """Get quick recommendation based on task type."""
        mapping = {
            TaskType.CREATIVE: InterfaceType.SPARKPAGE_UI,
            TaskType.TECHNICAL: InterfaceType.TERMINAL_TUI,
            TaskType.INTERACTIVE: InterfaceType.GAME_ENGINE,
            TaskType.HYBRID: InterfaceType.MULTI_VIEW,
        }
        return mapping.get(task_type, InterfaceType.TERMINAL_TUI)
    
    def get_selection_history(self, limit: int = 50) -> List[SelectionResult]:
        """Get recent selection history."""
        return self._selection_history[-limit:]
    
    def get_success_rates(self) -> Dict[str, float]:
        """Get success rates for all interfaces."""
        rates = {}
        for interface, data in self._success_rates.items():
            if data["total"] > 0:
                rates[interface.value] = data["success"] / data["total"]
            else:
                rates[interface.value] = 0.0
        return rates
    
    def __repr__(self) -> str:
        available = sum(1 for p in self._profiles.values() if p.is_available)
        return f"InterfaceSelector(interfaces={len(self._profiles)}, available={available})"
