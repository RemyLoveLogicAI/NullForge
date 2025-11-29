"""
Unit tests for AOL-CLI Fire Edition.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

# Models tests
from aol_fire.models import (
    Task, TaskStatus, TaskPriority,
    Plan, PlanStatus,
    Memory, MemoryType, MemoryEntry,
    AgentState, AgentRole,
    ToolCall, FileChange,
)


class TestTask:
    """Test Task model."""
    
    def test_task_creation(self):
        task = Task(title="Test task", description="A test")
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
    
    def test_task_start(self):
        task = Task(title="Test")
        task.start()
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None
    
    def test_task_complete(self):
        task = Task(title="Test")
        task.start()
        task.complete("Done!")
        assert task.status == TaskStatus.COMPLETED
        assert task.output == "Done!"
        assert task.completed_at is not None
    
    def test_task_fail(self):
        task = Task(title="Test")
        task.start()
        task.fail("Error occurred")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Error occurred"
    
    def test_task_add_subtask(self):
        task = Task(title="Parent")
        subtask = task.add_subtask("Child task")
        assert len(task.subtasks) == 1
        assert subtask.parent_id == task.id
    
    def test_task_progress(self):
        task = Task(title="Parent")
        task.add_subtask("Sub 1")
        task.add_subtask("Sub 2")
        
        assert task.progress == 0.0
        
        task.subtasks[0].complete("Done")
        assert task.progress == 50.0
        
        task.subtasks[1].complete("Done")
        assert task.progress == 100.0


class TestPlan:
    """Test Plan model."""
    
    def test_plan_creation(self):
        plan = Plan(goal="Build something")
        assert plan.goal == "Build something"
        assert plan.status == PlanStatus.PENDING
        assert len(plan.tasks) == 0
    
    def test_plan_add_task(self):
        plan = Plan(goal="Test")
        task = plan.add_task("First task", description="Do something")
        assert len(plan.tasks) == 1
        assert task.title == "First task"
    
    def test_plan_pending_tasks(self):
        plan = Plan(goal="Test")
        plan.add_task("Task 1")
        plan.add_task("Task 2")
        
        assert len(plan.pending_tasks) == 2
        
        plan.tasks[0].complete("Done")
        assert len(plan.pending_tasks) == 1
    
    def test_plan_is_complete(self):
        plan = Plan(goal="Test")
        plan.add_task("Task 1")
        plan.add_task("Task 2")
        
        assert not plan.is_complete
        
        plan.tasks[0].complete("Done")
        assert not plan.is_complete
        
        plan.tasks[1].complete("Done")
        assert plan.is_complete
    
    def test_plan_progress(self):
        plan = Plan(goal="Test")
        plan.add_task("Task 1")
        plan.add_task("Task 2")
        plan.add_task("Task 3")
        plan.add_task("Task 4")
        
        assert plan.progress == 0.0
        
        plan.tasks[0].complete("Done")
        assert plan.progress == 25.0
        
        plan.tasks[1].complete("Done")
        assert plan.progress == 50.0
    
    def test_plan_success_rate(self):
        plan = Plan(goal="Test")
        plan.add_task("Task 1")
        plan.add_task("Task 2")
        
        plan.tasks[0].complete("Done")
        plan.tasks[1].fail("Error")
        
        assert plan.success_rate == 50.0


class TestMemory:
    """Test Memory model."""
    
    def test_memory_creation(self):
        memory = Memory()
        assert memory.session_id is not None
        assert len(memory.entries) == 0
    
    def test_memory_add_entry(self):
        memory = Memory()
        entry = memory.add_entry(
            "Important fact",
            type=MemoryType.SEMANTIC,
            importance=0.8
        )
        
        assert len(memory.entries) == 1
        assert entry.content == "Important fact"
        assert entry.type == MemoryType.SEMANTIC
        assert entry.importance == 0.8
    
    def test_memory_add_message(self):
        memory = Memory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there")
        
        assert len(memory.conversation) == 2
        assert memory.conversation[0]["role"] == "user"
    
    def test_memory_search(self):
        memory = Memory()
        memory.add_entry("Python is a programming language")
        memory.add_entry("JavaScript runs in browsers")
        memory.add_entry("Python has great libraries")
        
        results = memory.search("Python")
        assert len(results) == 2


class TestAgentState:
    """Test AgentState model."""
    
    def test_state_creation(self):
        state = AgentState()
        assert state.session_id is not None
        assert state.iteration == 0
        assert state.error is None
    
    def test_state_is_complete_with_plan(self):
        state = AgentState()
        plan = Plan(goal="Test")
        plan.add_task("Task")
        state.plan = plan
        
        assert not state.is_complete
        
        plan.tasks[0].complete("Done")
        assert state.is_complete
    
    def test_state_is_complete_with_error(self):
        state = AgentState()
        assert not state.is_complete
        
        state.error = "Something went wrong"
        assert state.is_complete


# Configuration tests
from aol_fire.core import FireConfig, build_config, FIRE_PRESETS, get_preset


class TestConfig:
    """Test configuration."""
    
    def test_config_defaults(self):
        config = FireConfig()
        assert config.llm_provider == "custom"
        assert config.max_iterations == 100
        assert config.allow_shell_commands is True
    
    def test_config_get_api_base(self):
        config = FireConfig(llm_provider="openai")
        assert "openai" in config.get_api_base()
        
        config = FireConfig(llm_provider="ollama")
        assert "localhost" in config.get_api_base()
    
    def test_build_config_with_args(self):
        config = build_config(cli_args={
            "llm_provider": "venice",
            "max_iterations": 50,
        })
        
        assert config.llm_provider == "venice"
        assert config.max_iterations == 50
    
    def test_presets_exist(self):
        assert "openai" in FIRE_PRESETS
        assert "venice" in FIRE_PRESETS
        assert "ollama" in FIRE_PRESETS
    
    def test_get_preset(self):
        preset = get_preset("openai")
        assert preset["llm_provider"] == "openai"
        assert "orchestrator_model" in preset
    
    def test_invalid_preset(self):
        with pytest.raises(ValueError):
            get_preset("invalid-preset")


# Tool tests
from aol_fire.tools.file_tools import (
    ReadFileTool, WriteFileTool, EditFileTool,
    SearchFilesTool, ListDirectoryTool,
)


class TestFileTools:
    """Test file tools."""
    
    def test_read_file_tool(self, tmp_path):
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        tool = ReadFileTool(workspace_dir=tmp_path)
        result = tool._run("test.txt")
        
        assert "Hello, World!" in result
    
    def test_read_file_not_found(self, tmp_path):
        tool = ReadFileTool(workspace_dir=tmp_path)
        result = tool._run("nonexistent.txt")
        
        assert "Error" in result
    
    def test_write_file_tool(self, tmp_path):
        tool = WriteFileTool(workspace_dir=tmp_path)
        result = tool._run("output.txt", "Test content")
        
        assert "Created" in result or "Updated" in result
        assert (tmp_path / "output.txt").exists()
        assert (tmp_path / "output.txt").read_text() == "Test content"
    
    def test_edit_file_tool(self, tmp_path):
        # Create initial file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        tool = EditFileTool(workspace_dir=tmp_path)
        result = tool._run("test.txt", "World", "Python")
        
        assert "Edited" in result
        assert test_file.read_text() == "Hello, Python!"
    
    def test_list_directory_tool(self, tmp_path):
        # Create some files
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.py").write_text("content")
        (tmp_path / "subdir").mkdir()
        
        tool = ListDirectoryTool(workspace_dir=tmp_path)
        result = tool._run(".")
        
        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir" in result
    
    def test_search_files_tool(self, tmp_path):
        # Create files with content
        (tmp_path / "main.py").write_text("def hello():\n    print('hello')")
        (tmp_path / "utils.py").write_text("def helper():\n    return 42")
        
        tool = SearchFilesTool(workspace_dir=tmp_path)
        result = tool._run("def hello", ".", "*.py")
        
        assert "main.py" in result
        assert "hello" in result


# Workflow tests
from aol_fire.workflow import create_initial_state, should_continue


class TestWorkflow:
    """Test workflow logic."""
    
    def test_create_initial_state(self):
        config = FireConfig()
        state = create_initial_state("Test goal", config)
        
        assert state["goal"] == "Test goal"
        assert state["plan"] is None
        assert state["iteration"] == 0
    
    def test_should_continue_with_error(self):
        state = {"error": "Something wrong", "iteration": 0, "max_iterations": 100}
        result = should_continue(state)
        assert result == "reporter"
    
    def test_should_continue_max_iterations(self):
        state = {"error": None, "iteration": 100, "max_iterations": 100, "plan": None}
        result = should_continue(state)
        assert result == "reporter"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
