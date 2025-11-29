#!/usr/bin/env python3
"""
AOL-CLI Fire Edition 🔥
=======================

The Ultimate AI Coding Agent Command Line Interface.

Usage:
    fire run "Build a full-stack app"
    fire chat
    fire analyze ./project
    fire config --preset venice
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from aol_fire.core import FireConfig, build_config, FIRE_PRESETS
from aol_fire.tui import (
    console,
    print_banner,
    print_plan,
    print_task_progress,
    print_result,
    print_error,
    create_progress_display,
)
from aol_fire.tui.display import print_final_summary


# =============================================================================
# CLI Group
# =============================================================================

@click.group()
@click.version_option(version="2.0.0", prog_name="aol-cli-fire")
@click.pass_context
def cli(ctx):
    """
    🔥 AOL-CLI Fire Edition - The Ultimate AI Coding Agent 🔥
    
    A powerful, multi-agent CLI for executing complex programming
    and automation tasks using customizable LLM backends.
    
    \b
    Examples:
        fire run "Create a REST API with FastAPI"
        fire run "Build a React todo app" --preset venice
        fire chat --provider ollama
        fire analyze ./my-project
    """
    ctx.ensure_object(dict)


# =============================================================================
# Run Command
# =============================================================================

@cli.command()
@click.argument("goal", required=True)
@click.option(
    "--provider", "-p",
    type=click.Choice(["openai", "venice", "ollama", "groq", "together", "openrouter", "anthropic", "custom"]),
    default=None,
    help="LLM provider"
)
@click.option(
    "--preset",
    type=click.Choice(list(FIRE_PRESETS.keys())),
    default=None,
    help="Use a provider preset"
)
@click.option(
    "--model", "-m",
    default=None,
    help="Model name (overrides preset)"
)
@click.option(
    "--api-key", "-k",
    default=None,
    help="API key"
)
@click.option(
    "--workspace", "-w",
    type=click.Path(path_type=Path),
    default=None,
    help="Working directory"
)
@click.option(
    "--max-iterations", "-i",
    type=int,
    default=None,
    help="Maximum iterations"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Verbose output"
)
@click.option(
    "--debug", "-d",
    is_flag=True,
    default=False,
    help="Debug mode"
)
@click.option(
    "--no-review",
    is_flag=True,
    default=False,
    help="Disable code review"
)
@click.option(
    "--stream",
    is_flag=True,
    default=False,
    help="Stream output"
)
@click.pass_context
def run(
    ctx,
    goal: str,
    provider: Optional[str],
    preset: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
    workspace: Optional[Path],
    max_iterations: Optional[int],
    verbose: bool,
    debug: bool,
    no_review: bool,
    stream: bool,
):
    """
    🚀 Execute an AI agent to accomplish the specified GOAL.
    
    The agent will analyze your goal, create a plan, and execute
    it step by step using available tools.
    
    \b
    Examples:
        fire run "Create a Python CLI for task management"
        fire run "Build a REST API" --preset venice
        fire run "Add tests to utils.py" --workspace ./project
    """
    
    # Build configuration
    cli_args = {}
    
    if preset:
        from aol_fire.core import get_preset
        cli_args.update(get_preset(preset))
    
    if provider:
        cli_args["llm_provider"] = provider
    if model:
        cli_args["orchestrator_model"] = model
        cli_args["planner_model"] = model
        cli_args["coder_model"] = model
    if api_key:
        from pydantic import SecretStr
        cli_args["api_key"] = SecretStr(api_key)
    if workspace:
        cli_args["workspace_dir"] = workspace
    if max_iterations:
        cli_args["max_iterations"] = max_iterations
    if verbose:
        cli_args["verbose"] = True
    if debug:
        cli_args["debug"] = True
    if no_review:
        cli_args["enable_code_review"] = False
    
    try:
        config = build_config(cli_args=cli_args)
    except Exception as e:
        print_error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Validate API key
    if not config.get_api_key() and config.llm_provider != "ollama":
        print_error("No API key provided. Set via --api-key or environment variable.")
        console.print("[dim]Example: export OPENAI_API_KEY=your-key[/dim]")
        sys.exit(1)
    
    # Print banner
    print_banner()
    
    # Show goal
    console.print(Panel(
        f"[bold cyan]Goal:[/bold cyan] {goal}",
        title="🎯 Mission",
        border_style="cyan",
    ))
    console.print()
    
    # Run the agent
    try:
        if stream:
            run_with_streaming(goal, config)
        else:
            run_with_progress(goal, config)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        print_error(str(e))
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def run_with_progress(goal: str, config: FireConfig):
    """Run agent with progress display."""
    from aol_fire.workflow import build_fire_graph, create_initial_state
    
    with create_progress_display() as progress:
        task = progress.add_task("[cyan]Starting agent...", total=None)
        
        # Build graph
        graph = build_fire_graph(config)
        initial_state = create_initial_state(goal, config)
        
        # Stream through graph
        for event in graph.stream(initial_state):
            if "planner" in event:
                progress.update(task, description="[cyan]📋 Creating plan...")
                state = event["planner"]
                if state.get("plan"):
                    progress.stop()
                    print_plan(state["plan"])
                    progress.start()
            
            elif "executor" in event:
                state = event["executor"]
                plan = state.get("plan")
                if plan:
                    completed = len(plan.completed_tasks)
                    total = len(plan.tasks)
                    current = plan.current_task
                    if current:
                        progress.update(
                            task,
                            description=f"[yellow]⚡ ({completed}/{total}) {current.title[:40]}..."
                        )
            
            elif "reviewer" in event:
                progress.update(task, description="[blue]🔍 Reviewing...")
            
            elif "reporter" in event:
                progress.update(task, description="[green]📝 Generating report...")
        
        # Get final state
        final_state = graph.invoke(initial_state)
    
    # Display results
    print_final_summary(final_state)


def run_with_streaming(goal: str, config: FireConfig):
    """Run agent with streaming output."""
    from aol_fire.workflow import build_fire_graph, create_initial_state
    
    graph = build_fire_graph(config)
    initial_state = create_initial_state(goal, config)
    
    console.print("[cyan]🚀 Starting agent...[/cyan]\n")
    
    for event in graph.stream(initial_state):
        if "planner" in event:
            state = event["planner"]
            if state.get("plan"):
                print_plan(state["plan"])
        
        elif "executor" in event:
            state = event["executor"]
            plan = state.get("plan")
            if plan:
                for task in plan.tasks:
                    if task.status.value == "completed" and not hasattr(task, '_printed'):
                        print_task_progress(task, task.output[:100] if task.output else "")
                        task._printed = True
    
    # Get final state
    final_state = graph.invoke(initial_state)
    print_final_summary(final_state)


# =============================================================================
# Chat Command
# =============================================================================

@cli.command()
@click.option(
    "--provider", "-p",
    type=click.Choice(["openai", "venice", "ollama", "groq", "together", "openrouter", "anthropic", "custom"]),
    default=None,
)
@click.option("--preset", type=click.Choice(list(FIRE_PRESETS.keys())), default=None)
@click.option("--workspace", "-w", type=click.Path(path_type=Path), default=None)
@click.pass_context
def chat(ctx, provider, preset, workspace):
    """
    💬 Start an interactive chat session with the AI agent.
    
    Enter goals interactively and get results in real-time.
    Type 'exit' to quit, 'help' for commands.
    """
    
    cli_args = {}
    if preset:
        from aol_fire.core import get_preset
        cli_args.update(get_preset(preset))
    if provider:
        cli_args["llm_provider"] = provider
    if workspace:
        cli_args["workspace_dir"] = workspace
    
    config = build_config(cli_args=cli_args)
    
    print_banner()
    console.print("[bold cyan]Interactive Mode[/bold cyan]")
    console.print("[dim]Type your goals and watch the AI work. Type 'exit' to quit.[/dim]\n")
    
    while True:
        try:
            user_input = console.input("[bold cyan]fire>[/bold cyan] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[yellow]👋 Goodbye![/yellow]")
                break
            
            if user_input.lower() == "help":
                console.print("""
