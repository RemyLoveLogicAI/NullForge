"""
Showcase Runner
===============

Quick showcase script for demonstrations.
"""

import asyncio
from tri_core.demo.interactive import TriCoreDemo


async def run_showcase():
    """Run the complete showcase."""
    demo = TriCoreDemo()
    
    print(demo.print_banner())
    print("\n🚀 Starting Tri-Core Showcase...\n")
    
    results = await demo.run_full_demo("Create a roguelike dungeon crawler")
    
    print("\n📊 Final Statistics:")
    stats = demo.get_stats()
    
    print(f"  • Events published: {stats['event_bus']['events_published']}")
    print(f"  • State entries: {stats['state_sync']['total_entries']}")
    print(f"  • Tasks completed: {stats['orchestrator']['tasks_completed']}")
    print(f"  • Game players: {stats['game_engine']['players']}")
    
    print("\n✅ Showcase complete!")
    
    return results


def main():
    """Main entry point."""
    asyncio.run(run_showcase())


if __name__ == "__main__":
    main()
