"""
HeroAgent Gemini Provider

Google Gemini models via Gemini API.
"""

import json
from typing import Dict, List, Any, Optional, Generator

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from .base import BaseProvider, Response, ToolCall


class GeminiProvider(BaseProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            **kwargs: Additional options
        """
        super().__init__(api_key, **kwargs)

        if not HAS_GEMINI:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )

        genai.configure(api_key=api_key)
        self.model = kwargs.get('model', 'gemini-2.5-pro')
        self._model_instance = None

    def _get_model(self, tools: Optional[List[Dict[str, Any]]] = None):
        """Get or create model instance."""
        model_kwargs = {}
        if tools:
            model_kwargs['tools'] = self._convert_tools(tools)

        return genai.GenerativeModel(
            model_name=self.model,
            system_instruction=self.system_prompt,
            **model_kwargs
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Response:
        """Send messages and get a response."""
        model = self._get_model(tools)

        # Convert messages to Gemini format
        gemini_messages = self._convert_messages(messages)

        # Configure generation
        generation_config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
        )

        # Generate response
        response = model.generate_content(
            gemini_messages,
            generation_config=generation_config,
        )

        return self._parse_response(response)

    def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream messages and yield events."""
        model = self._get_model(tools)
        gemini_messages = self._convert_messages(messages)

        generation_config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
        )

        response = model.generate_content(
            gemini_messages,
            generation_config=generation_config,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield {
                    'type': 'text_delta',
                    'text': chunk.text,
                }

        yield {
            'type': 'final',
            'stop_reason': 'end_turn',
            'usage': {
                'input_tokens': 0,  # Gemini doesn't always provide this
                'output_tokens': 0,
            }
        }

    def supports_tools(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List:
        """Convert tools to Gemini format."""
        gemini_tools = []
        for tool in tools:
            # Gemini uses function declarations
            func_decl = {
                'name': tool['name'],
                'description': tool.get('description', ''),
                'parameters': tool.get('input_schema', {'type': 'object', 'properties': {}})
            }
            gemini_tools.append(func_decl)
        return gemini_tools

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List:
        """Convert messages to Gemini format."""
        gemini_messages = []
        for msg in messages:
            role = 'user' if msg['role'] == 'user' else 'model'
            content = msg['content']

            if isinstance(content, str):
                gemini_messages.append({
                    'role': role,
                    'parts': [content]
                })
            elif isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            parts.append(item.get('text', ''))
                        elif item.get('type') == 'tool_use':
                            parts.append({
                                'function_call': {
                                    'name': item.get('name'),
                                    'args': item.get('input', {})
                                }
                            })
                        elif item.get('type') == 'tool_result':
                            parts.append({
                                'function_response': {
                                    'name': 'tool',
                                    'response': {'result': item.get('content', '')}
                                }
                            })
                if parts:
                    gemini_messages.append({
                        'role': role,
                        'parts': parts
                    })

        return gemini_messages

    def _parse_response(self, response) -> Response:
        """Parse Gemini response."""
        content_text = ""
        tool_calls = []

        try:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'text'):
                        content_text += part.text
                    elif hasattr(part, 'function_call'):
                        fc = part.function_call
                        tool_calls.append(ToolCall(
                            id=f"call_{len(tool_calls)}",
                            name=fc.name,
                            input=dict(fc.args) if fc.args else {},
                        ))
        except Exception:
            if hasattr(response, 'text'):
                content_text = response.text

        stop_reason = 'end_turn'
        if tool_calls:
            stop_reason = 'tool_use'

        return Response(
            content=content_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage={
                'input_tokens': getattr(response, 'usage_metadata', {}).get('prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
                'output_tokens': getattr(response, 'usage_metadata', {}).get('candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
            }
        )

    def validate_config(self) -> bool:
        if not self.api_key:
            raise ValueError("Gemini API key not configured")
        return True
