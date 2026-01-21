"""
HeroAgent Hook Manager

Manages permission hooks for semi-autonomous mode.
Compatible with existing CodeHero semi_autonomous_hook.py.
"""

import os
import json
import subprocess
from typing import Dict, Any, Optional
from enum import Enum


class Permission(Enum):
    """Permission decision."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class HookManager:
    """Manages permission hooks for tool execution."""

    def __init__(self, hook_script: Optional[str] = None, skip_permissions: bool = False):
        """Initialize hook manager.

        Args:
            hook_script: Path to permission hook script
            skip_permissions: If True, always allow (autonomous mode)
        """
        self.hook_script = hook_script
        self.skip_permissions = skip_permissions
        self._hook_available = self._check_hook()

    def _check_hook(self) -> bool:
        """Check if hook script is available and executable."""
        if not self.hook_script:
            return False
        if not os.path.exists(self.hook_script):
            return False
        return os.access(self.hook_script, os.X_OK)

    def check_permission(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Permission:
        """Check if tool execution is permitted.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            context: Optional context (project path, ticket ID, etc.)

        Returns:
            Permission decision
        """
        # Autonomous mode - always allow
        if self.skip_permissions:
            return Permission.ALLOW

        # No hook configured - use defaults
        if not self._hook_available:
            return self._default_permission(tool_name, tool_input)

        # Call hook script
        return self._call_hook(tool_name, tool_input, context)

    def _default_permission(self, tool_name: str, tool_input: Dict[str, Any]) -> Permission:
        """Get default permission when no hook is configured.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters

        Returns:
            Permission decision
        """
        # Read-only tools are always allowed
        read_only_tools = {'Read', 'Glob', 'Grep'}
        if tool_name in read_only_tools:
            return Permission.ALLOW

        # Write operations need review
        if tool_name in {'Write', 'Edit'}:
            return Permission.ASK

        # Bash commands need careful review
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Dangerous commands
            dangerous_patterns = [
                'rm -rf',
                'rm -r /',
                'dd if=',
                'mkfs',
                ':(){',  # Fork bomb
                '> /dev/sd',
                'chmod -R 777',
                'wget -O - | sh',
                'curl | sh',
                'eval',
            ]
            for pattern in dangerous_patterns:
                if pattern in command:
                    return Permission.DENY
            # Ask for other bash commands
            return Permission.ASK

        return Permission.ASK

    def _call_hook(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Permission:
        """Call external hook script.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            context: Optional context

        Returns:
            Permission decision
        """
        try:
            # Prepare hook input
            hook_input = {
                'tool': tool_name,
                'input': tool_input,
            }
            if context:
                hook_input['context'] = context

            # Prepare environment
            env = os.environ.copy()
            env['CODEHERO_PROJECT_PATH'] = os.environ.get('CODEHERO_PROJECT_PATH', '')
            env['CODEHERO_TICKET_ID'] = os.environ.get('CODEHERO_TICKET_ID', '')
            env['CODEHERO_PROJECT_ID'] = os.environ.get('CODEHERO_PROJECT_ID', '')

            # Call hook
            result = subprocess.run(
                [self.hook_script],
                input=json.dumps(hook_input),
                capture_output=True,
                text=True,
                env=env,
                timeout=10,  # 10 second timeout
            )

            # Parse result
            output = result.stdout.strip().lower()
            if output == 'allow':
                return Permission.ALLOW
            elif output == 'deny':
                return Permission.DENY
            else:
                return Permission.ASK

        except subprocess.TimeoutExpired:
            # Hook timed out - deny for safety
            return Permission.DENY
        except Exception as e:
            # Hook failed - fall back to default
            return self._default_permission(tool_name, tool_input)

    def is_safe_path(self, path: str, allowed_paths: Optional[list] = None) -> bool:
        """Check if a path is safe to modify.

        Args:
            path: Path to check
            allowed_paths: List of allowed base paths

        Returns:
            True if path is safe
        """
        # Normalize path
        path = os.path.abspath(os.path.expanduser(path))

        # Always deny system paths
        dangerous_paths = [
            '/etc',
            '/bin',
            '/sbin',
            '/usr/bin',
            '/usr/sbin',
            '/boot',
            '/root',
            '/var/log',
            '/.git',
        ]
        for dangerous in dangerous_paths:
            if path.startswith(dangerous) or dangerous in path:
                return False

        # Check against allowed paths
        if allowed_paths:
            for allowed in allowed_paths:
                allowed = os.path.abspath(os.path.expanduser(allowed))
                if path.startswith(allowed):
                    return True
            return False

        return True

    def is_safe_command(self, command: str) -> bool:
        """Check if a bash command is safe to execute.

        Args:
            command: Command to check

        Returns:
            True if command is safe
        """
        # Very dangerous patterns
        very_dangerous = [
            'rm -rf /',
            'rm -rf /*',
            '> /dev/sd',
            'dd if=/dev/zero',
            'dd if=/dev/random',
            ':(){:|:&};:',  # Fork bomb
            'mkfs.',
            'wget.*|.*sh',
            'curl.*|.*sh',
            'chmod 777 /',
            'chown.*/',
        ]
        command_lower = command.lower()
        for pattern in very_dangerous:
            if pattern in command_lower:
                return False

        return True


class PermissionDeniedError(Exception):
    """Raised when a tool execution is denied."""

    def __init__(self, tool_name: str, reason: str = "Permission denied"):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"{tool_name}: {reason}")
