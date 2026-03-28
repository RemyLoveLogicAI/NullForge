"""
Narrative Engine
================

Dynamic narrative system for branching storylines in Clawdpoke.a0.
"""

from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import random

from tri_core.models import (
    PlayerState,
    Skill,
    NarrativeBranch,
    NarrativeChoice,
)

logger = logging.getLogger(__name__)


@dataclass
class NarrativeContext:
    """Context for narrative generation."""
    player_id: str
    player_name: str
    location: str
    skills: Dict[str, int]  # skill_id -> level
    flags: Dict[str, bool]
    history: List[str]  # Previous choice IDs
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedNarrative:
    """A dynamically generated narrative segment."""
    text: str
    choices: List[NarrativeChoice]
    context_updates: Dict[str, Any] = field(default_factory=dict)
    triggers: List[str] = field(default_factory=list)


class NarrativeEngine:
    """
    📖 Narrative Engine
    
    Manages dynamic storytelling and branching narratives.
    
    Features:
    - Static narrative branches
    - Dynamic narrative generation
    - Context-aware story progression
    - Skill-gated choices
    - Consequence tracking
    - Story templates
    """
    
    def __init__(self):
        """Initialize narrative engine."""
        self._branches: Dict[str, NarrativeBranch] = {}
        self._templates: Dict[str, str] = {}
        self._generators: Dict[str, Callable[[NarrativeContext], GeneratedNarrative]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}  # player_id -> choices
        
        # Initialize default templates
        self._init_templates()
    
    def _init_templates(self) -> None:
        """Initialize narrative templates."""
        self._templates = {
            "discovery": "As {player_name} explores {location}, something catches their eye...",
            "combat_start": "A hostile presence emerges before {player_name}. Combat is unavoidable.",
            "npc_greeting": "A figure approaches {player_name}. 'Greetings, traveler.'",
            "puzzle_found": "{player_name} discovers an ancient mechanism. Perhaps it can be activated...",
            "treasure_found": "Hidden among the ruins, {player_name} finds a gleaming artifact.",
            "skill_check_success": "Drawing upon their {skill_name} expertise, {player_name} succeeds.",
            "skill_check_fail": "Despite their efforts, {player_name}'s {skill_name} proves insufficient.",
        }
    
    # =========================================================================
    # BRANCH MANAGEMENT
    # =========================================================================
    
    def register_branch(self, branch: NarrativeBranch) -> None:
        """Register a narrative branch."""
        self._branches[branch.branch_id] = branch
        logger.debug(f"📖 Registered branch: {branch.branch_id}")
    
    def get_branch(self, branch_id: str) -> Optional[NarrativeBranch]:
        """Get a narrative branch."""
        return self._branches.get(branch_id)
    
    def remove_branch(self, branch_id: str) -> bool:
        """Remove a narrative branch."""
        if branch_id in self._branches:
            del self._branches[branch_id]
            return True
        return False
    
    # =========================================================================
    # NARRATIVE PRESENTATION
    # =========================================================================
    
    def present_branch(
        self,
        branch_id: str,
        context: NarrativeContext,
    ) -> Optional[Dict[str, Any]]:
        """
        Present a narrative branch to a player.
        
        Args:
            branch_id: Branch to present
            context: Player context
            
        Returns:
            Narrative presentation with available choices
        """
        branch = self._branches.get(branch_id)
        if not branch:
            return None
        
        # Process template variables in narrative text
        narrative_text = self._process_template(branch.narrative_text, context)
        
        # Filter choices based on requirements
        available_choices = self._filter_choices(branch.choices, context)
        
        return {
            "branch_id": branch.branch_id,
            "narrative_text": narrative_text,
            "location": branch.location,
            "all_choices": [self._choice_to_dict(c, context) for c in branch.choices],
            "available_choices": [self._choice_to_dict(c, context) for c in available_choices],
        }
    
    def _process_template(self, text: str, context: NarrativeContext) -> str:
        """Process template variables in text."""
        replacements = {
            "{player_name}": context.player_name,
            "{location}": context.location,
            "{player_id}": context.player_id,
        }
        
        # Add skill levels
        for skill_id, level in context.skills.items():
            replacements[f"{{skill_{skill_id}}}"] = str(level)
        
        # Add custom variables
        for key, value in context.variables.items():
            replacements[f"{{{key}}}"] = str(value)
        
        result = text
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
    def _filter_choices(
        self,
        choices: List[NarrativeChoice],
        context: NarrativeContext,
    ) -> List[NarrativeChoice]:
        """Filter choices based on player context."""
        available = []
        
        for choice in choices:
            if self._meets_requirements(choice, context):
                available.append(choice)
        
        return available
    
    def _meets_requirements(
        self,
        choice: NarrativeChoice,
        context: NarrativeContext,
    ) -> bool:
        """Check if player meets choice requirements."""
        for req in choice.required_skills:
            skill_id = req.get("skillId", "")
            required_level = req.get("level", 1)
            
            player_level = context.skills.get(skill_id, 0)
            if player_level < required_level:
                return False
        
        return True
    
    def _choice_to_dict(
        self,
        choice: NarrativeChoice,
        context: NarrativeContext,
    ) -> Dict[str, Any]:
        """Convert choice to dictionary with availability info."""
        meets_reqs = self._meets_requirements(choice, context)
        
        return {
            "choice_id": choice.choice_id,
            "text": choice.text,
            "available": meets_reqs,
            "requirements": choice.required_skills,
        }
    
    # =========================================================================
    # CHOICE PROCESSING
    # =========================================================================
    
    def make_choice(
        self,
        branch_id: str,
        choice_id: str,
        context: NarrativeContext,
    ) -> Dict[str, Any]:
        """
        Process a player's narrative choice.
        
        Args:
            branch_id: Current branch
            choice_id: Choice made
            context: Player context
            
        Returns:
            Result including consequences and next branch
        """
        branch = self._branches.get(branch_id)
        if not branch:
            return {"error": f"Branch not found: {branch_id}"}
        
        choice = next((c for c in branch.choices if c.choice_id == choice_id), None)
        if not choice:
            return {"error": f"Choice not found: {choice_id}"}
        
        # Check requirements
        if not self._meets_requirements(choice, context):
            return {"error": "Requirements not met"}
        
        # Record in history
        if context.player_id not in self._history:
            self._history[context.player_id] = []
        
        self._history[context.player_id].append({
            "branch_id": branch_id,
            "choice_id": choice_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Process consequences
        consequences = self._process_consequences(choice.consequences, context)
        
        # Get next branch
        next_branch_id = choice.consequences.get("next_branch")
        next_branch = self._branches.get(next_branch_id) if next_branch_id else None
        
        return {
            "choice_id": choice_id,
            "choice_text": choice.text,
            "consequences": consequences,
            "next_branch_id": next_branch_id,
            "next_branch": next_branch.model_dump() if next_branch else None,
        }
    
    def _process_consequences(
        self,
        consequences: Dict[str, Any],
        context: NarrativeContext,
    ) -> List[Dict[str, Any]]:
        """Process choice consequences."""
        results = []
        
        for key, value in consequences.items():
            if key == "add_experience":
                parts = value.split(":")
                if len(parts) == 2:
                    results.append({
                        "type": "experience",
                        "skill": parts[0],
                        "amount": int(parts[1]),
                    })
            
            elif key == "set_flag":
                results.append({
                    "type": "flag",
                    "flag": value,
                    "value": True,
                })
            
            elif key == "unset_flag":
                results.append({
                    "type": "flag",
                    "flag": value,
                    "value": False,
                })
            
            elif key == "move_to":
                results.append({
                    "type": "location",
                    "location": value,
                })
            
            elif key == "grant_skill":
                results.append({
                    "type": "skill",
                    "skill_id": value,
                })
            
            elif key == "grant_item":
                results.append({
                    "type": "item",
                    "item_id": value,
                })
            
            elif key == "trigger_event":
                results.append({
                    "type": "event",
                    "event_id": value,
                })
            
            elif key == "set_variable":
                var_name, var_value = value.split(":", 1)
                results.append({
                    "type": "variable",
                    "name": var_name,
                    "value": var_value,
                })
        
        return results
    
    # =========================================================================
    # DYNAMIC GENERATION
    # =========================================================================
    
    def register_generator(
        self,
        event_type: str,
        generator: Callable[[NarrativeContext], GeneratedNarrative],
    ) -> None:
        """Register a dynamic narrative generator."""
        self._generators[event_type] = generator
    
    def generate_narrative(
        self,
        event_type: str,
        context: NarrativeContext,
    ) -> Optional[GeneratedNarrative]:
        """
        Generate a dynamic narrative.
        
        Args:
            event_type: Type of event triggering narrative
            context: Player context
            
        Returns:
            Generated narrative or None
        """
        generator = self._generators.get(event_type)
        if generator:
            return generator(context)
        
        # Use template if available
        if event_type in self._templates:
            template = self._templates[event_type]
            text = self._process_template(template, context)
            return GeneratedNarrative(text=text, choices=[])
        
        return None
    
    def generate_discovery_narrative(
        self,
        context: NarrativeContext,
        discovery_type: str = "generic",
    ) -> NarrativeBranch:
        """Generate a discovery narrative based on context."""
        discoveries = {
            "ancient_artifact": {
                "text": f"{context.player_name} uncovers an ancient artifact, its surface covered in mysterious runes.",
                "choices": [
                    NarrativeChoice(
                        choice_id="examine_artifact",
                        text="Examine the artifact closely",
                        required_skills=[{"skillId": "archaeology", "level": 2}],
                        consequences={"add_experience": "archaeology:50"},
                    ),
                    NarrativeChoice(
                        choice_id="take_artifact",
                        text="Take the artifact",
                        required_skills=[],
                        consequences={"grant_item": "mysterious_artifact"},
                    ),
                    NarrativeChoice(
                        choice_id="leave_artifact",
                        text="Leave it undisturbed",
                        required_skills=[],
                        consequences={},
                    ),
                ],
            },
            "hidden_passage": {
                "text": f"Behind the crumbling wall, {context.player_name} discovers a hidden passage leading into darkness.",
                "choices": [
                    NarrativeChoice(
                        choice_id="enter_passage",
                        text="Enter the passage",
                        required_skills=[{"skillId": "exploration", "level": 3}],
                        consequences={"move_to": "hidden_area"},
                    ),
                    NarrativeChoice(
                        choice_id="mark_passage",
                        text="Mark the location for later",
                        required_skills=[],
                        consequences={"set_flag": "found_hidden_passage"},
                    ),
                ],
            },
            "generic": {
                "text": f"{context.player_name} makes an interesting discovery.",
                "choices": [
                    NarrativeChoice(
                        choice_id="investigate",
                        text="Investigate further",
                        required_skills=[],
                        consequences={"add_experience": "exploration:25"},
                    ),
                ],
            },
        }
        
        discovery = discoveries.get(discovery_type, discoveries["generic"])
        
        branch_id = f"discovery_{discovery_type}_{len(self._branches)}"
        
        return NarrativeBranch(
            branch_id=branch_id,
            narrative_text=discovery["text"],
            choices=discovery["choices"],
            location=context.location,
        )
    
    def generate_encounter_narrative(
        self,
        context: NarrativeContext,
        encounter_type: str = "generic",
    ) -> NarrativeBranch:
        """Generate an encounter narrative."""
        encounters = {
            "friendly_npc": {
                "text": f"A traveler approaches {context.player_name}. 'Well met, friend! These roads can be dangerous alone.'",
                "choices": [
                    NarrativeChoice(
                        choice_id="talk",
                        text="Strike up a conversation",
                        required_skills=[],
                        consequences={"add_experience": "social:20"},
                    ),
                    NarrativeChoice(
                        choice_id="trade",
                        text="Ask about trading",
                        required_skills=[],
                        consequences={"trigger_event": "open_trade"},
                    ),
                    NarrativeChoice(
                        choice_id="ignore",
                        text="Politely decline and continue",
                        required_skills=[],
                        consequences={},
                    ),
                ],
            },
            "hostile": {
                "text": f"Danger! A hostile creature blocks {context.player_name}'s path.",
                "choices": [
                    NarrativeChoice(
                        choice_id="fight",
                        text="Draw your weapon and fight",
                        required_skills=[{"skillId": "combat", "level": 1}],
                        consequences={"trigger_event": "start_combat"},
                    ),
                    NarrativeChoice(
                        choice_id="flee",
                        text="Attempt to flee",
                        required_skills=[{"skillId": "exploration", "level": 2}],
                        consequences={"move_to": "previous_location"},
                    ),
                    NarrativeChoice(
                        choice_id="sneak",
                        text="Try to sneak past",
                        required_skills=[{"skillId": "stealth", "level": 3}],
                        consequences={"add_experience": "stealth:30"},
                    ),
                ],
            },
        }
        
        encounter = encounters.get(encounter_type, encounters["friendly_npc"])
        branch_id = f"encounter_{encounter_type}_{len(self._branches)}"
        
        return NarrativeBranch(
            branch_id=branch_id,
            narrative_text=encounter["text"],
            choices=encounter["choices"],
            location=context.location,
        )
    
    # =========================================================================
    # HISTORY & TRACKING
    # =========================================================================
    
    def get_player_history(
        self,
        player_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get a player's narrative history."""
        return self._history.get(player_id, [])[-limit:]
    
    def has_made_choice(
        self,
        player_id: str,
        choice_id: str,
    ) -> bool:
        """Check if player has made a specific choice."""
        history = self._history.get(player_id, [])
        return any(h["choice_id"] == choice_id for h in history)
    
    def get_branch_visits(
        self,
        player_id: str,
        branch_id: str,
    ) -> int:
        """Count how many times a player has visited a branch."""
        history = self._history.get(player_id, [])
        return sum(1 for h in history if h["branch_id"] == branch_id)
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def list_branches(self) -> List[str]:
        """List all branch IDs."""
        return list(self._branches.keys())
    
    def stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "branches": len(self._branches),
            "templates": len(self._templates),
            "generators": len(self._generators),
            "players_tracked": len(self._history),
            "total_choices_made": sum(len(h) for h in self._history.values()),
        }
    
    def __repr__(self) -> str:
        s = self.stats()
        return f"NarrativeEngine(branches={s['branches']}, templates={s['templates']})"
