"""
NullForge Plugin Manager
========================
High-level plugin management with marketplace integration.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass

from .registry import (
    PluginRegistry, 
    PluginMetadata, 
    PluginCategory, 
    PluginStatus,
    PluginEntry,
    BUILTIN_PLUGINS
)
from .loader import PluginLoader, LoadResult


@dataclass
class InstallResult:
    """Result of a plugin installation."""
    success: bool
    plugin_id: str
    version: str
    message: str
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass  
class UpdateResult:
    """Result of a plugin update."""
    success: bool
    plugin_id: str
    old_version: str
    new_version: str
    message: str


class PluginManager:
    """
    High-level plugin manager with marketplace integration.
    
    Provides:
    - Plugin discovery and search
    - Installation from multiple sources
    - Updates and version management
    - Configuration management
    - Plugin lifecycle management
    """
    
    MARKETPLACE_URL = "https://plugins.nullforge.io"
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.home() / ".nullforge"
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.registry = PluginRegistry(self.base_path / "plugins")
        self.loader = PluginLoader(self.base_path / "plugins" / "installed")
        
        # Initialize with built-in plugins
        self._init_builtin_plugins()
    
    def _init_builtin_plugins(self) -> None:
        """Initialize registry with built-in plugins."""
        for metadata in BUILTIN_PLUGINS:
            if not self.registry.get(metadata.id):
                self.registry.register(metadata)
    
    # ===================
    # Discovery & Search
    # ===================
    
    def list_available(
        self, 
        category: Optional[PluginCategory] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """List available plugins from marketplace."""
        all_plugins = self.registry.get_all(category=category)
        
        # Sort by downloads
        all_plugins.sort(key=lambda x: -x.metadata.downloads)
        
        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        page_plugins = all_plugins[start:end]
        
        return {
            "plugins": [
                {
                    "id": p.metadata.id,
                    "name": p.metadata.name,
                    "version": p.metadata.version,
                    "description": p.metadata.description,
                    "author": p.metadata.author,
                    "category": p.metadata.category.value,
                    "tags": p.metadata.tags,
                    "downloads": p.metadata.downloads,
                    "rating": p.metadata.rating,
                    "verified": p.metadata.verified,
                    "status": p.status.value,
                    "enabled": p.enabled
                }
                for p in page_plugins
            ],
            "total": len(all_plugins),
            "page": page,
            "per_page": per_page,
            "total_pages": (len(all_plugins) + per_page - 1) // per_page
        }
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for plugins."""
        results = self.registry.search(query, limit)
        return [
            {
                "id": p.metadata.id,
                "name": p.metadata.name,
                "version": p.metadata.version,
                "description": p.metadata.description,
                "author": p.metadata.author,
                "category": p.metadata.category.value,
                "downloads": p.metadata.downloads,
                "rating": p.metadata.rating,
                "verified": p.metadata.verified,
                "status": p.status.value
            }
            for p in results
        ]
    
    def get_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed plugin information."""
        entry = self.registry.get(plugin_id)
        if not entry:
            return None
        
        meta = entry.metadata
        return {
            "id": meta.id,
            "name": meta.name,
            "version": meta.version,
            "description": meta.description,
            "author": meta.author,
            "email": meta.email,
            "homepage": meta.homepage,
            "repository": meta.repository,
            "license": meta.license,
            "category": meta.category.value,
            "tags": meta.tags,
            "keywords": meta.keywords,
            "nullforge_version": meta.nullforge_version,
            "python_version": meta.python_version,
            "dependencies": meta.dependencies,
            "plugin_dependencies": meta.plugin_dependencies,
            "downloads": meta.downloads,
            "rating": meta.rating,
            "ratings_count": meta.ratings_count,
            "verified": meta.verified,
            "created_at": meta.created_at.isoformat(),
            "updated_at": meta.updated_at.isoformat(),
            "status": entry.status.value,
            "enabled": entry.enabled,
            "config": entry.config,
            "error": entry.error
        }
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all plugin categories with counts."""
        stats = self.registry.get_stats()
        return [
            {
                "id": cat.value,
                "name": cat.value.replace("_", " ").title(),
                "count": stats["by_category"].get(cat.value, 0)
            }
            for cat in PluginCategory
        ]
    
    # ==============
    # Installation
    # ==============
    
    def install(
        self, 
        plugin_id: str,
        version: Optional[str] = None,
        source: str = "marketplace"
    ) -> InstallResult:
        """
        Install a plugin.
        
        Sources:
        - marketplace: Official NullForge marketplace
        - git: Git repository URL
        - pypi: PyPI package
        - local: Local directory path
        """
        entry = self.registry.get(plugin_id)
        
        if entry and entry.status == PluginStatus.INSTALLED:
            return InstallResult(
                success=False,
                plugin_id=plugin_id,
                version=entry.metadata.version,
                message="Plugin already installed"
            )
        
        # For demo, simulate installation of built-in plugins
        if source == "marketplace" and entry:
            # Simulate successful installation
            entry.status = PluginStatus.INSTALLED
            self.registry._save_local_registry()
            
            return InstallResult(
                success=True,
                plugin_id=plugin_id,
                version=entry.metadata.version,
                message=f"Successfully installed {entry.metadata.name} v{entry.metadata.version}"
            )
        
        elif source == "git":
            # Load from git repository
            result = self.loader.load_from_git(plugin_id, version or "main")
            if result.success:
                self.registry.register(result.metadata, result.plugin)
                return InstallResult(
                    success=True,
                    plugin_id=result.metadata.id,
                    version=result.metadata.version,
                    message=f"Successfully installed from Git",
                    warnings=result.warnings
                )
            else:
                return InstallResult(
                    success=False,
                    plugin_id=plugin_id,
                    version="",
                    message=result.error or "Installation failed"
                )
        
        elif source == "pypi":
            result = self.loader.load_from_pypi(plugin_id, version)
            if result.success:
                self.registry.register(result.metadata, result.plugin)
                return InstallResult(
                    success=True,
                    plugin_id=result.metadata.id,
                    version=result.metadata.version,
                    message=f"Successfully installed from PyPI",
                    warnings=result.warnings
                )
            else:
                return InstallResult(
                    success=False,
                    plugin_id=plugin_id,
                    version="",
                    message=result.error or "Installation failed"
                )
        
        elif source == "local":
            result = self.loader.load_from_path(Path(plugin_id))
            if result.success:
                self.registry.register(result.metadata, result.plugin)
                return InstallResult(
                    success=True,
                    plugin_id=result.metadata.id,
                    version=result.metadata.version,
                    message=f"Successfully installed from local path",
                    warnings=result.warnings
                )
            else:
                return InstallResult(
                    success=False,
                    plugin_id=plugin_id,
                    version="",
                    message=result.error or "Installation failed"
                )
        
        return InstallResult(
            success=False,
            plugin_id=plugin_id,
            version="",
            message=f"Unknown source: {source}"
        )
    
    def uninstall(self, plugin_id: str) -> InstallResult:
        """Uninstall a plugin."""
        entry = self.registry.get(plugin_id)
        
        if not entry:
            return InstallResult(
                success=False,
                plugin_id=plugin_id,
                version="",
                message="Plugin not found"
            )
        
        if entry.status not in [PluginStatus.INSTALLED, PluginStatus.ENABLED, PluginStatus.DISABLED]:
            return InstallResult(
                success=False,
                plugin_id=plugin_id,
                version=entry.metadata.version,
                message="Plugin is not installed"
            )
        
        # Unload if loaded
        self.loader.unload(plugin_id)
        
        # Reset status to available (keep in registry for marketplace)
        entry.status = PluginStatus.AVAILABLE
        entry.enabled = False
        entry.instance = None
        self.registry._save_local_registry()
        
        return InstallResult(
            success=True,
            plugin_id=plugin_id,
            version=entry.metadata.version,
            message=f"Successfully uninstalled {entry.metadata.name}"
        )
    
    def update(self, plugin_id: str) -> UpdateResult:
        """Update a plugin to the latest version."""
        entry = self.registry.get(plugin_id)
        
        if not entry:
            return UpdateResult(
                success=False,
                plugin_id=plugin_id,
                old_version="",
                new_version="",
                message="Plugin not found"
            )
        
        old_version = entry.metadata.version
        
        # For demo, simulate no updates available
        return UpdateResult(
            success=True,
            plugin_id=plugin_id,
            old_version=old_version,
            new_version=old_version,
            message="Already at latest version"
        )
    
    def update_all(self) -> List[UpdateResult]:
        """Update all installed plugins."""
        results = []
        for entry in self.registry.get_all(status=PluginStatus.INSTALLED):
            results.append(self.update(entry.metadata.id))
        return results
    
    # ===================
    # Enable/Disable
    # ===================
    
    def enable(self, plugin_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """Enable a plugin."""
        return self.registry.enable(plugin_id, config)
    
    def disable(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        return self.registry.disable(plugin_id)
    
    # ===================
    # Configuration
    # ===================
    
    def configure(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """Update plugin configuration."""
        entry = self.registry.get(plugin_id)
        if not entry:
            return False
        
        entry.config.update(config)
        
        # Reinitialize if enabled
        if entry.enabled and entry.instance:
            try:
                entry.instance.initialize(entry.config)
            except Exception as e:
                entry.error = str(e)
                return False
        
        self.registry._save_local_registry()
        return True
    
    def get_config(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin configuration."""
        entry = self.registry.get(plugin_id)
        return entry.config if entry else None
    
    # ===================
    # Statistics
    # ===================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics."""
        stats = self.registry.get_stats()
        return {
            "total_plugins": stats["total"],
            "enabled_plugins": stats["enabled"],
            "by_category": stats["by_category"],
            "by_status": stats["by_status"],
            "marketplace_url": self.MARKETPLACE_URL
        }
    
    def get_installed(self) -> List[Dict[str, Any]]:
        """Get list of installed plugins."""
        installed = self.registry.get_all(status=PluginStatus.INSTALLED)
        enabled = self.registry.get_all(status=PluginStatus.ENABLED)
        
        all_installed = installed + enabled
        
        return [
            {
                "id": p.metadata.id,
                "name": p.metadata.name,
                "version": p.metadata.version,
                "category": p.metadata.category.value,
                "enabled": p.enabled,
                "status": p.status.value
            }
            for p in all_installed
        ]
    
    def get_enabled(self) -> List[Dict[str, Any]]:
        """Get list of enabled plugins."""
        enabled = self.registry.get_all(enabled_only=True)
        return [
            {
                "id": p.metadata.id,
                "name": p.metadata.name,
                "version": p.metadata.version,
                "category": p.metadata.category.value
            }
            for p in enabled
        ]
