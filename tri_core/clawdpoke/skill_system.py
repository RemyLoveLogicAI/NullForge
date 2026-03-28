"""
Skill System
============

Advanced skill progression system for Clawdpoke.a0.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import math

from tri_core.models import Skill, SkillCategory

logger = logging.getLogger(__name__)


class ExperienceCurve(str, Enum):
    """Experience curve types for skill progression."""
    LINEAR = "linear"         # Same XP per level
    EXPONENTIAL = "exponential"  # Increasing XP per level
    LOGARITHMIC = "logarithmic"  # Decreasing XP gains per level
    POLYNOMIAL = "polynomial"    # Quadratic scaling


@dataclass
class SkillDefinition:
    """Definition of a skill."""
    id: str
    name: str
    category: SkillCategory
    description: str
    max_level: int = 100
    exp_curve: ExperienceCurve = ExperienceCurve.LINEAR
    base_exp_per_level: int = 100
    abilities: List[str] = field(default_factory=list)
    prerequisites: Dict[str, int] = field(default_factory=dict)  # skill_id: level
    bonuses: Dict[str, float] = field(default_factory=dict)  # stat: bonus per level


@dataclass
class SkillUnlock:
    """An unlocked ability from a skill."""
    skill_id: str
    ability_name: str
    unlock_level: int
    description: str
    effect: Dict[str, Any] = field(default_factory=dict)


class SkillTree:
    """
    🌳 Skill Tree
    
    Represents skill progression paths and unlocks.
    
    Features:
    - Prerequisite chains
    - Ability unlocks at levels
    - Branch paths
    """
    
    def __init__(self, name: str):
        """Initialize skill tree."""
        self.name = name
        self._nodes: Dict[str, SkillDefinition] = {}
        self._unlocks: Dict[str, List[SkillUnlock]] = {}  # skill_id -> unlocks
        self._connections: Dict[str, List[str]] = {}  # skill_id -> connected skills
    
    def add_skill(self, skill_def: SkillDefinition) -> None:
        """Add a skill to the tree."""
        self._nodes[skill_def.id] = skill_def
        self._unlocks[skill_def.id] = []
        self._connections[skill_def.id] = []
    
    def add_unlock(self, unlock: SkillUnlock) -> None:
        """Add an ability unlock to a skill."""
        if unlock.skill_id in self._unlocks:
            self._unlocks[unlock.skill_id].append(unlock)
    
    def connect(self, from_skill: str, to_skill: str) -> None:
        """Connect two skills in the tree."""
        if from_skill in self._connections:
            self._connections[from_skill].append(to_skill)
    
    def get_available_skills(self, unlocked_skills: Dict[str, int]) -> List[SkillDefinition]:
        """Get skills available based on current unlocks."""
        available = []
        
        for skill_id, skill_def in self._nodes.items():
            if skill_id in unlocked_skills:
                continue  # Already unlocked
            
            # Check prerequisites
            meets_prereqs = True
            for prereq_id, prereq_level in skill_def.prerequisites.items():
                if prereq_id not in unlocked_skills or unlocked_skills[prereq_id] < prereq_level:
                    meets_prereqs = False
                    break
            
            if meets_prereqs:
                available.append(skill_def)
        
        return available
    
    def get_unlocks_at_level(self, skill_id: str, level: int) -> List[SkillUnlock]:
        """Get abilities unlocked at a specific level."""
        return [
            unlock for unlock in self._unlocks.get(skill_id, [])
            if unlock.unlock_level == level
        ]
    
    def get_all_unlocks(self, skill_id: str, up_to_level: int) -> List[SkillUnlock]:
        """Get all abilities unlocked up to a level."""
        return [
            unlock for unlock in self._unlocks.get(skill_id, [])
            if unlock.unlock_level <= up_to_level
        ]


class SkillSystem:
    """
    🎯 Skill System
    
    Manages skill progression, experience, and abilities.
    
    Features:
    - Experience calculation with multiple curves
    - Level progression
    - Ability unlocks
    - Skill trees
    - Stat bonuses
    """
    
    def __init__(self):
        """Initialize skill system."""
        self._definitions: Dict[str, SkillDefinition] = {}
        self._trees: Dict[str, SkillTree] = {}
        self._level_callbacks: List[Callable[[str, str, int], None]] = []
        
        # Initialize default skills
        self._init_default_skills()
    
    def _init_default_skills(self) -> None:
        """Initialize default skill definitions."""
        default_skills = [
            SkillDefinition(
                id="programming",
                name="Programming",
                category=SkillCategory.TECHNICAL,
                description="Write and understand code",
                abilities=["code_review", "bug_fix", "optimization", "architecture"],
                bonuses={"code_quality": 0.01, "debug_speed": 0.02},
            ),
            SkillDefinition(
                id="design",
                name="Design",
                category=SkillCategory.CRAFTING,
                description="Create visual designs",
                abilities=["ui_design", "asset_creation", "animation", "branding"],
                bonuses={"visual_quality": 0.015},
            ),
            SkillDefinition(
                id="narrative",
                name="Narrative",
                category=SkillCategory.SOCIAL,
                description="Write compelling stories",
                abilities=["dialogue", "world_building", "character_development"],
                bonuses={"story_engagement": 0.02},
            ),
            SkillDefinition(
                id="combat",
                name="Combat",
                category=SkillCategory.COMBAT,
                description="Fight effectively",
                exp_curve=ExperienceCurve.EXPONENTIAL,
                abilities=["attack", "defend", "special_move", "combo"],
                bonuses={"damage": 0.02, "defense": 0.01},
            ),
            SkillDefinition(
                id="exploration",
                name="Exploration",
                category=SkillCategory.EXPLORATION,
                description="Discover new areas",
                abilities=["discover", "navigate", "map", "track"],
                bonuses={"discovery_chance": 0.01, "movement_speed": 0.005},
            ),
            SkillDefinition(
                id="magic",
                name="Magic",
                category=SkillCategory.MAGIC,
                description="Cast powerful spells",
                exp_curve=ExperienceCurve.EXPONENTIAL,
                abilities=["cast_spell", "enchant", "dispel", "summon"],
                bonuses={"spell_power": 0.025, "mana_regen": 0.01},
            ),
            SkillDefinition(
                id="archaeology",
                name="Archaeology",
                category=SkillCategory.EXPLORATION,
                description="Study ancient artifacts",
                abilities=["excavate", "analyze", "preserve", "translate"],
                bonuses={"artifact_quality": 0.02},
            ),
            SkillDefinition(
                id="crafting",
                name="Crafting",
                category=SkillCategory.CRAFTING,
                description="Create items and tools",
                abilities=["forge", "enchant_item", "repair", "upgrade"],
                bonuses={"item_quality": 0.015, "resource_efficiency": 0.01},
            ),
        ]
        
        for skill_def in default_skills:
            self.register_skill(skill_def)
    
    # =========================================================================
    # SKILL REGISTRATION
    # =========================================================================
    
    def register_skill(self, skill_def: SkillDefinition) -> None:
        """Register a skill definition."""
        self._definitions[skill_def.id] = skill_def
        logger.debug(f"📚 Registered skill: {skill_def.name}")
    
    def get_skill_definition(self, skill_id: str) -> Optional[SkillDefinition]:
        """Get a skill definition."""
        return self._definitions.get(skill_id)
    
    def list_skills(self, category: Optional[SkillCategory] = None) -> List[SkillDefinition]:
        """List all skills, optionally filtered by category."""
        skills = list(self._definitions.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills
    
    # =========================================================================
    # EXPERIENCE CALCULATION
    # =========================================================================
    
    def calculate_exp_for_level(self, skill_id: str, level: int) -> int:
        """Calculate experience required for a specific level."""
        skill_def = self._definitions.get(skill_id)
        if not skill_def:
            return level * 100  # Default
        
        base = skill_def.base_exp_per_level
        
        if skill_def.exp_curve == ExperienceCurve.LINEAR:
            return base * level
        
        elif skill_def.exp_curve == ExperienceCurve.EXPONENTIAL:
            return int(base * (1.5 ** (level - 1)))
        
        elif skill_def.exp_curve == ExperienceCurve.LOGARITHMIC:
            return int(base * (1 + math.log(level + 1)))
        
        elif skill_def.exp_curve == ExperienceCurve.POLYNOMIAL:
            return int(base * (level ** 1.5))
        
        return base * level
    
    def calculate_total_exp_for_level(self, skill_id: str, level: int) -> int:
        """Calculate total experience needed to reach a level."""
        total = 0
        for lvl in range(1, level + 1):
            total += self.calculate_exp_for_level(skill_id, lvl)
        return total
    
    def calculate_level_from_exp(self, skill_id: str, total_exp: int) -> tuple[int, int]:
        """
        Calculate level from total experience.
        
        Returns:
            Tuple of (level, remaining_exp_in_current_level)
        """
        level = 1
        remaining = total_exp
        
        while True:
            exp_needed = self.calculate_exp_for_level(skill_id, level)
            if remaining < exp_needed:
                break
            remaining -= exp_needed
            level += 1
            
            # Cap at max level
            skill_def = self._definitions.get(skill_id)
            if skill_def and level >= skill_def.max_level:
                break
        
        return level, remaining
    
    # =========================================================================
    # SKILL PROGRESSION
    # =========================================================================
    
    def grant_experience(
        self,
        skill: Skill,
        amount: int,
    ) -> Dict[str, Any]:
        """
        Grant experience to a skill.
        
        Args:
            skill: Skill to level
            amount: Experience to grant
            
        Returns:
            Progression result
        """
        old_level = skill.level
        skill.experience += amount
        
        skill_def = self._definitions.get(skill.id)
        max_level = skill_def.max_level if skill_def else 100
        
        # Check for level ups
        levels_gained = 0
        unlocks = []
        
        while skill.level < max_level:
            exp_needed = self.calculate_exp_for_level(skill.id, skill.level)
            if skill.experience < exp_needed:
                break
            
            skill.experience -= exp_needed
            skill.level += 1
            levels_gained += 1
            
            # Check for unlocks
            if skill.id in self._trees:
                tree = self._trees[skill.id]
                level_unlocks = tree.get_unlocks_at_level(skill.id, skill.level)
                unlocks.extend(level_unlocks)
            
            # Notify callbacks
            for callback in self._level_callbacks:
                try:
                    callback(skill.id, skill.name, skill.level)
                except Exception as e:
                    logger.error(f"Level callback error: {e}")
        
        return {
            "skill_id": skill.id,
            "experience_gained": amount,
            "old_level": old_level,
            "new_level": skill.level,
            "levels_gained": levels_gained,
            "current_exp": skill.experience,
            "exp_to_next": self.calculate_exp_for_level(skill.id, skill.level),
            "unlocks": [u.ability_name for u in unlocks],
        }
    
    def create_skill(
        self,
        skill_id: str,
        level: int = 1,
        experience: int = 0,
    ) -> Optional[Skill]:
        """Create a skill instance from a definition."""
        skill_def = self._definitions.get(skill_id)
        if not skill_def:
            return None
        
        return Skill(
            id=skill_id,
            name=skill_def.name,
            category=skill_def.category,
            level=level,
            experience=experience,
            description=skill_def.description,
        )
    
    # =========================================================================
    # SKILL TREES
    # =========================================================================
    
    def register_tree(self, tree: SkillTree) -> None:
        """Register a skill tree."""
        self._trees[tree.name] = tree
    
    def get_tree(self, name: str) -> Optional[SkillTree]:
        """Get a skill tree."""
        return self._trees.get(name)
    
    # =========================================================================
    # BONUSES
    # =========================================================================
    
    def calculate_bonuses(
        self,
        skills: Dict[str, Skill],
    ) -> Dict[str, float]:
        """Calculate total bonuses from all skills."""
        bonuses: Dict[str, float] = {}
        
        for skill_id, skill in skills.items():
            skill_def = self._definitions.get(skill_id)
            if not skill_def:
                continue
            
            for stat, bonus_per_level in skill_def.bonuses.items():
                current = bonuses.get(stat, 0)
                bonuses[stat] = current + (bonus_per_level * skill.level)
        
        return bonuses
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def on_level_up(self, callback: Callable[[str, str, int], None]) -> None:
        """Register a callback for level ups."""
        self._level_callbacks.append(callback)
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def get_progress(self, skill: Skill) -> Dict[str, Any]:
        """Get detailed progress information for a skill."""
        exp_for_current = self.calculate_exp_for_level(skill.id, skill.level)
        
        skill_def = self._definitions.get(skill.id)
        max_level = skill_def.max_level if skill_def else 100
        
        return {
            "skill_id": skill.id,
            "level": skill.level,
            "max_level": max_level,
            "current_exp": skill.experience,
            "exp_for_level": exp_for_current,
            "progress_percent": (skill.experience / exp_for_current * 100) if exp_for_current > 0 else 100,
            "total_exp_earned": self.calculate_total_exp_for_level(skill.id, skill.level - 1) + skill.experience,
        }
    
    def __repr__(self) -> str:
        return f"SkillSystem(skills={len(self._definitions)}, trees={len(self._trees)})"
