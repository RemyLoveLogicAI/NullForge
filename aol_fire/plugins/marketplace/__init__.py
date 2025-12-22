"""
NullForge Plugin Marketplace
============================
A comprehensive plugin system for extending NullForge capabilities.

Plugins can add:
- New tools (file operations, API integrations, etc.)
- Custom agents (specialized planners, coders, reviewers)
- Prompt templates
- Output formatters
- Provider integrations
"""

from .registry import PluginRegistry, Plugin, PluginMetadata
from .loader import PluginLoader
from .manager import PluginManager

__all__ = [
    'PluginRegistry',
    'Plugin', 
    'PluginMetadata',
    'PluginLoader',
    'PluginManager'
]
