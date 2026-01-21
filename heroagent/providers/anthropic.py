"""
HeroAgent Anthropic Provider

Claude models via Anthropic API.
"""

import json
from typing import Dict, List, Any, Optional, Generator

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from .base import BaseProvider, Response, ToolCall


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)

        if not HAS_ANTHROPIC:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = kwargs.get('model', 'claude-sonnet-4-20250514')

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
            tools: List of available tools
            max_tokens: Maximum tokens in response

        Returns:
            Response object
        """
        # Prepare request
        request_kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': messages,
        }

        if self.system_prompt:
            request_kwargs['system'] = self.system_prompt

        if tools:
            request_kwargs['tools'] = self._convert_tools(tools)

        # Make request
        response = self.client.messages.create(**request_kwargs)

        return self._parse_response(response)

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
            tools: List of available tools
            max_tokens: Maximum tokens in response

        Yields:
            Event dictionaries
        """
        # Prepare request
        request_kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': messages,
        }

        if self.system_prompt:
            request_kwargs['system'] = self.system_prompt

        if tools:
            request_kwargs['tools'] = self._convert_tools(tools)

        # Stream response
        with self.client.messages.stream(**request_kwargs) as stream:
            current_text = ""
            current_tool_use = None

            for event in stream:
                if event.type == 'content_block_start':
                    block = event.content_block
                    if block.type == 'text':
                        current_text = ""
                    elif block.type == 'tool_use':
                        current_tool_use = {
                            'id': block.id,
                            'name': block.name,
                            'input_json': ""
                        }
                        yield {
                            'type': 'tool_use_start',
                            'id': block.id,
                            'name': block.name,
                        }

                elif event.type == 'content_block_delta':
                    delta = event.delta
                    if delta.type == 'text_delta':
                        current_text += delta.text
                        yield {
                            'type': 'text_delta',
                            'text': delta.text,
                        }
                    elif delta.type == 'input_json_delta':
                        if current_tool_use:
                            current_tool_use['input_json'] += delta.partial_json

                elif event.type == 'content_block_stop':
                    if current_tool_use:
                        try:
                            tool_input = json.loads(current_tool_use['input_json'])
                        except json.JSONDecodeError:
                            tool_input = {}
                        yield {
                            'type': 'tool_use',
                            'id': current_tool_use['id'],
                            'name': current_tool_use['name'],
                            'input': tool_input,
                        }
                        current_tool_use = None

                elif event.type == 'message_stop':
                    yield {
                        'type': 'message_stop',
                    }

                elif event.type == 'message_delta':
                    if hasattr(event, 'usage'):
                        yield {
                            'type': 'usage',
                            'usage': {
                                'input_tokens': getattr(event.usage, 'input_tokens', 0),
                                'output_tokens': getattr(event.usage, 'output_tokens', 0),
                            }
                        }

            # Final message with full usage
            final_message = stream.get_final_message()
            yield {
                'type': 'final',
                'stop_reason': final_message.stop_reason,
                'usage': {
                    'input_tokens': final_message.usage.input_tokens,
                    'output_tokens': final_message.usage.output_tokens,
                }
            }

    def supports_tools(self) -> bool:
        """Anthropic supports tool use."""
        return True

    def supports_streaming(self) -> bool:
        """Anthropic supports streaming."""
        return True

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic format.

        Args:
            tools: Tools in HeroAgent format

        Returns:
            Tools in Anthropic API format
        """
        anthropic_tools = []
        for tool in tools:
            anthropic_tool = {
                'name': tool['name'],
                'description': tool.get('description', ''),
                'input_schema': tool.get('input_schema', tool.get('parameters', {'type': 'object', 'properties': {}})),
            }
            anthropic_tools.append(anthropic_tool)
        return anthropic_tools

    def _parse_response(self, response) -> Response:
        """Parse Anthropic response to standard format.

        Args:
            response: Anthropic API response

        Returns:
            Response object
        """
        content_text = ""
        tool_calls = []

        for block in response.content:
            if block.type == 'text':
                content_text += block.text
            elif block.type == 'tool_use':
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        return Response(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
            }
        )

    def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        if not self.client.api_key:
            raise ValueError("Anthropic API key not configured")
        if not self.model:
            raise ValueError("Model not set")
        return True
