"""
Orchestrator Agent - Coordinates the multi-agent system.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from aol_fire.models import AgentRole, AgentState, Plan, Task, TaskStatus
from aol_fire.core import FireConfig
from aol_fire.llm import create_chat_model
from aol_fire.agents.prompts import ORCHESTRATOR_PROMPT


class OrchestratorAgent:
    """
    The Orchestrator Agent coordinates the execution of complex tasks.
    
    It manages:
    - Task planning and delegation
    - Progress monitoring
    - Error handling and recovery
    - Result aggregation
    """
    
    def __init__(self, config: FireConfig):
        self.config = config
        self.llm = create_chat_model(config, "orchestrator")
        self.llm.system_prompt = ORCHESTRATOR_PROMPT
    
    def analyze_goal(self, goal: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze a user goal and determine the approach.
        
        Returns analysis including:
        - complexity: simple, moderate, complex
        - agents_needed: list of agent roles
        - approach: description of how to tackle it
        """
        from langchain_core.messages import HumanMessage
        
        prompt = f"""Analyze this goal and determine the best approach:

Goal: {goal}

Context: {context or 'No additional context'}

Respond with a JSON analysis:
{{
    "complexity": "simple|moderate|complex",
    "agents_needed": ["list", "of", "agent", "roles"],
    "approach": "Brief description of approach",
    "estimated_tasks": 5,
    "key_challenges": ["potential", "challenges"]
}}"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # Parse response
        import json
        try:
            # Extract JSON from response
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except:
            pass
        
        # Default analysis
        return {
            "complexity": "moderate",
            "agents_needed": ["planner", "coder"],
            "approach": "Standard planning and execution",
            "estimated_tasks": 5,
            "key_challenges": [],
        }
    
    def delegate_planning(self, goal: str, context: Dict) -> Plan:
        """Delegate planning to the Planner Agent."""
        from aol_fire.agents.planner import PlannerAgent
        
        planner = PlannerAgent(self.config)
        return planner.create_plan(goal, context)
    
    def select_agent_for_task(self, task: Task) -> AgentRole:
        """Select the best agent for a given task."""
        # Simple heuristic based on task tags
        tags = set(task.tags)
        
        if "research" in tags or "search" in tags:
            return AgentRole.RESEARCHER
        if "review" in tags or "qa" in tags:
            return AgentRole.REVIEWER
        if "debug" in tags or "fix" in tags or "error" in tags:
            return AgentRole.DEBUGGER
        if "deploy" in tags or "devops" in tags:
            return AgentRole.DEVOPS
        if "code" in tags or "implement" in tags or "create" in tags:
            return AgentRole.CODER
        
        # Default to coder for most tasks
        return AgentRole.CODER
    
    def summarize_progress(self, state: AgentState) -> str:
        """Generate a progress summary."""
        if not state.plan:
            return "No plan created yet."
        
        plan = state.plan
        summary_parts = [
            f"Goal: {plan.goal}",
            f"Progress: {plan.progress:.1f}%",
            f"Tasks: {len(plan.completed_tasks)}/{len(plan.tasks)} completed",
        ]
        
        if plan.failed_tasks:
            summary_parts.append(f"Failed: {len(plan.failed_tasks)} tasks")
        
        # Current task
        current = plan.current_task
        if current:
            summary_parts.append(f"Current: {current.title}")
        
        # Files changed
        if state.file_changes:
            created = len([f for f in state.file_changes if f.action == "created"])
            modified = len([f for f in state.file_changes if f.action == "modified"])
            summary_parts.append(f"Files: {created} created, {modified} modified")
        
        return "\n".join(summary_parts)
    
    def handle_error(self, error: str, task: Task, state: AgentState) -> str:
        """Handle an error during task execution."""
        from langchain_core.messages import HumanMessage
        
        prompt = f"""An error occurred during task execution. Analyze and suggest recovery:

Task: {task.title}
Description: {task.description}
Error: {error}

Recent tool calls: {[tc.tool_name for tc in state.tool_calls[-5:]]}

Respond with:
1. Error analysis
2. Suggested recovery action
3. Whether to retry, skip, or abort"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
