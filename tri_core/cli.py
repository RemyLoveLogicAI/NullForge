"""
Tri-Core CLI
============

Command-line interface for Tri-Core operations.
"""

import asyncio
import click
import logging
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
logging.basicConfig(level=logging.INFO)


@click.group()
def cli():
    """🔱 Tri-Core Integration Architecture CLI"""
    pass


@cli.command()
def demo():
    """Run the interactive demo showcase."""
    from tri_core.demo.interactive import TriCoreDemo
    
    async def run():
        demo = TriCoreDemo()
        console.print(demo.print_banner())
        results = await demo.run_full_demo()
        
        # Show stats
        stats = demo.get_stats()
        table = Table(title="📊 Demo Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Events Published", str(stats["event_bus"]["events_published"]))
        table.add_row("Tasks Completed", str(stats["orchestrator"]["tasks_completed"]))
        table.add_row("Game Players", str(stats["game_engine"]["players"]))
        
        console.print(table)
        return results
    
    asyncio.run(run())


@cli.command()
@click.argument("concept")
def pipeline(concept: str):
    """Run the game development pipeline."""
    from tri_core.demo.interactive import TriCoreDemo
    
    async def run():
        demo = TriCoreDemo()
        await demo.initialize()
        
        console.print(Panel(f"🚀 Starting pipeline for: {concept}", style="green"))
        result = await demo.run_game_development_demo(concept)
        
        console.print(Panel(f"✅ Pipeline completed!", style="green"))
        return result
    
    asyncio.run(run())


@cli.command()
def narrative():
    """Run the narrative demo."""
    from tri_core.demo.interactive import TriCoreDemo
    
    async def run():
        demo = TriCoreDemo()
        await demo.initialize()
        
        console.print(Panel("📖 Starting narrative demo...", style="blue"))
        result = await demo.run_narrative_demo()
        
        console.print(Panel("✅ Narrative demo complete!", style="green"))
        return result
    
    asyncio.run(run())


@cli.command()
def stats():
    """Show Tri-Core statistics."""
    from tri_core.demo.interactive import TriCoreDemo
    
    async def run():
        demo = TriCoreDemo()
        await demo.initialize()
        
        stats = demo.get_stats()
        
        table = Table(title="🔱 Tri-Core Statistics")
        table.add_column("Component", style="cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="green")
        
        # Event Bus
        table.add_row("Event Bus", "Published", str(stats["event_bus"]["events_published"]))
        table.add_row("Event Bus", "Delivered", str(stats["event_bus"]["events_delivered"]))
        
        # State Sync
        table.add_row("State Sync", "Entries", str(stats["state_sync"]["total_entries"]))
        
        # Orchestrator
        table.add_row("Orchestrator", "Tasks", str(stats["orchestrator"]["tasks_completed"]))
        
        # Game Engine
        table.add_row("Game Engine", "Players", str(stats["game_engine"]["players"]))
        
        console.print(table)
    
    asyncio.run(run())


@cli.command()
def version():
    """Show Tri-Core version."""
    from tri_core import __version__
    console.print(f"🔱 Tri-Core Integration Architecture v{__version__}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
