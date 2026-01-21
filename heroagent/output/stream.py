"""
HeroAgent Stream Output

JSON stream output compatible with CodeHero daemon.
Matches Claude Code's stream-json format exactly.
"""

import json
import sys
from typing import Any, Dict, Optional, List
from datetime import datetime


class StreamOutput:
    """JSON stream output handler for daemon compatibility.

    Outputs JSON in Claude Code format for seamless daemon integration.
    """

    def __init__(self, output_format: str = 'stream-json', verbose: bool = False):
        """Initialize stream output.

        Args:
            output_format: Output format ('stream-json', 'text', 'print')
            verbose: Enable verbose logging
        """
        self.output_format = output_format
        self.verbose = verbose
        self._buffer = ""
        self._pending_tool_uses: List[Dict[str, Any]] = []
        self._current_usage: Dict[str, int] = {}

    def emit(self, event: Dict[str, Any]):
        """Emit an event to output.

        Args:
            event: Event dictionary to emit
        """
        if self.output_format == 'stream-json':
            self._emit_json(event)
        elif self.output_format == 'text':
            self._emit_text(event)
        else:  # print
            self._emit_print(event)

    def _emit_json(self, event: Dict[str, Any]):
        """Emit JSON line."""
        print(json.dumps(event), flush=True)

    def _emit_text(self, event: Dict[str, Any]):
        """Emit formatted text."""
        event_type = event.get('type', '')

        if event_type == 'assistant':
            print(event.get('content', ''), end='', flush=True)
        elif event_type == 'text_delta':
            print(event.get('text', ''), end='', flush=True)
        elif event_type == 'tool_use':
            print(f"\n[TOOL: {event.get('name')}]", flush=True)
            if self.verbose:
                print(f"Input: {json.dumps(event.get('input', {}), indent=2)}", flush=True)
        elif event_type == 'tool_result':
            output = event.get('output', '')
            if len(output) > 500 and not self.verbose:
                output = output[:500] + '... (truncated)'
            print(f"[RESULT: {output}]", flush=True)
        elif event_type == 'error':
            print(f"\n[ERROR: {event.get('error', 'Unknown error')}]", flush=True)
        elif event_type == 'result':
            print(f"\n[Done. Tokens: {event.get('usage', {})}]", flush=True)

    def _emit_print(self, event: Dict[str, Any]):
        """Simple print output."""
        event_type = event.get('type', '')

        if event_type == 'assistant':
            print(event.get('content', ''), end='', flush=True)
        elif event_type == 'text_delta':
            print(event.get('text', ''), end='', flush=True)
        elif event_type == 'tool_use':
            # Silent for simple output
            pass
        elif event_type == 'tool_result':
            # Silent for simple output
            pass
        elif event_type == 'error':
            print(f"Error: {event.get('error', 'Unknown error')}", file=sys.stderr, flush=True)

    # Convenience methods for common events
    # These match Claude Code's stream-json format exactly

    def assistant(self, content: str, tool_uses: Optional[List[Dict]] = None):
        """Emit assistant message in Claude Code format.

        Format: {"type": "assistant", "message": {"content": [...], "usage": {...}}}
        """
        message_content = []

        # Add text content
        if content:
            message_content.append({
                'type': 'text',
                'text': content
            })

        # Add any pending tool uses
        if tool_uses:
            for tool in tool_uses:
                message_content.append({
                    'type': 'tool_use',
                    'id': tool.get('id', ''),
                    'name': tool.get('name', ''),
                    'input': tool.get('input', {})
                })

        self.emit({
            'type': 'assistant',
            'message': {
                'content': message_content,
                'usage': self._current_usage
            }
        })

    def text_delta(self, text: str):
        """Emit text delta (streaming)."""
        self.emit({'type': 'text_delta', 'text': text})
        self._buffer += text

    def tool_use(self, name: str, tool_input: Dict[str, Any], tool_id: Optional[str] = None):
        """Emit tool use event.

        Also emits as assistant message with tool_use content for daemon compatibility.
        """
        # Emit assistant message with tool_use (daemon expects this format)
        self.emit({
            'type': 'assistant',
            'message': {
                'content': [{
                    'type': 'tool_use',
                    'id': tool_id or '',
                    'name': name,
                    'input': tool_input
                }],
                'usage': self._current_usage
            }
        })

    def tool_result(self, name: str, output: str, is_error: bool = False, tool_id: Optional[str] = None):
        """Emit tool result event."""
        # Daemon reads tool results from result type
        self.emit({
            'type': 'result',
            'tool_use_id': tool_id,
            'result': output,
            'is_error': is_error
        })

    def error(self, error: str, details: Optional[str] = None):
        """Emit error event in Claude Code format."""
        self.emit({
            'type': 'error',
            'error': {
                'message': error,
                'type': 'agent_error',
                'details': details
            }
        })

    def result(self, usage: Dict[str, int], success: bool = True):
        """Emit final result event."""
        self.emit({
            'type': 'result',
            'success': success,
            'usage': usage,
        })

    def set_usage(self, usage: Dict[str, int]):
        """Set current usage for inclusion in messages."""
        self._current_usage = usage

    def log(self, message: str, level: str = 'info'):
        """Emit log event (only in verbose mode)."""
        if self.verbose:
            self.emit({
                'type': 'log',
                'level': level,
                'message': message,
                'timestamp': datetime.now().isoformat(),
            })

    def flush_buffer(self) -> str:
        """Get and clear the text buffer.

        Returns:
            Accumulated text from text_delta events
        """
        text = self._buffer
        self._buffer = ""
        return text

    def newline(self):
        """Emit a newline (for text formats)."""
        if self.output_format in ('text', 'print'):
            print(flush=True)


class SilentOutput:
    """Silent output handler for programmatic use."""

    def __init__(self):
        self.events = []
        self._buffer = ""
        self._current_usage: Dict[str, int] = {}

    def emit(self, event: Dict[str, Any]):
        """Store event."""
        self.events.append(event)

    def set_usage(self, usage: Dict[str, int]):
        """Set current usage."""
        self._current_usage = usage

    def assistant(self, content: str, tool_uses: Optional[List[Dict]] = None):
        self.emit({'type': 'assistant', 'content': content, 'tool_uses': tool_uses})

    def text_delta(self, text: str):
        self.emit({'type': 'text_delta', 'text': text})
        self._buffer += text

    def tool_use(self, name: str, tool_input: Dict[str, Any], tool_id: Optional[str] = None):
        self.emit({'type': 'tool_use', 'name': name, 'input': tool_input, 'id': tool_id})

    def tool_result(self, name: str, output: str, is_error: bool = False, tool_id: Optional[str] = None):
        self.emit({'type': 'tool_result', 'name': name, 'output': output, 'is_error': is_error, 'id': tool_id})

    def error(self, error: str, details: Optional[str] = None):
        self.emit({'type': 'error', 'error': error, 'details': details})

    def result(self, usage: Dict[str, int], success: bool = True):
        self.emit({'type': 'result', 'success': success, 'usage': usage})

    def log(self, message: str, level: str = 'info'):
        self.emit({'type': 'log', 'level': level, 'message': message})

    def flush_buffer(self) -> str:
        text = self._buffer
        self._buffer = ""
        return text

    def newline(self):
        pass

    def get_events(self) -> list:
        """Get all stored events."""
        return self.events

    def get_text(self) -> str:
        """Get all assistant text."""
        text = ""
        for event in self.events:
            if event['type'] == 'assistant':
                text += event.get('content', '')
            elif event['type'] == 'text_delta':
                text += event.get('text', '')
        return text
