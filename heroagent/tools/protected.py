"""
HeroAgent Protected Paths

Defines paths that should not be modified by the agent.
"""

import os
from typing import List, Optional

# Protected path prefixes - NEVER modify files in these directories
PROTECTED_PATHS = [
    '/opt/codehero/',
    '/etc/codehero/',
    '/var/backups/codehero/',
    '/etc/nginx/',
    '/etc/systemd/',
    '/etc/apache2/',
    '/etc/mysql/',
    '/etc/php/',
    '~/.claude',
    '/home/claude/.claude',
    '/root/.claude',
    # System paths
    '/bin/',
    '/sbin/',
    '/usr/bin/',
    '/usr/sbin/',
    '/boot/',
    '/proc/',
    '/sys/',
]

# Allowed path prefixes - files can only be written here
ALLOWED_PATHS = [
    '/var/www/projects/',
    '/opt/apps/',
    '/tmp/',
    '/home/claude/codehero/',  # For development
]


def is_protected_path(file_path: str) -> bool:
    """Check if a path is protected.

    Args:
        file_path: Path to check

    Returns:
        True if path is protected and should not be modified
    """
    # Expand and normalize path
    file_path = os.path.expanduser(file_path)
    file_path = os.path.abspath(file_path)

    # Check against protected paths
    for protected in PROTECTED_PATHS:
        protected = os.path.expanduser(protected)
        if file_path.startswith(protected):
            return True

    return False


def is_allowed_path(file_path: str, additional_allowed: Optional[List[str]] = None) -> bool:
    """Check if a path is in the allowed list.

    Args:
        file_path: Path to check
        additional_allowed: Additional allowed paths (e.g., from project config)

    Returns:
        True if path is allowed for writing
    """
    # Expand and normalize path
    file_path = os.path.expanduser(file_path)
    file_path = os.path.abspath(file_path)

    # Build allowed list
    allowed = list(ALLOWED_PATHS)
    if additional_allowed:
        allowed.extend(additional_allowed)

    # Check against allowed paths
    for allowed_path in allowed:
        allowed_path = os.path.expanduser(allowed_path)
        allowed_path = os.path.abspath(allowed_path)
        if file_path.startswith(allowed_path):
            return True

    return False


def check_path_permission(file_path: str, additional_allowed: Optional[List[str]] = None) -> tuple:
    """Check if writing to a path is permitted.

    Args:
        file_path: Path to check
        additional_allowed: Additional allowed paths

    Returns:
        Tuple of (is_allowed: bool, error_message: str or None)
    """
    # First check if explicitly protected
    if is_protected_path(file_path):
        return False, f"PROTECTED PATH: Cannot modify files in protected directory. Path: {file_path}"

    # Then check if in allowed paths
    if not is_allowed_path(file_path, additional_allowed):
        return False, f"PATH NOT ALLOWED: Can only write to /var/www/projects/ or /opt/apps/. Path: {file_path}"

    return True, None
