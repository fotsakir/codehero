"""
HeroAgent Base Tool Interface

Abstract base class for all tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result from tool execution."""
    output: str
    is_error: bool = False
    metadata: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """Abstract base class for tools."""

    # Tool metadata
    name: str = "BaseTool"
    description: str = "Base tool"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize tool.

        Args:
            config: Tool-specific configuration
        """
        self.config = config or {}

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult with output
        """
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for AI providers.

        Returns:
            JSON Schema for tool parameters
        """
        pass

    def to_tool_spec(self) -> Dict[str, Any]:
        """Convert to tool specification.

        Returns:
            Tool specification dict
        """
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': self.get_schema(),
        }
