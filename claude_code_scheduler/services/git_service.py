"""Git Service for Claude Code Scheduler.

This module provides Git operations including worktree management for
job isolation, enabling parallel execution without repository conflicts.

Key Components:
    - GitService: Main service class for git operations
    - GitServiceError: Exception for git operation failures

Dependencies:
    - subprocess: Git command execution
    - pathlib: Path handling

Related Modules:
    - models.job: JobWorkingDirectory with worktree configuration
    - services.sequential_scheduler: Uses GitService for job worktrees
    - ui.dialogs.job_editor_dialog: UI for worktree configuration

Calls:
    - subprocess.run: Execute git commands
    - git worktree add/remove: Manage worktrees

Called By:
    - SequentialScheduler.start_job: Create worktree for job
    - JobEditorDialog: Validate git repository

Example:
    >>> from claude_code_scheduler.services.git_service import GitService
    >>> git = GitService("~/projects/myrepo")
    >>> git.create_worktree("trees/feature-x", "main")

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import os
import subprocess  # nosec B404 - required for git commands
from pathlib import Path

from claude_code_scheduler.logging_config import get_logger

logger = get_logger(__name__)


class GitServiceError(Exception):
    """Error from git operations."""

    pass


class GitService:
    """Service for Git operations including worktree management."""

    def __init__(self, repo_path: str) -> None:
        """Initialize GitService.

        Args:
            repo_path: Path to the git repository.

        Raises:
            GitServiceError: If path is not a git repository.
        """
        self.repo_path = Path(os.path.expanduser(repo_path)).resolve()
        if not self._is_git_repo():
            raise GitServiceError(f"Not a git repository: {self.repo_path}")

    def _is_git_repo(self) -> bool:
        """Check if repo_path is a git repository."""
        git_dir = self.repo_path / ".git"
        return git_dir.exists() or (self.repo_path / "HEAD").exists()

    def _run_git(self, args: list[str]) -> str:
        """Run a git command and return output.

        Args:
            args: Git command arguments (without 'git' prefix).

        Returns:
            Command output as string.

        Raises:
            GitServiceError: If command fails.
        """
        cmd = ["git"] + args
        logger.debug("Running: %s in %s", " ".join(cmd), self.repo_path)
        try:
            result = subprocess.run(  # nosec B603, B607
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitServiceError(f"Git command failed: {e.stderr}") from e

    def list_branches(self, include_remote: bool = False) -> list[str]:
        """List available branches.

        Args:
            include_remote: Include remote branches.

        Returns:
            List of branch names.
        """
        args = ["branch", "--format=%(refname:short)"]
        if include_remote:
            args.append("-a")
        output = self._run_git(args)
        if not output:
            return []
        branches = [b.strip() for b in output.split("\n") if b.strip()]
        # Filter out HEAD references
        return [b for b in branches if not b.endswith("/HEAD")]

    def get_current_branch(self) -> str:
        """Get current branch name.

        Returns:
            Current branch name.
        """
        return self._run_git(["branch", "--show-current"])

    def list_worktrees(self) -> list[dict[str, str]]:
        """List existing worktrees.

        Returns:
            List of dicts with 'path', 'branch', 'commit' keys.
        """
        output = self._run_git(["worktree", "list", "--porcelain"])
        if not output:
            return []

        worktrees: list[dict[str, str]] = []
        current: dict[str, str] = {}

        for line in output.split("\n"):
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current["commit"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:].replace("refs/heads/", "")
            elif line == "detached":
                current["branch"] = "(detached)"
            elif line == "bare":
                current["bare"] = "true"

        if current:
            worktrees.append(current)

        return worktrees

    def _branch_exists(self, branch: str) -> bool:
        """Check if a branch exists.

        Args:
            branch: Branch name to check.

        Returns:
            True if branch exists.
        """
        try:
            self._run_git(["rev-parse", "--verify", f"refs/heads/{branch}"])
            return True
        except GitServiceError:
            return False

    def create_worktree(
        self,
        name: str,
        base_branch: str | None = None,
    ) -> str:
        """Create a new worktree in trees/ directory (idempotent).

        Always creates a new branch named after the worktree, based on the
        specified base branch (or current branch if not specified).

        This operation is idempotent:
        - If worktree directory already exists, logs warning and returns path
        - If branch already exists, reuses it for the worktree

        Args:
            name: Name for the worktree directory (created in trees/).
                  Also used as the new branch name.
            base_branch: Branch to base the new branch on. If None, uses current branch.

        Returns:
            Path to the created worktree.

        Raises:
            GitServiceError: If worktree creation fails.
        """
        trees_dir = self.repo_path / "trees"
        trees_dir.mkdir(exist_ok=True)

        worktree_path = trees_dir / name

        # Check if worktree directory already exists
        if worktree_path.exists():
            logger.warning(
                "Worktree '%s' already exists at %s, skipping creation",
                name,
                worktree_path,
            )
            return str(worktree_path)

        # Determine base branch
        source_branch = base_branch or self.get_current_branch()

        # Check if the branch already exists
        new_branch = name
        if self._branch_exists(new_branch):
            # Branch exists, create worktree using existing branch
            logger.warning(
                "Branch '%s' already exists, creating worktree with existing branch",
                new_branch,
            )
            args = ["worktree", "add", str(worktree_path), new_branch]
        else:
            # Create new branch from base
            logger.info(
                "Creating worktree '%s' with new branch '%s' from '%s'",
                name,
                new_branch,
                source_branch,
            )
            args = ["worktree", "add", "-b", new_branch, str(worktree_path), source_branch]

        self._run_git(args)
        logger.info("Created worktree: %s", worktree_path)

        return str(worktree_path)

    def remove_worktree(self, name: str, force: bool = False) -> None:
        """Remove a worktree from trees/ directory.

        Args:
            name: Name of the worktree to remove.
            force: Force removal even if dirty.

        Raises:
            GitServiceError: If removal fails.
        """
        worktree_path = self.repo_path / "trees" / name

        if not worktree_path.exists():
            logger.warning("Worktree does not exist: %s", worktree_path)
            return

        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(worktree_path))

        self._run_git(args)
        logger.info("Removed worktree: %s", worktree_path)

    def ensure_trees_gitignored(self) -> bool:
        """Ensure trees/ is in .gitignore.

        Returns:
            True if .gitignore was modified.
        """
        gitignore_path = self.repo_path / ".gitignore"
        trees_pattern = "/trees/"

        # Check if already ignored
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if trees_pattern in content or "trees/" in content:
                logger.debug("trees/ already in .gitignore")
                return False

        # Add to .gitignore
        with open(gitignore_path, "a") as f:
            if gitignore_path.exists() and not gitignore_path.read_text().endswith("\n"):
                f.write("\n")
            f.write(f"\n# Git worktrees for job isolation\n{trees_pattern}\n")

        logger.info("Added trees/ to .gitignore")
        return True

    def get_worktree_path(self, name: str) -> str:
        """Get full path to a worktree.

        Args:
            name: Name of the worktree.

        Returns:
            Full path to the worktree.
        """
        return str(self.repo_path / "trees" / name)
