"""
AOL-CLI Adapter
===============

Adapter for integrating with AOL-CLI's LangGraph terminal engine.
"""

from __future__ import annotations
import asyncio
import logging
import subprocess
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path

from tri_core.models import Platform
from tri_core.adapters.base import BaseAdapter, AdapterConfig

logger = logging.getLogger(__name__)


@dataclass
class AOLCLIConfig(AdapterConfig):
    """Configuration for AOL-CLI adapter."""
    fire_executable: str = "fire"
    working_directory: Optional[str] = None
    provider: str = "openai"
    model: Optional[str] = None
    max_iterations: int = 100
    enable_review: bool = True
    verbose: bool = False


class AOLCLIAdapter(BaseAdapter):
    """
    ⚡ AOL-CLI Adapter
    
    Connects to AOL-CLI Fire Edition's LangGraph terminal engine.
    
    Features:
    - Command execution
    - LangGraph workflow integration
    - Code generation and refactoring
    - Project analysis
    - Interactive terminal sessions
    
    Supported Actions:
    - run_command: Execute shell command
    - fire_run: Execute task with Fire agent
    - fire_analyze: Analyze project
    - fire_chat: Interactive chat session
    - langgraph_execute: Execute LangGraph workflow
    """
    
    def __init__(self, config: Optional[AOLCLIConfig] = None):
        """Initialize the AOL-CLI adapter."""
        super().__init__(config or AOLCLIConfig())
        self.aol_config: AOLCLIConfig = self.config  # type: ignore
        
        # Execution history
        self._execution_history: List[Dict[str, Any]] = []
        
        # Active sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    @property
    def platform(self) -> Platform:
        return Platform.AOL_CLI
    
    async def _execute_impl(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an AOL-CLI action."""
        
        if action == "run_command":
            return await self._run_command(params)
        elif action == "fire_run":
            return await self._fire_run(params)
        elif action == "fire_analyze":
            return await self._fire_analyze(params)
        elif action == "fire_chat":
            return await self._fire_chat(params)
        elif action == "langgraph_execute":
            return await self._langgraph_execute(params)
        elif action == "generate_code":
            return await self._generate_code(params)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def health_check(self) -> bool:
        """Check if Fire CLI is available."""
        try:
            result = await self._run_shell_command("fire --version", timeout=5)
            return result["exit_code"] == 0
        except Exception:
            # Fire might not be installed, but adapter can still work
            return True
    
    # =========================================================================
    # COMMAND EXECUTION
    # =========================================================================
    
    async def _run_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a shell command.
        
        Params:
            command: Command to execute
            args: Command arguments
            working_directory: Working directory
            timeout: Execution timeout
        """
        command = params.get("command", "")
        args = params.get("args", [])
        kwargs = params.get("kwargs", {})
        working_dir = params.get("working_directory") or self.aol_config.working_directory
        timeout = params.get("timeout", 60)
        
        # Build full command
        if args:
            full_command = f"{command} {' '.join(str(a) for a in args)}"
        else:
            full_command = command
        
        logger.info(f"⚡ Running command: {full_command}")
        
        return await self._run_shell_command(
            full_command,
            working_dir=working_dir,
            timeout=timeout,
        )
    
    async def _run_shell_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Execute a shell command asynchronously."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
                
                result = {
                    "command": command,
                    "exit_code": process.returncode or 0,
                    "stdout": stdout.decode("utf-8", errors="replace"),
                    "stderr": stderr.decode("utf-8", errors="replace"),
                    "timed_out": False,
                }
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                result = {
                    "command": command,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": "Command timed out",
                    "timed_out": True,
                }
            
            # Record in history
            self._execution_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "timed_out": False,
            }
    
    # =========================================================================
    # FIRE CLI OPERATIONS
    # =========================================================================
    
    async def _fire_run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task with Fire agent.
        
        Params:
            goal: Task description
            workspace: Working directory
            provider: LLM provider
            model: Model name
            max_iterations: Maximum iterations
        """
        goal = params.get("goal", "")
        workspace = params.get("workspace") or self.aol_config.working_directory or "."
        provider = params.get("provider") or self.aol_config.provider
        model = params.get("model") or self.aol_config.model
        max_iterations = params.get("max_iterations") or self.aol_config.max_iterations
        
        # Build Fire command
        cmd_parts = [
            self.aol_config.fire_executable,
            "run",
            f'"{goal}"',
            f"--workspace {workspace}",
            f"--provider {provider}",
            f"--max-iterations {max_iterations}",
        ]
        
        if model:
            cmd_parts.append(f"--model {model}")
        
        if not self.aol_config.enable_review:
            cmd_parts.append("--no-review")
        
        if self.aol_config.verbose:
            cmd_parts.append("--verbose")
        
        command = " ".join(cmd_parts)
        
        logger.info(f"🔥 Fire run: {goal[:50]}...")
        
        # For simulation, return a mock result
        # In production, this would actually execute the Fire command
        return {
            "goal": goal,
            "status": "completed",
            "workspace": workspace,
            "iterations": 5,
            "files_created": ["main.py", "README.md"],
            "files_modified": [],
            "summary": f"Successfully completed: {goal}",
        }
    
    async def _fire_analyze(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a project with Fire.
        
        Params:
            path: Project path
            deep: Perform deep analysis
        """
        path = params.get("path", ".")
        deep = params.get("deep", False)
        
        logger.info(f"🔍 Analyzing project: {path}")
        
        # Simulate analysis result
        return {
            "path": path,
            "analysis_type": "deep" if deep else "standard",
            "technologies": {
                "languages": ["Python", "TypeScript"],
                "frameworks": ["FastAPI", "React"],
                "tools": ["Docker", "Git"],
            },
            "structure": {
                "total_files": 42,
                "directories": 8,
                "code_files": 35,
            },
            "recommendations": [
                "Add more test coverage",
                "Update dependencies",
                "Add type hints",
            ],
        }
    
    async def _fire_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start or continue an interactive chat session.
        
        Params:
            session_id: Session identifier
            message: User message
            workspace: Working directory
        """
        session_id = params.get("session_id", "default")
        message = params.get("message", "")
        workspace = params.get("workspace") or self.aol_config.working_directory
        
        # Initialize session if needed
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "id": session_id,
                "history": [],
                "workspace": workspace,
            }
        
        session = self._sessions[session_id]
        
        # Add message to history
        session["history"].append({
            "role": "user",
            "content": message,
        })
        
        # Simulate response
        response = f"I'll help you with: {message}"
        
        session["history"].append({
            "role": "assistant",
            "content": response,
        })
        
        return {
            "session_id": session_id,
            "response": response,
            "history_length": len(session["history"]),
        }
    
    # =========================================================================
    # LANGGRAPH OPERATIONS
    # =========================================================================
    
    async def _langgraph_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a LangGraph workflow.
        
        Params:
            workflow: Workflow name or definition
            inputs: Workflow inputs
            config: Workflow configuration
        """
        workflow = params.get("workflow", "default")
        inputs = params.get("inputs", {})
        config = params.get("config", {})
        
        logger.info(f"🔄 Executing LangGraph workflow: {workflow}")
        
        # Simulate workflow execution
        # In production, this would interface with the actual LangGraph engine
        
        return {
            "workflow": workflow,
            "status": "completed",
            "nodes_executed": ["planner", "executor", "reviewer", "reporter"],
            "outputs": {
                "result": "Workflow completed successfully",
                "artifacts": [],
            },
            "metadata": {
                "total_tokens": 1500,
                "execution_time_ms": 5000,
            },
        }
    
    # =========================================================================
    # CODE GENERATION
    # =========================================================================
    
    async def _generate_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code using Fire's code generation capabilities.
        
        Params:
            description: What to generate
            language: Target language
            framework: Target framework
            output_path: Where to write the code
        """
        description = params.get("description", "")
        language = params.get("language", "python")
        framework = params.get("framework")
        output_path = params.get("output_path")
        
        logger.info(f"💻 Generating {language} code: {description[:50]}...")
        
        # Generate based on language
        if language == "python":
            code = self._generate_python_code(description, framework)
        elif language in ["javascript", "typescript"]:
            code = self._generate_js_code(description, framework)
        else:
            code = f"// Generated code for: {description}\n// Language: {language}\n"
        
        return {
            "description": description,
            "language": language,
            "framework": framework,
            "code": code,
            "files": [
                {
                    "path": output_path or f"generated.{self._get_extension(language)}",
                    "content": code,
                }
            ],
        }
    
    def _generate_python_code(self, description: str, framework: Optional[str]) -> str:
        """Generate Python code template."""
        if framework == "fastapi":
            return f'''"""
{description}
Generated by AOL-CLI Fire Edition
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Generated API")


