"""
Advanced tool system for AOL-CLI Fire Edition.

Includes:
- File operations (read, write, edit, search)
- Shell command execution
- Web search and content extraction
- Code analysis and manipulation
- Git operations
- Project understanding
"""

from aol_fire.tools.file_tools import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    SearchFilesTool,
    ListDirectoryTool,
    CreateDirectoryTool,
    DeletePathTool,
    MovePathTool,
)
from aol_fire.tools.shell_tools import (
    ExecuteCommandTool,
    BackgroundCommandTool,
)
from aol_fire.tools.web_tools import (
    WebSearchTool,
    FetchURLTool,
)
from aol_fire.tools.code_tools import (
    AnalyzeCodeTool,
    RunPythonTool,
)
from aol_fire.tools.git_tools import (
    GitStatusTool,
    GitCommitTool,
    GitDiffTool,
)
from aol_fire.tools.project_tools import (
    AnalyzeProjectTool,
)

from aol_fire.core import FireConfig
from typing import List
from langchain_core.tools import BaseTool


def create_all_tools(config: FireConfig) -> List[BaseTool]:
    """Create all available tools based on configuration."""
    workspace = config.workspace_dir
    workspace.mkdir(parents=True, exist_ok=True)
    
    tools = []
    
    # File tools (always available)
    tools.extend([
        ReadFileTool(workspace_dir=workspace),
        ListDirectoryTool(workspace_dir=workspace),
        SearchFilesTool(workspace_dir=workspace),
    ])
    
    # Write tools (if enabled)
    if config.allow_file_writes:
        tools.extend([
            WriteFileTool(workspace_dir=workspace),
            EditFileTool(workspace_dir=workspace),
            CreateDirectoryTool(workspace_dir=workspace),
            MovePathTool(workspace_dir=workspace),
        ])
    
    if config.allow_file_deletes:
        tools.append(DeletePathTool(workspace_dir=workspace))
    
    # Shell tools (if enabled)
    if config.allow_shell_commands:
        tools.extend([
            ExecuteCommandTool(
                workspace_dir=workspace,
                blocked_commands=config.blocked_commands,
            ),
            BackgroundCommandTool(workspace_dir=workspace),
        ])
    
    # Web tools (if enabled)
    if config.allow_web_search:
        tools.extend([
            WebSearchTool(),
            FetchURLTool(),
        ])
    
    # Code tools (if enabled)
    if config.allow_code_execution:
        tools.extend([
            AnalyzeCodeTool(workspace_dir=workspace),
            RunPythonTool(workspace_dir=workspace),
        ])
    
    # Git tools (always available)
    tools.extend([
        GitStatusTool(workspace_dir=workspace),
        GitDiffTool(workspace_dir=workspace),
    ])
    
    if config.allow_file_writes:
        tools.append(GitCommitTool(workspace_dir=workspace))
    
    # Project tools
    tools.append(AnalyzeProjectTool(workspace_dir=workspace))
    
    return tools


__all__ = [
    "create_all_tools",
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "SearchFilesTool",
    "ListDirectoryTool",
    "CreateDirectoryTool",
    "DeletePathTool",
    "MovePathTool",
    "ExecuteCommandTool",
    "BackgroundCommandTool",
    "WebSearchTool",
    "FetchURLTool",
    "AnalyzeCodeTool",
    "RunPythonTool",
    "GitStatusTool",
    "GitCommitTool",
    "GitDiffTool",
    "AnalyzeProjectTool",
]