[bold]Available Commands:[/bold]
  exit, quit, q    Exit interactive mode
  help             Show this help
  config           Show current configuration
  clear            Clear screen
  
Or type any goal to execute it.
""")
                continue
            
            if user_input.lower() == "config":
                display_config(config)
                continue
            
            if user_input.lower() == "clear":
                console.clear()
                print_banner()
                continue
            
            # Execute the goal
            run_with_streaming(user_input, config)
            console.print()
        
        except KeyboardInterrupt:
            console.print("\n[dim]Use 'exit' to quit[/dim]")
        except EOFError:
            break


# =============================================================================
# Analyze Command
# =============================================================================

@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--deep", is_flag=True, help="Perform deep analysis")
@click.pass_context
def analyze(ctx, path: Path, deep: bool):
    """
    🔍 Analyze a project structure and technologies.
    
    Detects languages, frameworks, dependencies, and project structure.
    """
    
    from aol_fire.tools.project_tools import AnalyzeProjectTool
    
    print_banner()
    
    console.print(f"[cyan]Analyzing project: {path}[/cyan]\n")
    
    tool = AnalyzeProjectTool(workspace_dir=path.parent if path.is_file() else path)
    result = tool._run(str(path), deep=deep)
    
    console.print(result)


# =============================================================================
# Config Command
# =============================================================================

@cli.command()
@click.option("--preset", type=click.Choice(list(FIRE_PRESETS.keys())), help="Show preset config")
@click.option("--list-presets", is_flag=True, help="List available presets")
@click.option("--show", is_flag=True, help="Show current config")
@click.pass_context
def config(ctx, preset, list_presets, show):
    """
    ⚙️  View and manage configuration.
    """
    
    if list_presets:
        from rich.table import Table
        
        table = Table(title="🔥 Available Presets", border_style="cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Models")
        
        for name, preset_config in FIRE_PRESETS.items():
            models = f"{preset_config.get('orchestrator_model', 'default')}"
            table.add_row(
                name,
                preset_config.get("llm_provider", ""),
                models[:40] + "..." if len(models) > 40 else models
            )
        
        console.print(table)
        return
    
    if preset:
        from aol_fire.core import get_preset
        preset_config = get_preset(preset)
        console.print(Panel(
            "\n".join(f"[cyan]{k}:[/cyan] {v}" for k, v in preset_config.items()),
            title=f"[bold]Preset: {preset}[/bold]",
            border_style="cyan",
        ))
        return
    
    # Show current config
    current_config = build_config()
    display_config(current_config)


def display_config(config: FireConfig):
    """Display configuration."""
    from rich.table import Table
    
    table = Table(title="⚙️  Current Configuration", show_header=False, border_style="dim")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Provider", config.llm_provider)
    table.add_row("API Base", config.get_api_base())
    table.add_row("Orchestrator Model", config.orchestrator_model)
    table.add_row("Coder Model", config.coder_model)
    table.add_row("Workspace", str(config.workspace_dir))
    table.add_row("Max Iterations", str(config.max_iterations))
    table.add_row("Shell Commands", "✓" if config.allow_shell_commands else "✗")
    table.add_row("File Writes", "✓" if config.allow_file_writes else "✗")
    table.add_row("Web Search", "✓" if config.allow_web_search else "✗")
    table.add_row("Code Review", "✓" if config.enable_code_review else "✗")
    
    console.print(table)


# =============================================================================
# Init Command
# =============================================================================

@cli.command()
@click.option("--workspace", "-w", type=click.Path(path_type=Path), default=Path.cwd())
@click.pass_context
def init(ctx, workspace: Path):
    """
    🎯 Initialize a new Fire workspace.
    """
    
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Create .env template
    env_file = workspace / ".env"
    if not env_file.exists():
        env_content = """# AOL-CLI Fire Edition Configuration
