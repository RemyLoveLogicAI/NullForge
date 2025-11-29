#!/usr/bin/env python3
"""
NullForge - Autonomous Enterprise Software Platform

A powerful AI agent for autonomous software synthesis, auditing, and deployment.

Usage:
    nullforge new <project>                    Initialize a new project
    nullforge synthesize "Build a REST API"    Generate code from natural language
    nullforge audit                            Run comprehensive code analysis
    nullforge deploy --docker                  Deploy to container
    nullforge chat                             Interactive mode
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from aol_fire.core import FireConfig, FireAgent, build_config, FIRE_PRESETS
from aol_fire.models import TaskStatus

console = Console()

# =============================================================================
# CLI Group
# =============================================================================

@click.group()
@click.version_option(version="2.0.0", prog_name="NullForge")
@click.pass_context
def cli(ctx):
    """
    🔥 NullForge - Autonomous Enterprise Software Platform
    
    Forge enterprise-grade software from natural language.
    Supports multiple LLM backends including Venice AI for uncensored operation.
    
    \b
    Examples:
        nullforge new my_api
        nullforge synthesize "Build a REST API with JWT auth"
        nullforge audit
        nullforge deploy --docker
    """
    ctx.ensure_object(dict)


# =============================================================================
# New Command
# =============================================================================

@cli.command()
@click.argument("project_name")
@click.option("--template", "-t", type=click.Choice(["api", "webapp", "cli", "library"]), default=None)
@click.option("--lang", "-l", type=click.Choice(["python", "rust", "typescript", "go"]), default="python")
@click.option("--no-git", is_flag=True, help="Skip git initialization")
@click.pass_context
def new(ctx, project_name: str, template: Optional[str], lang: str, no_git: bool):
    """
    Initialize a new NullForge project.
    
    Creates project directory with configuration and structure.
    """
    console.print(Panel(
        f"[bold cyan]Creating project:[/bold cyan] {project_name}",
        title="🔥 NullForge",
        border_style="cyan"
    ))
    
    project_path = Path.cwd() / project_name
    
    if project_path.exists():
        console.print(f"[red]Error:[/red] Directory already exists: {project_name}")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing project...", total=None)
        
        # Create directory structure
        project_path.mkdir(parents=True)
        (project_path / "src").mkdir()
        (project_path / "tests").mkdir()
        (project_path / "docs").mkdir()
        
        progress.update(task, description="Creating configuration...")
        
        # Create nullforge.yaml
        config_content = f"""# NullForge Project Configuration
project:
  name: {project_name}
  version: "0.1.0"
  language: {lang}

agent:
  max_iterations: 100
  enable_self_correction: true
  enable_code_review: true

security:
  enable_sandboxing: true
  allow_shell: true
  allow_network: true
"""
        (project_path / "nullforge.yaml").write_text(config_content)
        
        # Create .env template
        env_content = """# NullForge Environment Configuration
# FIRE_LLM_PROVIDER=venice
# VENICE_API_KEY=your-key-here
# FIRE_ORCHESTRATOR_MODEL=llama-3.1-405b
"""
        (project_path / ".env").write_text(env_content)
        
        # Create .gitignore
        gitignore_content = """# NullForge
.env
*.log
.nullforge/

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Node
node_modules/

# Build
dist/
build/
target/

# IDE
.idea/
.vscode/
*.swp
"""
        (project_path / ".gitignore").write_text(gitignore_content)
        
        # Create README
        readme_content = f"""# {project_name}

