"""
NullForge Project Intelligence Tools

Provides holistic project understanding:
- Language and framework detection
- Dependency analysis
- Architecture inference
- Health scoring
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


# =============================================================================
# Input Schemas
# =============================================================================

class AnalyzeProjectInput(BaseModel):
    """Input for project analysis."""
    path: str = Field(default=".", description="Project root path")
    depth: int = Field(default=3, description="Directory scan depth")


# =============================================================================
# Tool Implementation
# =============================================================================

class AnalyzeProjectTool(BaseTool):
    """
    Comprehensive project analysis.
    
    Features:
    - Language detection
    - Framework identification
    - Dependency extraction
    - Structure analysis
    - Health scoring
    """
    
    name: str = "analyze_project"
    description: str = """Analyze a project's structure, languages, frameworks, and health.

Provides:
- Detected programming languages
- Frameworks and libraries in use
- Project structure overview
- Dependencies list
- Health score and recommendations

Use this to understand a codebase before making changes."""
    
    args_schema: Type[BaseModel] = AnalyzeProjectInput
    workspace_dir: Path = Field(default=Path("."))
    
    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
    
    def _detect_languages(self, root: Path) -> Dict[str, int]:
        """Detect languages by file extensions."""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript (React)",
            ".tsx": "TypeScript (React)",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".kt": "Kotlin",
            ".swift": "Swift",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C/C++ Header",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".scala": "Scala",
            ".r": "R",
            ".sql": "SQL",
            ".sh": "Shell",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".json": "JSON",
            ".xml": "XML",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".md": "Markdown",
        }
        
        counts = {}
        
        for ext, lang in ext_map.items():
            files = list(root.rglob(f"*{ext}"))
            # Exclude common directories
            files = [f for f in files if not any(
                part in f.parts for part in [
                    "node_modules", ".git", "__pycache__", "venv", 
                    ".venv", "target", "build", "dist"
                ]
            )]
            if files:
                counts[lang] = counts.get(lang, 0) + len(files)
        
        return dict(sorted(counts.items(), key=lambda x: -x[1]))
    
    def _detect_frameworks(self, root: Path) -> List[str]:
        """Detect frameworks from config files."""
        frameworks = []
        
        # Python
        if (root / "requirements.txt").exists() or (root / "pyproject.toml").exists():
            frameworks.append("Python Project")
            
            for f in [root / "requirements.txt", root / "pyproject.toml", root / "setup.py"]:
                if f.exists():
                    content = f.read_text()
                    if "django" in content.lower():
                        frameworks.append("Django")
                    if "flask" in content.lower():
                        frameworks.append("Flask")
                    if "fastapi" in content.lower():
                        frameworks.append("FastAPI")
                    if "pytest" in content.lower():
                        frameworks.append("Pytest")
        
        # JavaScript/TypeScript
        if (root / "package.json").exists():
            frameworks.append("Node.js")
            try:
                pkg = json.loads((root / "package.json").read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                
                if "react" in deps:
                    frameworks.append("React")
                if "vue" in deps:
                    frameworks.append("Vue.js")
                if "angular" in deps or "@angular/core" in deps:
                    frameworks.append("Angular")
                if "next" in deps:
                    frameworks.append("Next.js")
                if "express" in deps:
                    frameworks.append("Express.js")
                if "typescript" in deps:
                    frameworks.append("TypeScript")
                if "jest" in deps:
                    frameworks.append("Jest")
                if "vite" in deps:
                    frameworks.append("Vite")
            except:
                pass
        
        # Rust
        if (root / "Cargo.toml").exists():
            frameworks.append("Rust/Cargo")
            content = (root / "Cargo.toml").read_text()
            if "actix" in content:
                frameworks.append("Actix")
            if "axum" in content:
                frameworks.append("Axum")
            if "tokio" in content:
                frameworks.append("Tokio")
        
        # Go
        if (root / "go.mod").exists():
            frameworks.append("Go Modules")
        
        # Docker
        if (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists():
            frameworks.append("Docker")
        
        # Kubernetes
        if any(root.rglob("*.yaml")) or any(root.rglob("*.yml")):
            for f in list(root.rglob("*.yaml")) + list(root.rglob("*.yml")):
                try:
                    if "apiVersion" in f.read_text() and "kind" in f.read_text():
                        frameworks.append("Kubernetes")
                        break
                except:
                    pass
        
        return list(set(frameworks))
    
    def _get_structure(self, root: Path, depth: int = 3) -> str:
        """Generate directory structure."""
        output = []
        
        def walk(path: Path, prefix: str = "", level: int = 0):
            if level >= depth:
                return
            
            try:
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                return
            
            # Filter out common non-essential directories
            skip_dirs = {
                "node_modules", ".git", "__pycache__", "venv", ".venv",
                "target", "build", "dist", ".idea", ".vscode", "coverage",
                ".pytest_cache", ".mypy_cache", "egg-info"
            }
            
            items = [i for i in items if i.name not in skip_dirs and not i.name.endswith(".egg-info")]
            
            for i, item in enumerate(items[:15]):  # Limit items per level
                is_last = i == len(items[:15]) - 1
                connector = "└── " if is_last else "├── "
                
                if item.is_dir():
                    output.append(f"{prefix}{connector}📁 {item.name}/")
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    walk(item, new_prefix, level + 1)
                else:
                    output.append(f"{prefix}{connector}📄 {item.name}")
            
            if len(items) > 15:
                output.append(f"{prefix}    ... and {len(items) - 15} more")
        
        output.append(f"📁 {root.name}/")
        walk(root)
        
        return "\n".join(output)
    
    def _calculate_health(self, root: Path, languages: Dict, frameworks: List) -> Dict[str, Any]:
        """Calculate project health score."""
        score = 50  # Base score
        issues = []
        recommendations = []
        
        # Check for README
        has_readme = any(root.glob("README*"))
        if has_readme:
            score += 10
        else:
            issues.append("Missing README")
            recommendations.append("Add a README.md with project documentation")
        
        # Check for tests
        has_tests = (
            (root / "tests").exists() or
            (root / "test").exists() or
            any(root.rglob("*_test.py")) or
            any(root.rglob("test_*.py")) or
            any(root.rglob("*.test.js")) or
            any(root.rglob("*.spec.js"))
        )
        if has_tests:
            score += 15
        else:
            issues.append("No tests found")
            recommendations.append("Add unit tests to improve reliability")
        
        # Check for CI/CD
        has_ci = (
            (root / ".github" / "workflows").exists() or
            (root / ".gitlab-ci.yml").exists() or
            (root / "Jenkinsfile").exists() or
            (root / ".circleci").exists()
        )
        if has_ci:
            score += 10
        else:
            recommendations.append("Consider adding CI/CD pipeline")
        
        # Check for .gitignore
        if (root / ".gitignore").exists():
            score += 5
        else:
            issues.append("Missing .gitignore")
            recommendations.append("Add .gitignore to exclude build artifacts")
        
        # Check for license
        has_license = any(root.glob("LICENSE*")) or any(root.glob("LICENCE*"))
        if has_license:
            score += 5
        else:
            recommendations.append("Consider adding a LICENSE file")
        
        # Check for documentation
        has_docs = (root / "docs").exists() or (root / "documentation").exists()
        if has_docs:
            score += 5
        
        # Framework-specific checks
        if "Python" in languages:
            if not (root / "requirements.txt").exists() and not (root / "pyproject.toml").exists():
                issues.append("Python project without dependency file")
                recommendations.append("Add requirements.txt or pyproject.toml")
        
        if "TypeScript" in frameworks:
            if not (root / "tsconfig.json").exists():
                issues.append("TypeScript without tsconfig.json")
        
        # Calculate grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": min(score, 100),
            "grade": grade,
            "issues": issues,
            "recommendations": recommendations,
        }
    
    def _run(
        self,
        path: str = ".",
        depth: int = 3,
    ) -> str:
        try:
            root = self._resolve_path(path)
            
            if not root.exists():
                return f"❌ Path not found: {path}"
            
            if not root.is_dir():
                return f"❌ Not a directory: {path}"
            
            output = [f"🔍 Project Analysis: {root.name}\n"]
            output.append("=" * 50)
            
            # Languages
            languages = self._detect_languages(root)
            if languages:
                output.append("\n📊 **Languages Detected:**")
                total_files = sum(languages.values())
                for lang, count in list(languages.items())[:8]:
                    pct = (count / total_files) * 100
                    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                    output.append(f"   {lang:20} {bar} {count:4} files ({pct:.1f}%)")
            
            # Frameworks
            frameworks = self._detect_frameworks(root)
            if frameworks:
                output.append("\n🛠️  **Frameworks & Tools:**")
                for fw in frameworks:
                    output.append(f"   • {fw}")
            
            # Structure
            output.append("\n📁 **Project Structure:**")
            output.append(self._get_structure(root, depth))
            
            # Health
            health = self._calculate_health(root, languages, frameworks)
            output.append(f"\n💚 **Health Score: {health['score']}/100 (Grade: {health['grade']})**")
            
            if health["issues"]:
                output.append("\n⚠️  **Issues:**")
                for issue in health["issues"]:
                    output.append(f"   • {issue}")
            
            if health["recommendations"]:
                output.append("\n💡 **Recommendations:**")
                for rec in health["recommendations"]:
                    output.append(f"   • {rec}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Analysis error: {str(e)}"
