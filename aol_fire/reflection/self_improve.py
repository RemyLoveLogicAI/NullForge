"""
NullForge Self-Improving Agent System
State of the Art reflection and self-improvement

Features:
- Execution reflection and analysis
- Performance tracking and optimization
- Automatic prompt refinement
- Learning from errors
- Continuous self-improvement
- Meta-cognitive reasoning
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
from pathlib import Path


class ReflectionType(Enum):
    """Types of reflection."""
    EXECUTION = "execution"  # Reflect on task execution
    ERROR = "error"  # Reflect on errors
    PERFORMANCE = "performance"  # Reflect on performance metrics
    QUALITY = "quality"  # Reflect on output quality
    PROCESS = "process"  # Reflect on overall process
    META = "meta"  # Meta-reflection on reflection


class ImprovementType(Enum):
    """Types of improvements."""
    PROMPT_REFINEMENT = "prompt_refinement"
    STRATEGY_ADJUSTMENT = "strategy_adjustment"
    TOOL_SELECTION = "tool_selection"
    ERROR_PREVENTION = "error_prevention"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    KNOWLEDGE_UPDATE = "knowledge_update"


@dataclass
class ExecutionRecord:
    """Record of a task execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    task_description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0
    success: bool = True
    error: Optional[str] = None
    tokens_used: int = 0
    tools_used: List[str] = field(default_factory=list)
    iterations: int = 1
    confidence: float = 0.8
    user_feedback: Optional[str] = None
    feedback_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReflectionResult:
    """Result of a reflection."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reflection_type: ReflectionType = ReflectionType.EXECUTION
    execution_id: str = ""
    analysis: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    improvement_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.7
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['reflection_type'] = self.reflection_type.value
        return data


@dataclass
class Improvement:
    """A concrete improvement to apply."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    improvement_type: ImprovementType = ImprovementType.PROMPT_REFINEMENT
    description: str = ""
    target: str = ""  # What is being improved
    old_value: Any = None
    new_value: Any = None
    expected_benefit: str = ""
    priority: int = 5  # 1-10
    status: str = "proposed"  # proposed, applied, verified, reverted
    effectiveness_score: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['improvement_type'] = self.improvement_type.value
        return data


