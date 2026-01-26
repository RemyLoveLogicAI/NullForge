"""
Tri-Core Integration Tests
==========================

Comprehensive tests for the Tri-Core Integration Architecture.
"""

import pytest
import asyncio
from datetime import datetime

# Import all components
from tri_core.models import (
    Platform,
    TaskType,
    TaskStatus,
    EventPriority,
    TriCoreEvent,
    Task,
    Skill,
    SkillCategory,
    PlayerState,
    GameAction,
)
from tri_core.event_bus.bus import UnifiedEventBus
from tri_core.event_bus.state_sync import StateSync
from tri_core.event_bus.event_bridge import EventBridge
from tri_core.orchestrator.trinity import TrinityOrchestrator
from tri_core.orchestrator.router import AgentRouter
from tri_core.orchestrator.executor import CLIExecutor
from tri_core.orchestrator.game_manager import GameStateManager
from tri_core.orchestrator.interface_selector import InterfaceSelector
from tri_core.adapters.genspark import GensparkAdapter
from tri_core.adapters.aol_cli import AOLCLIAdapter
from tri_core.adapters.clawdpoke import ClawdpokeAdapter
from tri_core.clawdpoke.game_engine import ClawdpokeEngine
from tri_core.clawdpoke.skill_system import SkillSystem
from tri_core.clawdpoke.narrative_engine import NarrativeEngine


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def event_bus():
    """Create a fresh event bus for testing."""
    UnifiedEventBus.reset_instance()
    return UnifiedEventBus()


@pytest.fixture
def state_sync():
    """Create a state sync instance."""
    return StateSync()


@pytest.fixture
def event_bridge():
    """Create an event bridge instance."""
    return EventBridge()


@pytest.fixture
def game_engine():
    """Create a game engine instance."""
    return ClawdpokeEngine()


@pytest.fixture
def skill_system():
    """Create a skill system instance."""
    return SkillSystem()


@pytest.fixture
def narrative_engine():
    """Create a narrative engine instance."""
    return NarrativeEngine()


# =============================================================================
# EVENT BUS TESTS
# =============================================================================

class TestEventBus:
    """Tests for the Unified Event Bus."""
    
    def test_singleton_pattern(self, event_bus):
        """Test that event bus is a singleton."""
        bus2 = UnifiedEventBus()
        assert bus2 is event_bus
    
    def test_subscribe_and_publish(self, event_bus):
        """Test basic pub/sub functionality."""
        received = []
        
        def callback(event):
            received.append(event)
        
        sub_id = event_bus.subscribe("test.topic", callback)
        
        event = TriCoreEvent(
            source=Platform.TRINITY,
            event_type="test",
            payload={"message": "hello"},
        )
        
        delivered = event_bus.publish("test.topic", event)
        
        assert delivered == 1
        assert len(received) == 1
        assert received[0].payload["message"] == "hello"
    
    def test_wildcard_subscription(self, event_bus):
        """Test wildcard topic matching."""
        received = []
        
        event_bus.subscribe("game.*", lambda e: received.append(e))
        
        event_bus.publish(
            "game.start",
            TriCoreEvent(source=Platform.CLAWDPOKE, event_type="start", payload={}),
        )
        event_bus.publish(
            "game.end",
            TriCoreEvent(source=Platform.CLAWDPOKE, event_type="end", payload={}),
        )
        event_bus.publish(
            "other.topic",
            TriCoreEvent(source=Platform.GENSPARK, event_type="other", payload={}),
        )
        
        assert len(received) == 2
    
    def test_state_sync(self, event_bus):
        """Test state synchronization."""
        event_bus.sync_state("player.health", 100, Platform.CLAWDPOKE)
        
        value = event_bus.get_state("player.health")
        assert value == 100
    
    def test_unsubscribe(self, event_bus):
        """Test unsubscription."""
        received = []
        sub_id = event_bus.subscribe("test", lambda e: received.append(e))
        
        # Publish before unsubscribe
        event_bus.publish("test", TriCoreEvent(source=Platform.TRINITY, event_type="test", payload={}))
        assert len(received) == 1
        
        # Unsubscribe and publish again
        event_bus.unsubscribe(sub_id)
        event_bus.publish("test", TriCoreEvent(source=Platform.TRINITY, event_type="test", payload={}))
        assert len(received) == 1  # Should still be 1


# =============================================================================
# STATE SYNC TESTS
# =============================================================================

