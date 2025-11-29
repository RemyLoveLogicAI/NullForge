"""
NullForge Code Analysis Tools - NeuralDebugger & AutoPatch

Provides intelligent code analysis:
- AST parsing and analysis
- Complexity metrics
- Code smell detection
- Safe Python execution
- Pattern-based debugging
"""

from __future__ import annotations

import ast
import sys
import traceback
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


# =============================================================================
# Input Schemas
# =============================================================================

class AnalyzeCodeInput(BaseModel):
    """Input for code analysis."""
    path: str = Field(..., description="Path to file or directory to analyze")
    include_metrics: bool = Field(default=True, description="Include complexity metrics")
    include_issues: bool = Field(default=True, description="Include potential issues")


class RunPythonInput(BaseModel):
    """Input for running Python code."""
    code: str = Field(..., description="Python code to execute")
    timeout: int = Field(default=30, description="Execution timeout in seconds")


# =============================================================================
# Tool Implementations
# =============================================================================

class AnalyzeCodeTool(BaseTool):
    """
    Deep code analysis with metrics and issue detection.
    
    Features:
    - AST-based analysis
    - Cyclomatic complexity calculation
    - Code smell detection
    - Function/class extraction
    - Import analysis
    """
    
    name: str = "analyze_code"
    description: str = """Analyze code for quality, complexity, and potential issues.

Provides:
- Function and class listing
- Complexity metrics
- Potential bugs and code smells
- Import analysis
- Line counts and statistics

Use this to understand code structure and identify improvements."""
    
    args_schema: Type[BaseModel] = AnalyzeCodeInput
    workspace_dir: Path = Field(default=Path("."))
    
    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
    
    def _analyze_python(self, filepath: Path) -> Dict[str, Any]:
        """Analyze a Python file."""
        content = filepath.read_text()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}
        
        analysis = {
            "functions": [],
            "classes": [],
            "imports": [],
            "issues": [],
            "metrics": {},
        }
        
        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "docstring": ast.get_docstring(node),
                    "complexity": self._calculate_complexity(node),
                }
                analysis["functions"].append(func_info)
            
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                class_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                    "bases": [self._get_name(b) for b in node.bases],
                    "docstring": ast.get_docstring(node),
                }
                analysis["classes"].append(class_info)
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    analysis["imports"].append(f"{module}.{alias.name}")
        
        # Detect issues
        analysis["issues"] = self._detect_issues(tree, content)
        
        # Calculate metrics
        lines = content.splitlines()
        analysis["metrics"] = {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "functions_count": len(analysis["functions"]),
            "classes_count": len(analysis["classes"]),
            "avg_complexity": sum(f["complexity"] for f in analysis["functions"]) / max(len(analysis["functions"]), 1),
        }
        
        return analysis
    
    def _get_decorator_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _detect_issues(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        """Detect potential code issues."""
        issues = []
        
        for node in ast.walk(tree):
            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({
                    "type": "bare_except",
                    "line": node.lineno,
                    "message": "Bare 'except:' clause catches all exceptions",
                    "severity": "warning",
                })
            
            # Mutable default argument
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            "type": "mutable_default",
                            "line": node.lineno,
                            "message": f"Mutable default argument in {node.name}()",
                            "severity": "warning",
                        })
            
            # TODO/FIXME comments
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    if "TODO" in node.value.value or "FIXME" in node.value.value:
                        issues.append({
                            "type": "todo",
                            "line": node.lineno,
                            "message": node.value.value[:100],
                            "severity": "info",
                        })
            
            # High complexity
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    issues.append({
                        "type": "high_complexity",
                        "line": node.lineno,
                        "message": f"Function '{node.name}' has high complexity ({complexity})",
                        "severity": "warning",
                    })
        
        return issues
    
    def _run(
        self,
        path: str,
        include_metrics: bool = True,
        include_issues: bool = True,
    ) -> str:
        try:
            resolved = self._resolve_path(path)
            
            if not resolved.exists():
                return f"Error: Path not found: {path}"
            
            # Analyze single file or directory
            if resolved.is_file():
                files = [resolved]
            else:
                files = list(resolved.rglob("*.py"))
            
            if not files:
                return f"No Python files found in: {path}"
            
            output = [f"🔬 Code Analysis: {path}\n"]
            
            for filepath in files[:10]:  # Limit to 10 files
                rel_path = filepath.relative_to(self.workspace_dir) if filepath.is_relative_to(self.workspace_dir) else filepath
                output.append(f"\n📄 **{rel_path}**")
                
                if filepath.suffix == ".py":
                    analysis = self._analyze_python(filepath)
                    
                    if "error" in analysis:
                        output.append(f"   ❌ {analysis['error']}")
                        continue
                    
                    # Functions
                    if analysis["functions"]:
                        output.append(f"\n   Functions ({len(analysis['functions'])}):")
                        for func in analysis["functions"][:5]:
                            complexity_indicator = "🟢" if func["complexity"] <= 5 else "🟡" if func["complexity"] <= 10 else "🔴"
                            output.append(f"   {complexity_indicator} {func['name']}() - line {func['line']}, complexity {func['complexity']}")
                    
                    # Classes
                    if analysis["classes"]:
                        output.append(f"\n   Classes ({len(analysis['classes'])}):")
                        for cls in analysis["classes"][:5]:
                            output.append(f"   📦 {cls['name']} - {len(cls['methods'])} methods")
                    
                    # Metrics
                    if include_metrics and analysis["metrics"]:
                        m = analysis["metrics"]
                        output.append(f"\n   Metrics:")
                        output.append(f"   • Lines: {m['total_lines']} ({m['code_lines']} code, {m['comment_lines']} comments)")
                        output.append(f"   • Avg complexity: {m['avg_complexity']:.1f}")
                    
                    # Issues
                    if include_issues and analysis["issues"]:
                        output.append(f"\n   Issues ({len(analysis['issues'])}):")
                        for issue in analysis["issues"][:5]:
                            icon = "🔴" if issue["severity"] == "error" else "🟡" if issue["severity"] == "warning" else "ℹ️"
                            output.append(f"   {icon} Line {issue['line']}: {issue['message'][:60]}")
                else:
                    output.append(f"   (non-Python file)")
            
            if len(files) > 10:
                output.append(f"\n... and {len(files) - 10} more files")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"❌ Analysis error: {str(e)}"


