"""
HeroAgent Base Provider Interface

Abstract base class for all AI providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass


@dataclass
class Message:
    """A conversation message."""
    role: str  # 'user', 'assistant', 'system'
    content: Any  # str or list of content blocks


@dataclass
class ToolCall:
    """A tool call from the model."""
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class ToolResult:
    """Result from tool execution."""
    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class Response:
    """Model response."""
    content: str
    tool_calls: List[ToolCall]
    stop_reason: str  # 'end_turn', 'tool_use', 'max_tokens'
    usage: Dict[str, int]  # {'input_tokens': N, 'output_tokens': M}


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize provider.

        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific options
        """
        self.api_key = api_key
        self.model: Optional[str] = None
        self.system_prompt: Optional[str] = None

    def set_model(self, model: str):
        """Set the model to use.

        Args:
            model: Model name/ID
        """
        self.model = model

    def set_system_prompt(self, prompt: str):
        """Set the system prompt.

        Args:
            prompt: System prompt text
        """
        self.system_prompt = prompt

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Response:
        """Send messages and get a response.

        Args:
            messages: List of conversation messages
            tools: List of available tools (Claude Code format)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific options

        Returns:
            Response object with content and optional tool calls
        """
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream messages and yield events.

        Args:
            messages: List of conversation messages
            tools: List of available tools (Claude Code format)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific options

        Yields:
            Event dictionaries with type and content
        """
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Check if provider supports tool use.

        Returns:
            True if provider supports tools
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming.

        Returns:
            True if provider supports streaming
        """
        pass

    def convert_tools_to_provider_format(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert tools from Claude Code format to provider format.

        Override in subclasses for providers with different tool formats.

        Args:
            tools: Tools in Claude Code format

        Returns:
            Tools in provider-specific format
        """
        return tools

    def convert_messages_to_provider_format(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert messages to provider format.

        Override in subclasses for providers with different message formats.

        Args:
            messages: Messages in standard format

        Returns:
            Messages in provider-specific format
        """
        return messages

    @staticmethod
    def create_user_message(content: str) -> Dict[str, Any]:
        """Create a user message.

        Args:
            content: Message text

        Returns:
            Message dict
        """
        return {'role': 'user', 'content': content}

    @staticmethod
    def create_assistant_message(content: str) -> Dict[str, Any]:
        """Create an assistant message.

        Args:
            content: Message text

        Returns:
            Message dict
        """
        return {'role': 'assistant', 'content': content}

    @staticmethod
    def create_tool_result_message(
        tool_call_id: str,
        result: str,
        is_error: bool = False
    ) -> Dict[str, Any]:
        """Create a tool result message.

        Args:
            tool_call_id: ID of the tool call
            result: Tool execution result
            is_error: Whether the result is an error

        Returns:
            Message dict
        """
        return {
            'role': 'user',
            'content': [{
                'type': 'tool_result',
                'tool_use_id': tool_call_id,
                'content': result,
                'is_error': is_error,
            }]
        }

    def validate_config(self) -> bool:
        """Validate provider configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.api_key:
            raise ValueError(f"API key not configured for {self.__class__.__name__}")
        if not self.model:
            raise ValueError(f"Model not set for {self.__class__.__name__}")
        return True
