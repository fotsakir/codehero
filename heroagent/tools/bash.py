"""
HeroAgent Bash Tool

Execute shell commands.
"""

import subprocess
import os
from typing import Dict, Any, Optional

from .base import BaseTool, ToolResult


class BashTool(BaseTool):
    """Execute bash commands."""

    name = "Bash"
    description = "Execute shell commands. Use for running scripts, git operations, and system commands."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.timeout = self.config.get('timeout', 120000) / 1000  # Convert ms to seconds
        self.max_output = self.config.get('max_output', 30000)
        self.cwd = self.config.get('cwd', os.getcwd())

    def execute(self, command: str, timeout: Optional[int] = None, cwd: Optional[str] = None, **kwargs) -> ToolResult:
        """Execute a bash command.

        Args:
            command: The command to execute
            timeout: Optional timeout in milliseconds
            cwd: Optional working directory

        Returns:
            ToolResult with command output
        """
        if not command:
            return ToolResult(output="Error: No command provided", is_error=True)

        # Use provided timeout or default
        timeout_sec = (timeout / 1000) if timeout else self.timeout
        working_dir = cwd or self.cwd

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=working_dir,
                env=os.environ.copy(),
            )

            output = result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += result.stderr

            # Truncate if too long
            if len(output) > self.max_output:
                output = output[:self.max_output] + f"\n... (truncated, {len(output)} total chars)"

            # Consider non-zero exit code as error
            is_error = result.returncode != 0

            return ToolResult(
                output=output if output else "(no output)",
                is_error=is_error,
                metadata={'returncode': result.returncode}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(
                output=f"Error: Command timed out after {timeout_sec} seconds",
                is_error=True
            )
        except Exception as e:
            return ToolResult(
                output=f"Error executing command: {str(e)}",
                is_error=True
            )

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Optional timeout in milliseconds (default: 120000)"
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory"
                }
            },
            "required": ["command"]
        }
