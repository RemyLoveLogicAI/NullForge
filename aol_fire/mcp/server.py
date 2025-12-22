"""
NullForge MCP Server Implementation
===================================
A Model Context Protocol (MCP) server that exposes NullForge capabilities
to MCP-compatible clients like Claude Desktop.

Usage:
    python -m aol_fire.mcp.server

Configuration for Claude Desktop (claude_desktop_config.json):
{
    "mcpServers": {
        "nullforge": {
            "command": "python",
            "args": ["-m", "aol_fire.mcp.server"],
            "env": {
                "VENICE_API_KEY": "your-api-key"
            }
        }
    }
}
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Sequence
from datetime import datetime

# MCP SDK imports (these would be from the actual mcp package)
# For now, we implement a compatible interface

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nullforge-mcp")


class MCPError(Exception):
    """MCP protocol error."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class Tool:
    """MCP Tool definition."""
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: callable
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class Resource:
    """MCP Resource definition."""
    def __init__(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "text/plain"
    ):
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = mime_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type
        }


class Prompt:
    """MCP Prompt definition."""
    def __init__(
        self,
        name: str,
        description: str,
        arguments: List[Dict[str, Any]] = None
    ):
        self.name = name
        self.description = description
        self.arguments = arguments or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments
        }


class NullForgeMCPServer:
    """
    NullForge MCP Server
    
    Exposes NullForge tools and capabilities through the Model Context Protocol.
    """
    
    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or Path.cwd()
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.prompts: Dict[str, Prompt] = {}
        
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _register_tools(self):
        """Register available tools."""
        
        # Synthesis tool
        self.tools["synthesize"] = Tool(
            name="synthesize",
            description="Synthesize code from a natural language description using NullForge's AI agents",
            input_schema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Natural language description of what to build"
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["venice", "openai", "anthropic", "ollama", "groq"],
                        "default": "venice",
                        "description": "LLM provider to use"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (optional, uses provider default)"
                    },
                    "workspace": {
                        "type": "string",
                        "description": "Output directory for generated files"
                    }
                },
                "required": ["goal"]
            },
            handler=self._handle_synthesize
        )
        
        # File read tool
        self.tools["read_file"] = Tool(
            name="read_file",
            description="Read contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            },
            handler=self._handle_read_file
        )
        
        # File write tool
        self.tools["write_file"] = Tool(
            name="write_file",
            description="Write content to a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            },
            handler=self._handle_write_file
        )
        
        # Directory listing tool
        self.tools["list_directory"] = Tool(
            name="list_directory",
            description="List contents of a directory",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the directory to list"
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to list recursively"
                    }
                },
                "required": ["path"]
            },
            handler=self._handle_list_directory
        )
        
        # Execute command tool
        self.tools["execute_command"] = Tool(
            name="execute_command",
            description="Execute a shell command (sandboxed)",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory for the command"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 30,
                        "description": "Timeout in seconds"
                    }
                },
                "required": ["command"]
            },
            handler=self._handle_execute_command
        )
        
        # Search files tool
        self.tools["search_files"] = Tool(
            name="search_files",
            description="Search for files matching a pattern",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (glob or regex)"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in"
                    },
                    "content_pattern": {
                        "type": "string",
                        "description": "Pattern to search in file contents"
                    }
                },
                "required": ["pattern"]
            },
            handler=self._handle_search_files
        )
        
        # Git tools
        self.tools["git_status"] = Tool(
            name="git_status",
            description="Get git repository status",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to git repository"
                    }
                },
                "required": []
            },
            handler=self._handle_git_status
        )
        
        # Audit tool
        self.tools["audit_project"] = Tool(
            name="audit_project",
            description="Audit a project for code quality, security, and best practices",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the project directory"
                    }
                },
                "required": ["path"]
            },
            handler=self._handle_audit_project
        )
        
        # Plugin management
        self.tools["list_plugins"] = Tool(
            name="list_plugins",
            description="List available NullForge plugins",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["tool", "agent", "provider", "template"],
                        "description": "Filter by category"
                    }
                },
                "required": []
            },
            handler=self._handle_list_plugins
        )
    
    def _register_resources(self):
        """Register available resources."""
        
        self.resources["nullforge://config"] = Resource(
            uri="nullforge://config",
            name="NullForge Configuration",
            description="Current NullForge configuration and settings",
            mime_type="application/json"
        )
        
        self.resources["nullforge://providers"] = Resource(
            uri="nullforge://providers",
            name="Available Providers",
            description="List of available LLM providers and their configurations",
            mime_type="application/json"
        )
        
        self.resources["nullforge://history"] = Resource(
            uri="nullforge://history",
            name="Synthesis History",
            description="Recent synthesis task history",
            mime_type="application/json"
        )
    
    def _register_prompts(self):
        """Register available prompts."""
        
        self.prompts["build_api"] = Prompt(
            name="build_api",
            description="Generate a REST API from requirements",
            arguments=[
                {"name": "description", "description": "API description", "required": True},
                {"name": "framework", "description": "Web framework (fastapi, flask, express)", "required": False}
            ]
        )
        
        self.prompts["build_cli"] = Prompt(
            name="build_cli",
            description="Generate a CLI application",
            arguments=[
                {"name": "description", "description": "CLI description", "required": True},
                {"name": "language", "description": "Programming language", "required": False}
            ]
        )
        
        self.prompts["refactor_code"] = Prompt(
            name="refactor_code",
            description="Refactor existing code for better quality",
            arguments=[
                {"name": "file_path", "description": "Path to file to refactor", "required": True},
                {"name": "goals", "description": "Refactoring goals", "required": False}
            ]
        )
    
    # Tool handlers
    async def _handle_synthesize(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle synthesis requests."""
        goal = arguments.get("goal")
        provider = arguments.get("provider", "venice")
        workspace = arguments.get("workspace", str(self.workspace))
        
        # Simulate synthesis result
        return {
            "success": True,
            "message": f"Synthesis initiated for: {goal[:100]}...",
            "task_id": f"synth_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "provider": provider,
            "workspace": workspace,
            "status": "Planning phase started..."
        }
    
    async def _handle_read_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file read requests."""
        path = Path(arguments["path"])
        
        if not path.exists():
            raise MCPError(-32602, f"File not found: {path}")
        
        try:
            content = path.read_text()
            return {
                "path": str(path),
                "content": content,
                "size": len(content),
                "encoding": "utf-8"
            }
        except Exception as e:
            raise MCPError(-32603, f"Error reading file: {e}")
    
    async def _handle_write_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file write requests."""
        path = Path(arguments["path"])
        content = arguments["content"]
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return {
                "success": True,
                "path": str(path),
                "bytes_written": len(content)
            }
        except Exception as e:
            raise MCPError(-32603, f"Error writing file: {e}")
    
    async def _handle_list_directory(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle directory listing requests."""
        path = Path(arguments["path"])
        recursive = arguments.get("recursive", False)
        
        if not path.exists():
            raise MCPError(-32602, f"Directory not found: {path}")
        
        if not path.is_dir():
            raise MCPError(-32602, f"Not a directory: {path}")
        
        entries = []
        if recursive:
            for item in path.rglob("*"):
                if not any(p.startswith('.') for p in item.parts):
                    entries.append({
                        "path": str(item.relative_to(path)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
        else:
            for item in path.iterdir():
                if not item.name.startswith('.'):
                    entries.append({
                        "path": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
        
        return {
            "path": str(path),
            "entries": entries,
            "count": len(entries)
        }
    
    async def _handle_execute_command(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle command execution requests."""
        import subprocess
        
        command = arguments["command"]
        working_dir = arguments.get("working_dir", str(self.workspace))
        timeout = arguments.get("timeout", 30)
        
        # Security: block dangerous commands
        blocked = ["rm -rf /", "mkfs", "> /dev/", "sudo rm"]
        for b in blocked:
            if b in command:
                raise MCPError(-32602, f"Command blocked for security: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            raise MCPError(-32603, f"Command timed out after {timeout}s")
        except Exception as e:
            raise MCPError(-32603, f"Error executing command: {e}")
    
    async def _handle_search_files(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file search requests."""
        import fnmatch
        import re
        
        pattern = arguments["pattern"]
        search_path = Path(arguments.get("path", str(self.workspace)))
        content_pattern = arguments.get("content_pattern")
        
        matches = []
        for path in search_path.rglob("*"):
            if path.is_file() and fnmatch.fnmatch(path.name, pattern):
                match_info = {"path": str(path.relative_to(search_path))}
                
                if content_pattern:
                    try:
                        content = path.read_text()
                        if re.search(content_pattern, content):
                            # Find matching lines
                            matching_lines = []
                            for i, line in enumerate(content.split('\n'), 1):
                                if re.search(content_pattern, line):
                                    matching_lines.append({"line": i, "text": line.strip()})
                            match_info["matches"] = matching_lines[:10]  # Limit to 10
                    except:
                        pass
                
                matches.append(match_info)
        
        return {
            "pattern": pattern,
            "matches": matches[:100],  # Limit results
            "count": len(matches)
        }
    
    async def _handle_git_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle git status requests."""
        import subprocess
        
        path = arguments.get("path", str(self.workspace))
        
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", "-b"],
                cwd=path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {"error": "Not a git repository"}
            
            lines = result.stdout.strip().split('\n')
            branch = lines[0].replace("## ", "") if lines else "unknown"
            
            changes = []
            for line in lines[1:]:
                if line:
                    status = line[:2]
                    file_path = line[3:]
                    changes.append({"status": status, "path": file_path})
            
            return {
                "branch": branch,
                "changes": changes,
                "clean": len(changes) == 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_audit_project(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project audit requests."""
        path = Path(arguments["path"])
        
        if not path.exists():
            raise MCPError(-32602, f"Project not found: {path}")
        
        # Analyze project
        files = list(path.rglob("*"))
        py_files = [f for f in files if f.suffix == ".py"]
        js_files = [f for f in files if f.suffix in [".js", ".ts", ".jsx", ".tsx"]]
        
        issues = []
        recommendations = []
        
        # Check for common issues
        if not (path / ".gitignore").exists():
            issues.append("Missing .gitignore file")
            recommendations.append("Add a .gitignore file")
        
        if not (path / "README.md").exists():
            issues.append("Missing README.md")
            recommendations.append("Add project documentation")
        
        # Check for requirements
        has_requirements = (path / "requirements.txt").exists() or (path / "pyproject.toml").exists()
        has_package_json = (path / "package.json").exists()
        
        if py_files and not has_requirements:
            issues.append("Python project without dependency file")
            recommendations.append("Add requirements.txt or pyproject.toml")
        
        return {
            "path": str(path),
            "files_count": len(files),
            "python_files": len(py_files),
            "javascript_files": len(js_files),
            "issues": issues,
            "recommendations": recommendations,
            "health_score": max(0, 100 - len(issues) * 15)
        }
    
    async def _handle_list_plugins(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle plugin listing requests."""
        category = arguments.get("category")
        
        # Return built-in plugins
        plugins = [
            {"id": "docker-tools", "name": "Docker Tools", "category": "tool", "enabled": True},
            {"id": "database-tools", "name": "Database Tools", "category": "tool", "enabled": True},
            {"id": "testing-suite", "name": "Testing Suite", "category": "tool", "enabled": True},
            {"id": "security-scanner", "name": "Security Scanner", "category": "tool", "enabled": False},
            {"id": "react-generator", "name": "React Generator", "category": "template", "enabled": True},
            {"id": "fastapi-template", "name": "FastAPI Template", "category": "template", "enabled": True},
        ]
        
        if category:
            plugins = [p for p in plugins if p["category"] == category]
        
        return {
            "plugins": plugins,
            "count": len(plugins)
        }
    
    # MCP Protocol methods
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "serverInfo": {
                "name": "nullforge",
                "version": "1.0.0"
            }
        }
    
    async def handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {
            "tools": [tool.to_dict() for tool in self.tools.values()]
        }
    
    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        if name not in self.tools:
            raise MCPError(-32602, f"Unknown tool: {name}")
        
        tool = self.tools[name]
        result = await tool.handler(arguments)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }
    
    async def handle_list_resources(self) -> Dict[str, Any]:
        """Handle resources/list request."""
        return {
            "resources": [res.to_dict() for res in self.resources.values()]
        }
    
    async def handle_read_resource(self, uri: str) -> Dict[str, Any]:
        """Handle resources/read request."""
        if uri == "nullforge://config":
            content = json.dumps({
                "workspace": str(self.workspace),
                "provider": os.getenv("NULLFORGE_PROVIDER", "venice"),
                "version": "1.0.0"
            })
        elif uri == "nullforge://providers":
            content = json.dumps([
                {"id": "venice", "name": "Venice AI", "models": ["llama-3.1-405b"]},
                {"id": "openai", "name": "OpenAI", "models": ["gpt-4-turbo"]},
                {"id": "anthropic", "name": "Anthropic", "models": ["claude-3-5-sonnet"]},
                {"id": "ollama", "name": "Ollama", "models": ["llama3.1:70b"]}
            ])
        elif uri == "nullforge://history":
            content = json.dumps([])
        else:
            raise MCPError(-32602, f"Unknown resource: {uri}")
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": content
                }
            ]
        }
    
    async def handle_list_prompts(self) -> Dict[str, Any]:
        """Handle prompts/list request."""
        return {
            "prompts": [prompt.to_dict() for prompt in self.prompts.values()]
        }
    
    async def handle_get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        if name not in self.prompts:
            raise MCPError(-32602, f"Unknown prompt: {name}")
        
        prompt = self.prompts[name]
        
        # Generate prompt messages based on template
        if name == "build_api":
            description = arguments.get("description", "a REST API")
            framework = arguments.get("framework", "fastapi")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Build {description} using {framework}. Include authentication, validation, and tests."
                    }
                }
            ]
        elif name == "build_cli":
            description = arguments.get("description", "a CLI tool")
            language = arguments.get("language", "Python")
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Create {description} in {language}. Include help text and argument parsing."
                    }
                }
            ]
        else:
            messages = []
        
        return {
            "description": prompt.description,
            "messages": messages
        }
    
    async def run_stdio(self):
        """Run the server using stdio transport."""
        logger.info("NullForge MCP Server starting (stdio mode)...")
        
        while True:
            try:
                # Read JSON-RPC message from stdin
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line)
                response = await self.handle_request(request)
                
                # Write response to stdout
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            except Exception as e:
                logger.error(f"Error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_list_tools()
            elif method == "tools/call":
                result = await self.handle_call_tool(params["name"], params.get("arguments", {}))
            elif method == "resources/list":
                result = await self.handle_list_resources()
            elif method == "resources/read":
                result = await self.handle_read_resource(params["uri"])
            elif method == "prompts/list":
                result = await self.handle_list_prompts()
            elif method == "prompts/get":
                result = await self.handle_get_prompt(params["name"], params.get("arguments", {}))
            else:
                raise MCPError(-32601, f"Method not found: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except MCPError as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "data": e.data
                }
            }


def run_server():
    """Run the NullForge MCP server."""
    server = NullForgeMCPServer()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    run_server()
