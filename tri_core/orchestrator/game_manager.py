"""
Game State Manager
==================

Maps agent actions to Clawdpoke.a0 game mechanics and 
manages game state throughout the Tri-Core workflow.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import copy

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
class GameEvent:
    """An event that occurred in the game."""
    event_id: str
    event_type: str
    timestamp: datetime
    player_id: str
    data: Dict[str, Any]
    

@dataclass
class WorldState:
    """State of the game world."""
    locations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    global_flags: Dict[str, bool] = field(default_factory=dict)
    time_of_day: str = "day"
    weather: str = "clear"
    active_quests: List[str] = field(default_factory=list)


class GameStateManager:
    """
    🎮 Game State Manager
    
    Central manager for Clawdpoke.a0 game state.
    
    Features:
    - Player state management
    - Skill progression system
    - Narrative branch handling
    - World state tracking
    - Event system
    - State persistence
    """
    
    def __init__(self):
        """Initialize the game state manager."""
        self._players: Dict[str, PlayerState] = {}
        self._world = WorldState()
        self._narrative_branches: Dict[str, NarrativeBranch] = {}
        self._event_history: List[GameEvent] = []
        self._event_listeners: Dict[str, List[Callable]] = {}
        self._skill_definitions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default skills
        self._init_default_skills()
        
        logger.info("🎮 Game State Manager initialized")
    
    def _init_default_skills(self) -> None:
        """Initialize default skill definitions."""
        self._skill_definitions = {
            "programming": {
                "category": SkillCategory.TECHNICAL,
                "base_exp_rate": 100,
                "description": "Write and understand code",
            },
            "design": {
                "category": SkillCategory.CRAFTING,
                "base_exp_rate": 80,
                "description": "Create visual designs and UI",
            },
            "narrative": {
                "category": SkillCategory.SOCIAL,
                "base_exp_rate": 90,
                "description": "Write compelling stories",
            },
            "combat": {
                "category": SkillCategory.COMBAT,
                "base_exp_rate": 120,
                "description": "Fight enemies effectively",
            },
            "exploration": {
                "category": SkillCategory.EXPLORATION,
                "base_exp_rate": 75,
                "description": "Discover new areas",
            },
            "magic": {
                "category": SkillCategory.MAGIC,
                "base_exp_rate": 150,
                "description": "Cast powerful spells",
            },
            "crafting": {
                "category": SkillCategory.CRAFTING,
                "base_exp_rate": 85,
                "description": "Create items and tools",
            },
            "archaeology": {
                "category": SkillCategory.EXPLORATION,
                "base_exp_rate": 100,
                "description": "Study ancient artifacts",
            },
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
            player_id: Unique player identifier
            name: Player name
            initial_skills: List of skill IDs to grant
            
        Returns:
            New player state
        """
        player = PlayerState(
            id=player_id,
            name=name,
        )
        
        # Grant initial skills
        for skill_id in (initial_skills or ["exploration"]):
            if skill_id in self._skill_definitions:
                skill_def = self._skill_definitions[skill_id]
                player.skills[skill_id] = Skill(
                    id=skill_id,
                    name=skill_id.title(),
                    category=skill_def["category"],
                    description=skill_def["description"],
                )
        
        self._players[player_id] = player
        
        # Emit event
        self._emit_event("player_created", player_id, {"name": name})
        
        logger.info(f"🎮 Created player: {name} ({player_id})")
        return player
    
    def get_player(self, player_id: str) -> Optional[PlayerState]:
        """Get a player's state."""
        return self._players.get(player_id)
    
    def update_player(
        self,
        player_id: str,
        updates: Dict[str, Any],
    ) -> Optional[PlayerState]:
        """
        Update a player's state.
        
        Args:
            player_id: Player identifier
            updates: Fields to update
            
        Returns:
            Updated player state
        """
        player = self._players.get(player_id)
        if not player:
            return None
        
        for key, value in updates.items():
            if hasattr(player, key):
                setattr(player, key, value)
        
        self._emit_event("player_updated", player_id, updates)
        return player
    
    def delete_player(self, player_id: str) -> bool:
        """Delete a player."""
        if player_id in self._players:
            del self._players[player_id]
            self._emit_event("player_deleted", player_id, {})
            return True
        return False
    
    # =========================================================================
    # SKILL SYSTEM
    # =========================================================================
    
    def grant_skill(
        self,
        player_id: str,
        skill_id: str,
        level: int = 1,
    ) -> Optional[Skill]:
        """
        Grant a skill to a player.
        
        Args:
            player_id: Player identifier
            skill_id: Skill to grant
            level: Initial skill level
            
        Returns:
            The granted skill
        """
        player = self._players.get(player_id)
        if not player:
            return None
        
        if skill_id not in self._skill_definitions:
            logger.warning(f"Unknown skill: {skill_id}")
            return None
        
        skill_def = self._skill_definitions[skill_id]
        skill = Skill(
            id=skill_id,
            name=skill_id.title(),
            category=skill_def["category"],
            level=level,
            description=skill_def["description"],
        )
        
        player.skills[skill_id] = skill
        self._emit_event("skill_granted", player_id, {"skill_id": skill_id, "level": level})
        
        logger.info(f"🎮 Granted skill {skill_id} to player {player_id}")
        return skill
    
    def add_experience(
        self,
        player_id: str,
        skill_id: str,
        amount: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Add experience to a skill.
        
        Args:
            player_id: Player identifier
            skill_id: Skill to level
            amount: Experience amount
            
        Returns:
            Level up information if applicable
        """
        player = self._players.get(player_id)
        if not player or skill_id not in player.skills:
            return None
        
        skill = player.skills[skill_id]
        old_level = skill.level
        skill.experience += amount
        
        # Check for level up (100 exp per level)
        exp_needed = skill.level * 100
        leveled_up = False
        
        while skill.experience >= exp_needed:
            skill.experience -= exp_needed
            skill.level += 1
            exp_needed = skill.level * 100
            leveled_up = True
        
        result = {
            "skill_id": skill_id,
            "old_level": old_level,
            "new_level": skill.level,
            "leveled_up": leveled_up,
            "current_exp": skill.experience,
        }
        
        if leveled_up:
            self._emit_event("skill_level_up", player_id, result)
            logger.info(f"🎮 Player {player_id} leveled up {skill_id} to {skill.level}")
        
        return result
    
    def check_skill_requirement(
        self,
        player_id: str,
        skill_id: str,
        required_level: int,
    ) -> bool:
        """Check if a player meets a skill requirement."""
        player = self._players.get(player_id)
        if not player:
            return False
        
        skill = player.skills.get(skill_id)
        return skill is not None and skill.level >= required_level
    
    # =========================================================================
    # GAME ACTIONS
    # =========================================================================
    
    def process_action(self, action: GameAction) -> GameStateUpdate:
        """
        Process a game action and update state accordingly.
        
        Args:
            action: The game action to process
            
        Returns:
            State update result
        """
        logger.info(f"🎮 Processing action: {action.action_type}")
        
        player = self._players.get(action.player_id)
        if not player:
            # Auto-create player
            player = self.create_player(action.player_id, f"Player_{action.player_id}")
        
        events_triggered = []
        world_changes = {}
        narrative = None
        
        # Process based on action type
        if action.action_type == "move":
            new_location = action.parameters.get("location")
            if new_location:
                old_location = player.location
                player.location = new_location
                world_changes["player_location"] = {
                    "from": old_location,
                    "to": new_location,
                }
                events_triggered.append(f"moved_to_{new_location}")
                
                # Grant exploration exp
                self.add_experience(action.player_id, "exploration", 10)
        
        elif action.action_type == "use_skill":
            skill_id = action.parameters.get("skill_id")
            if skill_id and skill_id in player.skills:
                # Grant experience for using skill
                self.add_experience(action.player_id, skill_id, 25)
                events_triggered.append(f"used_skill_{skill_id}")
        
        elif action.action_type == "interact":
            target = action.target
            if target:
                events_triggered.append(f"interacted_with_{target}")
                # Could trigger narrative branches here
        
        elif action.action_type == "narrative_choice":
            branch_id = action.parameters.get("branch_id")
            choice_id = action.parameters.get("choice_id")
            if branch_id and choice_id:
                narrative = self._process_narrative_choice(
                    action.player_id, branch_id, choice_id
                )
                events_triggered.append(f"chose_{choice_id}")
        
        elif action.action_type == "NARRATIVE_ADVANCEMENT":
            # Handle narrative advancement from orchestrator
            new_scene = action.parameters.get("newScene")
            if new_scene:
                narrative = NarrativeBranch(
                    branch_id=new_scene.get("id", "generated"),
                    narrative_text=new_scene.get("description", ""),
                    choices=[],
                    location=new_scene.get("location"),
                )
                events_triggered.append("narrative_advanced")
        
        # Record event
        self._emit_event(action.action_type, action.player_id, action.parameters)
        
        return GameStateUpdate(
            update_type=action.action_type,
            player_state=copy.deepcopy(player),
            narrative=narrative,
            world_changes=world_changes,
            events_triggered=events_triggered,
        )
    
    def _process_narrative_choice(
        self,
        player_id: str,
        branch_id: str,
        choice_id: str,
    ) -> Optional[NarrativeBranch]:
        """Process a narrative choice."""
        branch = self._narrative_branches.get(branch_id)
        if not branch:
            return None
        
        # Find the choice
        choice = next((c for c in branch.choices if c.choice_id == choice_id), None)
        if not choice:
            return None
        
        player = self._players.get(player_id)
        if not player:
            return None
        
        # Check requirements
        for req in choice.required_skills:
            skill_id = req.get("skillId")
            level = req.get("level", 1)
            if not self.check_skill_requirement(player_id, skill_id, level):
                logger.warning(f"Player {player_id} doesn't meet requirements for {choice_id}")
                return None
        
        # Apply consequences
        for key, value in choice.consequences.items():
            if key == "grant_skill":
                self.grant_skill(player_id, value)
            elif key == "add_experience":
                skill_id, amount = value.split(":")
                self.add_experience(player_id, skill_id, int(amount))
            elif key == "set_flag":
                player.flags[value] = True
            elif key == "move_to":
                player.location = value
        
        # Return next branch if defined
        next_branch_id = choice.consequences.get("next_branch")
        if next_branch_id:
            return self._narrative_branches.get(next_branch_id)
        
        return None
    
    # =========================================================================
    # NARRATIVE MANAGEMENT
    # =========================================================================
    
    def register_narrative_branch(self, branch: NarrativeBranch) -> None:
        """Register a narrative branch."""
        self._narrative_branches[branch.branch_id] = branch
        logger.debug(f"📖 Registered narrative branch: {branch.branch_id}")
    
    def get_narrative_branch(self, branch_id: str) -> Optional[NarrativeBranch]:
        """Get a narrative branch."""
        return self._narrative_branches.get(branch_id)
    
    def get_available_choices(
        self,
        player_id: str,
        branch_id: str,
    ) -> List[NarrativeChoice]:
        """Get choices available to a player in a branch."""
        branch = self._narrative_branches.get(branch_id)
        if not branch:
            return []
        
        available = []
        for choice in branch.choices:
            # Check skill requirements
            meets_requirements = True
            for req in choice.required_skills:
                if not self.check_skill_requirement(
                    player_id,
                    req.get("skillId", ""),
                    req.get("level", 1),
                ):
                    meets_requirements = False
                    break
            
            if meets_requirements:
                available.append(choice)
        
        return available
    
    # =========================================================================
    # WORLD STATE
    # =========================================================================
    
    def get_world_state(self) -> WorldState:
        """Get current world state."""
        return copy.deepcopy(self._world)
    
    def update_world(self, updates: Dict[str, Any]) -> None:
        """Update world state."""
        for key, value in updates.items():
            if hasattr(self._world, key):
                setattr(self._world, key, value)
        
        self._emit_event("world_updated", "system", updates)
    
    def set_location_data(
        self,
        location_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Set data for a location."""
        self._world.locations[location_id] = data
    
    def get_location_data(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a location."""
        return self._world.locations.get(location_id)
    
    # =========================================================================
    # EVENT SYSTEM
    # =========================================================================
    
    def _emit_event(
        self,
        event_type: str,
        player_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Emit a game event."""
        import uuid
        event = GameEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            player_id=player_id,
            data=data,
        )
        
        self._event_history.append(event)
        
        # Notify listeners
        for listener in self._event_listeners.get(event_type, []):
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")
        
        # Notify global listeners
        for listener in self._event_listeners.get("*", []):
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Global event listener error: {e}")
    
    def on_event(self, event_type: str, callback: Callable[[GameEvent], None]) -> None:
        """Register an event listener."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)
    
    def get_event_history(
        self,
        player_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[GameEvent]:
        """Get event history with optional filters."""
        events = self._event_history
        
        if player_id:
            events = [e for e in events if e.player_id == player_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def export_state(self) -> Dict[str, Any]:
        """Export complete game state for persistence."""
        return {
            "players": {
                pid: player.model_dump()
                for pid, player in self._players.items()
            },
            "world": {
                "locations": self._world.locations,
                "global_flags": self._world.global_flags,
                "time_of_day": self._world.time_of_day,
                "weather": self._world.weather,
                "active_quests": self._world.active_quests,
            },
            "narrative_branches": {
                bid: branch.model_dump()
                for bid, branch in self._narrative_branches.items()
            },
        }
    
    def import_state(self, state: Dict[str, Any]) -> None:
        """Import game state from exported data."""
        # Import players
        for pid, pdata in state.get("players", {}).items():
            self._players[pid] = PlayerState(**pdata)
        
        # Import world
        world_data = state.get("world", {})
        self._world.locations = world_data.get("locations", {})
        self._world.global_flags = world_data.get("global_flags", {})
        self._world.time_of_day = world_data.get("time_of_day", "day")
        self._world.weather = world_data.get("weather", "clear")
        self._world.active_quests = world_data.get("active_quests", [])
        
        # Import narrative branches
        for bid, bdata in state.get("narrative_branches", {}).items():
            self._narrative_branches[bid] = NarrativeBranch(**bdata)
        
        logger.info("🎮 Game state imported")
    
    def stats(self) -> Dict[str, Any]:
        """Get game statistics."""
        return {
            "players": len(self._players),
            "locations": len(self._world.locations),
            "narrative_branches": len(self._narrative_branches),
            "events_recorded": len(self._event_history),
            "active_quests": len(self._world.active_quests),
        }
    
    def __repr__(self) -> str:
        s = self.stats()
        return f"GameStateManager(players={s['players']}, events={s['events_recorded']})"