class PerformanceTracker:
    """
    Tracks performance metrics over time.
    
    Metrics tracked:
    - Success rate
    - Average duration
    - Token efficiency
    - Error frequency
    - User satisfaction
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = Path(persist_path) if persist_path else None
        
        self.metrics: Dict[str, List[float]] = {
            "success_rate": [],
            "duration_ms": [],
            "tokens_per_task": [],
            "iterations_per_task": [],
            "user_satisfaction": [],
            "confidence": []
        }
        
        self.aggregates: Dict[str, Dict[str, float]] = {}
        self.by_task_type: Dict[str, Dict[str, List[float]]] = {}
        
        if self.persist_path:
            self._load()
    
    def record(self, execution: ExecutionRecord):
        """Record metrics from an execution."""
        self.metrics["success_rate"].append(1.0 if execution.success else 0.0)
        self.metrics["duration_ms"].append(execution.duration_ms)
        self.metrics["tokens_per_task"].append(execution.tokens_used)
        self.metrics["iterations_per_task"].append(execution.iterations)
        self.metrics["confidence"].append(execution.confidence)
        
        if execution.feedback_score is not None:
            self.metrics["user_satisfaction"].append(execution.feedback_score)
        
        # Track by task type
        task_type = execution.task_type
        if task_type not in self.by_task_type:
            self.by_task_type[task_type] = {k: [] for k in self.metrics.keys()}
        
        self.by_task_type[task_type]["success_rate"].append(1.0 if execution.success else 0.0)
        self.by_task_type[task_type]["duration_ms"].append(execution.duration_ms)
        self.by_task_type[task_type]["tokens_per_task"].append(execution.tokens_used)
        
        self._update_aggregates()
        
        if self.persist_path:
            self._save()
    
    def _update_aggregates(self):
        """Update aggregate statistics."""
        for metric, values in self.metrics.items():
            if values:
                self.aggregates[metric] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "recent_mean": sum(values[-10:]) / len(values[-10:]) if len(values) >= 10 else sum(values) / len(values)
                }
    
    def get_trends(self, metric: str, window: int = 20) -> Dict[str, Any]:
        """Get trend analysis for a metric."""
        values = self.metrics.get(metric, [])
        if len(values) < window:
            return {"trend": "insufficient_data", "values": values}
        
        recent = values[-window:]
        older = values[-(2*window):-window] if len(values) >= 2*window else values[:-window]
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else recent_avg
        
        change = ((recent_avg - older_avg) / older_avg * 100) if older_avg != 0 else 0
        
        trend = "improving" if change > 5 else "declining" if change < -5 else "stable"
        
        return {
            "trend": trend,
            "change_percent": change,
            "recent_avg": recent_avg,
            "older_avg": older_avg,
            "values": recent
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "aggregates": self.aggregates,
            "trends": {
                metric: self.get_trends(metric)
                for metric in self.metrics.keys()
            },
            "by_task_type": {
                task_type: {
                    metric: sum(values) / len(values) if values else 0
                    for metric, values in metrics.items()
                }
                for task_type, metrics in self.by_task_type.items()
            }
        }
    
    def _save(self):
        """Save metrics to disk."""
        if self.persist_path:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, "w") as f:
                json.dump({
                    "metrics": self.metrics,
                    "by_task_type": self.by_task_type
                }, f, indent=2)
    
    def _load(self):
        """Load metrics from disk."""
        if self.persist_path and self.persist_path.exists():
            with open(self.persist_path) as f:
                data = json.load(f)
                self.metrics = data.get("metrics", self.metrics)
                self.by_task_type = data.get("by_task_type", {})
                self._update_aggregates()


class ReflectionEngine:
    """
    Engine for generating reflections on executions.
    
    Uses structured analysis to identify:
    - What went well
    - What could be improved
    - Root causes of issues
    - Concrete improvement actions
    """
    
    def __init__(self, llm_callable: Optional[Callable] = None):
        self.llm = llm_callable
        self.reflection_history: List[ReflectionResult] = []
    
    def reflect_on_execution(
        self,
        execution: ExecutionRecord,
        context: Optional[Dict[str, Any]] = None
    ) -> ReflectionResult:
        """
        Generate reflection on a task execution.
        
        Args:
            execution: The execution to reflect on
            context: Additional context
            
        Returns:
            ReflectionResult with analysis
        """
        reflection = ReflectionResult(
            reflection_type=ReflectionType.EXECUTION,
            execution_id=execution.id
        )
        
        # Analyze execution
        analysis_parts = []
        
        # Success/failure analysis
        if execution.success:
            analysis_parts.append(f"Task '{execution.task_type}' completed successfully.")
            reflection.strengths.append("Task completed without errors")
            
            # Check efficiency
            if execution.iterations == 1:
                reflection.strengths.append("Completed in single iteration")
            elif execution.iterations > 3:
                reflection.weaknesses.append(f"Required {execution.iterations} iterations")
                reflection.improvement_suggestions.append({
                    "type": "efficiency",
                    "suggestion": "Consider improving initial approach to reduce iterations"
                })
        else:
            analysis_parts.append(f"Task '{execution.task_type}' failed: {execution.error}")
            reflection.weaknesses.append(f"Failed with error: {execution.error}")
            
            # Analyze error
            if execution.error:
                reflection.root_causes.append(self._analyze_error(execution.error))
                reflection.improvement_suggestions.append({
                    "type": "error_prevention",
                    "suggestion": f"Add check for: {execution.error[:50]}"
                })
        
        # Duration analysis
        if execution.duration_ms > 10000:  # > 10 seconds
            reflection.weaknesses.append("Slow execution")
            reflection.improvement_suggestions.append({
                "type": "performance",
                "suggestion": "Optimize for faster execution"
            })
        elif execution.duration_ms < 2000:
            reflection.strengths.append("Fast execution")
        
        # Token efficiency
        if execution.tokens_used > 0:
            if execution.tokens_used > 5000:
                reflection.weaknesses.append("High token usage")
                reflection.improvement_suggestions.append({
                    "type": "efficiency",
                    "suggestion": "Reduce prompt verbosity"
                })
        
        # Confidence analysis
        if execution.confidence < 0.5:
            reflection.weaknesses.append("Low confidence in output")
            reflection.improvement_suggestions.append({
                "type": "quality",
                "suggestion": "Add verification step for low-confidence outputs"
            })
        
        # User feedback analysis
        if execution.feedback_score is not None:
            if execution.feedback_score >= 0.8:
                reflection.strengths.append("High user satisfaction")
            elif execution.feedback_score < 0.5:
                reflection.weaknesses.append("Low user satisfaction")
                reflection.lessons_learned.append(
                    "Output did not meet user expectations"
                )
        
        # Generate lessons
        if not execution.success:
            reflection.lessons_learned.append(
                f"Error type '{execution.error[:30]}...' should be handled proactively"
            )
        
        if execution.iterations > 1:
            reflection.lessons_learned.append(
                f"Task type '{execution.task_type}' may benefit from better initial planning"
            )
        
        reflection.analysis = " ".join(analysis_parts)
        reflection.confidence = self._calculate_reflection_confidence(execution, reflection)
        
        self.reflection_history.append(reflection)
        return reflection
    
    def _analyze_error(self, error: str) -> str:
        """Analyze an error to identify root cause."""
        error_lower = error.lower()
        
        if "timeout" in error_lower:
            return "Operation timed out - likely too complex or stuck"
        elif "memory" in error_lower:
            return "Memory issue - likely data too large"
        elif "permission" in error_lower:
            return "Permission denied - access control issue"
        elif "not found" in error_lower:
            return "Resource not found - missing dependency or path"
        elif "syntax" in error_lower:
            return "Syntax error - malformed code or input"
        elif "type" in error_lower:
            return "Type error - wrong data type used"
        elif "connection" in error_lower:
            return "Connection issue - network or service unavailable"
        else:
            return f"Unknown error type: {error[:50]}"
    
    def _calculate_reflection_confidence(
        self,
        execution: ExecutionRecord,
        reflection: ReflectionResult
    ) -> float:
        """Calculate confidence in the reflection."""
        confidence = 0.7  # Base confidence
        
        # More data = more confidence
        if execution.user_feedback:
            confidence += 0.1
        
        # Clear success/failure = more confidence
        if execution.success or execution.error:
            confidence += 0.1
        
        # Reduce if analysis is sparse
        if len(reflection.strengths) + len(reflection.weaknesses) < 2:
            confidence -= 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def reflect_on_pattern(
        self,
        executions: List[ExecutionRecord],
        pattern_type: str = "error"
    ) -> ReflectionResult:
        """
        Reflect on patterns across multiple executions.
        
        Args:
            executions: List of executions to analyze
            pattern_type: Type of pattern to look for
            
        Returns:
            ReflectionResult with pattern analysis
        """
        reflection = ReflectionResult(
            reflection_type=ReflectionType.PROCESS
        )
        
        if pattern_type == "error":
            # Analyze error patterns
            errors = [e.error for e in executions if e.error]
            error_types = {}
            for error in errors:
                error_category = self._analyze_error(error)
                error_types[error_category] = error_types.get(error_category, 0) + 1
            
            if error_types:
                most_common = max(error_types, key=error_types.get)
                reflection.analysis = f"Most common error pattern: {most_common}"
                reflection.root_causes.append(most_common)
                reflection.improvement_suggestions.append({
                    "type": "error_prevention",
                    "suggestion": f"Add proactive handling for: {most_common}",
                    "priority": error_types[most_common]
                })
        
        elif pattern_type == "performance":
            # Analyze performance patterns
            durations = [e.duration_ms for e in executions]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            slow_tasks = [e for e in executions if e.duration_ms > avg_duration * 1.5]
            if slow_tasks:
                slow_types = [e.task_type for e in slow_tasks]
                reflection.analysis = f"Slow task types: {set(slow_types)}"
                reflection.improvement_suggestions.append({
                    "type": "performance",
                    "suggestion": f"Optimize task types: {set(slow_types)}"
                })
        
        return reflection
    
    def meta_reflect(self) -> ReflectionResult:
        """
        Meta-reflection: reflect on the quality of reflections.
        
        Analyzes:
        - Are reflections leading to improvements?
        - Are the same issues recurring?
        - Is the reflection process effective?
        """
        reflection = ReflectionResult(
            reflection_type=ReflectionType.META
        )
        
        if len(self.reflection_history) < 5:
            reflection.analysis = "Insufficient reflection history for meta-analysis"
            return reflection
        
        # Check for recurring issues
        all_weaknesses = []
        for r in self.reflection_history:
            all_weaknesses.extend(r.weaknesses)
        
        weakness_counts = {}
        for w in all_weaknesses:
            weakness_counts[w] = weakness_counts.get(w, 0) + 1
        
        recurring = {w: c for w, c in weakness_counts.items() if c > 2}
        
        if recurring:
            reflection.analysis = f"Recurring issues detected: {list(recurring.keys())}"
            reflection.weaknesses.append("Some issues keep recurring despite reflection")
            reflection.improvement_suggestions.append({
                "type": "meta",
                "suggestion": "Consider more aggressive improvement actions for recurring issues"
            })
        else:
            reflection.strengths.append("No recurring issues - improvements are effective")
        
        # Check reflection quality
        avg_confidence = sum(r.confidence for r in self.reflection_history) / len(self.reflection_history)
        if avg_confidence < 0.6:
            reflection.weaknesses.append("Low average reflection confidence")
            reflection.improvement_suggestions.append({
                "type": "meta",
                "suggestion": "Gather more execution data for better reflections"
            })
        
        return reflection


class SelfImprovingAgent:
    """
    Agent that improves itself through reflection.
    
    The improvement loop:
    1. Execute tasks
    2. Reflect on execution
    3. Identify improvements
    4. Apply improvements
    5. Verify effectiveness
    6. Repeat
    """
    
    def __init__(
        self,
        persist_directory: str = ".nullforge/self_improve",
        llm_callable: Optional[Callable] = None
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.performance_tracker = PerformanceTracker(
            persist_path=self.persist_directory / "performance.json"
        )
        self.reflection_engine = ReflectionEngine(llm_callable)
        
        self.executions: List[ExecutionRecord] = []
        self.improvements: List[Improvement] = []
        self.current_config: Dict[str, Any] = self._load_config()
        
        # Improvement thresholds
        self.improvement_threshold = 0.3  # Apply improvement if score < this
        self.verification_threshold = 0.6  # Keep improvement if effectiveness > this
    
    def _load_config(self) -> Dict[str, Any]:
        """Load current configuration."""
        config_path = self.persist_directory / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {
            "prompts": {},
            "strategies": {},
            "tool_preferences": {},
            "error_handlers": {}
        }
    
    def _save_config(self):
        """Save configuration."""
        config_path = self.persist_directory / "config.json"
        with open(config_path, "w") as f:
            json.dump(self.current_config, f, indent=2)
    
    def record_execution(
        self,
        task_type: str,
        task_description: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        success: bool,
        error: Optional[str] = None,
        tokens_used: int = 0,
        tools_used: Optional[List[str]] = None,
        iterations: int = 1,
        confidence: float = 0.8
    ) -> ExecutionRecord:
        """Record a task execution."""
        execution = ExecutionRecord(
            task_type=task_type,
            task_description=task_description,
            input_data=input_data,
            output_data=output_data,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_ms=(end_time - start_time).total_seconds() * 1000,
            success=success,
            error=error,
            tokens_used=tokens_used,
            tools_used=tools_used or [],
            iterations=iterations,
            confidence=confidence
        )
        
        self.executions.append(execution)
        self.performance_tracker.record(execution)
        
        # Trigger reflection if needed
        if not success or confidence < 0.5:
            self._trigger_reflection(execution)
        
        # Periodic reflection
        if len(self.executions) % 10 == 0:
            self._periodic_reflection()
        
        return execution
    
    def add_user_feedback(
        self,
        execution_id: str,
        feedback: str,
        score: float
    ):
        """Add user feedback to an execution."""
        for execution in self.executions:
            if execution.id == execution_id:
                execution.user_feedback = feedback
                execution.feedback_score = score
                
                # Re-reflect if feedback is negative
                if score < 0.5:
                    self._trigger_reflection(execution)
                break
    
    def _trigger_reflection(self, execution: ExecutionRecord):
        """Trigger reflection on an execution."""
        reflection = self.reflection_engine.reflect_on_execution(execution)
        
        # Generate improvements from reflection
        for suggestion in reflection.improvement_suggestions:
            improvement = self._create_improvement(suggestion, execution)
            if improvement:
                self.improvements.append(improvement)
                
                # Auto-apply high-priority improvements
                if improvement.priority >= 8:
                    self._apply_improvement(improvement)
    
    def _periodic_reflection(self):
        """Periodic reflection on recent executions."""
        recent = self.executions[-20:]
        
        # Pattern analysis
        error_reflection = self.reflection_engine.reflect_on_pattern(recent, "error")
        perf_reflection = self.reflection_engine.reflect_on_pattern(recent, "performance")
        
        # Meta-reflection every 50 executions
        if len(self.executions) % 50 == 0:
            meta_reflection = self.reflection_engine.meta_reflect()
    
    def _create_improvement(
        self,
        suggestion: Dict[str, Any],
        execution: ExecutionRecord
    ) -> Optional[Improvement]:
        """Create an improvement from a suggestion."""
        suggestion_type = suggestion.get("type", "")
        
        if suggestion_type == "prompt_refinement":
            return Improvement(
                improvement_type=ImprovementType.PROMPT_REFINEMENT,
                description=suggestion.get("suggestion", ""),
                target=f"prompt:{execution.task_type}",
                priority=suggestion.get("priority", 5)
            )
        elif suggestion_type == "error_prevention":
            return Improvement(
                improvement_type=ImprovementType.ERROR_PREVENTION,
                description=suggestion.get("suggestion", ""),
                target=f"error_handler:{execution.error[:30] if execution.error else 'unknown'}",
                priority=suggestion.get("priority", 7)
            )
        elif suggestion_type == "performance":
            return Improvement(
                improvement_type=ImprovementType.PERFORMANCE_OPTIMIZATION,
                description=suggestion.get("suggestion", ""),
                target=f"strategy:{execution.task_type}",
                priority=suggestion.get("priority", 5)
            )
        
        return None
    
    def _apply_improvement(self, improvement: Improvement):
        """Apply an improvement to the configuration."""
        if improvement.improvement_type == ImprovementType.PROMPT_REFINEMENT:
            # Store prompt refinement
            target = improvement.target.replace("prompt:", "")
            if "prompts" not in self.current_config:
                self.current_config["prompts"] = {}
            self.current_config["prompts"][target] = {
                "refinement": improvement.description,
                "applied_at": datetime.now().isoformat()
            }
        
        elif improvement.improvement_type == ImprovementType.ERROR_PREVENTION:
            # Store error handler
            target = improvement.target.replace("error_handler:", "")
            if "error_handlers" not in self.current_config:
                self.current_config["error_handlers"] = {}
            self.current_config["error_handlers"][target] = {
                "handler": improvement.description,
                "applied_at": datetime.now().isoformat()
            }
        
        elif improvement.improvement_type == ImprovementType.PERFORMANCE_OPTIMIZATION:
            # Store strategy adjustment
            target = improvement.target.replace("strategy:", "")
            if "strategies" not in self.current_config:
                self.current_config["strategies"] = {}
            self.current_config["strategies"][target] = {
                "optimization": improvement.description,
                "applied_at": datetime.now().isoformat()
            }
        
        improvement.status = "applied"
        self._save_config()
    
    def verify_improvements(self):
        """Verify effectiveness of applied improvements."""
        applied = [i for i in self.improvements if i.status == "applied"]
        
        for improvement in applied:
            # Check recent executions related to this improvement
            target_type = improvement.target.split(":")[1] if ":" in improvement.target else ""
            
            recent_related = [
                e for e in self.executions[-20:]
                if target_type in e.task_type or target_type in (e.error or "")
            ]
            
            if not recent_related:
                continue
            
            # Calculate effectiveness
            success_rate = sum(1 for e in recent_related if e.success) / len(recent_related)
            
            improvement.effectiveness_score = success_rate
            
            if success_rate >= self.verification_threshold:
                improvement.status = "verified"
            elif success_rate < self.improvement_threshold:
                # Revert ineffective improvement
                self._revert_improvement(improvement)
    
    def _revert_improvement(self, improvement: Improvement):
        """Revert an ineffective improvement."""
        # Remove from config
        if improvement.improvement_type == ImprovementType.PROMPT_REFINEMENT:
            target = improvement.target.replace("prompt:", "")
            if target in self.current_config.get("prompts", {}):
                del self.current_config["prompts"][target]
        
        improvement.status = "reverted"
        self._save_config()
    
    def get_improvement_status(self) -> Dict[str, Any]:
        """Get status of all improvements."""
        return {
            "total": len(self.improvements),
            "by_status": {
                status: len([i for i in self.improvements if i.status == status])
                for status in ["proposed", "applied", "verified", "reverted"]
            },
            "by_type": {
                itype.value: len([i for i in self.improvements if i.improvement_type == itype])
                for itype in ImprovementType
            },
            "recent": [i.to_dict() for i in self.improvements[-5:]]
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return {
            "summary": self.performance_tracker.get_summary(),
            "executions_count": len(self.executions),
            "improvements": self.get_improvement_status(),
            "current_config": self.current_config,
            "reflection_count": len(self.reflection_engine.reflection_history)
        }
    
    def export_learnings(self, output_path: str) -> str:
        """Export all learnings to a file."""
        learnings = {
            "executions": [e.to_dict() for e in self.executions],
            "reflections": [r.to_dict() for r in self.reflection_engine.reflection_history],
            "improvements": [i.to_dict() for i in self.improvements],
            "config": self.current_config,
            "performance": self.performance_tracker.get_summary()
        }
        
        with open(output_path, "w") as f:
            json.dump(learnings, f, indent=2)
        
        return output_path


# Global instance
_self_improving_agent: Optional[SelfImprovingAgent] = None


def get_self_improving_agent() -> SelfImprovingAgent:
    """Get or create the global self-improving agent."""
    global _self_improving_agent
    if _self_improving_agent is None:
        _self_improving_agent = SelfImprovingAgent()
    return _self_improving_agent
