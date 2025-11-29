"""
Planner Agent - Creates detailed execution plans.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from aol_fire.models import Plan, Task, TaskPriority
from aol_fire.core import FireConfig
from aol_fire.llm import create_chat_model
from aol_fire.agents.prompts import PLANNER_PROMPT


class PlannerAgent:
    """
    The Planner Agent creates detailed execution plans.
    
    It analyzes goals and breaks them into actionable tasks
    with proper ordering, dependencies, and estimates.
    """
    
    def __init__(self, config: FireConfig):
        self.config = config
        self.llm = create_chat_model(config, "planner")
        self.llm.system_prompt = PLANNER_PROMPT
    
    def create_plan(
        self, 
        goal: str, 
        context: Optional[Dict] = None,
        existing_files: Optional[List[str]] = None
    ) -> Plan:
        """
        Create an execution plan for a goal.
        
        Args:
            goal: The user's goal
            context: Additional context (project info, etc.)
            existing_files: List of existing files in the project
        
        Returns:
            A Plan object with ordered tasks
        """
        from langchain_core.messages import HumanMessage
        
        context_str = ""
        if context:
            context_str = f"\n\nProject Context:\n{json.dumps(context, indent=2)}"
        
        if existing_files:
            files_str = "\n".join(f"  - {f}" for f in existing_files[:30])
            context_str += f"\n\nExisting Files:\n{files_str}"
        
        prompt = f"""Create a detailed execution plan for this goal:

Goal: {goal}
{context_str}

Remember to:
1. Break into 5-15 specific, actionable tasks
2. Order tasks by dependencies
3. Include setup and verification steps
4. Estimate time for each task

Respond with a JSON plan as specified in your instructions."""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # Parse the plan from response
        return self._parse_plan_response(goal, response.content)
    
    def _parse_plan_response(self, goal: str, response: str) -> Plan:
        """Parse the LLM response into a Plan object."""
        plan = Plan(goal=goal)
        
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > start:
                data = json.loads(response[start:end])
                
                plan.reasoning = data.get("reasoning", "")
                
                for task_data in data.get("tasks", []):
                    priority_map = {
                        "high": TaskPriority.HIGH,
                        "medium": TaskPriority.MEDIUM,
                        "low": TaskPriority.LOW,
                        "critical": TaskPriority.CRITICAL,
                    }
                    
                    task = plan.add_task(
                        title=task_data.get("title", "Unnamed task"),
                        description=task_data.get("description", ""),
                        priority=priority_map.get(
                            task_data.get("priority", "medium").lower(),
                            TaskPriority.MEDIUM
                        ),
                        estimated_duration_mins=task_data.get("estimated_mins"),
                        tags=task_data.get("tags", []),
                    )
        except json.JSONDecodeError:
            # Fallback: create a simple plan from the response
            plan.add_task(
                title="Execute goal",
                description=f"Execute the goal: {goal}\n\nLLM suggested: {response[:500]}",
                priority=TaskPriority.HIGH,
            )
        
        # If no tasks were created, add a default
        if not plan.tasks:
            plan.add_task(
                title="Execute goal",
                description=goal,
                priority=TaskPriority.HIGH,
            )
        
        return plan
    
    def refine_plan(
        self, 
        plan: Plan, 
        feedback: str,
        completed_tasks: Optional[List[Task]] = None
    ) -> Plan:
        """
        Refine an existing plan based on feedback or progress.
        
        Args:
            plan: The current plan
            feedback: Feedback or new information
            completed_tasks: Tasks already completed
        
        Returns:
            Updated Plan object
        """
        from langchain_core.messages import HumanMessage
        
        completed_str = ""
        if completed_tasks:
            completed_str = "\n".join(
                f"  ✓ {t.title}: {t.output or 'completed'}"
                for t in completed_tasks
            )
            completed_str = f"\n\nCompleted Tasks:\n{completed_str}"
        
        remaining_str = "\n".join(
            f"  - {t.title}"
            for t in plan.pending_tasks
        )
        
        prompt = f"""Refine this execution plan based on new information:

Original Goal: {plan.goal}

Feedback: {feedback}
{completed_str}

Remaining Tasks:
{remaining_str}

Should we:
1. Continue with remaining tasks?
2. Add new tasks?
3. Modify existing tasks?
4. Skip any tasks?

Respond with an updated JSON plan."""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # Parse and merge with existing plan
        updated = self._parse_plan_response(plan.goal, response.content)
        
        # Preserve completed tasks
        if completed_tasks:
            updated.tasks = completed_tasks + updated.tasks
        
        return updated
    
    def estimate_complexity(self, goal: str) -> Dict[str, Any]:
        """
        Estimate the complexity of a goal before planning.
        
        Returns:
            Dictionary with complexity metrics
        """
        from langchain_core.messages import HumanMessage
        
        prompt = f"""Estimate the complexity of this programming goal:

Goal: {goal}

Respond with JSON:
{{
    "complexity": "simple|moderate|complex|very_complex",
    "estimated_tasks": <number>,
    "estimated_time_mins": <number>,
    "key_components": ["list", "of", "components"],
    "potential_challenges": ["list", "of", "challenges"],
    "recommended_approach": "brief description"
}}"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        try:
            start = response.content.find('{')
            end = response.content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response.content[start:end])
        except:
            pass
        
        return {
            "complexity": "moderate",
            "estimated_tasks": 5,
            "estimated_time_mins": 30,
            "key_components": [],
            "potential_challenges": [],
            "recommended_approach": "Standard iterative development",
        }
