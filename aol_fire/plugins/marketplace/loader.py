"""
NullForge Plugin Loader
=======================
Handles loading, validation, and instantiation of plugins.
"""

import os
import sys
import json
import importlib
import importlib.util
import hashlib
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Type, List
from dataclasses import dataclass

from .registry import Plugin, PluginMetadata, PluginCategory, PluginStatus


@dataclass
class LoadResult:
    """Result of a plugin load operation."""
    success: bool
    plugin: Optional[Plugin] = None
    metadata: Optional[PluginMetadata] = None
    error: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class PluginLoader:
    """Loads and validates NullForge plugins."""
    
    MANIFEST_FILE = "nullforge_plugin.json"
    ENTRY_POINT_FILE = "plugin.py"
    
    def __init__(self, plugins_dir: Optional[Path] = None):
        self.plugins_dir = plugins_dir or Path.home() / ".nullforge" / "plugins" / "installed"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_plugins: Dict[str, Plugin] = {}
    
    def load_from_path(self, plugin_path: Path) -> LoadResult:
        """Load a plugin from a directory path."""
        warnings = []
        
        # Check manifest
        manifest_path = plugin_path / self.MANIFEST_FILE
        if not manifest_path.exists():
            return LoadResult(
                success=False,
                error=f"Plugin manifest not found: {self.MANIFEST_FILE}"
            )
        
        # Parse manifest
        try:
            manifest_data = json.loads(manifest_path.read_text())
            metadata = PluginMetadata(**manifest_data)
        except Exception as e:
            return LoadResult(
                success=False,
                error=f"Invalid plugin manifest: {e}"
            )
        
        # Check entry point
        entry_point = plugin_path / self.ENTRY_POINT_FILE
        if not entry_point.exists():
            # Try alternative entry points
            for alt in ["__init__.py", "main.py", f"{metadata.id.replace('-', '_')}.py"]:
                alt_path = plugin_path / alt
                if alt_path.exists():
                    entry_point = alt_path
                    break
            else:
                return LoadResult(
                    success=False,
                    metadata=metadata,
                    error=f"Plugin entry point not found"
                )
        
        # Validate dependencies
        missing_deps = self._check_dependencies(metadata.dependencies)
        if missing_deps:
            warnings.append(f"Missing dependencies: {', '.join(missing_deps)}")
        
        # Load the plugin module
        try:
            spec = importlib.util.spec_from_file_location(
                f"nullforge_plugins.{metadata.id.replace('-', '_')}",
                entry_point
            )
            if spec is None or spec.loader is None:
                return LoadResult(
                    success=False,
                    metadata=metadata,
                    error="Could not create module spec"
                )
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                return LoadResult(
                    success=False,
                    metadata=metadata,
                    error="No Plugin subclass found in module"
                )
            
            # Instantiate plugin
            plugin_instance = plugin_class()
            plugin_instance.metadata = metadata
            
            self._loaded_plugins[metadata.id] = plugin_instance
            
            return LoadResult(
                success=True,
                plugin=plugin_instance,
                metadata=metadata,
                warnings=warnings
            )
            
        except Exception as e:
            return LoadResult(
                success=False,
                metadata=metadata,
                error=f"Failed to load plugin module: {e}",
                warnings=warnings
            )
    
    def load_from_git(self, repo_url: str, ref: str = "main") -> LoadResult:
        """Load a plugin from a Git repository."""
        # Clone to temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="nullforge_plugin_"))
        
        try:
            # Clone repository
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref, repo_url, str(temp_dir)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return LoadResult(
                    success=False,
                    error=f"Git clone failed: {result.stderr}"
                )
            
            # Load from cloned directory
            load_result = self.load_from_path(temp_dir)
            
            if load_result.success and load_result.metadata:
                # Copy to plugins directory
                plugin_dir = self.plugins_dir / load_result.metadata.id
                if plugin_dir.exists():
                    shutil.rmtree(plugin_dir)
                shutil.copytree(temp_dir, plugin_dir)
                
                # Update load result with new path
                load_result = self.load_from_path(plugin_dir)
            
            return load_result
            
        except subprocess.TimeoutExpired:
            return LoadResult(
                success=False,
                error="Git clone timed out"
            )
        except Exception as e:
            return LoadResult(
                success=False,
                error=f"Failed to load from Git: {e}"
            )
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def load_from_pypi(self, package_name: str, version: Optional[str] = None) -> LoadResult:
        """Load a plugin from PyPI."""
        try:
            # Install package
            pkg_spec = f"{package_name}=={version}" if version else package_name
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg_spec, "--quiet"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return LoadResult(
                    success=False,
                    error=f"pip install failed: {result.stderr}"
                )
            
            # Try to import the package
            module_name = package_name.replace("-", "_")
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                return LoadResult(
                    success=False,
                    error=f"Could not import installed package: {e}"
                )
            
            # Find plugin class
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                return LoadResult(
                    success=False,
                    error="No Plugin subclass found in package"
                )
            
            # Get metadata from package
            metadata = self._extract_metadata_from_module(module, package_name, version)
            
            # Instantiate
            plugin_instance = plugin_class()
            plugin_instance.metadata = metadata
            
            self._loaded_plugins[metadata.id] = plugin_instance
            
            return LoadResult(
                success=True,
                plugin=plugin_instance,
                metadata=metadata
            )
            
        except subprocess.TimeoutExpired:
            return LoadResult(
                success=False,
                error="pip install timed out"
            )
        except Exception as e:
            return LoadResult(
                success=False,
                error=f"Failed to load from PyPI: {e}"
            )
    
    def unload(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        if plugin_id not in self._loaded_plugins:
            return False
        
        plugin = self._loaded_plugins[plugin_id]
        try:
            plugin.cleanup()
        except Exception:
            pass
        
        del self._loaded_plugins[plugin_id]
        return True
    
    def get_loaded(self, plugin_id: str) -> Optional[Plugin]:
        """Get a loaded plugin instance."""
        return self._loaded_plugins.get(plugin_id)
    
    def get_all_loaded(self) -> Dict[str, Plugin]:
        """Get all loaded plugins."""
        return dict(self._loaded_plugins)
    
    def _find_plugin_class(self, module) -> Optional[Type[Plugin]]:
        """Find a Plugin subclass in a module."""
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type) and
                issubclass(obj, Plugin) and
                obj is not Plugin
            ):
                return obj
        return None
    
    def _check_dependencies(self, dependencies: List[str]) -> List[str]:
        """Check which dependencies are missing."""
        missing = []
        for dep in dependencies:
            # Parse dependency spec (e.g., "requests>=2.28.0")
            pkg_name = dep.split(">=")[0].split("==")[0].split("<")[0].strip()
            try:
                importlib.import_module(pkg_name.replace("-", "_"))
            except ImportError:
                missing.append(dep)
        return missing
    
    def _extract_metadata_from_module(
        self, 
        module, 
        package_name: str, 
        version: Optional[str]
    ) -> PluginMetadata:
        """Extract metadata from a loaded module."""
        # Try to get metadata from module attributes
        return PluginMetadata(
            id=package_name,
            name=getattr(module, "__title__", package_name),
            version=version or getattr(module, "__version__", "0.0.0"),
            description=getattr(module, "__description__", ""),
            author=getattr(module, "__author__", "Unknown"),
            category=getattr(module, "__category__", PluginCategory.TOOL)
        )
    
    def verify_checksum(self, plugin_path: Path, expected_checksum: str) -> bool:
        """Verify plugin directory checksum."""
        computed = self._compute_directory_checksum(plugin_path)
        return computed == expected_checksum
    
    def _compute_directory_checksum(self, directory: Path) -> str:
        """Compute SHA256 checksum of a directory."""
        sha256 = hashlib.sha256()
        
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file() and not file_path.name.startswith("."):
                sha256.update(file_path.name.encode())
                sha256.update(file_path.read_bytes())
        
        return sha256.hexdigest()
    
    def install_dependencies(self, dependencies: List[str]) -> bool:
        """Install Python dependencies for a plugin."""
        if not dependencies:
            return True
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + dependencies + ["--quiet"],
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode == 0
        except Exception:
            return False
