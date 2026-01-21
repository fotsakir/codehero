"""
HeroAgent Ollama Provider

Local Ollama models via Ollama API.
"""

import json
import requests
from typing import Dict, List, Any, Optional, Generator

from .base import BaseProvider, Response, ToolCall


class OllamaProvider(BaseProvider):
    """Local Ollama provider."""

    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        """Initialize Ollama provider.

        Args:
            api_key: Not used for Ollama (local)
            base_url: Ollama API base URL
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.model = kwargs.get('model', 'llama3.3')

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Response:
        """Send messages and get a response."""
        # Convert messages to Ollama format
        ollama_messages = self._convert_messages(messages)

        # Add system message
        if self.system_prompt:
            ollama_messages.insert(0, {
                'role': 'system',
                'content': self.system_prompt
            })

        # Prepare request
        request_data = {
            'model': self.model,
            'messages': ollama_messages,
            'stream': False,
            'options': {
                'num_predict': max_tokens,
            }
        }

        # Note: Ollama tool support varies by model
        if tools:
            request_data['tools'] = self._convert_tools(tools)

        # Make request
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=request_data,
            timeout=300,  # 5 minute timeout for local models
        )
        response.raise_for_status()

        return self._parse_response(response.json())

    def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream messages and yield events."""
        ollama_messages = self._convert_messages(messages)

        if self.system_prompt:
            ollama_messages.insert(0, {
                'role': 'system',
                'content': self.system_prompt
            })

        request_data = {
            'model': self.model,
            'messages': ollama_messages,
            'stream': True,
            'options': {
                'num_predict': max_tokens,
            }
        }

        if tools:
            request_data['tools'] = self._convert_tools(tools)

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=request_data,
            stream=True,
            timeout=300,
        )
        response.raise_for_status()

        full_content = ""

        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if 'message' in data and 'content' in data['message']:
                        text = data['message']['content']
                        full_content += text
                        yield {
                            'type': 'text_delta',
                            'text': text,
                        }

                    # Check for tool calls
                    if 'message' in data and 'tool_calls' in data['message']:
                        for tc in data['message']['tool_calls']:
                            yield {
                                'type': 'tool_use',
                                'id': f"call_{tc.get('id', 0)}",
                                'name': tc['function']['name'],
                                'input': tc['function'].get('arguments', {}),
                            }

                    if data.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue

        yield {
            'type': 'final',
            'stop_reason': 'end_turn',
            'usage': {
                'input_tokens': 0,
                'output_tokens': 0,
            }
        }

    def supports_tools(self) -> bool:
        # Tool support varies by model
        return True

    def supports_streaming(self) -> bool:
        return True

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert tools to Ollama format."""
        ollama_tools = []
        for tool in tools:
            ollama_tools.append({
                'type': 'function',
                'function': {
                    'name': tool['name'],
                    'description': tool.get('description', ''),
                    'parameters': tool.get('input_schema', {'type': 'object', 'properties': {}})
                }
            })
        return ollama_tools

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert messages to Ollama format."""
        ollama_messages = []

        for msg in messages:
            role = msg['role']
            content = msg['content']

            if isinstance(content, str):
                ollama_messages.append({
                    'role': role,
                    'content': content
                })
            elif isinstance(content, list):
                # Handle complex content
                text_parts = []
                tool_calls = []

                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif item.get('type') == 'tool_use':
                            tool_calls.append({
                                'id': item.get('id'),
                                'function': {
                                    'name': item.get('name'),
                                    'arguments': item.get('input', {})
                                }
                            })
                        elif item.get('type') == 'tool_result':
                            ollama_messages.append({
                                'role': 'tool',
                                'content': item.get('content', '')
                            })

                if text_parts or tool_calls:
                    msg_data = {
                        'role': role,
                        'content': '\n'.join(text_parts) if text_parts else ''
                    }
                    if tool_calls:
                        msg_data['tool_calls'] = tool_calls
                    ollama_messages.append(msg_data)

        return ollama_messages

    def _parse_response(self, response_data: Dict[str, Any]) -> Response:
        """Parse Ollama response."""
        message = response_data.get('message', {})
        content_text = message.get('content', '')
        tool_calls = []

        # Handle tool calls if present
        if 'tool_calls' in message:
            for tc in message['tool_calls']:
                tool_calls.append(ToolCall(
                    id=f"call_{tc.get('id', len(tool_calls))}",
                    name=tc['function']['name'],
                    input=tc['function'].get('arguments', {}),
                ))

        stop_reason = 'end_turn'
        if tool_calls:
            stop_reason = 'tool_use'

        # Ollama provides some usage info
        prompt_eval = response_data.get('prompt_eval_count', 0)
        eval_count = response_data.get('eval_count', 0)

        return Response(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage={
                'input_tokens': prompt_eval,
                'output_tokens': eval_count,
            }
        )

    def validate_config(self) -> bool:
        # Check if Ollama is running
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return True
        except Exception:
            raise ValueError(f"Cannot connect to Ollama at {self.base_url}")

    def list_models(self) -> List[str]:
        """List available Ollama models.

        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return [m['name'] for m in data.get('models', [])]
        except Exception:
            return []
