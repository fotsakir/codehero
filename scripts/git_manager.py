#!/usr/bin/env python3
"""
Git Manager - Local Git Version Control for CodeHero Projects
Manages Git repositories for project version control with auto-commit support.
"""

import subprocess
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# .gitignore patterns by project type
GITIGNORE_PATTERNS = {
    'common': [
        '# OS files',
        '.DS_Store',
        'Thumbs.db',
        '',
        '# IDE',
        '.idea/',
        '.vscode/',
        '*.swp',
        '*.swo',
        '',
        '# Environment',
        '.env',
        '.env.local',
        '.env.*.local',
        '*.log',
        '',
        '# Python',
        '__pycache__/',
        '*.py[cod]',
        '*$py.class',
        '.Python',
        '*.so',
        '',
        '# Node',
        'node_modules/',
        '',
    ],
    'php': [
        '# PHP/Composer',
        'vendor/',
        'composer.lock',
        'storage/logs/',
        'storage/framework/cache/',
        'storage/framework/sessions/',
        'storage/framework/views/',
        'bootstrap/cache/',
        '.phpunit.result.cache',
    ],
    'python': [
        '# Python',
        'venv/',
        '.venv/',
        'env/',
        '.env/',
        '*.egg-info/',
        'dist/',
        'build/',
        '.pytest_cache/',
        '.coverage',
        'htmlcov/',
    ],
    'node': [
        '# Node.js',
        'node_modules/',
        'dist/',
        'build/',
        '.next/',
        '.nuxt/',
        'package-lock.json',
        'yarn.lock',
        'pnpm-lock.yaml',
    ],
    'dotnet': [
        '# .NET',
        'bin/',
        'obj/',
        '*.user',
        '*.suo',
        '*.userosscache',
        '*.sln.docstates',
        'packages/',
        '*.nupkg',
    ],
    'java': [
        '# Java',
        'target/',
        '*.class',
        '*.jar',
        '*.war',
        '.gradle/',
        'build/',
    ],
    'flutter': [
        '# Flutter/Dart',
        '.dart_tool/',
        '.packages',
        'build/',
        '.flutter-plugins',
        '.flutter-plugins-dependencies',
    ],
}