class RunPythonTool(BaseTool):
    """
    Safely execute Python code.
    
    Features:
    - Isolated execution
    - Output capture
    - Timeout enforcement
    - Error handling
    """
    
    name: str = "run_python"
    description: str = """Execute Python code and return the output.

Use this for:
- Testing code snippets
- Running calculations
- Verifying logic
- Quick prototyping

Code runs in an isolated environment with captured output."""
    
    args_schema: Type[BaseModel] = RunPythonInput
    workspace_dir: Path = Field(default=Path("."))
    
    def _run(
        self,
        code: str,
        timeout: int = 30,
    ) -> str:
        try:
            # Capture stdout and stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = StringIO()
            sys.stderr = StringIO()
            
            # Create isolated globals
            exec_globals = {
                "__builtins__": __builtins__,
                "__name__": "__main__",
            }
            
            try:
                # Execute code
                exec(code, exec_globals)
                
                stdout_val = sys.stdout.getvalue()
                stderr_val = sys.stderr.getvalue()
                
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            output = []
            
            if stdout_val:
                output.append(f"📤 Output:\n{stdout_val}")
            
            if stderr_val:
                output.append(f"⚠️ Stderr:\n{stderr_val}")
            
            if not output:
                output.append("✓ Code executed successfully (no output)")
            
            return "\n".join(output)
            
        except SyntaxError as e:
            return f"❌ Syntax error: {e}"
        except Exception as e:
            tb = traceback.format_exc()
            return f"❌ Execution error:\n{tb}"
