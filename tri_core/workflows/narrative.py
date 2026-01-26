"""
Multi-Agent Narrative Workflow
==============================

Dynamic narrative generation using coordinated multi-agent workflows.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from tri_core.models import (
    Platform,
    NarrativeBranch,
    NarrativeChoice,
    PlayerState,
    TriCoreEvent,
)
from tri_core.event_bus.bus import UnifiedEventBus, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class NarrativeRequest:
    """Request for narrative generation."""
    player_id: str
    player_context: Dict[str, Any]
    current_branch_id: Optional[str] = None
    choice_made: Optional[str] = None
    additional_context: Dict[str, Any] = None


@dataclass
class NarrativeResponse:
    """Response from narrative generation."""
    branch: NarrativeBranch
    scene_data: Dict[str, Any]
    updated_player_state: Dict[str, Any]
    generated_assets: List[str]


class MultiAgentNarrativeWorkflow:
    """
    📖 Multi-Agent Narrative Workflow
    
    Generates dynamic narratives using coordinated agents across all platforms.
    
    Flow:
    1. Player makes choice (Clawdpoke)
    2. NarrativeAgent generates consequences (Genspark)
    3. Executor generates scene implementation (AOL-CLI)
    4. Game renders the scene (Clawdpoke)
    
    This implements the dynamic narrative system from the spec.
    """
    
    def __init__(
        self,
        event_bus: Optional[UnifiedEventBus] = None,
    ):
        """Initialize the narrative workflow."""
        self.event_bus = event_bus or get_event_bus()
        
        # Adapters (to be set)
        self._genspark = None
        self._aol_cli = None
        self._clawdpoke = None
        
        # Narrative state
        self._active_narratives: Dict[str, NarrativeBranch] = {}
        self._generation_history: List[Dict[str, Any]] = []
        
        logger.info("📖 Multi-Agent Narrative Workflow initialized")
    
    def set_adapters(self, genspark, aol_cli, clawdpoke) -> None:
        """Set platform adapters."""
        self._genspark = genspark
        self._aol_cli = aol_cli
        self._clawdpoke = clawdpoke
    
    async def handle_player_choice(
        self,
        player_id: str,
        choice_id: str,
        player_state: PlayerState,
    ) -> NarrativeResponse:
        """
        Handle a player's narrative choice.
        
        This is the main entry point as shown in the spec's example.
        
        Args:
            player_id: Player identifier
            choice_id: The choice made
            player_state: Current player state
            
        Returns:
            Generated narrative response
        """
        logger.info(f"📖 Handling choice '{choice_id}' for player {player_id}")
        
        # 1. Generate narrative consequences via Genspark
        narrative_response = await self._generate_narrative_consequences(
            player_id, choice_id, player_state
        )
        
        # 2. Generate implementation via AOL-CLI
        implementation = await self._generate_implementation(
            narrative_response, player_state
        )
        
        # 3. Update game state via Clawdpoke
        updated_state = await self._update_game_state(
            player_id, implementation, player_state
        )
        
        # Create response
        branch = NarrativeBranch(
            branch_id=f"generated_{choice_id}",
            narrative_text=narrative_response.get("narrative", ""),
            choices=self._parse_choices(narrative_response.get("choices", [])),
            location=implementation.get("location"),
        )
        
        # Store in active narratives
        self._active_narratives[player_id] = branch
        
        # Record in history
        self._generation_history.append({
            "player_id": player_id,
            "choice_id": choice_id,
            "branch_id": branch.branch_id,
        })
        
        # Publish event
        await self.event_bus.publish_async(
            "narrative.generated",
            TriCoreEvent(
                source=Platform.TRINITY,
                event_type="narrative_generated",
                payload={
                    "player_id": player_id,
                    "branch_id": branch.branch_id,
                },
            )
        )
        
        return NarrativeResponse(
            branch=branch,
            scene_data=implementation,
            updated_player_state=updated_state,
            generated_assets=implementation.get("assets", []),
        )
    
    async def _generate_narrative_consequences(
        self,
        player_id: str,
        choice_id: str,
        player_state: PlayerState,
    ) -> Dict[str, Any]:
        """
        Step 1: Generate narrative consequences via Genspark.
        
        Calls the NarrativeAgent to generate story consequences.
        """
        if self._genspark:
            result = await self._genspark.execute(
                "call_agent",
                {
                    "agent": "NarrativeWriter",
                    "task": "generateConsequence",
                    "context": {
                        "action": "generateConsequence",
                        "choice": choice_id,
                        "playerContext": {
                            "name": player_state.name,
                            "level": player_state.level,
                            "location": player_state.location,
                            "skills": {
                                sid: s.level for sid, s in player_state.skills.items()
                            },
                            "flags": player_state.flags,
                        },
                    },
                }
            )
            
            agent_result = result.get("result", {})
            
            return {
                "narrative": agent_result.get("story", {}).get("synopsis", "The story continues..."),
                "elements": agent_result.get("elements", []),
                "choices": self._generate_follow_up_choices(choice_id, player_state),
                "requiredAssets": [],
            }
        
        # Simulation mode
        return {
            "narrative": f"Having chosen to {choice_id.replace('_', ' ')}, {player_state.name} faces new possibilities...",
            "elements": ["discovery", "challenge"],
            "choices": self._generate_follow_up_choices(choice_id, player_state),
            "requiredAssets": [],
        }
    
    def _generate_follow_up_choices(
        self,
        choice_id: str,
        player_state: PlayerState,
    ) -> List[Dict[str, Any]]:
        """Generate contextual follow-up choices."""
        base_choices = [
            {
                "id": "continue_exploring",
                "text": "Continue exploring",
                "requirements": [],
            },
            {
                "id": "return_back",
                "text": "Return to the previous area",
                "requirements": [],
            },
        ]
        
        # Add skill-based choices
        if "combat" in player_state.skills:
            base_choices.append({
                "id": "prepare_for_battle",
                "text": "Prepare for potential combat",
                "requirements": [{"skillId": "combat", "level": 1}],
            })
        
        if "archaeology" in player_state.skills:
            base_choices.append({
                "id": "study_surroundings",
                "text": "Study the area for historical clues",
                "requirements": [{"skillId": "archaeology", "level": 2}],
            })
        
        return base_choices
    
    async def _generate_implementation(
        self,
        narrative_response: Dict[str, Any],
        player_state: PlayerState,
    ) -> Dict[str, Any]:
        """
        Step 2: Generate implementation via AOL-CLI.
        
        Converts narrative elements into implementable scene data.
        """
        if self._aol_cli:
            result = await self._aol_cli.execute(
                "generate_code",
                {
                    "description": f"Generate scene implementation for: {narrative_response.get('narrative', '')[:100]}",
                    "language": "python",
                    "framework": None,
                }
            )
            
            return {
                "sceneId": f"scene_{len(self._generation_history)}",
                "sceneName": "generated_scene",
                "location": player_state.location,
                "narrativeElements": narrative_response.get("elements", []),
                "assets": [],
                "code": result.get("code", ""),
            }
        
        # Simulation mode
        return {
            "sceneId": f"scene_{len(self._generation_history)}",
            "sceneName": "generated_scene",
            "location": player_state.location,
            "narrativeElements": narrative_response.get("elements", []),
            "assets": [],
        }
    
    async def _update_game_state(
        self,
        player_id: str,
        implementation: Dict[str, Any],
        player_state: PlayerState,
    ) -> Dict[str, Any]:
        """
        Step 3: Update game state via Clawdpoke.
        
        Renders the scene and updates player state.
        """
        if self._clawdpoke:
            result = await self._clawdpoke.execute(
                "update_state",
                {
                    "action_type": "NARRATIVE_ADVANCEMENT",
                    "player_id": player_id,
                    "parameters": {
                        "newScene": implementation,
                        "playerState": player_state.model_dump(),
                    },
                }
            )
            
            return result.get("player_state", player_state.model_dump())
        
        # Simulation mode
        return player_state.model_dump()
    
    def _parse_choices(
        self,
        choices_data: List[Dict[str, Any]],
    ) -> List[NarrativeChoice]:
        """Parse choice data into NarrativeChoice objects."""
        return [
            NarrativeChoice(
                choice_id=c.get("id", f"choice_{i}"),
                text=c.get("text", "Continue"),
                required_skills=c.get("requirements", []),
                consequences=c.get("consequences", {}),
            )
            for i, c in enumerate(choices_data)
        ]
    
    # =========================================================================
    # NARRATIVE MANAGEMENT
    # =========================================================================
    
    def get_active_narrative(self, player_id: str) -> Optional[NarrativeBranch]:
        """Get the active narrative for a player."""
        return self._active_narratives.get(player_id)
    
    def get_generation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get narrative generation history."""
        return self._generation_history[-limit:]
    
    async def generate_random_encounter(
        self,
        player_id: str,
        player_state: PlayerState,
        encounter_type: str = "discovery",
    ) -> NarrativeBranch:
        """
        Generate a random narrative encounter.
        
        Args:
            player_id: Player identifier
            player_state: Current player state
            encounter_type: Type of encounter
            
        Returns:
            Generated narrative branch
        """
        if self._genspark:
            result = await self._genspark.execute(
                "call_agent",
                {
                    "agent": "NarrativeWriter",
                    "task": f"Generate a {encounter_type} encounter for {player_state.name} at {player_state.location}",
                    "context": {
                        "player_level": player_state.level,
                        "player_skills": list(player_state.skills.keys()),
                    },
                }
            )
            
            story = result.get("result", {}).get("story", {})
            
            return NarrativeBranch(
                branch_id=f"encounter_{encounter_type}_{len(self._generation_history)}",
                narrative_text=story.get("synopsis", f"A {encounter_type} awaits..."),
                choices=self._parse_choices(
                    self._generate_follow_up_choices(encounter_type, player_state)
                ),
                location=player_state.location,
            )
        
        # Simulation mode
        encounters = {
            "discovery": "You discover something interesting...",
            "combat": "A hostile creature appears!",
            "puzzle": "An ancient mechanism blocks your path.",
            "npc": "A traveler approaches you.",
        }
        
        return NarrativeBranch(
            branch_id=f"encounter_{encounter_type}_{len(self._generation_history)}",
            narrative_text=encounters.get(encounter_type, "Something happens..."),
            choices=[
                NarrativeChoice(
                    choice_id="investigate",
                    text="Investigate",
                    required_skills=[],
                ),
                NarrativeChoice(
                    choice_id="ignore",
                    text="Ignore and continue",
                    required_skills=[],
                ),
            ],
            location=player_state.location,
        )
    
    def __repr__(self) -> str:
        return (
            f"MultiAgentNarrativeWorkflow("
            f"active={len(self._active_narratives)}, "
            f"history={len(self._generation_history)})"
        )