# ====================================

# Provider: openai, venice, ollama, groq, together, openrouter, anthropic, custom
# FIRE_LLM_PROVIDER=openai

# API Keys (uncomment and fill in)
# OPENAI_API_KEY=sk-...
# VENICE_API_KEY=...
# GROQ_API_KEY=...
# TOGETHER_API_KEY=...
# OPENROUTER_API_KEY=...

# Models
# FIRE_ORCHESTRATOR_MODEL=gpt-4-turbo-preview
# FIRE_CODER_MODEL=gpt-4-turbo-preview

# Behavior
# FIRE_MAX_ITERATIONS=100
# FIRE_ENABLE_CODE_REVIEW=true
# FIRE_VERBOSE=false
"""
        env_file.write_text(env_content)
        console.print(f"[green]✓[/green] Created {env_file}")
    
    # Create .gitignore
    gitignore = workspace / ".gitignore"
    if not gitignore.exists():
        gitignore_content = """.env
*.log
__pycache__/
.venv/
node_modules/
"""
        gitignore.write_text(gitignore_content)
        console.print(f"[green]✓[/green] Created {gitignore}")
    
    console.print()
    console.print("[bold green]🔥 Workspace initialized![/bold green]")
    console.print()
    console.print("Next steps:")
    console.print("  1. Edit [cyan].env[/cyan] with your API keys")
    console.print("  2. Run: [cyan]fire run \"Your goal here\"[/cyan]")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
