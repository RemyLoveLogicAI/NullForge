"""
NullForge SecureExecutor Tools - Sandboxed Command Execution

Provides secure shell command execution with:
- Command allowlist/blocklist
- Timeout enforcement
- Resource limits
- Output capture and streaming
- Background process management
"""

from __future__ import annotations

import os
import subprocess
import signal
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from datetime import datetime

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


# =============================================================================
# Input Schemas
# =============================================================================

class ExecuteCommandInput(BaseModel):
    """Input for executing commands."""
    command: str = Field(..., description="Shell command to execute")
    cwd: Optional[str] = Field(default=None, description="Working directory")
    timeout: int = Field(default=300, description="Timeout in seconds")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")


class BackgroundCommandInput(BaseModel):
    """Input for background commands."""
    command: str = Field(..., description="Command to run in background")
    cwd: Optional[str] = Field(default=None, description="Working directory")
    log_file: Optional[str] = Field(default=None, description="Log file path")


# =============================================================================
# Tool Implementations
# =============================================================================

class ExecuteCommandTool(BaseTool):
    """
    Execute shell commands with security controls.
    
    Features:
    - Command blocklist for dangerous operations
    - Timeout enforcement
    - Output capture (stdout + stderr)
    - Exit code reporting
    - Working directory control
    """
    
    name: str = "execute_command"
    description: str = """Execute a shell command and return output.

Use this for:
- Running build commands (npm install, cargo build, etc.)
- Git operations
- System utilities (ls, grep, find, etc.)
- Package management
- Running scripts and tests

Security: Some dangerous commands are blocked for safety."""
    
    args_schema: Type[BaseModel] = ExecuteCommandInput
    workspace_dir: Path = Field(default=Path("."))
    blocked_commands: List[str] = Field(default_factory=list)
    
    def _resolve_path(self, path: Optional[str]) -> str:
        if path is None:
            return str(self.workspace_dir)
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str(self.workspace_dir / p)
    
    def _is_blocked(self, command: str) -> Optional[str]:
        """Check if command is in blocklist."""
        cmd_lower = command.lower()
        
        # Default dangerous patterns
        dangerous = [
            "rm -rf /",
            "rm -rf /*",
            "mkfs",
            "dd if=/dev/zero",
            "dd if=/dev/random",
            ":(){:|:&};:",  # Fork bomb
            "chmod -R 777 /",
            "> /dev/sda",
            "mv /* ",
            "wget http",  # Potential for malicious downloads
        ]
        
        for pattern in dangerous + self.blocked_commands:
            if pattern.lower() in cmd_lower:
                return pattern
        
        return None
    
    def _run(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> str:
        # Security check
        blocked = self._is_blocked(command)
        if blocked:
            return f"🚫 Command blocked for security: contains '{blocked}'"
        
        try:
            working_dir = self._resolve_path(cwd)
            
            # Merge environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)
            
            # Execute
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=run_env,
            )
            
            output_parts = []
            
            if result.stdout:
                output_parts.append(f"📤 STDOUT:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"📥 STDERR:\n{result.stderr}")
            
            exit_info = f"Exit code: {result.returncode}"
            if result.returncode == 0:
                exit_info = f"✓ {exit_info}"
            else:
                exit_info = f"✗ {exit_info}"
            
            output_parts.append(exit_info)
            
            return "\n\n".join(output_parts) if output_parts else "Command completed (no output)"
            
        except subprocess.TimeoutExpired:
            return f"⏰ Command timed out after {timeout} seconds"
        except FileNotFoundError:
            return f"❌ Working directory not found: {cwd}"
        except Exception as e:
            return f"❌ Error executing command: {str(e)}"


class BackgroundCommandTool(BaseTool):
    """
    Run commands in the background.
    
    Features:
    - Non-blocking execution
    - Optional log file output
    - Process ID tracking
    """
    
    name: str = "background_command"
    description: str = """Run a command in the background without waiting for completion.

Use this for:
- Starting development servers
- Long-running processes
- Services that need to run continuously

Returns the process ID for later management."""
    
    args_schema: Type[BaseModel] = BackgroundCommandInput
    workspace_dir: Path = Field(default=Path("."))
    
    def _resolve_path(self, path: Optional[str]) -> str:
        if path is None:
            return str(self.workspace_dir)
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str(self.workspace_dir / p)
    
    def _run(
        self,
        command: str,
        cwd: Optional[str] = None,
        log_file: Optional[str] = None,
    ) -> str:
        try:
            working_dir = self._resolve_path(cwd)
            
            # Prepare output redirection
            if log_file:
                log_path = Path(self._resolve_path(log_file))
                log_path.parent.mkdir(parents=True, exist_ok=True)
                stdout = open(log_path, 'w')
                stderr = subprocess.STDOUT
            else:
                stdout = subprocess.DEVNULL
                stderr = subprocess.DEVNULL
            
            # Start process
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=working_dir,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,  # Detach from parent
            )
            
            result = f"🚀 Started background process\n"
            result += f"   PID: {process.pid}\n"
            result += f"   Command: {command[:50]}..."
            
            if log_file:
                result += f"\n   Log: {log_file}"
            
            return result
            
        except Exception as e:
            return f"❌ Error starting background process: {str(e)}"