Created with [NullForge](https://nullforge.io) 🔥

## Getting Started

```bash
cd {project_name}
nullforge synthesize "Your project description"
```

## Development

```bash
nullforge audit     # Run code analysis
nullforge deploy    # Deploy to container
```
"""
        (project_path / "README.md").write_text(readme_content)
        
        # Initialize git
        if not no_git:
            progress.update(task, description="Initializing git...")
            import subprocess
            subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit from NullForge"], cwd=project_path, capture_output=True)
    
    console.print()
    console.print("[green]✓[/green] Project created successfully!")
    console.print()
    
    # Show structure
    tree = Tree(f"📁 {project_name}/")
    tree.add("📁 src/")
    tree.add("📁 tests/")
    tree.add("📁 docs/")
    tree.add("📄 nullforge.yaml")
    tree.add("📄 .env")
    tree.add("📄 .gitignore")
    tree.add("📄 README.md")
    console.print(tree)
    
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  cd {project_name}")
    console.print('  nullforge synthesize "Your project description"')


# =============================================================================
# Synthesize Command
# =============================================================================

@cli.command()
@click.argument("task")
@click.option("--provider", "-p", type=click.Choice(list(FIRE_PRESETS.keys())), default=None)
@click.option("--model", "-m", default=None, help="Model to use")
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory")
@click.option("--dry-run", is_flag=True, help="Show plan without executing")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def synthesize(ctx, task: str, provider: Optional[str], model: Optional[str], output: str, dry_run: bool, verbose: bool):
    """
    Generate code from natural language description.
    
    The agent will:
    1. Analyze your requirements
    2. Create an execution plan
    3. Generate code and files
    4. Run tests and validation
    """
    console.print(Panel(
        f"[bold cyan]Task:[/bold cyan] {task}",
        title="🔥 NullForge Synthesizer",
        border_style="cyan"
    ))
    console.print()
    
    # Build config
    cli_args = {"workspace_dir": Path(output), "verbose": verbose}
    if model:
        cli_args["orchestrator_model"] = model
        cli_args["planner_model"] = model
        cli_args["coder_model"] = model
    
    try:
        config = build_config(preset=provider, cli_args=cli_args)
    except Exception as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        sys.exit(1)
    
    # Check API key
    if not config.get_api_key() and config.llm_provider not in ("ollama",):
        console.print("[red]Error:[/red] No API key configured.")
        console.print("Set via environment variable or .env file:")
        console.print("  export VENICE_API_KEY=your-key")
        console.print("  export OPENAI_API_KEY=your-key")
        sys.exit(1)
    
    if dry_run:
        console.print("[yellow]Dry run mode - showing plan only[/yellow]")
        console.print()
        # Would show plan here
        return
    
    # Run agent
    try:
        agent = FireAgent(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            prog_task = progress.add_task("Initializing...", total=None)
            
            for event in agent.stream(task):
                if "planner" in event:
                    progress.update(prog_task, description="📋 Creating execution plan...")
                elif "executor" in event:
                    state = event.get("executor", {})
                    plan = state.get("plan")
                    if plan and plan.current_task:
                        progress.update(prog_task, description=f"⚡ {plan.current_task.title[:50]}...")
                elif "reporter" in event:
                    progress.update(prog_task, description="📝 Generating summary...")
        
        # Get final state
        final_state = agent.run(task)
        
        # Display results
        console.print()
        if final_state.get("final_output"):
            console.print(Panel(
                Markdown(final_state["final_output"]),
                title="✅ Synthesis Complete",
                border_style="green"
            ))
        
        if final_state.get("error"):
            console.print(Panel(
                final_state["error"],
                title="❌ Error",
                border_style="red"
            ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


# =============================================================================
# Audit Command  
# =============================================================================

@cli.command()
@click.option("--path", "-p", type=click.Path(exists=True), default=".")
@click.option("--fix", is_flag=True, help="Auto-fix correctable issues")
@click.option("--security-only", is_flag=True, help="Run only security checks")
@click.pass_context
def audit(ctx, path: str, fix: bool, security_only: bool):
    """
    Run comprehensive code analysis and compliance checks.
    
    Analyzes:
    - Code quality and complexity
    - Security vulnerabilities
    - Test coverage
    - Documentation completeness
    """
    from aol_fire.tools.code_tools import AnalyzeCodeTool
    from aol_fire.tools.project_tools import AnalyzeProjectTool
    
    console.print(Panel(
        f"[bold cyan]Auditing:[/bold cyan] {path}",
        title="🔍 NullForge Audit",
        border_style="cyan"
    ))
    console.print()
    
    workspace = Path(path)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing project...", total=None)
        
        # Project analysis
        project_tool = AnalyzeProjectTool(workspace_dir=workspace)
        project_result = project_tool._run(path=".")
        
        progress.update(task, description="Analyzing code quality...")
        
        # Code analysis
        code_tool = AnalyzeCodeTool(workspace_dir=workspace)
        code_result = code_tool._run(path=".")
    
    console.print()
    console.print(Panel(
        project_result,
        title="📊 Project Analysis",
        border_style="blue"
    ))
    
    console.print()
    console.print(Panel(
        code_result,
        title="🔬 Code Analysis",
        border_style="blue"
    ))


# =============================================================================
# Deploy Command
# =============================================================================

@cli.command()
@click.option("--docker", "target", flag_value="docker", help="Deploy as Docker container")
@click.option("--k8s", "target", flag_value="k8s", help="Deploy to Kubernetes")
@click.option("--dry-run", is_flag=True, help="Generate manifests without applying")
@click.pass_context
def deploy(ctx, target: Optional[str], dry_run: bool):
    """
    Deploy the project to container or cluster.
    """
    if not target:
        target = "docker"
    
    console.print(Panel(
        f"[bold cyan]Deploying to:[/bold cyan] {target}",
        title="🚀 NullForge Deploy",
        border_style="cyan"
    ))
    console.print()
    
    if dry_run:
        console.print("[yellow]Dry run - generating manifests only[/yellow]")
    
    # Would implement actual deployment here
    console.print("[yellow]Deployment feature coming soon![/yellow]")
    console.print()
    console.print("For now, use the synthesizer:")
    console.print('  nullforge synthesize "Generate Dockerfile and docker-compose.yml"')


# =============================================================================
# Chat Command
# =============================================================================

@cli.command()
@click.option("--provider", "-p", type=click.Choice(list(FIRE_PRESETS.keys())), default=None)
@click.pass_context
def chat(ctx, provider: Optional[str]):
    """
    Start an interactive chat session.
    
    Enter goals and commands interactively with memory.
    """
    console.print(Panel(
        "[bold cyan]NullForge Interactive Mode[/bold cyan]\n\n"
        "Enter your goals and watch the AI work.\n"
        "Type 'exit' to quit, 'help' for commands.",
        title="🔥 NullForge Chat",
        border_style="cyan"
    ))
    console.print()
    
    config = build_config(preset=provider)
    
    while True:
        try:
            user_input = console.input("[bold cyan]nullforge>[/bold cyan] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() == "help":
                console.print("""
[bold]Commands:[/bold]
  exit, quit     Exit chat mode
  help           Show this help
  clear          Clear screen
  status         Show current status
  
Or enter any task to execute it.
""")
                continue
            
            if user_input.lower() == "clear":
                console.clear()
                continue
            
            # Execute task
            console.print()
            console.print(f"[dim]Processing: {user_input}[/dim]")
            console.print()
            
            # Would run agent here
            console.print("[yellow]Full chat mode coming soon![/yellow]")
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except EOFError:
            break


# =============================================================================
# Config Command
# =============================================================================

@cli.command()
@click.option("--show", is_flag=True, help="Show current configuration")
@click.option("--list-presets", is_flag=True, help="List available presets")
@click.pass_context
def config(ctx, show: bool, list_presets: bool):
    """
    View or modify NullForge configuration.
    """
    if list_presets:
        table = Table(title="🔥 Available Presets", border_style="cyan")
        table.add_column("Preset", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Orchestrator Model", style="yellow")
        
        for name, preset in FIRE_PRESETS.items():
            table.add_row(
                name,
                preset.get("llm_provider", ""),
                preset.get("orchestrator_model", "")[:40]
            )
        
        console.print(table)
        return
    
    if show or not (list_presets):
        config = build_config()
        
        table = Table(title="🔧 Current Configuration", show_header=False, border_style="cyan")
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
        
        console.print(table)


# =============================================================================
# Doctor Command
# =============================================================================

@cli.command()
@click.pass_context
def doctor(ctx):
    """
    Run system diagnostics.
    """
    console.print(Panel(
        "[bold]System Diagnostics[/bold]",
        title="🏥 NullForge Doctor",
        border_style="cyan"
    ))
    console.print()
    
    checks = []
    
    # Python version
    import sys
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    checks.append(("Python", py_version, py_ok))
    
    # Git
    import subprocess
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        git_version = result.stdout.strip().replace("git version ", "")
        checks.append(("Git", git_version, True))
    except:
        checks.append(("Git", "Not found", False))
    
    # Docker
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        docker_version = result.stdout.strip().split(",")[0].replace("Docker version ", "")
        checks.append(("Docker", docker_version, True))
    except:
        checks.append(("Docker", "Not found", False))
    
    # API Key
    config = build_config()
    api_key = config.get_api_key()
    if api_key:
        checks.append(("API Key", f"Configured ({config.llm_provider})", True))
    else:
        checks.append(("API Key", "Not configured", False))
    
    # Display results
    all_ok = True
    for name, value, ok in checks:
        icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  {icon} {name}: {value}")
        if not ok:
            all_ok = False
    
    console.print()
    if all_ok:
        console.print("[green]All systems operational.[/green]")
    else:
        console.print("[yellow]Some checks failed. Review the issues above.[/yellow]")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
