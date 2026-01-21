"""
HeroAgent Edit Tool

Edit files with search/replace and protected path checking.
"""

import os
from typing import Dict, Any, Optional

from .base import BaseTool, ToolResult
from .protected import check_path_permission


class EditTool(BaseTool):
    """Edit files with search/replace."""

    name = "Edit"
    description = "Edit a file by replacing a specific string. The old_string must match exactly."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.backup = self.config.get('backup', False)

    def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **kwargs
    ) -> ToolResult:
        """Edit a file.

        Args:
            file_path: Path to the file to edit
            old_string: String to search for
            new_string: String to replace with
            replace_all: Replace all occurrences (default: False)

        Returns:
            ToolResult with status
        """
        if not file_path:
            return ToolResult(output="Error: No file path provided", is_error=True)

        if old_string is None:
            return ToolResult(output="Error: No old_string provided", is_error=True)

        if new_string is None:
            return ToolResult(output="Error: No new_string provided", is_error=True)

        if old_string == new_string:
            return ToolResult(output="Error: old_string and new_string are identical", is_error=True)

        # Expand path
        file_path = os.path.expanduser(file_path)

        # Check protected paths
        allowed, error_msg = check_path_permission(file_path)
        if not allowed:
            return ToolResult(output=error_msg, is_error=True)

        if not os.path.exists(file_path):
            return ToolResult(output=f"Error: File not found: {file_path}", is_error=True)

        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if old_string exists
            if old_string not in content:
                return ToolResult(
                    output=f"Error: String not found in file. Make sure old_string matches exactly.",
                    is_error=True
                )

            # Check for multiple occurrences when not using replace_all
            if not replace_all:
                count = content.count(old_string)
                if count > 1:
                    return ToolResult(
                        output=f"Error: Found {count} occurrences of old_string. Use replace_all=true to replace all, or provide more context to make the match unique.",
                        is_error=True
                    )

            # Create backup if enabled
            if self.backup:
                backup_path = file_path + '.bak'
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return ToolResult(
                output=f"Edited {file_path} ({replacements} replacement{'s' if replacements > 1 else ''})",
                metadata={
                    'replacements': replacements,
                    'file': file_path
                }
            )

        except PermissionError:
            return ToolResult(output=f"Error: Permission denied: {file_path}", is_error=True)
        except Exception as e:
            return ToolResult(output=f"Error editing file: {str(e)}", is_error=True)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to edit"
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to search for and replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "The string to replace old_string with"
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace all occurrences (default: false)"
                }
            },
            "required": ["file_path", "old_string", "new_string"]
        }
