"""
HeroAgent Write Tool

Write/create files with protected path checking.
"""

import os
import html
from typing import Dict, Any, Optional

from .base import BaseTool, ToolResult
from .protected import check_path_permission


# File extensions that might contain HTML entities that need unescaping
HTML_EXTENSIONS = {'.html', '.htm', '.css', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.php', '.xml', '.svg'}


class WriteTool(BaseTool):
    """Write files."""

    name = "Write"
    description = "Write content to a file. Creates the file if it doesn't exist, overwrites if it does."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.backup = self.config.get('backup', False)

    def execute(self, file_path: str, content: str, **kwargs) -> ToolResult:
        """Write to a file.

        Args:
            file_path: Path to the file to write
            content: Content to write to the file

        Returns:
            ToolResult with status
        """
        if not file_path:
            return ToolResult(output="Error: No file path provided", is_error=True)

        if content is None:
            return ToolResult(output="Error: No content provided", is_error=True)

        # Expand path
        file_path = os.path.expanduser(file_path)

        # Check protected paths
        allowed, error_msg = check_path_permission(file_path)
        if not allowed:
            return ToolResult(output=error_msg, is_error=True)

        # Unescape HTML entities for web files (workaround for some models)
        _, ext = os.path.splitext(file_path.lower())
        if ext in HTML_EXTENSIONS:
            # Check if content appears to be escaped HTML
            if '&lt;' in content or '&gt;' in content:
                content = html.unescape(content)

        try:
            # Create parent directories if needed
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)

            # Create backup if enabled and file exists
            if self.backup and os.path.exists(file_path):
                backup_path = file_path + '.bak'
                with open(file_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(old_content)

            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            file_existed = os.path.exists(file_path)
            action = "Updated" if file_existed else "Created"
            lines = content.count('\n') + (1 if content and not content.endswith('\n') else 0)

            return ToolResult(
                output=f"{action} {file_path} ({lines} lines)",
                metadata={
                    'action': action.lower(),
                    'lines': lines,
                    'bytes': len(content.encode('utf-8'))
                }
            )

        except PermissionError:
            return ToolResult(output=f"Error: Permission denied: {file_path}", is_error=True)
        except Exception as e:
            return ToolResult(output=f"Error writing file: {str(e)}", is_error=True)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
