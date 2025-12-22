"""
NullForge Plugin Registry
=========================
Central registry for managing plugins, their metadata, and versions.
"""

import json
import hashlib
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Type
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class PluginCategory(str, Enum):
    """Categories of plugins."""
    TOOL = "tool"
    AGENT = "agent"
    PROVIDER = "provider"
    FORMATTER = "formatter"
    TEMPLATE = "template"
    INTEGRATION = "integration"
    THEME = "theme"
    LANGUAGE = "language"


class PluginStatus(str, Enum):
    """Plugin installation status."""
    AVAILABLE = "available"
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    OUTDATED = "outdated"
    INCOMPATIBLE = "incompatible"


class PluginMetadata(BaseModel):
    """Metadata for a plugin."""
    id: str = Field(..., description="Unique plugin identifier (e.g., 'nullforge-docker-tools')")
    name: str = Field(..., description="Human-readable name")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    description: str = Field(..., description="Plugin description")
    author: str = Field(..., description="Author name or organization")
    email: Optional[str] = Field(None, description="Author email")
    homepage: Optional[str] = Field(None, description="Project homepage URL")
    repository: Optional[str] = Field(None, description="Git repository URL")
    license: str = Field(default="MIT", description="License type")
    category: PluginCategory = Field(..., description="Plugin category")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    keywords: List[str] = Field(default_factory=list, description="Keywords for search")
    
    # Dependencies
    nullforge_version: str = Field(default=">=1.0.0", description="Required NullForge version")
    python_version: str = Field(default=">=3.11", description="Required Python version")
    dependencies: List[str] = Field(default_factory=list, description="Python package dependencies")
    plugin_dependencies: List[str] = Field(default_factory=list, description="Other required plugins")
    
    # Stats
    downloads: int = Field(default=0, description="Download count")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Average rating")
    ratings_count: int = Field(default=0, description="Number of ratings")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Verification
    verified: bool = Field(default=False, description="Officially verified plugin")
    checksum: Optional[str] = Field(None, description="SHA256 checksum")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "nullforge-docker-tools",
                "name": "Docker Tools",
                "version": "1.2.0",
                "description": "Docker container management tools for NullForge",
                "author": "NullForge Team",
                "category": "tool",
                "tags": ["docker", "containers", "devops"],
                "downloads": 15420,
                "rating": 4.8,
                "verified": True
            }
        }


class Plugin(ABC):
    """Base class for all NullForge plugins."""
    
    metadata: PluginMetadata
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        pass
    
    def get_tools(self) -> List[Callable]:
        """Return list of tools provided by this plugin."""
        return []
    
    def get_agents(self) -> List[Type]:
        """Return list of agent classes provided by this plugin."""
        return []
    
    def get_prompts(self) -> Dict[str, str]:
        """Return dictionary of prompt templates."""
        return {}
    
    def get_formatters(self) -> Dict[str, Callable]:
        """Return dictionary of output formatters."""
        return {}
    
    def on_synthesis_start(self, goal: str, config: Dict[str, Any]) -> None:
        """Hook called when synthesis starts."""
        pass
    
    def on_synthesis_complete(self, result: Dict[str, Any]) -> None:
        """Hook called when synthesis completes."""
        pass
    
    def on_error(self, error: Exception) -> None:
        """Hook called on errors."""
        pass


@dataclass
class PluginEntry:
    """Registry entry for a plugin."""
    metadata: PluginMetadata
    status: PluginStatus = PluginStatus.AVAILABLE
    instance: Optional[Plugin] = None
    install_path: Optional[Path] = None
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = False
    error: Optional[str] = None


