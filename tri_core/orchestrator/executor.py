"""
CLI Executor
============

Translates high-level agent decisions into executable AOL-CLI commands.
Interfaces with LangGraph workflows for complex execution patterns.
"""

from __future__ import annotations
import asyncio
import logging
import subprocess
import shlex
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tri_core.models import (
    Platform,
    CLICommand,
    CommandResult,
    TaskStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """Configuration for CLI execution."""
    default_timeout: int = 60
    max_output_size: int = 1_000_000  # 1MB
    shell: str = "/bin/bash"
    enable_streaming: bool = True
    working_directory: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of a CLI execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    started_at: datetime
    completed_at: datetime
    timed_out: bool = False
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class CLIExecutor:
    """
    ⚡ CLI Executor
    
    Executes CLI commands with advanced features:
    - Command translation from high-level intents
    - Async execution with streaming
    - Output capturing and parsing
    - Timeout handling
    - Environment management
    - Command chaining
    """
    
    # Command templates for common operations
    COMMAND_TEMPLATES = {
        "generate_code": "fire run \"{task}\" --workspace {workspace}",
        "run_tests": "fire run \"Run all tests\" --workspace {workspace}",
        "analyze_project": "fire analyze {path}",
        "deploy": "fire run \"Deploy the application\" --workspace {workspace}",
        "refactor": "fire run \"Refactor: {description}\" --workspace {workspace}",
        "create_api": "fire run \"Create a REST API for {resource}\" --workspace {workspace}",
        "add_feature": "fire run \"Add feature: {feature}\" --workspace {workspace}",
    }
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Initialize the CLI executor."""
        self.config = config or ExecutionConfig()
        self._execution_history: List[ExecutionResult] = []
        self._active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._command_hooks: Dict[str, List[Callable]] = {
            "pre_execute": [],
            "post_execute": [],
        }
        
        logger.info("⚡ CLI Executor initialized")
    
    # =========================================================================
    # COMMAND TRANSLATION
    # =========================================================================
    
    def translate_intent(
        self,
        intent: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        Translate a high-level intent into a CLI command.
        
        Args:
            intent: Intent name (e.g., "generate_code", "run_tests")
            parameters: Intent parameters
            
        Returns:
            CLI command string
        """
        if intent in self.COMMAND_TEMPLATES:
            template = self.COMMAND_TEMPLATES[intent]
            # Fill in parameters
            try:
                return template.format(**parameters)
            except KeyError as e:
                logger.warning(f"Missing parameter for intent {intent}: {e}")
                return f"fire run \"{intent}: {parameters}\""
        else:
            # Fallback to direct fire run
            return f"fire run \"{intent}\""
    
    def parse_command(self, command: str) -> CLICommand:
        """Parse a command string into a CLICommand object."""
        parts = shlex.split(command)
        if not parts:
            return CLICommand(command="")
        
        return CLICommand(
            command=parts[0],
            args=parts[1:] if len(parts) > 1 else [],
            working_directory=self.config.working_directory,
        )
    
    # =========================================================================
    # EXECUTION
    # =========================================================================
    
    async def execute(
        self,
        command: str,
        *,
        timeout: Optional[int] = None,
        working_directory: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
    ) -> ExecutionResult:
        """
        Execute a CLI command asynchronously.
        
        Args:
            command: Command to execute
            timeout: Execution timeout in seconds
            working_directory: Working directory for execution
            environment: Additional environment variables
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Execution result
        """
        timeout = timeout or self.config.default_timeout
        cwd = working_directory or self.config.working_directory
        
        # Merge environment
        env = {**self.config.environment, **(environment or {})}
        
        # Pre-execution hooks
        for hook in self._command_hooks["pre_execute"]:
            command = hook(command) or command
        
        logger.info(f"⚡ Executing: {command}")
        started_at = datetime.utcnow()
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                cwd=cwd,
                env=env if env else None,
            )
            
            # Store for potential cancellation
            process_id = f"proc_{id(process)}"
            self._active_processes[process_id] = process
            
            try:
                # Wait with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
                
                timed_out = False
                exit_code = process.returncode or 0
                
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {timeout}s: {command}")
                process.kill()
                await process.wait()
                stdout, stderr = b"", b"Command timed out"
                timed_out = True
                exit_code = -1
            
            finally:
                del self._active_processes[process_id]
            
            completed_at = datetime.utcnow()
            execution_time = (completed_at - started_at).total_seconds()
            
            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
            
            # Truncate if too large
            if len(stdout_str) > self.config.max_output_size:
                stdout_str = stdout_str[:self.config.max_output_size] + "\n... [truncated]"
            if len(stderr_str) > self.config.max_output_size:
                stderr_str = stderr_str[:self.config.max_output_size] + "\n... [truncated]"
            
            result = ExecutionResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at,
                timed_out=timed_out,
            )
            
            # Post-execution hooks
            for hook in self._command_hooks["post_execute"]:
                hook(result)
            
            # Store in history
            self._execution_history.append(result)
            
            if result.success:
                logger.info(f"✅ Command completed in {execution_time:.2f}s")
            else:
                logger.warning(f"⚠️ Command failed with exit code {exit_code}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Execution error: {e}")
            completed_at = datetime.utcnow()
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=(completed_at - started_at).total_seconds(),
                started_at=started_at,
                completed_at=completed_at,
                timed_out=False,
            )
    
    async def execute_chain(
        self,
        commands: List[str],
        *,
        stop_on_failure: bool = True,
        **kwargs,
    ) -> List[ExecutionResult]:
        """
        Execute a chain of commands sequentially.
        
        Args:
            commands: List of commands to execute
            stop_on_failure: Stop chain if a command fails
            **kwargs: Additional execution options
            
        Returns:
            List of execution results
        """
        results = []
        
        for command in commands:
            result = await self.execute(command, **kwargs)
            results.append(result)
            
            if stop_on_failure and not result.success:
                logger.warning(f"Chain stopped due to failure: {command}")
                break
        
        return results
    
    async def execute_parallel(
        self,
        commands: List[str],
        **kwargs,
    ) -> List[ExecutionResult]:
        """
        Execute commands in parallel.
        
        Args:
            commands: List of commands to execute
            **kwargs: Additional execution options
            
        Returns:
            List of execution results
        """
        tasks = [self.execute(cmd, **kwargs) for cmd in commands]
        return await asyncio.gather(*tasks)
    
    # =========================================================================
    # STREAMING EXECUTION
    # =========================================================================
    
    async def execute_streaming(
        self,
        command: str,
        callback: Callable[[str, str], None],
        **kwargs,
    ) -> ExecutionResult:
        """
        Execute a command with streaming output.
        
        Args:
            command: Command to execute
            callback: Function called with (stream_type, data) for each output chunk
            **kwargs: Additional execution options
            
        Returns:
            Final execution result
        """
        cwd = kwargs.get("working_directory") or self.config.working_directory
        timeout = kwargs.get("timeout") or self.config.default_timeout
        
        logger.info(f"⚡ Streaming execution: {command}")
        started_at = datetime.utcnow()
        
        stdout_chunks = []
        stderr_chunks = []
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            
            async def read_stream(stream, stream_type: str, chunks: list):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    chunks.append(text)
                    callback(stream_type, text)
            
            # Read both streams concurrently
            await asyncio.gather(
                read_stream(process.stdout, "stdout", stdout_chunks),
                read_stream(process.stderr, "stderr", stderr_chunks),
            )
            
            await process.wait()
            
            completed_at = datetime.utcnow()
            
            return ExecutionResult(
                command=command,
                exit_code=process.returncode or 0,
                stdout="".join(stdout_chunks),
                stderr="".join(stderr_chunks),
                execution_time=(completed_at - started_at).total_seconds(),
                started_at=started_at,
                completed_at=completed_at,
            )
            
        except Exception as e:
            completed_at = datetime.utcnow()
            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="".join(stdout_chunks),
                stderr=str(e),
                execution_time=(completed_at - started_at).total_seconds(),
                started_at=started_at,
                completed_at=completed_at,
            )
    
    # =========================================================================
    # HOOKS & UTILITIES
    # =========================================================================
    
    def add_hook(self, hook_type: str, callback: Callable) -> None:
        """Add an execution hook."""
        if hook_type in self._command_hooks:
            self._command_hooks[hook_type].append(callback)
    
    def remove_hook(self, hook_type: str, callback: Callable) -> bool:
        """Remove an execution hook."""
        if hook_type in self._command_hooks:
            try:
                self._command_hooks[hook_type].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    async def cancel_all(self) -> int:
        """Cancel all active processes."""
        count = 0
        for process in self._active_processes.values():
            try:
                process.kill()
                count += 1
            except ProcessLookupError:
                pass
        self._active_processes.clear()
        return count
    
    def get_history(self, limit: int = 50) -> List[ExecutionResult]:
        """Get execution history."""
        return self._execution_history[-limit:]
    
    def clear_history(self) -> int:
        """Clear execution history."""
        count = len(self._execution_history)
        self._execution_history.clear()
        return count
    
    def __repr__(self) -> str:
        return (
            f"CLIExecutor("
            f"history={len(self._execution_history)}, "
            f"active={len(self._active_processes)})"
        )
