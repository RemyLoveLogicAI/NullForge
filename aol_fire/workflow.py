"""
LangGraph Workflow for AOL-CLI Fire Edition.

Implements a sophisticated multi-agent workflow with:
- Planning phase
- Execution phase with tool calling
- Review and verification phase
- Final reporting
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Annotated, Sequence
import operator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from aol_fire.models import (
    AgentRole,
    AgentState,
    ExecutionMetrics,
    FileChange,
    Plan,
    PlanStatus,
    Task,
    TaskStatus,
    ToolCall,
)
from aol_fire.core import FireConfig
from aol_fire.llm import create_chat_model
from aol_fire.tools import create_all_tools
from aol_fire.agents import OrchestratorAgent, PlannerAgent, CoderAgent


# =============================================================================
# State Type
# =============================================================================

class WorkflowState(Dict[str, Any]):
    """Type definition for workflow state."""
    pass


# =============================================================================
# Node Functions
# =============================================================================

def create_planner_node(config: FireConfig):
    """Create the planning node."""
    
    def planner_node(state: WorkflowState) -> WorkflowState:
        """
        Plan the execution strategy.
        
        Input: User goal
        Output: Structured execution plan
        """
        goal = state.get("goal", "")
        memory = state.get("memory")
        
        # Analyze project context if available
        context = {}
        if memory and memory.project_structure:
            context["project_structure"] = memory.project_structure
        
        # Create plan
        planner = PlannerAgent(config)
        plan = planner.create_plan(goal, context)
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now()
        
        # Update state
        state["plan"] = plan
        state["iteration"] = state.get("iteration", 0) + 1
        
        # Add message
        task_list = "\n".join(f"  {i+1}. {t.title}" for i, t in enumerate(plan.tasks))
        state["messages"] = state.get("messages", []) + [
            AIMessage(content=f"Created plan with {len(plan.tasks)} tasks:\n{task_list}")
        ]
        
        return state
    
    return planner_node


def create_executor_node(config: FireConfig, tools: List):
    """Create the execution node."""
    
    tool_map = {t.name: t for t in tools}
    
    def executor_node(state: WorkflowState) -> WorkflowState:
        """
        Execute the current task.
        
        Uses tools to accomplish tasks and tracks results.
        """
        plan = state.get("plan")
        if not plan:
            state["error"] = "No plan to execute"
            return state
        
        # Get current task
        current = plan.current_task
        if not current:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now()
            return state
        
        # Mark task in progress
        current.start()
        
        # Create coder agent with tools
        coder = CoderAgent(config, tools)
        
        # Build context
        context = {}
        if state.get("memory"):
            context["project_info"] = state["memory"].working_context
        
        # Execute task
        start_time = time.time()
        result = coder.execute_task(current, context)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Update task
        if result.get("success"):
            current.complete(result.get("output", "Completed"))
        else:
            current.fail(result.get("error", "Unknown error"))
        
        # Track tool calls
        for tc in result.get("tool_calls", []):
            state.setdefault("tool_calls", []).append(tc)
        
        # Track file changes
        for fc in result.get("file_changes", []):
            state.setdefault("file_changes", []).append(fc)
        
        # Update iteration
        state["iteration"] = state.get("iteration", 0) + 1
        
        # Add message
        status = "✓" if result.get("success") else "✗"
        state["messages"] = state.get("messages", []) + [
            AIMessage(content=f"{status} Task: {current.title}\n{result.get('output', '')[:500]}")
        ]
        
        return state
    
    return executor_node


def create_reviewer_node(config: FireConfig):
    """Create the review node."""
    
    def reviewer_node(state: WorkflowState) -> WorkflowState:
        """
        Review completed work and suggest improvements.
        """
        plan = state.get("plan")
        if not plan:
            return state
        
        # Only review if enabled and there were file changes
        if not config.enable_code_review:
            return state
        
        file_changes = state.get("file_changes", [])
        if not file_changes:
            return state
        
        # Create review summary
        from aol_fire.llm import create_chat_model
        llm = create_chat_model(config, "fast")
        
        files_summary = ", ".join(set(fc.path for fc in file_changes[:10]))
        
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(
            content=f"Briefly review the changes made to: {files_summary}. Focus on any obvious issues."
        )])
        
        state["review_notes"] = response.content
        
        return state
    
    return reviewer_node


def create_reporter_node(config: FireConfig):
    """Create the reporting node."""
    
    def reporter_node(state: WorkflowState) -> WorkflowState:
        """
        Generate final summary report.
        """
        plan = state.get("plan")
        file_changes = state.get("file_changes", [])
        tool_calls = state.get("tool_calls", [])
        
        # Build report
        report_parts = ["# Execution Summary\n"]
        
        if plan:
            report_parts.append(f"## Goal\n{plan.goal}\n")
            report_parts.append(f"## Results\n")
            report_parts.append(f"- Tasks completed: {len(plan.completed_tasks)}/{len(plan.tasks)}")
            report_parts.append(f"- Success rate: {plan.success_rate:.1f}%\n")
            
            if plan.completed_tasks:
                report_parts.append("### Completed Tasks")
                for task in plan.completed_tasks:
                    report_parts.append(f"- ✓ {task.title}")
            
            if plan.failed_tasks:
                report_parts.append("\n### Failed Tasks")
                for task in plan.failed_tasks:
                    report_parts.append(f"- ✗ {task.title}: {task.error}")
        
        if file_changes:
            report_parts.append("\n## Files Changed")
            unique_files = {}
            for fc in file_changes:
                if fc.path not in unique_files:
                    unique_files[fc.path] = fc.action
            
            for path, action in sorted(unique_files.items()):
                icon = "📄" if action == "created" else "📝"
                report_parts.append(f"- {icon} {path} ({action})")
        
        if state.get("review_notes"):
            report_parts.append(f"\n## Review Notes\n{state['review_notes']}")
        
        state["final_output"] = "\n".join(report_parts)
        
        return state
    
    return reporter_node


# =============================================================================
# Routing Functions
# =============================================================================

def should_continue(state: WorkflowState) -> Literal["executor", "reviewer", "reporter", "end"]:
    """Determine the next step in the workflow."""
    
    # Check for errors
    if state.get("error"):
        return "reporter"
    
    # Check iteration limit
    max_iter = state.get("max_iterations", 100)
    if state.get("iteration", 0) >= max_iter:
        return "reporter"
    
    # Check plan status
    plan = state.get("plan")
    if not plan:
        return "end"
    
    # More tasks to execute?
    if plan.current_task:
        return "executor"
    
    # Plan complete - review if enabled
    if plan.is_complete:
        if state.get("config", {}).get("enable_code_review") and not state.get("review_notes"):
            return "reviewer"
        return "reporter"
    
    return "reporter"


def after_planning(state: WorkflowState) -> Literal["executor", "reporter"]:
    """Route after planning."""
    plan = state.get("plan")
    
    if not plan or not plan.tasks:
        return "reporter"
    
    return "executor"


# =============================================================================
# Graph Builder
# =============================================================================

def build_fire_graph(config: FireConfig) -> StateGraph:
    """
    Build the complete Fire workflow graph.
    
    Workflow:
    1. Planner: Create execution plan
    2. Executor: Execute tasks (loop)
    3. Reviewer: Review completed work
    4. Reporter: Generate summary
    """
    
    # Create tools
    tools = create_all_tools(config)
    
    # Create node functions
    planner = create_planner_node(config)
    executor = create_executor_node(config, tools)
    reviewer = create_reviewer_node(config)
    reporter = create_reporter_node(config)
    
    # Build graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("planner", planner)
    workflow.add_node("executor", executor)
    workflow.add_node("reviewer", reviewer)
    workflow.add_node("reporter", reporter)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Add edges
    workflow.add_conditional_edges(
        "planner",
        after_planning,
        {
            "executor": "executor",
            "reporter": "reporter",
        }
    )
    
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "reviewer": "reviewer",
            "reporter": "reporter",
            "end": END,
        }
    )
    
    workflow.add_edge("reviewer", "reporter")
    workflow.add_edge("reporter", END)
    
    return workflow.compile()


def create_initial_state(goal: str, config: FireConfig) -> WorkflowState:
    """Create the initial workflow state."""
    from aol_fire.models import Memory
    
    return {
        "goal": goal,
        "plan": None,
        "messages": [],
        "memory": Memory(),
        "tool_calls": [],
        "file_changes": [],
        "iteration": 0,
        "max_iterations": config.max_iterations,
        "config": {
            "enable_code_review": config.enable_code_review,
        },
        "error": None,
        "final_output": None,
        "review_notes": None,
    }
