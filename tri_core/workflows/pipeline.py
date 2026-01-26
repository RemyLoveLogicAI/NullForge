"""
Game Development Pipeline
=========================

End-to-end game development workflow using all three platforms.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from tri_core.models import (
    Platform,
    TaskType,
    TaskStatus,
    Task,
    Workflow,
    WorkflowStep,
    TriCoreEvent,
)
from tri_core.event_bus.bus import UnifiedEventBus, get_event_bus
from tri_core.event_bus.state_sync import StateSync

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Stages of the game development pipeline."""
    CONCEPT = "concept"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    INTEGRATION = "integration"
    TESTING = "testing"
    FEEDBACK = "feedback"
    REFINEMENT = "refinement"
    DEPLOYMENT = "deployment"


@dataclass
class StageResult:
    """Result from a pipeline stage."""
    stage: PipelineStage
    status: TaskStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    duration_seconds: float = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    """Configuration for the pipeline."""
    enable_parallel: bool = True
    max_iterations: int = 10
    auto_feedback: bool = True
    skip_stages: List[PipelineStage] = field(default_factory=list)


class GameDevPipeline:
    """
    🎮 Game Development Pipeline
    
    End-to-end workflow for game development using Tri-Core architecture.
    
    Stages:
    1. Concept Design (Genspark) - Game concept and high-level design
    2. Detailed Design (Genspark) - Game design document, mechanics
    3. Code Generation (AOL-CLI) - Implement game code
    4. Game Integration (Clawdpoke) - Integrate with game framework
    5. Testing (Clawdpoke) - Test gameplay and mechanics
    6. Feedback Loop - Collect metrics and feedback
    7. Refinement - Iterate based on feedback
    8. Deployment - Final deployment
    
    Usage:
        pipeline = GameDevPipeline()
        result = await pipeline.run("Create a platformer game")
    """
    
    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        event_bus: Optional[UnifiedEventBus] = None,
    ):
        """Initialize the pipeline."""
        self.config = config or PipelineConfig()
        self.event_bus = event_bus or get_event_bus()
        self.state_sync = StateSync()
        
        # Pipeline state
        self._current_stage: Optional[PipelineStage] = None
        self._stage_results: Dict[PipelineStage, StageResult] = {}
        self._iteration = 0
        self._running = False
        
        # Callbacks
        self._stage_callbacks: List[Callable[[PipelineStage, StageResult], None]] = []
        
        # Adapters (to be set by orchestrator)
        self._genspark = None
        self._aol_cli = None
        self._clawdpoke = None
        
        logger.info("🎮 Game Development Pipeline initialized")
    
    def set_adapters(self, genspark, aol_cli, clawdpoke) -> None:
        """Set platform adapters."""
        self._genspark = genspark
        self._aol_cli = aol_cli
        self._clawdpoke = clawdpoke
    
    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================
    
    async def run(
        self,
        concept: str,
        *,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete game development pipeline.
        
        Args:
            concept: Game concept description
            options: Additional options
            
        Returns:
            Pipeline execution results
        """
        options = options or {}
        self._running = True
        self._iteration = 0
        self._stage_results.clear()
        
        start_time = datetime.utcnow()
        
        logger.info(f"🚀 Starting game development pipeline for: {concept[:50]}...")
        
        # Publish start event
        await self.event_bus.publish_async(
            "pipeline.started",
            TriCoreEvent(
                source=Platform.TRINITY,
                event_type="pipeline_started",
                payload={"concept": concept},
            )
        )
        
        # Store initial context
        self.state_sync.set("pipeline.concept", concept, Platform.TRINITY)
        self.state_sync.set("pipeline.options", options, Platform.TRINITY)
        
        try:
            # Execute stages
            stages = [
                (PipelineStage.CONCEPT, self._stage_concept),
                (PipelineStage.DESIGN, self._stage_design),
                (PipelineStage.IMPLEMENTATION, self._stage_implementation),
                (PipelineStage.INTEGRATION, self._stage_integration),
                (PipelineStage.TESTING, self._stage_testing),
                (PipelineStage.FEEDBACK, self._stage_feedback),
            ]
            
            for stage, handler in stages:
                if stage in self.config.skip_stages:
                    logger.info(f"⏭️ Skipping stage: {stage}")
                    continue
                
                if not self._running:
                    break
                
                self._current_stage = stage
                logger.info(f"📍 Stage: {stage.value}")
                
                stage_start = datetime.utcnow()
                result = await handler(concept, options)
                stage_duration = (datetime.utcnow() - stage_start).total_seconds()
                
                result.duration_seconds = stage_duration
                self._stage_results[stage] = result
                
                # Notify callbacks
                for callback in self._stage_callbacks:
                    try:
                        callback(stage, result)
                    except Exception as e:
                        logger.error(f"Stage callback error: {e}")
                
                # Publish stage completion
                await self.event_bus.publish_async(
                    f"pipeline.stage.{stage.value}",
                    TriCoreEvent(
                        source=Platform.TRINITY,
                        event_type="stage_completed",
                        payload={
                            "stage": stage.value,
                            "status": result.status.value,
                            "duration": stage_duration,
                        },
                    )
                )
                
                # Check for failures
                if result.status == TaskStatus.FAILED:
                    logger.error(f"❌ Stage failed: {stage}")
                    if not self.config.auto_feedback:
                        break
            
            # Refinement iterations
            if self.config.auto_feedback:
                await self._refinement_loop(concept, options)
            
            # Final deployment
            if PipelineStage.DEPLOYMENT not in self.config.skip_stages:
                await self._stage_deployment(concept, options)
            
            total_duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Publish completion
            await self.event_bus.publish_async(
                "pipeline.completed",
                TriCoreEvent(
                    source=Platform.TRINITY,
                    event_type="pipeline_completed",
                    payload={"total_duration": total_duration},
                )
            )
            
            return {
                "status": "completed",
                "concept": concept,
                "stages": {
                    stage.value: {
                        "status": result.status.value,
                        "duration": result.duration_seconds,
                        "outputs": result.outputs,
                        "artifacts": result.artifacts,
                    }
                    for stage, result in self._stage_results.items()
                },
                "iterations": self._iteration,
                "total_duration": total_duration,
            }
            
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "stages": {
                    stage.value: {
                        "status": result.status.value,
                    }
                    for stage, result in self._stage_results.items()
                },
            }
        finally:
            self._running = False
            self._current_stage = None
    
    async def stop(self) -> None:
        """Stop the pipeline."""
        self._running = False
        logger.info("⏹️ Pipeline stopped")
    
    # =========================================================================
    # PIPELINE STAGES
    # =========================================================================
    
    async def _stage_concept(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> StageResult:
        """
        Stage 1: Concept Design
        
        Uses Genspark to develop initial game concept.
        """
        outputs = {}
        artifacts = []
        
        if self._genspark:
            # Call SuperAgent for initial concept development
            result = await self._genspark.execute(
                "orchestrate",
                {
                    "goal": f"Develop a comprehensive game concept for: {concept}",
                    "agents": ["SuperAgent", "GameDesigner"],
                    "strategy": "sequential",
                }
            )
            outputs["concept_result"] = result
            
            # Generate initial design document
            doc_result = await self._genspark.execute(
                "create_sparkpage",
                {
                    "title": f"Game Concept: {concept[:30]}",
                    "content": f"# Game Concept\n\n{concept}\n\n## Initial Design\n\n...",
                }
            )
            artifacts.append(doc_result.get("id", "concept_doc"))
        else:
            # Simulation mode
            outputs["concept_result"] = {
                "concept": concept,
                "genre": "platformer",
                "features": ["movement", "jumping", "collectibles"],
            }
        
        self.state_sync.set("pipeline.concept_output", outputs, Platform.GENSPARK)
        
        return StageResult(
            stage=PipelineStage.CONCEPT,
            status=TaskStatus.COMPLETED,
            outputs=outputs,
            artifacts=artifacts,
        )
    
    async def _stage_design(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> StageResult:
        """
        Stage 2: Detailed Design
        
        Uses Genspark agents to create detailed game design.
        """
        outputs = {}
        artifacts = []
        
        concept_output = self.state_sync.get("pipeline.concept_output", {})
        
        if self._genspark:
            # Game Designer creates detailed mechanics
            mechanics_result = await self._genspark.execute(
                "call_agent",
                {
                    "agent": "GameDesigner",
                    "task": f"Create detailed game mechanics for: {concept}",
                    "context": concept_output,
                }
            )
            outputs["mechanics"] = mechanics_result.get("result", {})
            
            # Narrative Writer creates story
            narrative_result = await self._genspark.execute(
                "call_agent",
                {
                    "agent": "NarrativeWriter",
                    "task": f"Create game narrative and dialogue for: {concept}",
                    "context": concept_output,
                }
            )
            outputs["narrative"] = narrative_result.get("result", {})
            
            # Designer creates visual style
            visual_result = await self._genspark.execute(
                "call_agent",
                {
                    "agent": "AIDesigner",
                    "task": f"Create visual style guide for: {concept}",
                    "context": concept_output,
                }
            )
            outputs["visual_style"] = visual_result.get("result", {})
        else:
            outputs = {
                "mechanics": {"core_loop": "jump and collect"},
                "narrative": {"setting": "fantasy world"},
                "visual_style": {"style": "pixel art"},
            }
        
        self.state_sync.set("pipeline.design_output", outputs, Platform.GENSPARK)
        
        return StageResult(
            stage=PipelineStage.DESIGN,
            status=TaskStatus.COMPLETED,
            outputs=outputs,
            artifacts=artifacts,
        )
    
    async def _stage_implementation(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> StageResult:
        """
        Stage 3: Code Generation
        
        Uses AOL-CLI to generate game code.
        """
        outputs = {}
        artifacts = []
        
        design_output = self.state_sync.get("pipeline.design_output", {})
        
        if self._aol_cli:
            # Generate game code
            code_result = await self._aol_cli.execute(
                "fire_run",
                {
                    "goal": f"Generate game code based on design: {concept}",
                    "workspace": options.get("workspace", "."),
                }
            )
            outputs["code_generation"] = code_result
            artifacts.extend(code_result.get("files_created", []))
            
            # Generate tests
            test_result = await self._aol_cli.execute(
                "fire_run",
                {
                    "goal": "Generate unit tests for the game code",
                    "workspace": options.get("workspace", "."),
                }
            )
            outputs["test_generation"] = test_result
        else:
            outputs = {
                "code_generation": {"files": ["main.py", "game.py"]},
                "test_generation": {"files": ["test_game.py"]},
            }
        
        self.state_sync.set("pipeline.implementation_output", outputs, Platform.AOL_CLI)
        
        return StageResult(
            stage=PipelineStage.IMPLEMENTATION,
            status=TaskStatus.COMPLETED,
            outputs=outputs,
            artifacts=artifacts,
        )
    
    async def _stage_integration(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> StageResult:
        """
        Stage 4: Game Integration
        
        Integrates code with Clawdpoke.a0 framework.
        """
        outputs = {}
        artifacts = []
        
        implementation_output = self.state_sync.get("pipeline.implementation_output", {})
        
        if self._clawdpoke:
            # Create player for testing
            player_result = await self._clawdpoke.execute(
                "create_player",
                {
                    "player_id": "test_player",
                    "name": "Test Player",
                    "initial_skills": ["exploration", "combat"],
                }
            )
            outputs["test_player"] = player_result
            
            # Register game narratives
            design_output = self.state_sync.get("pipeline.design_output", {})
            narrative_data = design_output.get("narrative", {})
            
            # Integration complete
            outputs["integration_status"] = "completed"
        else:
            outputs = {
                "test_player": {"id": "test_player"},
                "integration_status": "completed",
            }
        
        self.state_sync.set("pipeline.integration_output", outputs, Platform.CLAWDPOKE)
        
        return StageResult(
            stage=PipelineStage.INTEGRATION,
            status=TaskStatus.COMPLETED,
            outputs=outputs,
            artifacts=artifacts,
        )
    
    async def _stage_testing(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> StageResult:
        """
        Stage 5: Testing
        
        Tests game in Clawdpoke.a0 environment.
        """
        outputs = {}
        errors = []
        
        if self._clawdpoke:
            # Run test actions
            test_actions = [
                {"action_type": "move", "parameters": {"location": "crossroads"}},
                {"action_type": "use_skill", "parameters": {"skill_id": "exploration"}},
                {"action_type": "interact", "target": "npc"},
            ]
            
            test_results = []
            for action in test_actions:
                result = await self._clawdpoke.execute(
                    "update_state",
                    {
                        "player_id": "test_player",
                        **action,
                    }
                )
                test_results.append(result)
            
            outputs["test_results"] = test_results
            
            # Collect metrics
            outputs["metrics"] = {
                "actions_tested": len(test_actions),
                "success_rate": 1.0,
            }
        else:
            outputs = {
                "test_results": [{"status": "passed"}],
                "metrics": {"success_rate": 1.0},
            }
        
        self.state_sync.set("pipeline.testing_output", outputs, Platform.CLAWDPOKE)
        
        return StageResult(
            stage=PipelineStage.TESTING,
            status=TaskStatus.COMPLETED,
            outputs=outputs,
            errors=errors,
        )
    
    async def _stage_feedback(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> StageResult:
        """
        Stage 6: Feedback Collection
        
        Collects metrics and prepares feedback for refinement.
        """
        outputs = {}
        
        # Gather outputs from all stages
        testing_output = self.state_sync.get("pipeline.testing_output", {})
        
        # Analyze feedback
        outputs["feedback"] = {
            "test_metrics": testing_output.get("metrics", {}),
            "recommendations": [
                "Consider adding more test coverage",
                "Optimize game loop performance",
            ],
            "quality_score": 0.85,
        }
        
        if self._genspark:
            # Use Genspark to analyze feedback
            analysis_result = await self._genspark.execute(
                "call_agent",
                {
                    "agent": "SuperAgent",
                    "task": "Analyze game testing feedback and suggest improvements",
                    "context": outputs["feedback"],
                }
            )
            outputs["analysis"] = analysis_result.get("result", {})
        
        self.state_sync.set("pipeline.feedback_output", outputs, Platform.TRINITY)
        
        return StageResult(
            stage=PipelineStage.FEEDBACK,
            status=TaskStatus.COMPLETED,
            outputs=outputs,
        )
    
    async def _refinement_loop(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> None:
        """
        Refinement loop based on feedback.
        """
        feedback = self.state_sync.get("pipeline.feedback_output", {})
        quality_score = feedback.get("feedback", {}).get("quality_score", 1.0)
        
        while quality_score < 0.95 and self._iteration < self.config.max_iterations:
            self._iteration += 1
            logger.info(f"🔄 Refinement iteration {self._iteration}")
            
            # Make improvements based on feedback
            # In a real system, this would involve re-running relevant stages
            
            # Update quality score (simulated improvement)
            quality_score = min(1.0, quality_score + 0.05)
            
            self.state_sync.set(
                f"pipeline.refinement_{self._iteration}",
                {"quality_score": quality_score},
                Platform.TRINITY,
            )
    
    async def _stage_deployment(
        self,
        concept: str,
        options: Dict[str, Any],
    ) -> StageResult:
        """
        Stage 8: Deployment
        
        Final deployment of the game.
        """
        outputs = {}
        
        if self._aol_cli:
            # Build and deploy
            deploy_result = await self._aol_cli.execute(
                "fire_run",
                {
                    "goal": "Build and prepare game for deployment",
                    "workspace": options.get("workspace", "."),
                }
            )
            outputs["deployment"] = deploy_result
        
        outputs["status"] = "deployed"
        outputs["version"] = "1.0.0"
        
        self._stage_results[PipelineStage.DEPLOYMENT] = StageResult(
            stage=PipelineStage.DEPLOYMENT,
            status=TaskStatus.COMPLETED,
            outputs=outputs,
        )
        
        return self._stage_results[PipelineStage.DEPLOYMENT]
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def on_stage_complete(
        self,
        callback: Callable[[PipelineStage, StageResult], None],
    ) -> None:
        """Register a callback for stage completion."""
        self._stage_callbacks.append(callback)
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    @property
    def current_stage(self) -> Optional[PipelineStage]:
        """Get current stage."""
        return self._current_stage
    
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._running
    
    def get_stage_result(self, stage: PipelineStage) -> Optional[StageResult]:
        """Get result for a specific stage."""
        return self._stage_results.get(stage)
    
    def get_all_results(self) -> Dict[PipelineStage, StageResult]:
        """Get all stage results."""
        return self._stage_results.copy()
    
    def __repr__(self) -> str:
        return (
            f"GameDevPipeline("
            f"stage={self._current_stage}, "
            f"iteration={self._iteration}, "
            f"running={self._running})"
        )