class TestStateSync:
    """Tests for State Synchronization."""
    
    def test_set_and_get(self, state_sync):
        """Test basic set and get."""
        version = state_sync.set("key", "value", Platform.GENSPARK)
        
        assert version == 1
        assert state_sync.get("key") == "value"
    
    def test_versioning(self, state_sync):
        """Test version incrementing."""
        v1 = state_sync.set("key", "value1", Platform.GENSPARK)
        v2 = state_sync.set("key", "value2", Platform.AOL_CLI)
        
        assert v1 == 1
        assert v2 == 2
    
    def test_expiration(self, state_sync):
        """Test TTL expiration."""
        import time
        
        state_sync.set("temp", "value", Platform.TRINITY, ttl=1)
        assert state_sync.get("temp") == "value"
        
        time.sleep(1.1)
        assert state_sync.get("temp") is None
    
    def test_snapshot_and_restore(self, state_sync):
        """Test snapshot functionality."""
        state_sync.set("a", 1, Platform.TRINITY)
        state_sync.set("b", 2, Platform.TRINITY)
        
        state_sync.create_snapshot("test_snapshot")
        
        state_sync.set("a", 999, Platform.TRINITY)
        state_sync.set("c", 3, Platform.TRINITY)
        
        state_sync.restore_snapshot("test_snapshot")
        
        assert state_sync.get("a") == 1
        assert state_sync.get("b") == 2
        assert state_sync.get("c") is None


# =============================================================================
# GAME ENGINE TESTS
# =============================================================================

class TestGameEngine:
    """Tests for the Clawdpoke Game Engine."""
    
    def test_create_player(self, game_engine):
        """Test player creation."""
        player = game_engine.create_player("p1", "Hero")
        
        assert player.id == "p1"
        assert player.name == "Hero"
        assert player.location == "start"
        assert "exploration" in player.skills
    
    def test_process_move_action(self, game_engine):
        """Test movement action."""
        game_engine.create_player("p1", "Hero")
        
        result = game_engine.process_action(
            GameAction(
                action_type="move",
                player_id="p1",
                parameters={"location": "crossroads"},
            )
        )
        
        assert result.player_state.location == "crossroads"
        assert "moved_to_crossroads" in result.events_triggered
    
    def test_skill_experience(self, game_engine):
        """Test skill experience gain."""
        player = game_engine.create_player("p1", "Hero", ["combat"])
        initial_exp = player.skills["combat"].experience
        
        game_engine.process_action(
            GameAction(
                action_type="use_skill",
                player_id="p1",
                parameters={"skill_id": "combat"},
            )
        )
        
        assert player.skills["combat"].experience > initial_exp
    
    def test_location_connectivity(self, game_engine):
        """Test location connections."""
        player = game_engine.create_player("p1", "Hero")
        
        # Can move to connected location
        result1 = game_engine.process_action(
            GameAction(
                action_type="move",
                player_id="p1",
                parameters={"location": "crossroads"},
            )
        )
        assert result1.player_state.location == "crossroads"
        
        # Can't move to unknown location
        result2 = game_engine.process_action(
            GameAction(
                action_type="move",
                player_id="p1",
                parameters={"location": "unknown_place"},  # Unknown location
            )
        )
        # Should fail
        assert "move_failed_unknown_location" in result2.events_triggered


# =============================================================================
# SKILL SYSTEM TESTS
# =============================================================================

class TestSkillSystem:
    """Tests for the Skill System."""
    
    def test_experience_calculation_linear(self, skill_system):
        """Test linear experience curve."""
        exp_l1 = skill_system.calculate_exp_for_level("exploration", 1)
        exp_l2 = skill_system.calculate_exp_for_level("exploration", 2)
        
        # Linear should scale proportionally
        assert exp_l2 == exp_l1 * 2
    
    def test_grant_experience(self, skill_system):
        """Test experience grant and level up."""
        skill = skill_system.create_skill("combat", level=1, experience=0)
        
        # Grant enough exp to level up
        result = skill_system.grant_experience(skill, 150)
        
        assert "levels_gained" in result
        assert result["experience_gained"] == 150
    
    def test_create_skill(self, skill_system):
        """Test skill creation from definition."""
        skill = skill_system.create_skill("magic")
        
        assert skill is not None
        assert skill.id == "magic"
        assert skill.category == SkillCategory.MAGIC


# =============================================================================
# NARRATIVE ENGINE TESTS
# =============================================================================

