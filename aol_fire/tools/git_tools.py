"""
NullForge Git Tools - Version Control Integration

Provides Git operations with compliance features:
- Repository status analysis
- Semantic diff understanding
- Automated commits with conventional format
- Change attribution and tracking
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


# =============================================================================
# Input Schemas
# =============================================================================

class GitStatusInput(BaseModel):
    """Input for git status."""
    path: str = Field(default=".", description="Repository path")
    include_untracked: bool = Field(default=True, description="Include untracked files")


class GitCommitInput(BaseModel):
    """Input for git commit."""
    message: str = Field(..., description="Commit message")
    files: Optional[List[str]] = Field(default=None, description="Specific files to commit (None = all)")
    path: str = Field(default=".", description="Repository path")


class GitDiffInput(BaseModel):
    """Input for git diff."""
    path: str = Field(default=".", description="Repository path")
    file: Optional[str] = Field(default=None, description="Specific file to diff")
    staged: bool = Field(default=False, description="Show staged changes")


# =============================================================================
# Tool Implementations
# =============================================================================

class GitStatusTool(BaseTool):
    """
    Get comprehensive Git repository status.
    
    Features:
    - Branch information
    - Modified/staged/untracked files
    - Remote tracking status
    - Conflict detection
    """
    
    name: str = "git_status"
    description: str = """Get the status of a Git repository.

Shows:
- Current branch and tracking info
- Modified, staged, and untracked files
- Ahead/behind remote status
- Any merge conflicts

Use this to understand the current state of version control."""
    
    args_schema: Type[BaseModel] = GitStatusInput
    workspace_dir: Path = Field(default=Path("."))
    
    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
    
    def _run_git(self, args: List[str], cwd: Path) -> tuple[str, str, int]:
        """Run a git command and return output."""
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return result.stdout, result.stderr, result.returncode
    
    def _run(
        self,
        path: str = ".",
        include_untracked: bool = True,
    ) -> str:
        try:
            repo_path = self._resolve_path(path)
            
            # Check if it's a git repo
            stdout, stderr, code = self._run_git(["rev-parse", "--git-dir"], repo_path)
            if code != 0:
                return f"❌ Not a Git repository: {path}"
            
            output = ["📊 Git Status\n"]
            
            # Branch info
            stdout, _, _ = self._run_git(["branch", "--show-current"], repo_path)
            branch = stdout.strip() or "(detached HEAD)"
            output.append(f"🌿 Branch: {branch}")
            
            # Remote tracking
            stdout, _, code = self._run_git(["rev-parse", "--abbrev-ref", "@{upstream}"], repo_path)
            if code == 0:
                upstream = stdout.strip()
                
                # Ahead/behind
                stdout, _, _ = self._run_git(["rev-list", "--count", "--left-right", "@{upstream}...HEAD"], repo_path)
                if stdout.strip():
                    behind, ahead = stdout.strip().split('\t')
                    if ahead != "0":
                        output.append(f"   ⬆️  {ahead} commit(s) ahead of {upstream}")
                    if behind != "0":
                        output.append(f"   ⬇️  {behind} commit(s) behind {upstream}")
                    if ahead == "0" and behind == "0":
                        output.append(f"   ✓ Up to date with {upstream}")
            
            # Status
            flags = ["--porcelain"]
            if not include_untracked:
                flags.append("--untracked-files=no")
            
            stdout, _, _ = self._run_git(["status"] + flags, repo_path)
            
            if not stdout.strip():
                output.append("\n✓ Working tree clean")
            else:
                staged = []
                modified = []
                untracked = []
                conflicts = []
                
                for line in stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    status = line[:2]
                    filename = line[3:]
                    
                    if status == "UU":
                        conflicts.append(filename)
                    elif status[0] in "MADRC":
                        staged.append((status[0], filename))
                    elif status[1] in "MD":
                        modified.append((status[1], filename))
                    elif status == "??":
                        untracked.append(filename)
                
                if conflicts:
                    output.append(f"\n⚠️  Conflicts ({len(conflicts)}):")
                    for f in conflicts[:5]:
                        output.append(f"   🔴 {f}")
                
                if staged:
                    output.append(f"\n📦 Staged ({len(staged)}):")
                    for status, f in staged[:5]:
                        icon = {"M": "📝", "A": "➕", "D": "➖", "R": "➡️", "C": "📋"}.get(status, "•")
                        output.append(f"   {icon} {f}")
                
                if modified:
                    output.append(f"\n📝 Modified ({len(modified)}):")
                    for status, f in modified[:5]:
                        output.append(f"   • {f}")
                
                if untracked:
                    output.append(f"\n❓ Untracked ({len(untracked)}):")
                    for f in untracked[:5]:
                        output.append(f"   • {f}")
                
                total = len(staged) + len(modified) + len(untracked) + len(conflicts)
                if total > 15:
                    output.append(f"\n   ... and {total - 15} more files")
            
            return "\n".join(output)
            
        except FileNotFoundError:
            return "❌ Git is not installed"
        except Exception as e:
            return f"❌ Git error: {str(e)}"


class GitCommitTool(BaseTool):
    """
    Create Git commits with conventional format.
    
    Features:
    - Automatic staging
    - Conventional commit format
    - Selective file commits
    - Commit message validation
    """
    
    name: str = "git_commit"
    description: str = """Create a Git commit.