class PluginRegistry:
    """Central registry for all plugins."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or Path.home() / ".nullforge" / "plugins"
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self._plugins: Dict[str, PluginEntry] = {}
        self._remote_index: Dict[str, PluginMetadata] = {}
        self._load_local_registry()
    
    def _load_local_registry(self) -> None:
        """Load locally installed plugins."""
        registry_file = self.registry_path / "registry.json"
        if registry_file.exists():
            try:
                data = json.loads(registry_file.read_text())
                for plugin_id, entry_data in data.get("plugins", {}).items():
                    metadata = PluginMetadata(**entry_data["metadata"])
                    self._plugins[plugin_id] = PluginEntry(
                        metadata=metadata,
                        status=PluginStatus(entry_data.get("status", "available")),
                        enabled=entry_data.get("enabled", False),
                        config=entry_data.get("config", {})
                    )
            except Exception as e:
                print(f"Warning: Could not load plugin registry: {e}")
    
    def _save_local_registry(self) -> None:
        """Save registry to disk."""
        registry_file = self.registry_path / "registry.json"
        data = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "plugins": {
                pid: {
                    "metadata": entry.metadata.model_dump(mode='json'),
                    "status": entry.status.value,
                    "enabled": entry.enabled,
                    "config": entry.config
                }
                for pid, entry in self._plugins.items()
            }
        }
        registry_file.write_text(json.dumps(data, indent=2, default=str))
    
    def register(self, metadata: PluginMetadata, instance: Optional[Plugin] = None) -> None:
        """Register a plugin."""
        entry = PluginEntry(
            metadata=metadata,
            status=PluginStatus.INSTALLED if instance else PluginStatus.AVAILABLE,
            instance=instance,
            enabled=instance is not None
        )
        self._plugins[metadata.id] = entry
        self._save_local_registry()
    
    def unregister(self, plugin_id: str) -> bool:
        """Unregister a plugin."""
        if plugin_id in self._plugins:
            entry = self._plugins[plugin_id]
            if entry.instance:
                entry.instance.cleanup()
            del self._plugins[plugin_id]
            self._save_local_registry()
            return True
        return False
    
    def get(self, plugin_id: str) -> Optional[PluginEntry]:
        """Get a plugin entry by ID."""
        return self._plugins.get(plugin_id)
    
    def get_all(self, 
                category: Optional[PluginCategory] = None,
                status: Optional[PluginStatus] = None,
                enabled_only: bool = False) -> List[PluginEntry]:
        """Get all plugins matching filters."""
        results = []
        for entry in self._plugins.values():
            if category and entry.metadata.category != category:
                continue
            if status and entry.status != status:
                continue
            if enabled_only and not entry.enabled:
                continue
            results.append(entry)
        return results
    
    def search(self, query: str, limit: int = 20) -> List[PluginEntry]:
        """Search plugins by query."""
        query_lower = query.lower()
        scored = []
        
        for entry in self._plugins.values():
            score = 0
            meta = entry.metadata
            
            # Exact ID match
            if query_lower == meta.id.lower():
                score += 100
            # ID contains query
            elif query_lower in meta.id.lower():
                score += 50
            
            # Name match
            if query_lower in meta.name.lower():
                score += 40
            
            # Description match
            if query_lower in meta.description.lower():
                score += 20
            
            # Tag match
            for tag in meta.tags:
                if query_lower in tag.lower():
                    score += 30
                    break
            
            # Keyword match
            for kw in meta.keywords:
                if query_lower in kw.lower():
                    score += 25
                    break
            
            if score > 0:
                scored.append((score, entry))
        
        # Sort by score descending
        scored.sort(key=lambda x: (-x[0], -x[1].metadata.downloads))
        return [entry for _, entry in scored[:limit]]
    
    def enable(self, plugin_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Enable a plugin."""
        entry = self._plugins.get(plugin_id)
        if not entry:
            return False
        
        entry.enabled = True
        if config:
            entry.config.update(config)
        
        if entry.instance:
            try:
                entry.instance.initialize(entry.config)
                entry.status = PluginStatus.ENABLED
            except Exception as e:
                entry.error = str(e)
                entry.enabled = False
                return False
        
        self._save_local_registry()
        return True
    
    def disable(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        entry = self._plugins.get(plugin_id)
        if not entry:
            return False
        
        entry.enabled = False
        entry.status = PluginStatus.DISABLED
        
        if entry.instance:
            try:
                entry.instance.cleanup()
            except Exception:
                pass
        
        self._save_local_registry()
        return True
    
    def get_enabled_tools(self) -> List[Callable]:
        """Get all tools from enabled plugins."""
        tools = []
        for entry in self._plugins.values():
            if entry.enabled and entry.instance:
                tools.extend(entry.instance.get_tools())
        return tools
    
    def get_enabled_agents(self) -> List[Type]:
        """Get all agent classes from enabled plugins."""
        agents = []
        for entry in self._plugins.values():
            if entry.enabled and entry.instance:
                agents.extend(entry.instance.get_agents())
        return agents
    
    def update_remote_index(self, index_url: str = "https://plugins.nullforge.io/index.json") -> None:
        """Update the remote plugin index."""
        # In production, this would fetch from a real registry
        # For now, we'll use built-in plugins
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total = len(self._plugins)
        by_category = {}
        by_status = {}
        enabled = 0
        
        for entry in self._plugins.values():
            cat = entry.metadata.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            
            status = entry.status.value
            by_status[status] = by_status.get(status, 0) + 1
            
            if entry.enabled:
                enabled += 1
        
        return {
            "total": total,
            "enabled": enabled,
            "by_category": by_category,
            "by_status": by_status
        }


# Built-in plugins registry with sample plugins
BUILTIN_PLUGINS: List[PluginMetadata] = [
    PluginMetadata(
        id="nullforge-docker-tools",
        name="Docker Tools",
        version="1.0.0",
        description="Docker and container management tools. Build, run, and manage containers directly from NullForge.",
        author="NullForge Team",
        category=PluginCategory.TOOL,
        tags=["docker", "containers", "devops", "kubernetes"],
        keywords=["container", "image", "dockerfile", "compose"],
        downloads=15420,
        rating=4.8,
        ratings_count=234,
        verified=True
    ),
    PluginMetadata(
        id="nullforge-aws-tools",
        name="AWS Integration",
        version="1.2.0",
        description="AWS cloud integration tools. Deploy to EC2, Lambda, S3, and more.",
        author="NullForge Team",
        category=PluginCategory.INTEGRATION,
        tags=["aws", "cloud", "lambda", "s3", "ec2"],
        keywords=["amazon", "cloud", "serverless", "deploy"],
        downloads=12350,
        rating=4.7,
        ratings_count=189,
        verified=True
    ),
    PluginMetadata(
        id="nullforge-database-tools",
        name="Database Tools",
        version="2.0.0",
        description="Database management and migration tools. Support for PostgreSQL, MySQL, SQLite, MongoDB.",
        author="NullForge Team",
        category=PluginCategory.TOOL,
        tags=["database", "sql", "postgresql", "mysql", "mongodb"],
        keywords=["db", "migration", "schema", "query"],
        downloads=18900,
        rating=4.9,
        ratings_count=312,
        verified=True
    ),
    PluginMetadata(
        id="nullforge-testing-suite",
        name="Advanced Testing Suite",
        version="1.5.0",
        description="Comprehensive testing tools. Unit tests, integration tests, mocking, coverage reports.",
        author="NullForge Team",
        category=PluginCategory.TOOL,
        tags=["testing", "pytest", "unittest", "coverage", "mocking"],
        keywords=["test", "assert", "mock", "fixture"],
        downloads=22100,
        rating=4.8,
        ratings_count=445,
        verified=True
    ),
    PluginMetadata(
        id="nullforge-security-scanner",
        name="Security Scanner",
        version="1.1.0",
        description="Security vulnerability scanner. OWASP checks, dependency audits, code analysis.",
        author="NullForge Team",
        category=PluginCategory.TOOL,
        tags=["security", "vulnerability", "audit", "owasp"],
        keywords=["scan", "cve", "vulnerability", "secure"],
        downloads=9800,
        rating=4.6,
        ratings_count=156,
        verified=True
    ),
    PluginMetadata(
        id="nullforge-graphql-tools",
        name="GraphQL Tools",
        version="1.0.0",
        description="GraphQL schema generation, resolvers, and API tools.",
        author="Community",
        category=PluginCategory.TOOL,
        tags=["graphql", "api", "schema", "resolver"],
        keywords=["query", "mutation", "subscription"],
        downloads=7650,
        rating=4.5,
        ratings_count=98,
        verified=False
    ),
    PluginMetadata(
        id="nullforge-react-generator",
        name="React Component Generator",
        version="2.1.0",
        description="Generate React components, hooks, and full applications with TypeScript support.",
        author="Community",
        category=PluginCategory.TEMPLATE,
        tags=["react", "typescript", "frontend", "components"],
        keywords=["jsx", "tsx", "hooks", "redux"],
        downloads=31200,
        rating=4.7,
        ratings_count=523,
        verified=True
    ),
    PluginMetadata(
        id="nullforge-fastapi-template",
        name="FastAPI Project Template",
        version="1.3.0",
        description="Full-featured FastAPI project templates with authentication, database, and testing.",
        author="NullForge Team",
        category=PluginCategory.TEMPLATE,
        tags=["fastapi", "python", "api", "template"],
        keywords=["rest", "async", "pydantic", "sqlalchemy"],
        downloads=28500,
        rating=4.9,
        ratings_count=467,
        verified=True
    ),
    PluginMetadata(
        id="nullforge-ollama-provider",
        name="Ollama Enhanced Provider",
        version="1.0.0",
        description="Enhanced Ollama integration with model management and optimization.",
        author="Community",
        category=PluginCategory.PROVIDER,
        tags=["ollama", "local", "llm", "models"],
        keywords=["llama", "mistral", "codellama"],
        downloads=14200,
        rating=4.6,
        ratings_count=201,
        verified=False
    ),
    PluginMetadata(
        id="nullforge-code-reviewer",
        name="AI Code Reviewer",
        version="1.2.0",
        description="Advanced AI-powered code review agent with style checking and best practices.",
        author="NullForge Team",
        category=PluginCategory.AGENT,
        tags=["review", "quality", "linting", "best-practices"],
        keywords=["code review", "style", "lint", "quality"],
        downloads=19800,
        rating=4.8,
        ratings_count=334,
        verified=True
    ),
]
