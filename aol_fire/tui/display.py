"""
Rich display components for AOL-CLI Fire Edition.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree
from rich.live import Live
from rich.layout import Layout

from aol_fire.models import Plan, Task, TaskStatus


# Global console instance
console = Console()


# =============================================================================
# Banner and Branding
# =============================================================================

FIRE_BANNER = """
[bold red]     █████╗  ██████╗ ██╗          ██████╗██╗     ██╗[/bold red]
[bold orange1]    ██╔══██╗██╔═══██╗██║         ██╔════╝██║     ██║[/bold orange1]
[bold yellow]    ███████║██║   ██║██║         ██║     ██║     ██║[/bold yellow]
[bold orange1]    ██╔══██║██║   ██║██║         ██║     ██║     ██║[/bold orange1]
[bold red]    ██║  ██║╚██████╔╝███████╗    ╚██████╗███████╗██║[/bold red]
[dim]    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝     ╚═════╝╚══════╝╚═╝[/dim]
                                                  
[bold cyan]           🔥 FIRE EDITION 🔥[/bold cyan]
[dim]        The Ultimate AI Coding Agent[/dim]
"""


def print_banner():
    """Print the Fire Edition banner."""
    console.print(FIRE_BANNER)


def print_header(text: str, style: str = "bold cyan"):
    """Print a section header."""
    console.print()
    console.print(f"[{style}]{'═' * 60}[/{style}]")
    console.print(f"[{style}]  {text}[/{style}]")
    console.print(f"[{style}]{'═' * 60}[/{style}]")
    console.print()


# =============================================================================
# Plan Display
# =============================================================================

def print_plan(plan: Plan):
    """Print an execution plan in a nice format."""
    
    # Create table
    table = Table(
        title=f"[bold]Execution Plan[/bold]",
        title_style="bold cyan",
        show_header=True,
        header_style="bold",
        border_style="cyan",
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Task", style="white")
    table.add_column("Priority", width=8)
    table.add_column("Status", width=12)
    
    priority_colors = {
        "critical": "red",
        "high": "yellow",
        "medium": "blue",
        "low": "dim",
    }
    
    status_icons = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.IN_PROGRESS: "🔄",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.BLOCKED: "🚫",
        TaskStatus.CANCELLED: "⛔",
    }
    
    for i, task in enumerate(plan.tasks, 1):
        priority_color = priority_colors.get(task.priority.value, "white")
        status_icon = status_icons.get(task.status, "❓")
        
        table.add_row(
            str(i),
            task.title[:50] + ("..." if len(task.title) > 50 else ""),
            f"[{priority_color}]{task.priority.value}[/{priority_color}]",
            f"{status_icon} {task.status.value}",
        )
    
    console.print(table)
    console.print()


def print_plan_tree(plan: Plan):
    """Print plan as a tree structure."""
    tree = Tree(f"[bold cyan]📋 {plan.goal}[/bold cyan]")
    
    for task in plan.tasks:
        status_icon = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
        }.get(task.status, "❓")
        
        style = "green" if task.status == TaskStatus.COMPLETED else \
                "red" if task.status == TaskStatus.FAILED else \
                "yellow" if task.status == TaskStatus.IN_PROGRESS else "dim"
        
        branch = tree.add(f"[{style}]{status_icon} {task.title}[/{style}]")
        
        if task.subtasks:
            for subtask in task.subtasks:
                branch.add(f"[dim]  └─ {subtask.title}[/dim]")
    
    console.print(tree)


# =============================================================================
# Task Progress
# =============================================================================

def print_task_progress(task: Task, message: str = ""):
    """Print task progress update."""
    status_color = {
        TaskStatus.PENDING: "dim",
        TaskStatus.IN_PROGRESS: "yellow",
        TaskStatus.COMPLETED: "green",
        TaskStatus.FAILED: "red",
    }.get(task.status, "white")
    
    status_icon = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.IN_PROGRESS: "🔄",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
    }.get(task.status, "❓")
    
    console.print(f"[{status_color}]{status_icon} {task.title}[/{status_color}]")
    
    if message:
        console.print(f"   [dim]{message[:100]}[/dim]")


def create_progress_display():
    """Create a rich progress display for long-running operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    )