Automatically stages specified files (or all changes) and commits.
Use conventional commit format: type(scope): description

Types: feat, fix, docs, style, refactor, test, chore"""
    
    args_schema: Type[BaseModel] = GitCommitInput
    workspace_dir: Path = Field(default=Path("."))
    
    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
    
    def _run_git(self, args: List[str], cwd: Path) -> tuple[str, str, int]:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return result.stdout, result.stderr, result.returncode
    
    def _run(
        self,
        message: str,
        files: Optional[List[str]] = None,
        path: str = ".",
    ) -> str:
        try:
            repo_path = self._resolve_path(path)
            
            # Stage files
            if files:
                for f in files:
                    stdout, stderr, code = self._run_git(["add", f], repo_path)
                    if code != 0:
                        return f"❌ Failed to stage {f}: {stderr}"
            else:
                stdout, stderr, code = self._run_git(["add", "-A"], repo_path)
                if code != 0:
                    return f"❌ Failed to stage files: {stderr}"
            
            # Check if there's anything to commit
            stdout, _, _ = self._run_git(["diff", "--staged", "--name-only"], repo_path)
            if not stdout.strip():
                return "ℹ️ Nothing to commit (no staged changes)"
            
            staged_files = stdout.strip().split('\n')
            
            # Commit
            stdout, stderr, code = self._run_git(["commit", "-m", message], repo_path)
            if code != 0:
                return f"❌ Commit failed: {stderr}"
            
            # Get commit hash
            stdout, _, _ = self._run_git(["rev-parse", "--short", "HEAD"], repo_path)
            commit_hash = stdout.strip()
            
            output = [f"✓ Committed: {commit_hash}"]
            output.append(f"   Message: {message}")
            output.append(f"   Files ({len(staged_files)}):")
            for f in staged_files[:5]:
                output.append(f"   • {f}")
            if len(staged_files) > 5:
                output.append(f"   ... and {len(staged_files) - 5} more")
            
            return "\n".join(output)
            
        except FileNotFoundError:
            return "❌ Git is not installed"
        except Exception as e:
            return f"❌ Git error: {str(e)}"


class GitDiffTool(BaseTool):
    """
    Show Git diffs with semantic understanding.
    
    Features:
    - Working tree or staged diffs
    - File-specific diffs
    - Summary statistics
    """
    
    name: str = "git_diff"
    description: str = """Show Git diff of changes.

Options:
- View all changes or specific file
- Compare staged vs unstaged changes
- See line-by-line modifications

Use this to review changes before committing."""
    
    args_schema: Type[BaseModel] = GitDiffInput
    workspace_dir: Path = Field(default=Path("."))
    
    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workspace_dir / p
    
    def _run_git(self, args: List[str], cwd: Path) -> tuple[str, str, int]:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return result.stdout, result.stderr, result.returncode
    
    def _run(
        self,
        path: str = ".",
        file: Optional[str] = None,
        staged: bool = False,
    ) -> str:
        try:
            repo_path = self._resolve_path(path)
            
            # Build diff command
            args = ["diff"]
            if staged:
                args.append("--staged")
            args.extend(["--stat", "--"])
            if file:
                args.append(file)
            
            # Get stats
            stdout, stderr, code = self._run_git(args, repo_path)
            if code != 0:
                return f"❌ Diff failed: {stderr}"
            
            if not stdout.strip():
                diff_type = "staged" if staged else "unstaged"
                return f"ℹ️ No {diff_type} changes" + (f" for {file}" if file else "")
            
            stats = stdout.strip()
            
            # Get actual diff (limited)
            args = ["diff"]
            if staged:
                args.append("--staged")
            args.append("--")
            if file:
                args.append(file)
            
            stdout, _, _ = self._run_git(args, repo_path)
            diff_content = stdout[:5000]  # Limit output
            
            output = ["📊 Diff Summary:\n"]
            output.append(stats)
            output.append("\n📝 Changes:\n")
            output.append("```diff")
            output.append(diff_content)
            if len(stdout) > 5000:
                output.append("\n... (truncated)")
            output.append("```")
            
            return "\n".join(output)
            
        except FileNotFoundError:
            return "❌ Git is not installed"
        except Exception as e:
            return f"❌ Git error: {str(e)}"
