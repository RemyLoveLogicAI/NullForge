"""
Clawdpoke.a0 Adapter
====================

Adapter for integrating with Clawdpoke.a0 game framework and skill system.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

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
from tri_core.adapters.base import BaseAdapter, AdapterConfig

logger = logging.getLogger(__name__)


@dataclass
class ClawdpokeConfig(AdapterConfig):
    """Configuration for Clawdpoke.a0 adapter."""
    game_server_url: str = "http://localhost:8080"
    enable_skills_mcp: bool = True
    enable_games_mcp: bool = True
    default_player_id: str = "player_1"


class ClawdpokeAdapter(BaseAdapter):
    """
    🎮 Clawdpoke.a0 Adapter
    
    Connects to Clawdpoke.a0 game framework with integrated skill system.
    
    Features:
    - Game state management
    - Skill progression system
    - Narrative branching
    - Player management
    - World state tracking
    
    Supported Actions:
    - update_state: Update game state
    - get_player: Get player state
    - create_player: Create new player
    - use_skill: Use a player skill
    - make_choice: Make a narrative choice
    - get_narrative: Get current narrative branch
    - register_narrative: Register new narrative
    """
    
    def __init__(self, config: Optional[ClawdpokeConfig] = None):
        """Initialize the Clawdpoke adapter."""
        super().__init__(config or ClawdpokeConfig())
        self.clawdpoke_config: ClawdpokeConfig = self.config  # type: ignore
        
        # Game state (in-memory simulation)
        self._players: Dict[str, PlayerState] = {}
        self._narratives: Dict[str, NarrativeBranch] = {}
        self._world_state: Dict[str, Any] = {
            "time": "day",
            "weather": "clear",
            "active_events": [],
        }
        
        # Skill definitions
        self._skill_defs = self._init_skill_definitions()
        
        # Initialize default narrative
        self._init_default_narratives()
    
    @property
    def platform(self) -> Platform:
        return Platform.CLAWDPOKE
    
    def _init_skill_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize skill definitions."""
        return {
            "programming": {
                "category": SkillCategory.TECHNICAL,
                "max_level": 100,
                "exp_curve": "linear",
                "abilities": ["code_review", "bug_fix", "optimization"],
            },
            "design": {
                "category": SkillCategory.CRAFTING,
                "max_level": 100,
                "exp_curve": "linear",
                "abilities": ["ui_design", "asset_creation", "branding"],
            },
            "narrative": {
                "category": SkillCategory.SOCIAL,
                "max_level": 100,
                "exp_curve": "linear",
                "abilities": ["storytelling", "dialogue", "world_building"],
            },
            "combat": {
                "category": SkillCategory.COMBAT,
                "max_level": 100,
                "exp_curve": "exponential",
                "abilities": ["attack", "defend", "special_move"],
            },
            "exploration": {
                "category": SkillCategory.EXPLORATION,
                "max_level": 100,
                "exp_curve": "linear",
                "abilities": ["discover", "navigate", "map"],
            },
            "magic": {
                "category": SkillCategory.MAGIC,
                "max_level": 100,
                "exp_curve": "exponential",
                "abilities": ["cast_spell", "enchant", "dispel"],
            },
            "archaeology": {
                "category": SkillCategory.EXPLORATION,
                "max_level": 100,
                "exp_curve": "linear",
                "abilities": ["excavate", "analyze", "preserve"],
            },
        }
    
    def _init_default_narratives(self) -> None:
        """Initialize default narrative branches."""
        # Hero's crossroads narrative from spec
        self._narratives["hero_decision_1"] = NarrativeBranch(
            branch_id="hero_decision_1",
            narrative_text="The hero stands at the crossroads. To the north, ancient ruins beckon with promises of forgotten knowledge. To the east, a river winds toward a distant settlement.",
            choices=[
                NarrativeChoice(
                    choice_id="investigate_ruins",
                    text="Investigate the ancient ruins",
                    required_skills=[{"skillId": "archaeology", "level": 3}],
                    consequences={
                        "add_experience": "archaeology:50",
                        "next_branch": "ruins_discovery",
                    },
                ),
                NarrativeChoice(
                    choice_id="follow_river",
                    text="Follow the river to the settlement",
                    required_skills=[],
                    consequences={
                        "add_experience": "exploration:25",
                        "next_branch": "settlement_arrival",
                    },
                ),
            ],
            location="crossroads",
        )
        
        self._narratives["ruins_discovery"] = NarrativeBranch(
            branch_id="ruins_discovery",
            narrative_text="The ancient ruins reveal secrets long buried. Intricate carvings cover the walls, depicting a civilization that mastered both technology and magic.",
            choices=[
                NarrativeChoice(
                    choice_id="study_carvings",
                    text="Study the carvings in detail",
                    required_skills=[],
                    consequences={
                        "add_experience": "archaeology:75",
                        "set_flag": "studied_ancient_carvings",
                    },
                ),
                NarrativeChoice(
                    choice_id="explore_deeper",
                    text="Explore deeper into the ruins",
                    required_skills=[{"skillId": "exploration", "level": 5}],
                    consequences={
                        "add_experience": "exploration:50",
                        "next_branch": "ruins_depths",
                    },
                ),
            ],
            location="ancient_ruins",
        )
        
        self._narratives["settlement_arrival"] = NarrativeBranch(
            branch_id="settlement_arrival",
            narrative_text="The settlement is alive with activity. Merchants hawk their wares, children play in the streets, and a job board catches your eye.",
            choices=[
                NarrativeChoice(
                    choice_id="visit_merchant",
                    text="Visit the merchant",
                    required_skills=[],
                    consequences={
                        "move_to": "merchant_shop",
                    },
                ),
                NarrativeChoice(
                    choice_id="check_jobs",
                    text="Check the job board",
                    required_skills=[],
                    consequences={
                        "set_flag": "checked_job_board",
                    },
                ),
            ],
            location="settlement",
        )
    
    async def _execute_impl(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a Clawdpoke action."""
        
        if action == "update_state":
            return await self._update_state(params)
        elif action == "get_player":
            return await self._get_player(params)
        elif action == "create_player":
            return await self._create_player(params)
        elif action == "use_skill":
            return await self._use_skill(params)
        elif action == "make_choice":
            return await self._make_choice(params)
        elif action == "get_narrative":
            return await self._get_narrative(params)
        elif action == "register_narrative":
            return await self._register_narrative(params)
        elif action == "get_world_state":
            return await self._get_world_state(params)
        elif action == "update_world":
            return await self._update_world(params)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def health_check(self) -> bool:
        """Check if game server is healthy."""
        # Simulated health check
        return True
    
    # =========================================================================
    # PLAYER OPERATIONS
    # =========================================================================
    
    async def _create_player(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new player.
        
        Params:
            player_id: Player identifier
            name: Player name
            initial_skills: List of starting skills
        """
        player_id = params.get("player_id", f"player_{len(self._players)}")
        name = params.get("name", f"Player {len(self._players) + 1}")
        initial_skills = params.get("initial_skills", ["exploration"])
        
        # Create player
        player = PlayerState(
            id=player_id,
            name=name,
        )
        
        # Grant initial skills
        for skill_id in initial_skills:
            if skill_id in self._skill_defs:
                skill_def = self._skill_defs[skill_id]
                player.skills[skill_id] = Skill(
                    id=skill_id,
                    name=skill_id.title(),
                    category=skill_def["category"],
                    level=1,
                    description=f"Proficiency in {skill_id}",
                )
        
        self._players[player_id] = player
        
        logger.info(f"🎮 Created player: {name} ({player_id})")
        
        return {
            "player_id": player_id,
            "name": name,
            "player_state": player.model_dump(),
        }
    
    async def _get_player(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get player state."""
        player_id = params.get("player_id", self.clawdpoke_config.default_player_id)
        
        player = self._players.get(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        
        return {
            "player_id": player_id,
            "player_state": player.model_dump(),
        }
    
    # =========================================================================
    # STATE UPDATE
    # =========================================================================
    
    async def _update_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update game state based on action.
        
        Params:
            action_type: Type of action
            player_id: Player performing action
            target: Action target (optional)
            parameters: Additional parameters
        """
        action_type = params.get("action_type", "generic")
        player_id = params.get("player_id", self.clawdpoke_config.default_player_id)
        target = params.get("target")
        action_params = params.get("parameters", {})
        
        # Get or create player
        if player_id not in self._players:
            await self._create_player({"player_id": player_id})
        
        player = self._players[player_id]
        events_triggered = []
        world_changes = {}
        narrative = None
        
        # Process action
        if action_type == "move":
            new_location = action_params.get("location")
            if new_location:
                old_location = player.location
                player.location = new_location
                world_changes["player_moved"] = {
                    "from": old_location,
                    "to": new_location,
                }
                events_triggered.append(f"moved_to_{new_location}")
                
                # Grant exploration exp
                self._add_experience(player, "exploration", 10)
        
        elif action_type == "use_skill":
            skill_id = action_params.get("skill_id")
            result = await self._use_skill({
                "player_id": player_id,
                "skill_id": skill_id,
            })
            events_triggered.append(f"used_skill_{skill_id}")
        
        elif action_type == "make_choice":
            branch_id = action_params.get("branch_id")
            choice_id = action_params.get("choice_id")
            choice_result = await self._make_choice({
                "player_id": player_id,
                "branch_id": branch_id,
                "choice_id": choice_id,
            })
            narrative = choice_result.get("next_narrative")
            events_triggered.append(f"made_choice_{choice_id}")
        
        elif action_type == "NARRATIVE_ADVANCEMENT":
            # Handle narrative advancement from orchestrator
            new_scene = action_params.get("newScene", {})
            narrative = NarrativeBranch(
                branch_id=new_scene.get("id", "generated"),
                narrative_text=new_scene.get("description", ""),
                choices=[],
                location=new_scene.get("location"),
            )
            events_triggered.append("narrative_advanced")
        
        logger.info(f"🎮 State updated: {action_type} by {player_id}")
        
        return {
            "update_type": action_type,
            "player_state": player.model_dump(),
            "narrative": narrative.model_dump() if narrative else None,
            "world_changes": world_changes,
            "events_triggered": events_triggered,
        }
    
    # =========================================================================
    # SKILL OPERATIONS
    # =========================================================================
    
    async def _use_skill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use a player skill.
        
        Params:
            player_id: Player identifier
            skill_id: Skill to use
            target: Skill target (optional)
        """
        player_id = params.get("player_id", self.clawdpoke_config.default_player_id)
        skill_id = params.get("skill_id")
        target = params.get("target")
        
        player = self._players.get(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        
        skill = player.skills.get(skill_id)
        if not skill:
            raise ValueError(f"Player doesn't have skill: {skill_id}")
        
        # Calculate skill effectiveness
        effectiveness = skill.level / 100.0
        
        # Grant experience for using skill
        exp_gained = self._add_experience(player, skill_id, 25)
        
        logger.info(f"🎮 {player.name} used {skill_id} (level {skill.level})")
        
        return {
            "skill_id": skill_id,
            "skill_level": skill.level,
            "effectiveness": effectiveness,
            "experience_gained": exp_gained,
            "new_level": skill.level,
        }
    
    def _add_experience(self, player: PlayerState, skill_id: str, amount: int) -> Dict[str, Any]:
        """Add experience to a skill."""
        skill = player.skills.get(skill_id)
        if not skill:
            # Create skill if not exists
            if skill_id in self._skill_defs:
                skill_def = self._skill_defs[skill_id]
                skill = Skill(
                    id=skill_id,
                    name=skill_id.title(),
                    category=skill_def["category"],
                )
                player.skills[skill_id] = skill
            else:
                return {"error": f"Unknown skill: {skill_id}"}
        
        old_level = skill.level
        skill.experience += amount
        
        # Level up check (100 exp per level)
        while skill.experience >= skill.level * 100:
            skill.experience -= skill.level * 100
            skill.level += 1
        
        return {
            "skill_id": skill_id,
            "experience_added": amount,
            "old_level": old_level,
            "new_level": skill.level,
            "leveled_up": skill.level > old_level,
        }
    
    # =========================================================================
    # NARRATIVE OPERATIONS
    # =========================================================================
    
    async def _get_narrative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a narrative branch.
        
        Params:
            branch_id: Narrative branch ID
            player_id: Player for choice filtering
        """
        branch_id = params.get("branch_id")
        player_id = params.get("player_id")
        
        if branch_id not in self._narratives:
            raise ValueError(f"Narrative not found: {branch_id}")
        
        branch = self._narratives[branch_id]
        
        # Filter available choices based on player skills
        available_choices = []
        if player_id and player_id in self._players:
            player = self._players[player_id]
            for choice in branch.choices:
                meets_requirements = True
                for req in choice.required_skills:
                    skill = player.skills.get(req.get("skillId", ""))
                    if not skill or skill.level < req.get("level", 1):
                        meets_requirements = False
                        break
                if meets_requirements:
                    available_choices.append(choice)
        else:
            available_choices = branch.choices
        
        return {
            "branch_id": branch.branch_id,
            "narrative_text": branch.narrative_text,
            "location": branch.location,
            "choices": [c.model_dump() for c in branch.choices],
            "available_choices": [c.model_dump() for c in available_choices],
        }
    
    async def _make_choice(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a narrative choice.
        
        Params:
            player_id: Player making choice
            branch_id: Current narrative branch
            choice_id: Choice to make
        """
        player_id = params.get("player_id", self.clawdpoke_config.default_player_id)
        branch_id = params.get("branch_id")
        choice_id = params.get("choice_id")
        
        if branch_id not in self._narratives:
            raise ValueError(f"Narrative not found: {branch_id}")
        
        player = self._players.get(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        
        branch = self._narratives[branch_id]
        choice = next((c for c in branch.choices if c.choice_id == choice_id), None)
        
        if not choice:
            raise ValueError(f"Choice not found: {choice_id}")
        
        # Check requirements
        for req in choice.required_skills:
            skill = player.skills.get(req.get("skillId", ""))
            if not skill or skill.level < req.get("level", 1):
                raise ValueError(f"Requirements not met for choice: {choice_id}")
        
        # Apply consequences
        consequences_applied = []
        next_narrative = None
        
        for key, value in choice.consequences.items():
            if key == "add_experience":
                skill_id, amount = value.split(":")
                result = self._add_experience(player, skill_id, int(amount))
                consequences_applied.append({"type": "experience", "result": result})
            
            elif key == "set_flag":
                player.flags[value] = True
                consequences_applied.append({"type": "flag", "flag": value})
            
            elif key == "move_to":
                player.location = value
                consequences_applied.append({"type": "move", "location": value})
            
            elif key == "next_branch":
                if value in self._narratives:
                    next_narrative = self._narratives[value]
        
        logger.info(f"🎮 {player.name} chose: {choice.text}")
        
        return {
            "choice_id": choice_id,
            "choice_text": choice.text,
            "consequences_applied": consequences_applied,
            "next_narrative": next_narrative.model_dump() if next_narrative else None,
            "player_state": player.model_dump(),
        }
    
    async def _register_narrative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a new narrative branch.
        
        Params:
            branch_id: Branch identifier
            narrative_text: Story text
            choices: List of choices
            location: Optional location
        """
        branch_id = params.get("branch_id")
        narrative_text = params.get("narrative_text", "")
        choices_data = params.get("choices", [])
        location = params.get("location")
        
        choices = [
            NarrativeChoice(**c) if isinstance(c, dict) else c
            for c in choices_data
        ]
        
        branch = NarrativeBranch(
            branch_id=branch_id,
            narrative_text=narrative_text,
            choices=choices,
            location=location,
        )
        
        self._narratives[branch_id] = branch
        
        logger.info(f"📖 Registered narrative: {branch_id}")
        
        return {
            "branch_id": branch_id,
            "choices_count": len(choices),
        }
    
    # =========================================================================
    # WORLD OPERATIONS
    # =========================================================================
    
    async def _get_world_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current world state."""
        return self._world_state.copy()
    
    async def _update_world(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update world state."""
        updates = params.get("updates", {})
        
        for key, value in updates.items():
            self._world_state[key] = value
        
        return self._world_state.copy()
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def get_all_players(self) -> Dict[str, PlayerState]:
        """Get all players."""
        return self._players.copy()
    
    def get_all_narratives(self) -> Dict[str, NarrativeBranch]:
        """Get all narrative branches."""
        return self._narratives.copy()
    
    def get_skill_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get all skill definitions."""
        return self._skill_defs.copy()
