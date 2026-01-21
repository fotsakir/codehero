"""
HeroAgent Grep Tool

Search file contents.
"""

import os
import re
import subprocess
from typing import Dict, Any, Optional, List

from .base import BaseTool, ToolResult


class GrepTool(BaseTool):
    """Search file contents."""

    name = "Grep"
    description = "Search for patterns in files. Supports regex and filtering by file type."

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.max_results = self.config.get('max_results', 500)
        self.use_ripgrep = self._check_ripgrep()

    def _check_ripgrep(self) -> bool:
        """Check if ripgrep is available."""
        try:
            subprocess.run(['rg', '--version'], capture_output=True)
            return True
        except FileNotFoundError:
            return False

    def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        type: Optional[str] = None,
        output_mode: str = 'files_with_matches',
        case_insensitive: bool = False,
        context_before: int = 0,
        context_after: int = 0,
        **kwargs
    ) -> ToolResult:
        """Search for pattern in files.

        Args:
            pattern: Regex pattern to search for
            path: Directory to search in
            glob: File glob pattern to filter (e.g., "*.py")
            type: File type to search (e.g., "py", "js")
            output_mode: 'files_with_matches', 'content', or 'count'
            case_insensitive: Enable case-insensitive search
            context_before: Lines to show before matches
            context_after: Lines to show after matches

        Returns:
            ToolResult with search results
        """
        if not pattern:
            return ToolResult(output="Error: No pattern provided", is_error=True)

        search_path = os.path.expanduser(path) if path else os.getcwd()

        if not os.path.exists(search_path):
            return ToolResult(output=f"Error: Path not found: {search_path}", is_error=True)

        try:
            if self.use_ripgrep:
                return self._search_ripgrep(
                    pattern, search_path, glob, type, output_mode,
                    case_insensitive, context_before, context_after
                )
            else:
                return self._search_python(
                    pattern, search_path, glob, output_mode, case_insensitive
                )
        except Exception as e:
            return ToolResult(output=f"Error searching: {str(e)}", is_error=True)

    def _search_ripgrep(
        self,
        pattern: str,
        path: str,
        glob: Optional[str],
        file_type: Optional[str],
        output_mode: str,
        case_insensitive: bool,
        context_before: int,
        context_after: int
    ) -> ToolResult:
        """Search using ripgrep."""
        cmd = ['rg', '--no-heading']

        if output_mode == 'files_with_matches':
            cmd.append('-l')
        elif output_mode == 'count':
            cmd.append('-c')
        else:  # content
            cmd.append('-n')  # Line numbers
            if context_before > 0:
                cmd.extend(['-B', str(context_before)])
            if context_after > 0:
                cmd.extend(['-A', str(context_after)])

        if case_insensitive:
            cmd.append('-i')

        if glob:
            cmd.extend(['--glob', glob])

        if file_type:
            cmd.extend(['--type', file_type])

        cmd.extend(['--max-count', str(self.max_results)])
        cmd.append(pattern)
        cmd.append(path)

        result = subprocess.run(cmd, capture_output=True, text=True)

        output = result.stdout
        if not output:
            return ToolResult(
                output=f"No matches found for pattern: {pattern}",
                metadata={'total': 0}
            )

        lines = output.strip().split('\n')
        return ToolResult(
            output=output.strip(),
            metadata={'total': len(lines)}
        )

    def _search_python(
        self,
        pattern: str,
        path: str,
        glob_pattern: Optional[str],
        output_mode: str,
        case_insensitive: bool
    ) -> ToolResult:
        """Search using Python (fallback)."""
        import glob as glob_module

        # Compile regex
        flags = re.IGNORECASE if case_insensitive else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(output=f"Invalid regex: {e}", is_error=True)

        # Find files
        if glob_pattern:
            file_pattern = os.path.join(path, '**', glob_pattern)
        else:
            file_pattern = os.path.join(path, '**', '*')

        files = glob_module.glob(file_pattern, recursive=True)
        files = [f for f in files if os.path.isfile(f)]

        results = []
        for file_path in files[:1000]:  # Limit files scanned
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            if output_mode == 'files_with_matches':
                                results.append(file_path)
                                break
                            elif output_mode == 'count':
                                results.append(file_path)
                            else:  # content
                                results.append(f"{file_path}:{line_num}:{line.rstrip()}")
                            if len(results) >= self.max_results:
                                break
            except Exception:
                continue

            if len(results) >= self.max_results:
                break

        if output_mode == 'files_with_matches':
            results = list(set(results))
        elif output_mode == 'count':
            from collections import Counter
            counts = Counter(results)
            results = [f"{f}:{c}" for f, c in counts.items()]

        if not results:
            return ToolResult(
                output=f"No matches found for pattern: {pattern}",
                metadata={'total': 0}
            )

        return ToolResult(
            output='\n'.join(results[:self.max_results]),
            metadata={'total': len(results)}
        )

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in. Defaults to current directory."
                },
                "glob": {
                    "type": "string",
                    "description": "File glob pattern to filter (e.g., '*.py', '*.{ts,tsx}')"
                },
                "type": {
                    "type": "string",
                    "description": "File type to search (e.g., 'py', 'js', 'rust')"
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["files_with_matches", "content", "count"],
                    "description": "Output mode: 'files_with_matches' (default), 'content', or 'count'"
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case insensitive search"
                },
                "-B": {
                    "type": "integer",
                    "description": "Lines to show before matches"
                },
                "-A": {
                    "type": "integer",
                    "description": "Lines to show after matches"
                }
            },
            "required": ["pattern"]
        }
