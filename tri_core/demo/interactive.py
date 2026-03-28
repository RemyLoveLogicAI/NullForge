"""
Interactive Demo
================

Interactive demonstration of the Tri-Core Integration Architecture.
Perfect for hackathons and showcases.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from tri_core.event_bus.bus import UnifiedEventBus
from tri_core.event_bus.state_sync import StateSync
from tri_core.orchestrator.trinity import TrinityOrchestrator
from tri_core.adapters.genspark import GensparkAdapter
from tri_core.adapters.aol_cli import AOLCLIAdapter
from tri_core.adapters.clawdpoke import ClawdpokeAdapter
from tri_core.clawdpoke.game_engine import ClawdpokeEngine
from tri_core.workflows.pipeline import GameDevPipeline
from tri_core.workflows.narrative import MultiAgentNarrativeWorkflow
from tri_core.models import (
    Platform,
    Task,
    TaskType,
    GameAction,
    PlayerState,
    TriCoreEvent,
)

logger = logging.getLogger(__name__)


class TriCoreDemo:
    """
    🔱 Tri-Core Interactive Demo
    
    A comprehensive demonstration of the Tri-Core Integration Architecture
    showcasing all three platforms working together.
    
    Perfect for:
    - Hackathon presentations
    - Technical demos
    - Architecture showcases
    - Integration testing
    
    Usage:
        demo = TriCoreDemo()
        await demo.initialize()
        await demo.run_game_development_demo("Create a platformer game")
        await demo.run_narrative_demo()
    """
    
    def __init__(self):
        """Initialize the demo."""
        # Core components
        self.event_bus = UnifiedEventBus()
        self.state_sync = StateSync()
        self.orchestrator = TrinityOrchestrator(event_bus=self.event_bus)
        
        # Adapters
        self.genspark = GensparkAdapter()
        self.aol_cli = AOLCLIAdapter()
        self.clawdpoke = ClawdpokeAdapter()
        
        # Game engine
        self.game_engine = ClawdpokeEngine()
        
        # Workflows
        self.pipeline = GameDevPipeline(event_bus=self.event_bus)
        self.narrative_workflow = MultiAgentNarrativeWorkflow(event_bus=self.event_bus)
        
        # Demo state
        self._initialized = False
        self._demo_player: Optional[PlayerState] = None
        self._demo_log: List[Dict[str, Any]] = []
        
        logger.info("🔱 Tri-Core Demo created")
    
    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return
        
        self._log("Initializing Tri-Core Demo...")
        
        # Register adapters with orchestrator
        self.orchestrator.register_adapter(Platform.GENSPARK, self.genspark)
        self.orchestrator.register_adapter(Platform.AOL_CLI, self.aol_cli)
        self.orchestrator.register_adapter(Platform.CLAWDPOKE, self.clawdpoke)
        
        # Set adapters for pipeline
        self.pipeline.set_adapters(self.genspark, self.aol_cli, self.clawdpoke)
        
        # Set adapters for narrative workflow
        self.narrative_workflow.set_adapters(self.genspark, self.aol_cli, self.clawdpoke)
        
        # Connect adapters
        await self.genspark.connect()
        await self.aol_cli.connect()
        await self.clawdpoke.connect()
        
        # Create demo player
        self._demo_player = self.game_engine.create_player(
            "demo_player",
            "Demo Hero",
            initial_skills=["exploration", "combat", "archaeology"],
        )
        
        self._initialized = True
        self._log("✅ Tri-Core Demo initialized successfully!")
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log a demo message."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
        }
        self._demo_log.append(entry)
        
        if level == "info":
            logger.info(f"🔱 {message}")
        elif level == "error":
            logger.error(f"❌ {message}")
        else:
            logger.debug(f"📝 {message}")
    
    # =========================================================================
    # DEMO SCENARIOS
    # =========================================================================
    
    async def run_full_demo(self, game_concept: str = "Create a platformer game") -> Dict[str, Any]:
        """
        Run the complete Tri-Core demonstration.
        
        Shows all capabilities in sequence.
        """
        await self.initialize()
        
        self._log("=" * 60)
        self._log("🔱 TRI-CORE INTEGRATION ARCHITECTURE DEMO")
        self._log("=" * 60)
        
        results = {}
        
        # 1. Event Bus Demo
        self._log("\n📡 DEMO 1: Unified Event Bus")
        results["event_bus"] = await self._demo_event_bus()
        
        # 2. Multi-Agent Demo
        self._log("\n🤖 DEMO 2: Multi-Agent Orchestration (Genspark)")
        results["agents"] = await self._demo_agents()
        
        # 3. CLI Execution Demo
        self._log("\n⚡ DEMO 3: CLI Execution (AOL-CLI)")
        results["cli"] = await self._demo_cli()
        
        # 4. Game Engine Demo
        self._log("\n🎮 DEMO 4: Game Framework (Clawdpoke.a0)")
        results["game"] = await self._demo_game()
        
        # 5. Pipeline Demo
        self._log("\n🚀 DEMO 5: Game Development Pipeline")
        results["pipeline"] = await self.run_game_development_demo(game_concept)
        
        # 6. Narrative Demo
        self._log("\n📖 DEMO 6: Multi-Agent Narrative")
        results["narrative"] = await self.run_narrative_demo()
        
        self._log("\n" + "=" * 60)
        self._log("✅ DEMO COMPLETE!")
        self._log("=" * 60)
        
        return {
            "status": "completed",
            "results": results,
            "log": self._demo_log,
        }
    
    async def _demo_event_bus(self) -> Dict[str, Any]:
        """Demonstrate the event bus."""
        events_received = []
        
        # Subscribe to events
        def on_event(event: TriCoreEvent):
            events_received.append(event.event_type)
        
        sub_id = self.event_bus.subscribe("demo.*", on_event)
        
        # Publish events
        self.event_bus.publish(
            "demo.test",
            TriCoreEvent(
                source=Platform.TRINITY,
                event_type="demo_event",
                payload={"message": "Hello from Event Bus!"},
            )
        )
        
        # State sync
        self.state_sync.set("demo.value", 42, Platform.TRINITY)
        value = self.state_sync.get("demo.value")
        
        self._log(f"  → Published event, received {len(events_received)} events")
        self._log(f"  → State sync: stored 42, retrieved {value}")
        
        # Cleanup
        self.event_bus.unsubscribe(sub_id)
        
        return {
            "events_published": 1,
            "events_received": len(events_received),
            "state_sync_works": value == 42,
        }
    
    async def _demo_agents(self) -> Dict[str, Any]:
        """Demonstrate Genspark agents."""
        # List agents
        agents_result = await self.genspark.execute("list_agents", {"include_capabilities": True})
        agents = agents_result.get("agents", [])
        
        self._log(f"  → Found {len(agents)} Genspark agents")
        
        # Call an agent
        result = await self.genspark.execute(
            "call_agent",
            {
                "agent": "AIDesigner",
                "task": "Design a simple game UI",
                "context": {"style": "modern"},
            }
        )
        
        self._log(f"  → AIDesigner responded with design recommendations")
        
        # Orchestrate
        orchestration = await self.genspark.execute(
            "orchestrate",
            {
                "goal": "Create a game concept",
                "strategy": "sequential",
            }
        )
        
        steps = orchestration.get("steps_completed", 0)
        self._log(f"  → Orchestration completed {steps} steps")
        
        return {
            "agents_available": len(agents),
            "agent_call_success": result.get("status") == "completed",
            "orchestration_steps": steps,
        }
    
    async def _demo_cli(self) -> Dict[str, Any]:
        """Demonstrate AOL-CLI."""
        # Fire run (simulated)
        result = await self.aol_cli.execute(
            "fire_run",
            {
                "goal": "Create a simple Python function",
                "workspace": ".",
            }
        )
        
        self._log(f"  → Fire run completed: {result.get('status')}")
        
        # Project analysis
        analysis = await self.aol_cli.execute(
            "fire_analyze",
            {"path": ".", "deep": False}
        )
        
        techs = analysis.get("technologies", {})
        self._log(f"  → Project analysis found: {techs.get('languages', [])}")
        
        # Code generation
        code_result = await self.aol_cli.execute(
            "generate_code",
            {
                "description": "A simple game loop",
                "language": "python",
            }
        )
        
        self._log(f"  → Generated code in Python")
        
        return {
            "fire_run_success": result.get("status") == "completed",
            "analysis_complete": bool(analysis),
            "code_generated": bool(code_result.get("code")),
        }
    
    async def _demo_game(self) -> Dict[str, Any]:
        """Demonstrate Clawdpoke game framework."""
        # Create player via adapter
        player_result = await self.clawdpoke.execute(
            "create_player",
            {
                "player_id": "adapter_player",
                "name": "Adapter Hero",
                "initial_skills": ["exploration"],
            }
        )
        
        self._log(f"  → Created player: {player_result.get('name')}")
        
        # Use skill
        skill_result = await self.clawdpoke.execute(
            "use_skill",
            {
                "player_id": "adapter_player",
                "skill_id": "exploration",
            }
        )
        
        self._log(f"  → Used skill, gained {skill_result.get('experience_gained', 0)} XP")
        
        # Get narrative
        narrative = await self.clawdpoke.execute(
            "get_narrative",
            {
                "branch_id": "hero_decision_1",
                "player_id": "adapter_player",
            }
        )
        
        choices = len(narrative.get("available_choices", []))
        self._log(f"  → Narrative branch has {choices} available choices")
        
        # Game engine direct usage
        action_result = self.game_engine.process_action(
            GameAction(
                action_type="move",
                player_id="demo_player",
                parameters={"location": "crossroads"},
            )
        )
        
        self._log(f"  → Moved player to {action_result.player_state.location}")
        
        return {
            "player_created": bool(player_result),
            "skill_used": bool(skill_result),
            "narrative_loaded": choices > 0,
            "game_action_processed": bool(action_result),
        }
    
    async def run_game_development_demo(
        self,
        concept: str = "Create a platformer game with jumping mechanics",
    ) -> Dict[str, Any]:
        """
        Run a game development pipeline demo.
        
        Args:
            concept: Game concept to develop
            
        Returns:
            Pipeline results
        """
        await self.initialize()
        
        self._log(f"  → Starting pipeline for: {concept[:50]}...")
        
        # Set up stage callback
        def on_stage(stage, result):
            self._log(f"    → Stage {stage.value}: {result.status.value}")
        
        self.pipeline.on_stage_complete(on_stage)
        
        # Run pipeline
        result = await self.pipeline.run(concept)
        
        self._log(f"  → Pipeline completed in {result.get('total_duration', 0):.2f}s")
        
        return result
    
    async def run_narrative_demo(self) -> Dict[str, Any]:
        """
        Run a multi-agent narrative demo.
        
        Demonstrates dynamic story generation across platforms.
        """
        await self.initialize()
        
        self._log("  → Starting narrative demo...")
        
        # Ensure demo player exists
        if not self._demo_player:
            self._demo_player = self.game_engine.create_player(
                "demo_player",
                "Demo Hero",
                initial_skills=["exploration", "archaeology"],
            )
        
        # Generate a narrative response
        response = await self.narrative_workflow.handle_player_choice(
            "demo_player",
            "investigate_ruins",
            self._demo_player,
        )
        
        self._log(f"  → Generated narrative: {response.branch.narrative_text[:50]}...")
        self._log(f"  → Choices available: {len(response.branch.choices)}")
        
        # Generate random encounter
        encounter = await self.narrative_workflow.generate_random_encounter(
            "demo_player",
            self._demo_player,
            "discovery",
        )
        
        self._log(f"  → Generated encounter: {encounter.narrative_text[:50]}...")
        
        return {
            "narrative_generated": bool(response.branch),
            "choices_count": len(response.branch.choices),
            "encounter_generated": bool(encounter),
        }
    
    async def run_integration_demo(self) -> Dict[str, Any]:
        """
        Demonstrate full cross-platform integration.
        
        Shows data flowing between all three platforms.
        """
        await self.initialize()
        
        self._log("  → Running integration demo...")
        
        # 1. Create task in Genspark
        task = Task(
            name="Integration Test",
            description="Test cross-platform integration",
            task_type=TaskType.HYBRID,
        )
        
        # 2. Execute through orchestrator
        result = await self.orchestrator.execute_task(task)
        
        self._log(f"  → Task executed through orchestrator")
        
        # 3. Check state sync
        state_entries = self.state_sync.stats()["total_entries"]
        
        self._log(f"  → State sync has {state_entries} entries")
        
        # 4. Check event metrics
        metrics = self.event_bus.get_metrics()
        
        self._log(f"  → Event bus: {metrics['events_published']} events published")
        
        return {
            "task_completed": bool(result),
            "state_entries": state_entries,
            "events_published": metrics["events_published"],
        }
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def get_demo_log(self) -> List[Dict[str, Any]]:
        """Get the demo log."""
        return self._demo_log.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "initialized": self._initialized,
            "event_bus": self.event_bus.get_metrics(),
            "state_sync": self.state_sync.stats(),
            "orchestrator": self.orchestrator.get_stats(),
            "genspark": self.genspark.get_metrics(),
            "aol_cli": self.aol_cli.get_metrics(),
            "clawdpoke": self.clawdpoke.get_metrics(),
            "game_engine": self.game_engine.stats(),
            "pipeline": {
                "current_stage": self.pipeline.current_stage,
                "is_running": self.pipeline.is_running,
            },
        }
    
    def print_banner(self) -> str:
        """Print the demo banner."""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🔱 TRI-CORE INTEGRATION ARCHITECTURE 🔱                    ║
║                                                              ║
║   Genspark + AOL-CLI + Clawdpoke.a0                         ║
║                                                              ║
║   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        ║
║   │  GENSPARK   │◄─►│   AOL-CLI   │◄─►│ CLAWDPOKE  │        ║
║   │ Multi-Agent │  │  Terminal   │  │    Game     │        ║
║   └─────────────┘  └─────────────┘  └─────────────┘        ║
║          │               │               │                  ║
║          └───────────────┼───────────────┘                  ║
║                          │                                  ║
║               ┌──────────┴──────────┐                      ║
║               │  TRINITY ORCHESTRATOR │                      ║
║               └─────────────────────┘                      ║
║                                                              ║
║   Version 1.0 | Hackathon Ready | Production Grade          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        return banner
    
    def __repr__(self) -> str:
        return f"TriCoreDemo(initialized={self._initialized})"


async def run_demo():
    """Run the interactive demo."""
    demo = TriCoreDemo()
    
    # Print banner
    print(demo.print_banner())
    
    # Run full demo
    results = await demo.run_full_demo()
    
    # Print stats
    print("\n📊 Final Statistics:")
    stats = demo.get_stats()
    print(f"  • Event Bus: {stats['event_bus']['events_published']} events published")
    print(f"  • Orchestrator: {stats['orchestrator'].get('tasks_completed', 0)} tasks completed")
    print(f"  • Game Engine: {stats['game_engine'].get('players', 0)} players active")
    
    return results


if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the demo
    try:
        results = asyncio.run(run_demo())
        print("\n✅ Demo completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
