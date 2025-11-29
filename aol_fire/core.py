"""
Core configuration and agent setup for AOL-CLI Fire Edition.
"""

from __future__ import annotations

import os
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class FireConfig(BaseSettings):
    """
    Configuration for AOL-CLI Fire Edition.
    
    Supports loading from environment variables and .env files.
    """
    
    # ==========================================================================
    # LLM Configuration
    # ==========================================================================
    
    llm_provider: Literal[
        "openai", "venice", "ollama", "groq", 
        "together", "openrouter", "anthropic", "custom"
    ] = Field(default="custom")
    
    # API credentials
    api_key: Optional[SecretStr] = Field(default=None)
    api_base: Optional[str] = Field(default=None)
    
    # Model selection
    orchestrator_model: str = Field(default="gpt-4-turbo-preview")
    planner_model: str = Field(default="gpt-4-turbo-preview")
    coder_model: str = Field(default="gpt-4-turbo-preview")
    fast_model: str = Field(default="gpt-3.5-turbo")  # For quick tasks
    
    # Model parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096)
    
    # ==========================================================================
    # Agent Behavior
    # ==========================================================================
    
    max_iterations: int = Field(default=100, ge=1, le=500)
    max_task_retries: int = Field(default=3)
    api_timeout: int = Field(default=120, ge=10, le=600)
    
    # Multi-agent
    enable_multi_agent: bool = Field(default=True)
    enable_code_review: bool = Field(default=True)
    enable_auto_debug: bool = Field(default=True)
    
    # ==========================================================================
    # Workspace Configuration
    # ==========================================================================
    
    workspace_dir: Path = Field(default=Path("./workspace"))
    data_dir: Path = Field(default=Path.home() / ".aol-fire")
    
    # ==========================================================================
    # Memory & Persistence
    # ==========================================================================
    
    enable_memory: bool = Field(default=True)
    enable_semantic_search: bool = Field(default=True)
    memory_db_path: Optional[Path] = Field(default=None)
    max_conversation_history: int = Field(default=50)
    
    # ==========================================================================
    # Tool Permissions
    # ==========================================================================
    
    allow_shell_commands: bool = Field(default=True)
    allow_file_writes: bool = Field(default=True)
    allow_file_deletes: bool = Field(default=True)
    allow_network: bool = Field(default=True)
    allow_web_search: bool = Field(default=True)
    allow_code_execution: bool = Field(default=True)
    
    # Shell restrictions
    blocked_commands: List[str] = Field(default_factory=lambda: [
        "rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "chmod -R 777 /"
    ])
    
    # ==========================================================================
    # Output & Display
    # ==========================================================================
    
    verbose: bool = Field(default=False)
    debug: bool = Field(default=False)
    show_tool_calls: bool = Field(default=True)
    show_thinking: bool = Field(default=False)
    color_output: bool = Field(default=True)
    
    # ==========================================================================
    # Safety (set to False for unrestricted operation)
    # ==========================================================================
    
    enable_content_filter: bool = Field(default=False)
    enable_safety_checks: bool = Field(default=False)
    confirm_destructive: bool = Field(default=False)
    
    class Config:
        env_prefix = "FIRE_"
        env_file = ".env"
        extra = "ignore"
    
    @field_validator('workspace_dir', 'data_dir', mode='before')
    @classmethod
    def validate_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v
    
    @property
    def config_hash(self) -> str:
        """Generate a hash of the configuration for caching."""
        config_str = f"{self.llm_provider}:{self.orchestrator_model}:{self.planner_model}"
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    
    def get_api_key(self) -> Optional[str]:
        """Get the API key as a string."""
        if self.api_key:
            return self.api_key.get_secret_value()
        
        # Try provider-specific env vars
        key_map = {
            "openai": "OPENAI_API_KEY",
            "venice": "VENICE_API_KEY",
            "groq": "GROQ_API_KEY",
            "together": "TOGETHER_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "custom": "CUSTOM_API_KEY",
        }
        
        env_var = key_map.get(self.llm_provider)
        if env_var:
            return os.getenv(env_var)
        return None
    
    def get_api_base(self) -> str:
        """Get the API base URL."""
        if self.api_base:
            return self.api_base
        
        base_map = {
            "openai": "https://api.openai.com/v1",
            "venice": "https://api.venice.ai/api/v1",
            "ollama": "http://localhost:11434/v1",
            "groq": "https://api.groq.com/openai/v1",
            "together": "https://api.together.xyz/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "custom": os.getenv("CUSTOM_API_BASE", "http://localhost:8000/v1"),
        }
        
        return base_map.get(self.llm_provider, "http://localhost:8000/v1")
    
    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.data_dir / "sessions").mkdir(exist_ok=True)
        (self.data_dir / "memory").mkdir(exist_ok=True)
        (self.data_dir / "plugins").mkdir(exist_ok=True)


# =============================================================================
# Provider Presets
# =============================================================================