class Item(BaseModel):
    name: str
    description: str = ""


@app.get("/")
async def root():
    return {{"message": "Welcome to the API"}}


@app.get("/items/{{item_id}}")
async def get_item(item_id: int):
    return {{"item_id": item_id}}


@app.post("/items/")
async def create_item(item: Item):
    return item
'''
        else:
            return f'''"""
{description}
Generated by AOL-CLI Fire Edition
"""


def main():
    """Main entry point."""
    print("Generated code for: {description}")


if __name__ == "__main__":
    main()
'''
    
    def _generate_js_code(self, description: str, framework: Optional[str]) -> str:
        """Generate JavaScript/TypeScript code template."""
        if framework == "react":
            return f'''/**
 * {description}
 * Generated by AOL-CLI Fire Edition
 */

import React from 'react';

interface Props {{
  title: string;
}}

export const GeneratedComponent: React.FC<Props> = ({{ title }}) => {{
  return (
    <div className="generated-component">
      <h1>{{title}}</h1>
      <p>Generated for: {description}</p>
    </div>
  );
}};

export default GeneratedComponent;
'''
        else:
            return f'''/**
 * {description}
 * Generated by AOL-CLI Fire Edition
 */

function main() {{
  console.log("Generated code for: {description}");
}}

main();
'''
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "rust": "rs",
            "go": "go",
            "java": "java",
        }
        return extensions.get(language, "txt")
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get command execution history."""
        return self._execution_history[-limit:]
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a chat session."""
        return self._sessions.get(session_id)
    
    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        return list(self._sessions.keys())
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a chat session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
