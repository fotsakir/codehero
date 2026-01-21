"""
HeroAgent Read Tool

Read file contents (text and images).
"""

import os
import base64
import mimetypes
from typing import Dict, Any, Optional

from .base import BaseTool, ToolResult


# Image extensions that should be returned as base64
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


class ReadTool(BaseTool):
    """Read file contents."""

    name = "Read"
    description = "Read the contents of a file. Returns file content with line numbers."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.max_lines = self.config.get('max_lines', 2000)
        self.max_line_length = self.config.get('max_line_length', 2000)

    def execute(self, file_path: str, offset: int = 0, limit: Optional[int] = None, **kwargs) -> ToolResult:
        """Read a file.

        Args:
            file_path: Path to the file to read
            offset: Line number to start from (0-based)
            limit: Maximum number of lines to read

        Returns:
            ToolResult with file contents (or base64 for images)
        """
        if not file_path:
            return ToolResult(output="Error: No file path provided", is_error=True)

        # Expand path
        file_path = os.path.expanduser(file_path)

        if not os.path.exists(file_path):
            return ToolResult(output=f"Error: File not found: {file_path}", is_error=True)

        if os.path.isdir(file_path):
            return ToolResult(output=f"Error: Path is a directory: {file_path}", is_error=True)

        # Check if image
        _, ext = os.path.splitext(file_path.lower())
        if ext in IMAGE_EXTENSIONS:
            return self._read_image(file_path, ext)

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            total_lines = len(lines)
            max_lines = limit or self.max_lines

            # Apply offset
            if offset > 0:
                lines = lines[offset:]

            # Apply limit
            lines = lines[:max_lines]

            # Format with line numbers (1-based like cat -n)
            output_lines = []
            for i, line in enumerate(lines):
                line_num = offset + i + 1
                # Truncate long lines
                if len(line) > self.max_line_length:
                    line = line[:self.max_line_length] + "... (truncated)\n"
                # Format: "    1\t<content>"
                output_lines.append(f"{line_num:6}\t{line.rstrip()}")

            output = '\n'.join(output_lines)

            # Add truncation notice if needed
            if total_lines > offset + max_lines:
                remaining = total_lines - (offset + max_lines)
                output += f"\n\n... ({remaining} more lines)"

            return ToolResult(
                output=output if output else "(empty file)",
                metadata={
                    'total_lines': total_lines,
                    'lines_read': len(output_lines),
                    'offset': offset
                }
            )

        except PermissionError:
            return ToolResult(output=f"Error: Permission denied: {file_path}", is_error=True)
        except Exception as e:
            return ToolResult(output=f"Error reading file: {str(e)}", is_error=True)

    def _read_image(self, file_path: str, ext: str) -> ToolResult:
        """Read an image file and return as base64.

        Args:
            file_path: Path to image
            ext: File extension

        Returns:
            ToolResult with base64 image data
        """
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()

            # Get file size
            file_size = len(image_data)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                return ToolResult(
                    output=f"Error: Image too large ({file_size // 1024 // 1024}MB). Max 10MB.",
                    is_error=True
                )

            # Encode to base64
            b64_data = base64.b64encode(image_data).decode('utf-8')

            # Determine mime type
            mime_type = mimetypes.guess_type(file_path)[0] or f'image/{ext[1:]}'

            # Return as special image format that provider can interpret
            return ToolResult(
                output=f"[IMAGE:{mime_type}:{b64_data}]",
                metadata={
                    'type': 'image',
                    'mime_type': mime_type,
                    'base64': b64_data,
                    'size': file_size,
                    'path': file_path
                }
            )

        except Exception as e:
            return ToolResult(output=f"Error reading image: {str(e)}", is_error=True)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start from (0-based). Default: 0"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read"
                }
            },
            "required": ["file_path"]
        }
