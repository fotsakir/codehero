"""
HeroAgent Glob Tool

Find files by pattern.
"""

import os
import glob as glob_module
from typing import Dict, Any, Optional, List

from .base import BaseTool, ToolResult


class GlobTool(BaseTool):
    """Find files by glob pattern."""

    name = "Glob"
    description = "Find files matching a glob pattern (e.g., '**/*.py', 'src/**/*.ts')."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.max_results = self.config.get('max_results', 1000)

    def execute(self, pattern: str, path: Optional[str] = None, **kwargs) -> ToolResult:
        """Find files matching pattern.

        Args:
            pattern: Glob pattern to match
            path: Optional directory to search in

        Returns:
            ToolResult with list of matching files
        """
        if not pattern:
            return ToolResult(output="Error: No pattern provided", is_error=True)

        # Determine search path
        search_path = os.path.expanduser(path) if path else os.getcwd()

        if not os.path.exists(search_path):
            return ToolResult(output=f"Error: Path not found: {search_path}", is_error=True)

        try:
            # Build full pattern
            if os.path.isabs(pattern):
                full_pattern = pattern
            else:
                full_pattern = os.path.join(search_path, pattern)

            # Find matches
            matches = glob_module.glob(full_pattern, recursive=True)

            # Sort by modification time (newest first)
            matches.sort(key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0, reverse=True)

            # Limit results
            total_matches = len(matches)
            matches = matches[:self.max_results]

            # Format output
            if not matches:
                return ToolResult(
                    output=f"No files found matching pattern: {pattern}",
                    metadata={'total': 0}
                )

            output = '\n'.join(matches)
            if total_matches > self.max_results:
                output += f"\n\n... ({total_matches - self.max_results} more files)"

            return ToolResult(
                output=output,
                metadata={
                    'total': total_matches,
                    'returned': len(matches)
                }
            )

        except Exception as e:
            return ToolResult(output=f"Error searching files: {str(e)}", is_error=True)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against (e.g., '**/*.py', 'src/*.ts')"
                },
                "path": {
                    "type": "string",
                    "description": "Optional directory to search in. Defaults to current directory."
                }
            },
            "required": ["pattern"]
        }