class TestNarrativeEngine:
    """Tests for the Narrative Engine."""
    
    def test_register_and_get_branch(self, narrative_engine):
        """Test branch registration."""
        from tri_core.models import NarrativeBranch, NarrativeChoice
        
        branch = NarrativeBranch(
            branch_id="test_branch",
            narrative_text="Test narrative",
            choices=[
                NarrativeChoice(
                    choice_id="choice1",
                    text="First choice",
                    required_skills=[],
                )
            ],
        )
        
        narrative_engine.register_branch(branch)
        
        retrieved = narrative_engine.get_branch("test_branch")
        assert retrieved is not None
        assert retrieved.branch_id == "test_branch"
    
    def test_skill_gated_choices(self, narrative_engine):
        """Test that choices are filtered by skill requirements."""
        from tri_core.models import NarrativeBranch, NarrativeChoice
        from tri_core.clawdpoke.narrative_engine import NarrativeContext
        
        branch = NarrativeBranch(
            branch_id="skill_test",
            narrative_text="Test",
            choices=[
                NarrativeChoice(
                    choice_id="easy",
                    text="Easy choice",
                    required_skills=[],
                ),
                NarrativeChoice(
                    choice_id="hard",
                    text="Hard choice",
                    required_skills=[{"skillId": "magic", "level": 10}],
                ),
            ],
        )
        
        narrative_engine.register_branch(branch)
        
        # Context with low skills
        context = NarrativeContext(
            player_id="p1",
            player_name="Hero",
            location="test",
            skills={"magic": 1},
            flags={},
            history=[],
        )
        
        result = narrative_engine.present_branch("skill_test", context)
        
        # Should have 2 total choices but only 1 available
        assert len(result["all_choices"]) == 2
        assert len(result["available_choices"]) == 1


# =============================================================================
# ADAPTER TESTS
# =============================================================================

class TestAdapters:
    """Tests for platform adapters."""
    
    @pytest.mark.asyncio
    async def test_genspark_adapter(self):
        """Test Genspark adapter."""
        adapter = GensparkAdapter()
        
        # Connect
        connected = await adapter.connect()
        assert connected
        
        # List agents
        result = await adapter.execute("list_agents", {})
        assert "agents" in result
        assert len(result["agents"]) > 0
        
        # Call agent
        result = await adapter.execute(
            "call_agent",
            {"agent": "AIDesigner", "task": "Test task"}
        )
        assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_aol_cli_adapter(self):
        """Test AOL-CLI adapter."""
        adapter = AOLCLIAdapter()
        
        connected = await adapter.connect()
        assert connected
        
        # Fire run (simulated)
        result = await adapter.execute(
            "fire_run",
            {"goal": "Test goal", "workspace": "."}
        )
        assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_clawdpoke_adapter(self):
        """Test Clawdpoke adapter."""
        adapter = ClawdpokeAdapter()
        
        connected = await adapter.connect()
        assert connected
        
        # Create player
        result = await adapter.execute(
            "create_player",
            {"player_id": "test_p", "name": "Test Player"}
        )
        assert result["player_id"] == "test_p"
        
        # Use skill
        result = await adapter.execute(
            "use_skill",
            {"player_id": "test_p", "skill_id": "exploration"}
        )
        assert "experience_gained" in result


# =============================================================================
# ORCHESTRATOR TESTS
# =============================================================================

class TestOrchestrator:
    """Tests for the Trinity Orchestrator."""
    
    @pytest.mark.asyncio
    async def test_task_execution(self):
        """Test basic task execution."""
        UnifiedEventBus.reset_instance()
        orchestrator = TrinityOrchestrator()
        
        # Register adapters
        orchestrator.register_adapter(Platform.GENSPARK, GensparkAdapter())
        orchestrator.register_adapter(Platform.AOL_CLI, AOLCLIAdapter())
        orchestrator.register_adapter(Platform.CLAWDPOKE, ClawdpokeAdapter())
        
        task = Task(
            name="Test Task",
            description="A test task",
            task_type=TaskType.CREATIVE,
        )
        
        result = await orchestrator.execute_task(task)
        
        assert "agent_response" in result
    
    def test_interface_selection(self):
        """Test interface selection."""
        selector = InterfaceSelector()
        
        task = Task(
            name="Design Task",
            description="Create a visual design",
            task_type=TaskType.CREATIVE,
        )
        
        result = selector.select(task)
        
        # Creative tasks should route to Genspark's UI
        assert result.platform == Platform.GENSPARK


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the full system."""
    
    @pytest.mark.asyncio
    async def test_full_demo_flow(self):
        """Test the complete demo flow."""
        from tri_core.demo.interactive import TriCoreDemo
        
        demo = TriCoreDemo()
        await demo.initialize()
        
        # Run event bus demo
        result = await demo._demo_event_bus()
        assert result["state_sync_works"]
        
        # Run agents demo
        result = await demo._demo_agents()
        assert result["agents_available"] > 0
        
        # Run game demo
        result = await demo._demo_game()
        assert result["game_action_processed"]
    
    @pytest.mark.asyncio
    async def test_narrative_workflow(self):
        """Test the narrative workflow."""
        from tri_core.demo.interactive import TriCoreDemo
        
        demo = TriCoreDemo()
        await demo.initialize()
        
        result = await demo.run_narrative_demo()
        
        assert result["narrative_generated"]
        assert result["choices_count"] > 0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
