"""
HeroAgent OpenAI Provider

OpenAI GPT models via OpenAI API.
"""

import json
from typing import Dict, List, Any, Optional, Generator

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .base import BaseProvider, Response, ToolCall


class OpenAIProvider(BaseProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)

        if not HAS_OPENAI:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self.model = kwargs.get('model', 'gpt-4o')

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Response:
        """Send messages and get a response."""
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages)

        # Add system message
        if self.system_prompt:
            openai_messages.insert(0, {
                'role': 'system',
                'content': self.system_prompt
            })

        # Prepare request
        request_kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': openai_messages,
        }

        if tools:
            request_kwargs['tools'] = self._convert_tools(tools)
            request_kwargs['tool_choice'] = 'auto'

        # Make request
        response = self.client.chat.completions.create(**request_kwargs)

        return self._parse_response(response)

    def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream messages and yield events."""
        openai_messages = self._convert_messages(messages)

        if self.system_prompt:
            openai_messages.insert(0, {
                'role': 'system',
                'content': self.system_prompt
            })

        request_kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'messages': openai_messages,
            'stream': True,
        }

        if tools:
            request_kwargs['tools'] = self._convert_tools(tools)
            request_kwargs['tool_choice'] = 'auto'

        stream = self.client.chat.completions.create(**request_kwargs)

        current_tool_calls = {}

        for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            delta = choice.delta

            # Text content
            if delta.content:
                yield {
                    'type': 'text_delta',
                    'text': delta.content,
                }

            # Tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in current_tool_calls:
                        current_tool_calls[tc.index] = {
                            'id': tc.id or f"call_{tc.index}",
                            'name': tc.function.name if tc.function else '',
                            'arguments': ''
                        }
                    if tc.function and tc.function.arguments:
                        current_tool_calls[tc.index]['arguments'] += tc.function.arguments

            # End of stream
            if choice.finish_reason:
                break

        # Emit tool calls
        for tc_data in current_tool_calls.values():
            try:
                args = json.loads(tc_data['arguments']) if tc_data['arguments'] else {}
            except json.JSONDecodeError:
                args = {}
            yield {
                'type': 'tool_use',
                'id': tc_data['id'],
                'name': tc_data['name'],
                'input': args,
            }

        yield {
            'type': 'final',
            'stop_reason': 'end_turn',
            'usage': {'input_tokens': 0, 'output_tokens': 0}
        }

    def supports_tools(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to OpenAI format."""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                'type': 'function',
                'function': {
                    'name': tool['name'],
                    'description': tool.get('description', ''),
                    'parameters': tool.get('input_schema', {'type': 'object', 'properties': {}})
                }
            })
        return openai_tools

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert messages to OpenAI format."""
        openai_messages = []

        for msg in messages:
            role = msg['role']
            content = msg['content']

            if isinstance(content, str):
                openai_messages.append({
                    'role': role,
                    'content': content
                })
            elif isinstance(content, list):
                # Handle tool use and results
                text_parts = []
                tool_calls = []
                tool_results = []

                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif item.get('type') == 'tool_use':
                            tool_calls.append({
                                'id': item.get('id', f"call_{len(tool_calls)}"),
                                'type': 'function',
                                'function': {
                                    'name': item.get('name'),
                                    'arguments': json.dumps(item.get('input', {}))
                                }
                            })
                        elif item.get('type') == 'tool_result':
                            tool_results.append({
                                'role': 'tool',
                                'tool_call_id': item.get('tool_use_id'),
                                'content': item.get('content', '')
                            })

                if role == 'assistant' and tool_calls:
                    openai_messages.append({
                        'role': 'assistant',
                        'content': '\n'.join(text_parts) if text_parts else None,
                        'tool_calls': tool_calls
                    })
                elif tool_results:
                    openai_messages.extend(tool_results)
                elif text_parts:
                    openai_messages.append({
                        'role': role,
                        'content': '\n'.join(text_parts)
                    })

        return openai_messages

    def _parse_response(self, response) -> Response:
        """Parse OpenAI response."""
        message = response.choices[0].message

        content_text = message.content or ""
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=args,
                ))

        stop_reason = 'end_turn'
        if response.choices[0].finish_reason == 'tool_calls':
            stop_reason = 'tool_use'
        elif response.choices[0].finish_reason == 'length':
            stop_reason = 'max_tokens'

        return Response(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage={
                'input_tokens': response.usage.prompt_tokens if response.usage else 0,
                'output_tokens': response.usage.completion_tokens if response.usage else 0,
            }
        )

    def validate_config(self) -> bool:
        if not self.client.api_key:
            raise ValueError("OpenAI API key not configured")
        return True