# =============================================================================
# Results Display
# =============================================================================

def print_result(result: Dict[str, Any], title: str = "Result"):
    """Print execution result."""
    
    panel_content = []
    
    if result.get("success"):
        panel_content.append("[green]✓ Success[/green]")
    else:
        panel_content.append("[red]✗ Failed[/red]")
    
    if result.get("output"):
        output = result["output"]
        if len(output) > 500:
            output = output[:500] + "..."
        panel_content.append(f"\n{output}")
    
    if result.get("error"):
        panel_content.append(f"\n[red]Error: {result['error']}[/red]")
    
    if result.get("file_changes"):
        panel_content.append("\n[bold]Files Changed:[/bold]")
        for fc in result["file_changes"][:10]:
            icon = "📄" if fc.action == "created" else "📝"
            panel_content.append(f"  {icon} {fc.path}")
    
    console.print(Panel(
        "\n".join(panel_content),
        title=f"[bold]{title}[/bold]",
        border_style="cyan",
    ))


def print_final_summary(state: Dict[str, Any]):
    """Print the final execution summary."""
    
    console.print()
    console.print("[bold cyan]═" * 60 + "[/bold cyan]")
    console.print("[bold cyan]  EXECUTION COMPLETE[/bold cyan]")
    console.print("[bold cyan]═" * 60 + "[/bold cyan]")
    console.print()
    
    # Print summary
    if state.get("final_output"):
        console.print(Markdown(state["final_output"]))
    
    # Print metrics
    plan = state.get("plan")
    if plan:
        console.print()
        metrics_table = Table(show_header=False, box=None)
        metrics_table.add_column("Metric", style="dim")
        metrics_table.add_column("Value", style="bold")
        
        metrics_table.add_row("Tasks Completed", f"{len(plan.completed_tasks)}/{len(plan.tasks)}")
        metrics_table.add_row("Success Rate", f"{plan.success_rate:.1f}%")
        metrics_table.add_row("Iterations", str(state.get("iteration", 0)))
        
        file_changes = state.get("file_changes", [])
        if file_changes:
            created = len([f for f in file_changes if f.action == "created"])
            modified = len([f for f in file_changes if f.action == "modified"])
            metrics_table.add_row("Files Created", str(created))
            metrics_table.add_row("Files Modified", str(modified))
        
        console.print(Panel(metrics_table, title="[bold]Metrics[/bold]", border_style="dim"))


# =============================================================================
# Error Display
# =============================================================================

def print_error(error: str, title: str = "Error"):
    """Print an error message."""
    console.print(Panel(
        f"[red]{error}[/red]",
        title=f"[bold red]{title}[/bold red]",
        border_style="red",
    ))


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[yellow]⚠️  {message}[/yellow]")


# =============================================================================
# Code Display
# =============================================================================

def print_code(code: str, language: str = "python", title: Optional[str] = None):
    """Print syntax-highlighted code."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    
    if title:
        console.print(Panel(syntax, title=f"[bold]{title}[/bold]", border_style="dim"))
    else:
        console.print(syntax)


def print_diff(diff: str):
    """Print a git-style diff."""
    lines = []
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(f"[green]{line}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(f"[red]{line}[/red]")
        elif line.startswith("@@"):
            lines.append(f"[cyan]{line}[/cyan]")
        else:
            lines.append(line)
    
    console.print("\n".join(lines))


# =============================================================================
# Interactive Elements
# =============================================================================

def confirm(message: str, default: bool = False) -> bool:
    """Ask for confirmation."""
    default_str = "Y/n" if default else "y/N"
    response = console.input(f"[yellow]{message}[/yellow] [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    return response in ("y", "yes")


def select_option(options: List[str], prompt: str = "Select an option") -> int:
    """Display options and get user selection."""
    console.print(f"\n[bold]{prompt}:[/bold]")
    
    for i, option in enumerate(options, 1):
        console.print(f"  [cyan]{i}.[/cyan] {option}")
    
    while True:
        try:
            choice = int(console.input("\n[dim]Enter number:[/dim] "))
            if 1 <= choice <= len(options):
                return choice - 1
            console.print("[red]Invalid choice[/red]")
        except ValueError:
            console.print("[red]Please enter a number[/red]")