class GitManager:
    """Manages Git operations for a project repository."""

    def __init__(self, repo_path: str, project_type: str = 'web', tech_stack: str = ''):
        """
        Initialize GitManager for a repository path.

        Args:
            repo_path: Path to the repository directory
            project_type: Type of project (web, app, php, python, etc.)
            tech_stack: Technology stack string for gitignore generation
        """
        self.repo_path = repo_path
        self.project_type = project_type
        self.tech_stack = tech_stack.lower() if tech_stack else ''
        self.git_dir = os.path.join(repo_path, '.git')

    def is_initialized(self) -> bool:
        """Check if Git repository is already initialized."""
        return os.path.isdir(self.git_dir)

    def init_repo(self) -> Tuple[bool, str]:
        """
        Initialize a new Git repository.

        Returns:
            Tuple of (success, message)
        """
        if self.is_initialized():
            return True, "Repository already initialized"

        try:
            # Create directory if it doesn't exist
            if not os.path.exists(self.repo_path):
                os.makedirs(self.repo_path, mode=0o2775, exist_ok=True)

            # Initialize git
            result = self._run_git(['init'])
            if result[0] != 0:
                return False, f"Failed to init: {result[2]}"

            # Configure git
            self._run_git(['config', 'user.email', 'codehero@localhost'])
            self._run_git(['config', 'user.name', 'CodeHero'])

            # Create .gitignore
            self.create_gitignore()

            # Initial commit
            self._run_git(['add', '.gitignore'])
            self._run_git(['commit', '-m', 'Initial commit - CodeHero project initialized'])

            return True, "Repository initialized successfully"

        except Exception as e:
            return False, f"Error initializing repository: {str(e)}"

    def create_gitignore(self) -> bool:
        """
        Create .gitignore file based on project type and tech stack.

        Returns:
            True if created successfully
        """
        gitignore_path = os.path.join(self.repo_path, '.gitignore')

        # Start with common patterns
        patterns = GITIGNORE_PATTERNS['common'].copy()

        # Add patterns based on project type
        if self.project_type in GITIGNORE_PATTERNS:
            patterns.extend(['', f'# {self.project_type.title()} specific'])
            patterns.extend(GITIGNORE_PATTERNS[self.project_type])

        # Add patterns based on tech stack
        for tech, tech_patterns in GITIGNORE_PATTERNS.items():
            if tech != 'common' and tech in self.tech_stack:
                patterns.extend(['', f'# {tech.title()}'])
                patterns.extend(tech_patterns)

        # Write gitignore
        try:
            with open(gitignore_path, 'w') as f:
                f.write('\n'.join(patterns) + '\n')
            return True
        except Exception as e:
            print(f"[Git] Error creating .gitignore: {e}")
            return False

    def auto_commit(self, ticket_number: str, title: str,
                    session_id: int = None, status: str = 'awaiting_input',
                    duration_seconds: int = 0, tokens_used: int = 0) -> Tuple[bool, str, Optional[str]]:
        """
        Create an automatic commit with ticket information.

        Args:
            ticket_number: Ticket number (e.g., "PROJ-0001")
            title: Ticket title
            session_id: Optional session ID
            status: Ticket status
            duration_seconds: Duration in seconds
            tokens_used: Number of tokens used

        Returns:
            Tuple of (success, message, commit_hash)
        """
        if not self.is_initialized():
            # Initialize repo on first commit
            success, msg = self.init_repo()
            if not success:
                return False, msg, None

        try:
            # Check for changes
            status_result = self._run_git(['status', '--porcelain'])
            if status_result[0] != 0:
                return False, f"Failed to get status: {status_result[2]}", None

            if not status_result[1].strip():
                return True, "No changes to commit", None

            # Stage all changes
            self._run_git(['add', '-A'])

            # Build commit message
            duration_str = self._format_duration(duration_seconds)
            message_lines = [
                f"[{ticket_number}] {title}",
                "",
                f"Ticket: {ticket_number}",
            ]
            if session_id:
                message_lines.append(f"Session: #{session_id}")
            message_lines.extend([
                f"Status: {status}",
                f"Duration: {duration_str}",
                f"Tokens: {tokens_used:,}",
            ])

            # Get file stats
            diff_stat = self._run_git(['diff', '--cached', '--stat'])
            if diff_stat[1]:
                # Extract file count from stat
                lines = diff_stat[1].strip().split('\n')
                if lines:
                    message_lines.extend(["", lines[-1] if len(lines) > 1 else f"Files changed: {len(lines)}"])

            commit_message = '\n'.join(message_lines)

            # Create commit
            result = self._run_git(['commit', '-m', commit_message])
            if result[0] != 0:
                return False, f"Failed to commit: {result[2]}", None

            # Get commit hash
            hash_result = self._run_git(['rev-parse', 'HEAD'])
            commit_hash = hash_result[1].strip() if hash_result[0] == 0 else None

            return True, "Commit created successfully", commit_hash

        except Exception as e:
            return False, f"Error creating commit: {str(e)}", None

    def get_commits(self, limit: int = 50) -> List[Dict]:
        """
        Get list of recent commits.

        Args:
            limit: Maximum number of commits to return

        Returns:
            List of commit dictionaries
        """
        if not self.is_initialized():
            return []

        try:
            # Get commits with format: hash|short_hash|author|date|subject
            format_str = '%H|%h|%an|%ai|%s'
            result = self._run_git([
                'log', f'-{limit}', f'--format={format_str}'
            ])

            if result[0] != 0 or not result[1].strip():
                return []

            commits = []
            for line in result[1].strip().split('\n'):
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'short_hash': parts[1],
                        'author': parts[2],
                        'date': parts[3],
                        'message': parts[4],
                    })

            return commits

        except Exception as e:
            print(f"[Git] Error getting commits: {e}")
            return []

    def get_commit_detail(self, commit_hash: str) -> Optional[Dict]:
        """
        Get detailed information about a specific commit.

        Args:
            commit_hash: Full or short commit hash

        Returns:
            Commit detail dictionary or None
        """
        if not self.is_initialized():
            return None

        try:
            # Get commit info
            format_str = '%H|%h|%an|%ae|%ai|%B'
            result = self._run_git(['show', '-s', f'--format={format_str}', commit_hash])

            if result[0] != 0:
                return None

            parts = result[1].split('|', 5)
            if len(parts) < 6:
                return None

            # Get file stats
            stat_result = self._run_git(['show', '--stat', '--format=', commit_hash])
            files_changed = 0
            insertions = 0
            deletions = 0

            if stat_result[0] == 0 and stat_result[1]:
                # Parse stat summary line
                lines = stat_result[1].strip().split('\n')
                if lines:
                    summary = lines[-1]
                    # Parse "X files changed, Y insertions(+), Z deletions(-)"
                    match = re.search(r'(\d+) files? changed', summary)
                    if match:
                        files_changed = int(match.group(1))
                    match = re.search(r'(\d+) insertions?\(\+\)', summary)
                    if match:
                        insertions = int(match.group(1))
                    match = re.search(r'(\d+) deletions?\(-\)', summary)
                    if match:
                        deletions = int(match.group(1))

            # Get changed files list
            files_result = self._run_git(['show', '--name-status', '--format=', commit_hash])
            changed_files = []
            if files_result[0] == 0 and files_result[1]:
                for line in files_result[1].strip().split('\n'):
                    if '\t' in line:
                        status, filepath = line.split('\t', 1)
                        changed_files.append({
                            'status': status,
                            'path': filepath,
                        })

            return {
                'hash': parts[0],
                'short_hash': parts[1],
                'author': parts[2],
                'author_email': parts[3],
                'date': parts[4],
                'message': parts[5].strip(),
                'files_changed': files_changed,
                'insertions': insertions,
                'deletions': deletions,
                'files': changed_files,
            }

        except Exception as e:
            print(f"[Git] Error getting commit detail: {e}")
            return None

    def get_diff(self, commit_hash: str, file_path: str = None) -> Optional[str]:
        """
        Get diff for a commit, optionally for a specific file.

        Args:
            commit_hash: Commit hash
            file_path: Optional file path to get diff for

        Returns:
            Diff string or None
        """
        if not self.is_initialized():
            return None

        try:
            args = ['show', '--format=', commit_hash]
            if file_path:
                args.extend(['--', file_path])

            result = self._run_git(args)
            return result[1] if result[0] == 0 else None

        except Exception as e:
            print(f"[Git] Error getting diff: {e}")
            return None

    def get_file_at_commit(self, commit_hash: str, file_path: str) -> Optional[str]:
        """
        Get file content at a specific commit.

        Args:
            commit_hash: Commit hash
            file_path: File path relative to repo root

        Returns:
            File content or None
        """
        if not self.is_initialized():
            return None

        try:
            result = self._run_git(['show', f'{commit_hash}:{file_path}'])
            return result[1] if result[0] == 0 else None

        except Exception as e:
            print(f"[Git] Error getting file at commit: {e}")
            return None

    def get_status(self) -> Dict:
        """
        Get current repository status.

        Returns:
            Dictionary with status information
        """
        if not self.is_initialized():
            return {'initialized': False}

        try:
            # Get branch
            branch_result = self._run_git(['branch', '--show-current'])
            branch = branch_result[1].strip() if branch_result[0] == 0 else 'unknown'

            # Get status
            status_result = self._run_git(['status', '--porcelain'])

            modified = []
            added = []
            deleted = []
            untracked = []

            if status_result[0] == 0 and status_result[1]:
                for line in status_result[1].strip().split('\n'):
                    if len(line) >= 3:
                        status = line[:2]
                        filepath = line[3:]
                        if status == '??':
                            untracked.append(filepath)
                        elif 'M' in status:
                            modified.append(filepath)
                        elif 'A' in status:
                            added.append(filepath)
                        elif 'D' in status:
                            deleted.append(filepath)

            # Get last commit
            last_commit = None
            log_result = self._run_git(['log', '-1', '--format=%h|%s|%ai'])
            if log_result[0] == 0 and log_result[1]:
                parts = log_result[1].strip().split('|', 2)
                if len(parts) >= 3:
                    last_commit = {
                        'short_hash': parts[0],
                        'message': parts[1],
                        'date': parts[2],
                    }

            return {
                'initialized': True,
                'branch': branch,
                'modified': modified,
                'added': added,
                'deleted': deleted,
                'untracked': untracked,
                'has_changes': bool(modified or added or deleted or untracked),
                'last_commit': last_commit,
            }

        except Exception as e:
            print(f"[Git] Error getting status: {e}")
            return {'initialized': True, 'error': str(e)}

    def rollback_to_commit(self, target_hash: str, reason: str = "Manual rollback") -> Tuple[bool, str]:
        """
        Rollback to a specific commit by creating a new commit.
        This preserves history (safe rollback).

        Args:
            target_hash: Target commit hash to rollback to
            reason: Reason for rollback

        Returns:
            Tuple of (success, message)
        """
        if not self.is_initialized():
            return False, "Repository not initialized"

        try:
            # Verify target commit exists
            verify = self._run_git(['cat-file', '-t', target_hash])
            if verify[0] != 0:
                return False, f"Commit {target_hash} not found"

            # Get short hash for message
            short_result = self._run_git(['rev-parse', '--short', target_hash])
            short_hash = short_result[1].strip() if short_result[0] == 0 else target_hash[:7]

            # Checkout all files from target commit
            checkout_result = self._run_git(['checkout', target_hash, '--', '.'])
            if checkout_result[0] != 0:
                return False, f"Failed to checkout files: {checkout_result[2]}"

            # Stage all changes
            self._run_git(['add', '-A'])

            # Check if there are changes to commit
            status = self._run_git(['status', '--porcelain'])
            if not status[1].strip():
                return True, f"Already at commit {short_hash}"

            # Create rollback commit
            message = f"Rollback to {short_hash}: {reason}"
            commit_result = self._run_git(['commit', '-m', message])
            if commit_result[0] != 0:
                return False, f"Failed to create rollback commit: {commit_result[2]}"

            return True, f"Successfully rolled back to {short_hash}"

        except Exception as e:
            return False, f"Error during rollback: {str(e)}"

    def get_context_for_claude(self, max_commits: int = 5) -> str:
        """
        Generate Git context string to include in Claude's prompt.

        Args:
            max_commits: Maximum number of recent commits to show

        Returns:
            Formatted context string
        """
        if not self.is_initialized():
            return ""

        try:
            status = self.get_status()
            if not status.get('initialized'):
                return ""

            lines = [
                "=== GIT CONTEXT ===",
                f"Repository: {self.repo_path}",
                f"Branch: {status.get('branch', 'unknown')}",
            ]

            # Last commit
            if status.get('last_commit'):
                lc = status['last_commit']
                lines.append(f"Last commit: {lc['short_hash']} - {lc['message']}")

            # Uncommitted changes
            if status.get('has_changes'):
                lines.append("")
                lines.append("Uncommitted changes:")
                for f in status.get('modified', [])[:10]:
                    lines.append(f"  M {f}")
                for f in status.get('added', [])[:10]:
                    lines.append(f"  A {f}")
                for f in status.get('deleted', [])[:10]:
                    lines.append(f"  D {f}")
                for f in status.get('untracked', [])[:10]:
                    lines.append(f"  ? {f}")

            # Recent commits
            commits = self.get_commits(max_commits)
            if commits:
                lines.append("")
                lines.append("Recent commits:")
                for c in commits:
                    lines.append(f"  - {c['short_hash']} {c['message']}")

            lines.append("===================")
            return '\n'.join(lines)

        except Exception as e:
            print(f"[Git] Error getting context: {e}")
            return ""

    def _run_git(self, args: List[str]) -> Tuple[int, str, str]:
        """
        Run a git command in the repository.

        Args:
            args: Git command arguments (without 'git' prefix)

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            cmd = ['git', '-C', self.repo_path] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, '', 'Command timed out'
        except Exception as e:
            return 1, '', str(e)

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} min"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"


# Convenience function for quick repo operations
def get_git_manager(project: Dict) -> Optional[GitManager]:
    """
    Get GitManager for a project.

    Args:
        project: Project dictionary with web_path, app_path, project_type, tech_stack

    Returns:
        GitManager instance or None
    """
    # Determine which path to use
    path = project.get('web_path') or project.get('app_path')
    if not path or not os.path.exists(path):
        return None

    return GitManager(
        repo_path=path,
        project_type=project.get('project_type', 'web'),
        tech_stack=project.get('tech_stack', '')
    )


if __name__ == '__main__':
    # Test the GitManager
    import tempfile
    import shutil

    # Create temp directory for testing
    test_dir = tempfile.mkdtemp(prefix='git_test_')
    print(f"Testing in: {test_dir}")

    try:
        # Initialize
        gm = GitManager(test_dir, 'python', 'flask')
        success, msg = gm.init_repo()
        print(f"Init: {success} - {msg}")

        # Create a test file
        with open(os.path.join(test_dir, 'test.py'), 'w') as f:
            f.write('print("Hello World")\n')

        # Auto commit
        success, msg, commit_hash = gm.auto_commit(
            ticket_number='TEST-0001',
            title='Add test file',
            session_id=1,
            duration_seconds=120,
            tokens_used=5000
        )
        print(f"Commit: {success} - {msg} - {commit_hash}")

        # Get status
        status = gm.get_status()
        print(f"Status: {status}")

        # Get commits
        commits = gm.get_commits()
        print(f"Commits: {len(commits)}")
        for c in commits:
            print(f"  - {c['short_hash']} {c['message']}")

        # Get context for Claude
        context = gm.get_context_for_claude()
        print(f"\nClaude context:\n{context}")

    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print("\nTest completed, temp directory cleaned up.")
