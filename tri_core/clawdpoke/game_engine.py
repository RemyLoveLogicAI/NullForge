"""
Clawdpoke.a0 Game Engine
========================

The core game engine powering the Clawdpoke.a0 game framework.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from tri_core.models import (
    Platform,
    PlayerState,
    Skill,
    SkillCategory,
    GameAction,
    GameStateUpdate,
    NarrativeBranch,
    NarrativeChoice,
)

logger = logging.getLogger(__name__)


@dataclass
class GameConfig:
    """Configuration for the game engine."""
    tick_rate: float = 60.0  # Updates per second
    max_players: int = 1000
    enable_persistence: bool = True
    enable_events: bool = True
    default_location: str = "start"


@dataclass
class Location:
    """A location in the game world."""
    id: str
    name: str
    description: str
    connected_locations: List[str] = field(default_factory=list)
    npcs: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)


class ClawdpokeEngine:
    """
    🎮 Clawdpoke.a0 Game Engine
    
    The core engine powering the game framework.
    
    Features:
    - Player management
    - Skill progression
    - Location/world management
    - Event system
    - Game loop
    - State persistence
    
    Usage:
        engine = ClawdpokeEngine()
        player = engine.create_player("player_1", "Hero")
        engine.process_action(GameAction(action_type="move", player_id="player_1", parameters={"location": "village"}))
    """
    
    def __init__(self, config: Optional[GameConfig] = None):
        """Initialize the game engine."""
        self.config = config or GameConfig()
        
        # Core state
        self._players: Dict[str, PlayerState] = {}
        self._locations: Dict[str, Location] = {}
        self._narratives: Dict[str, NarrativeBranch] = {}
        
        # Event system
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._event_queue: List[Dict[str, Any]] = []
        
        # Game loop
        self._running = False
        self._tick_count = 0
        self._last_update = datetime.utcnow()
        
        # Initialize world
        self._init_world()
        
        logger.info("🎮 Clawdpoke.a0 Game Engine initialized")
    
    def _init_world(self) -> None:
        """Initialize the game world."""
        # Create starting locations
        self._locations = {
            "start": Location(
                id="start",
                name="Starting Point",
                description="Your journey begins here.",
                connected_locations=["crossroads", "tutorial_area"],
            ),
            "crossroads": Location(
                id="crossroads",
                name="The Crossroads",
                description="A junction where many paths meet.",
                connected_locations=["start", "village", "forest", "ancient_ruins"],
            ),
            "village": Location(
                id="village",
                name="Riverside Village",
                description="A peaceful village by the river.",
                connected_locations=["crossroads", "merchant_shop", "tavern"],
                npcs=["merchant", "innkeeper"],
            ),
            "forest": Location(
                id="forest",
                name="Dark Forest",
                description="A mysterious forest full of secrets.",
                connected_locations=["crossroads", "forest_clearing"],
                events=["random_encounter"],
            ),
            "ancient_ruins": Location(
                id="ancient_ruins",
                name="Ancient Ruins",
                description="Crumbling structures hint at a forgotten civilization.",
                connected_locations=["crossroads", "ruins_depths"],
                events=["discovery"],
            ),
            "tutorial_area": Location(
                id="tutorial_area",
                name="Training Grounds",
                description="A safe place to learn the basics.",
                connected_locations=["start"],
            ),
        }
    
    # =========================================================================
    # PLAYER MANAGEMENT
    # =========================================================================
    
    def create_player(
        self,
        player_id: str,
        name: str,
        initial_skills: Optional[List[str]] = None,
    ) -> PlayerState:
        """
        Create a new player.
        
        Args:
            player_id: Unique identifier
            name: Display name
            initial_skills: Skills to grant at creation
            
        Returns:
            New player state
        """
        player = PlayerState(
            id=player_id,
            name=name,
            location=self.config.default_location,
        )
        
        # Grant initial skills
        for skill_id in (initial_skills or ["exploration"]):
            player.skills[skill_id] = Skill(
                id=skill_id,
                name=skill_id.replace("_", " ").title(),
                category=SkillCategory.EXPLORATION,
                level=1,
            )
        
        self._players[player_id] = player
        
        # Emit event
        self._emit("player_created", {
            "player_id": player_id,
            "name": name,
        })
        
        logger.info(f"🎮 Player created: {name}")
        return player
    
    def get_player(self, player_id: str) -> Optional[PlayerState]:
        """Get a player by ID."""
        return self._players.get(player_id)
    
    def get_all_players(self) -> List[PlayerState]:
        """Get all players."""
        return list(self._players.values())
    
    def update_player(
        self,
        player_id: str,
        **updates,
    ) -> Optional[PlayerState]:
        """Update player attributes."""
        player = self._players.get(player_id)
        if not player:
            return None
        
        for key, value in updates.items():
            if hasattr(player, key):
                setattr(player, key, value)
        
        self._emit("player_updated", {"player_id": player_id, "updates": updates})
        return player
    
    # =========================================================================
    # ACTION PROCESSING
    # =========================================================================
    
    def process_action(self, action: GameAction) -> GameStateUpdate:
        """
        Process a game action.
        
        Args:
            action: The action to process
            
        Returns:
            State update result
        """
        player = self._players.get(action.player_id)
        if not player:
            # Auto-create player
            player = self.create_player(action.player_id, f"Player_{action.player_id}")
        
        events = []
        world_changes = {}
        narrative = None
        
        # Route to action handler
        handler = getattr(self, f"_action_{action.action_type}", None)
        if handler:
            result = handler(player, action)
            events.extend(result.get("events", []))
            world_changes.update(result.get("world_changes", {}))
            narrative = result.get("narrative")
        else:
            # Generic action
            events.append(f"action_{action.action_type}")
        
        self._emit("action_processed", {
            "action": action.action_type,
            "player_id": action.player_id,
        })
        
        return GameStateUpdate(
            update_type=action.action_type,
            player_state=player,
            narrative=narrative,
            world_changes=world_changes,
            events_triggered=events,
        )
    
    def _action_move(self, player: PlayerState, action: GameAction) -> Dict[str, Any]:
        """Handle move action."""
        new_location = action.parameters.get("location")
        
        if not new_location:
            return {"events": ["move_failed_no_destination"]}
        
        # Check if location exists
        if new_location not in self._locations:
            return {"events": ["move_failed_unknown_location"]}
        
        # Check if connected
        current_loc = self._locations.get(player.location)
        if current_loc and new_location not in current_loc.connected_locations:
            return {"events": ["move_failed_not_connected"]}
        
        old_location = player.location
        player.location = new_location
        
        # Grant exploration XP
        self._grant_experience(player, "exploration", 10)
        
        return {
            "events": [f"moved_to_{new_location}"],
            "world_changes": {
                "player_location": {
                    "from": old_location,
                    "to": new_location,
                }
            },
        }
    
    def _action_use_skill(self, player: PlayerState, action: GameAction) -> Dict[str, Any]:
        """Handle skill use action."""
        skill_id = action.parameters.get("skill_id")
        
        if not skill_id or skill_id not in player.skills:
            return {"events": ["skill_use_failed"]}
        
        skill = player.skills[skill_id]
        
        # Grant XP for using skill
        self._grant_experience(player, skill_id, 25)
        
        return {
            "events": [f"used_{skill_id}"],
            "world_changes": {
                "skill_used": {
                    "skill": skill_id,
                    "level": skill.level,
                }
            },
        }
    
    def _action_interact(self, player: PlayerState, action: GameAction) -> Dict[str, Any]:
        """Handle interaction action."""
        target = action.target
        
        if not target:
            return {"events": ["interact_failed_no_target"]}
        
        return {
            "events": [f"interacted_with_{target}"],
        }
    
    def _action_combat(self, player: PlayerState, action: GameAction) -> Dict[str, Any]:
        """Handle combat action."""
        attack_type = action.parameters.get("attack_type", "basic")
        target = action.target
        
        # Calculate damage based on skills
        combat_skill = player.skills.get("combat")
        base_damage = 10
        skill_bonus = (combat_skill.level * 2) if combat_skill else 0
        total_damage = base_damage + skill_bonus
        
        # Grant combat XP
        self._grant_experience(player, "combat", 20)
        
        return {
            "events": [f"attacked_{target}"],
            "world_changes": {
                "combat": {
                    "attacker": player.id,
                    "target": target,
                    "damage": total_damage,
                }
            },
        }
    
    # =========================================================================
    # SKILL SYSTEM
    # =========================================================================
    
    def _grant_experience(
        self,
        player: PlayerState,
        skill_id: str,
        amount: int,
    ) -> Dict[str, Any]:
        """Grant experience to a skill."""
        if skill_id not in player.skills:
            # Create skill if not exists
            player.skills[skill_id] = Skill(
                id=skill_id,
                name=skill_id.replace("_", " ").title(),
                category=SkillCategory.TECHNICAL,
                level=1,
            )
        
        skill = player.skills[skill_id]
        old_level = skill.level
        skill.experience += amount
        
        # Level up (100 XP per level)
        while skill.experience >= skill.level * 100:
            skill.experience -= skill.level * 100
            skill.level += 1
            self._emit("skill_level_up", {
                "player_id": player.id,
                "skill_id": skill_id,
                "new_level": skill.level,
            })
        
        return {
            "skill_id": skill_id,
            "experience_gained": amount,
            "old_level": old_level,
            "new_level": skill.level,
            "leveled_up": skill.level > old_level,
        }
    
    def grant_skill(
        self,
        player_id: str,
        skill_id: str,
        level: int = 1,
    ) -> Optional[Skill]:
        """Grant a skill to a player."""
        player = self._players.get(player_id)
        if not player:
            return None
        
        skill = Skill(
            id=skill_id,
            name=skill_id.replace("_", " ").title(),
            category=SkillCategory.TECHNICAL,
            level=level,
        )
        
        player.skills[skill_id] = skill
        
        self._emit("skill_granted", {
            "player_id": player_id,
            "skill_id": skill_id,
            "level": level,
        })
        
        return skill
    
    # =========================================================================
    # LOCATION SYSTEM
    # =========================================================================
    
    def get_location(self, location_id: str) -> Optional[Location]:
        """Get a location by ID."""
        return self._locations.get(location_id)
    
    def get_connected_locations(self, location_id: str) -> List[Location]:
        """Get locations connected to a given location."""
        location = self._locations.get(location_id)
        if not location:
            return []
        
        return [
            self._locations[loc_id]
            for loc_id in location.connected_locations
            if loc_id in self._locations
        ]
    
    def add_location(self, location: Location) -> None:
        """Add a new location to the world."""
        self._locations[location.id] = location
        self._emit("location_added", {"location_id": location.id})
    
    # =========================================================================
    # NARRATIVE SYSTEM
    # =========================================================================
    
    def register_narrative(self, branch: NarrativeBranch) -> None:
        """Register a narrative branch."""
        self._narratives[branch.branch_id] = branch
    
    def get_narrative(self, branch_id: str) -> Optional[NarrativeBranch]:
        """Get a narrative branch."""
        return self._narratives.get(branch_id)
    
    def get_available_choices(
        self,
        player_id: str,
        branch_id: str,
    ) -> List[NarrativeChoice]:
        """Get choices available to a player."""
        branch = self._narratives.get(branch_id)
        if not branch:
            return []
        
        player = self._players.get(player_id)
        if not player:
            return branch.choices
        
        available = []
        for choice in branch.choices:
            meets_requirements = True
            for req in choice.required_skills:
                skill = player.skills.get(req.get("skillId", ""))
                if not skill or skill.level < req.get("level", 1):
                    meets_requirements = False
                    break
            if meets_requirements:
                available.append(choice)
        
        return available
    
    # =========================================================================
    # EVENT SYSTEM
    # =========================================================================
    
    def on(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def off(self, event_type: str, handler: Callable) -> bool:
        """Remove an event handler."""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False
    
    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event."""
        if not self.config.enable_events:
            return
        
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._event_queue.append(event)
        
        # Notify handlers
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        # Also call wildcard handlers
        for handler in self._event_handlers.get("*", []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Wildcard handler error: {e}")
    
    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events."""
        return self._event_queue[-limit:]
    
    # =========================================================================
    # GAME LOOP
    # =========================================================================
    
    async def start(self) -> None:
        """Start the game loop."""
        self._running = True
        logger.info("🎮 Game loop started")
        
        while self._running:
            await self._tick()
            await asyncio.sleep(1.0 / self.config.tick_rate)
    
    async def stop(self) -> None:
        """Stop the game loop."""
        self._running = False
        logger.info("🎮 Game loop stopped")
    
    async def _tick(self) -> None:
        """Process one game tick."""
        self._tick_count += 1
        self._last_update = datetime.utcnow()
        
        # Process any pending game logic
        # (In a real game, this would handle AI, physics, etc.)
    
    @property
    def is_running(self) -> bool:
        """Check if game is running."""
        return self._running
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def export_state(self) -> Dict[str, Any]:
        """Export game state for persistence."""
        return {
            "players": {
                pid: player.model_dump()
                for pid, player in self._players.items()
            },
            "locations": {
                lid: {
                    "id": loc.id,
                    "name": loc.name,
                    "description": loc.description,
                    "connected_locations": loc.connected_locations,
                    "npcs": loc.npcs,
                    "items": loc.items,
                    "events": loc.events,
                }
                for lid, loc in self._locations.items()
            },
            "narratives": {
                nid: narrative.model_dump()
                for nid, narrative in self._narratives.items()
            },
            "tick_count": self._tick_count,
        }
    
    def import_state(self, state: Dict[str, Any]) -> None:
        """Import game state from persistence."""
        # Import players
        for pid, pdata in state.get("players", {}).items():
            self._players[pid] = PlayerState(**pdata)
        
        # Import locations
        for lid, ldata in state.get("locations", {}).items():
            self._locations[lid] = Location(**ldata)
        
        # Import narratives
        for nid, ndata in state.get("narratives", {}).items():
            self._narratives[nid] = NarrativeBranch(**ndata)
        
        self._tick_count = state.get("tick_count", 0)
        logger.info("🎮 Game state imported")
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "players": len(self._players),
            "locations": len(self._locations),
            "narratives": len(self._narratives),
            "events_queued": len(self._event_queue),
            "tick_count": self._tick_count,
            "running": self._running,
        }
    
    def __repr__(self) -> str:
        s = self.stats()
        return f"ClawdpokeEngine(players={s['players']}, running={s['running']})"
