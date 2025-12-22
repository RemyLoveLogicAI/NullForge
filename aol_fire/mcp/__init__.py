"""
NullForge MCP Server
====================
Model Context Protocol server for integration with Claude Desktop and other MCP clients.

This allows NullForge tools to be used directly from Claude Desktop.
"""

from .server import NullForgeMCPServer, run_server

__all__ = ['NullForgeMCPServer', 'run_server']