FIRE_PRESETS: Dict[str, Dict[str, Any]] = {
    # OpenAI
    "openai": {
        "llm_provider": "openai",
        "orchestrator_model": "gpt-4-turbo-preview",
        "planner_model": "gpt-4-turbo-preview",
        "coder_model": "gpt-4-turbo-preview",
        "fast_model": "gpt-3.5-turbo",
    },
    "openai-4o": {
        "llm_provider": "openai",
        "orchestrator_model": "gpt-4o",
        "planner_model": "gpt-4o",
        "coder_model": "gpt-4o",
        "fast_model": "gpt-4o-mini",
    },
    
    # Venice AI (Uncensored)
    "venice": {
        "llm_provider": "venice",
        "orchestrator_model": "llama-3.1-405b",
        "planner_model": "llama-3.1-405b",
        "coder_model": "llama-3.1-70b",
        "fast_model": "llama-3.1-8b",
    },
    "venice-uncensored": {
        "llm_provider": "venice",
        "orchestrator_model": "llama-3.1-405b",
        "planner_model": "llama-3.1-405b",
        "coder_model": "dolphin-2.9.2-qwen2-72b",
        "fast_model": "dolphin-llama3-70b",
    },
    
    # Ollama (Local)
    "ollama": {
        "llm_provider": "ollama",
        "orchestrator_model": "llama3.1:70b",
        "planner_model": "llama3.1:70b",
        "coder_model": "codestral:latest",
        "fast_model": "llama3.1:8b",
    },
    "ollama-code": {
        "llm_provider": "ollama",
        "orchestrator_model": "deepseek-coder-v2:latest",
        "planner_model": "llama3.1:70b",
        "coder_model": "deepseek-coder-v2:latest",
        "fast_model": "llama3.1:8b",
    },
    
    # Groq (Fast)
    "groq": {
        "llm_provider": "groq",
        "orchestrator_model": "llama-3.1-70b-versatile",
        "planner_model": "llama-3.1-70b-versatile",
        "coder_model": "llama-3.1-70b-versatile",
        "fast_model": "llama-3.1-8b-instant",
    },
    
    # Together AI
    "together": {
        "llm_provider": "together",
        "orchestrator_model": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        "planner_model": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        "coder_model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "fast_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    },
    
    # OpenRouter
    "openrouter": {
        "llm_provider": "openrouter",
        "orchestrator_model": "anthropic/claude-3.5-sonnet",
        "planner_model": "anthropic/claude-3.5-sonnet",
        "coder_model": "anthropic/claude-3.5-sonnet",
        "fast_model": "meta-llama/llama-3.1-8b-instruct",
    },
    "openrouter-free": {
        "llm_provider": "openrouter",
        "orchestrator_model": "meta-llama/llama-3.1-8b-instruct:free",
        "planner_model": "meta-llama/llama-3.1-8b-instruct:free",
        "coder_model": "meta-llama/llama-3.1-8b-instruct:free",
        "fast_model": "meta-llama/llama-3.1-8b-instruct:free",
    },
    
    # Anthropic
    "anthropic": {
        "llm_provider": "anthropic",
        "orchestrator_model": "claude-3-5-sonnet-20241022",
        "planner_model": "claude-3-5-sonnet-20241022",
        "coder_model": "claude-3-5-sonnet-20241022",
        "fast_model": "claude-3-haiku-20240307",
    },
}


def get_preset(name: str) -> Dict[str, Any]:
    """Get a provider preset configuration."""
    if name not in FIRE_PRESETS:
        available = ", ".join(FIRE_PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return FIRE_PRESETS[name].copy()


def build_config(
    preset: Optional[str] = None,
    cli_args: Optional[Dict[str, Any]] = None,
    env_file: Optional[Path] = None,
) -> FireConfig:
    """
    Build configuration from multiple sources.
    
    Priority (highest to lowest):
    1. CLI arguments
    2. Preset values
    3. Environment variables
    4. Defaults
    """
    config_dict = {}
    
    # Apply preset
    if preset:
        config_dict.update(get_preset(preset))
    
    # Override with CLI args
    if cli_args:
        config_dict.update({k: v for k, v in cli_args.items() if v is not None})
    
    return FireConfig(**config_dict)


class FireAgent:
    """
    Main agent class for AOL-CLI Fire Edition.
    
    This is the high-level interface for running the agent.
    """
    
    def __init__(self, config: Optional[FireConfig] = None):
        self.config = config or FireConfig()
        self.config.ensure_directories()
        self._graph = None
        self._tools = None
    
    def run(self, goal: str) -> Dict[str, Any]:
        """
        Run the agent to accomplish a goal.
        
        Args:
            goal: The user's goal/task
        
        Returns:
            Final state dictionary with results
        """
        from aol_fire.workflow import build_fire_graph, create_initial_state
        
        if self._graph is None:
            self._graph = build_fire_graph(self.config)
        
        initial_state = create_initial_state(goal, self.config)
        final_state = self._graph.invoke(initial_state)
        
        return final_state
    
    async def run_async(self, goal: str) -> Dict[str, Any]:
        """Async version of run."""
        from aol_fire.workflow import build_fire_graph, create_initial_state
        
        if self._graph is None:
            self._graph = build_fire_graph(self.config)
        
        initial_state = create_initial_state(goal, self.config)
        final_state = await self._graph.ainvoke(initial_state)
        
        return final_state
    
    def stream(self, goal: str):
        """
        Stream the agent execution for real-time updates.
        
        Yields state updates as the agent progresses.
        """
        from aol_fire.workflow import build_fire_graph, create_initial_state
        
        if self._graph is None:
            self._graph = build_fire_graph(self.config)
        
        initial_state = create_initial_state(goal, self.config)
        
        for event in self._graph.stream(initial_state):
            yield event
    
    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Simple chat interface for quick interactions.
        
        Args:
            message: User message
            context: Optional context dictionary
        
        Returns:
            Agent response
        """
        from aol_fire.llm import create_chat_model
        
        model = create_chat_model(self.config, "fast")
        response = model.invoke(message)
        return response.content
