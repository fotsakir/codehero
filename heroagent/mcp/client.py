"""
HeroAgent MCP Client

JSON-RPC 2.0 client for MCP (Model Context Protocol) servers.
"""

import json
import subprocess
import threading
import queue
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class MCPTool:
    """An MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPClient:
    """Client for communicating with MCP servers via stdio."""

    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        """Initialize MCP client.

        Args:
            command: Command to start the MCP server
            args: Arguments for the command
            env: Environment variables
        """
        self.command = command
        self.args = args or []
        self.env = env
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._responses: Dict[int, Any] = {}
        self._response_queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._connected = False
        self._tools: List[MCPTool] = []

    def connect(self) -> bool:
        """Connect to the MCP server.

        Returns:
            True if connection successful
        """
        try:
            import os
            env = os.environ.copy()
            if self.env:
                env.update(self.env)

            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,  # Line buffered
            )

            # Start reader thread
            self._reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            self._reader_thread.start()

            # Initialize MCP connection
            self._initialize()
            self._connected = True
            return True

        except Exception as e:
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None
        self._connected = False

    def _read_responses(self):
        """Background thread to read server responses."""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    try:
                        response = json.loads(line.strip())
                        self._response_queue.put(response)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                break

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            Response result
        """
        self._request_id += 1
        request = {
            'jsonrpc': '2.0',
            'id': self._request_id,
            'method': method,
        }
        if params:
            request['params'] = params

        # Send request
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()

        # Wait for response with matching ID
        timeout = 30  # 30 second timeout
        try:
            while True:
                response = self._response_queue.get(timeout=timeout)
                if response.get('id') == self._request_id:
                    if 'error' in response:
                        raise MCPError(
                            response['error'].get('code', -1),
                            response['error'].get('message', 'Unknown error')
                        )
                    return response.get('result', {})
        except queue.Empty:
            raise MCPError(-1, f"Timeout waiting for response to {method}")

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: Method name
            params: Method parameters
        """
        notification = {
            'jsonrpc': '2.0',
            'method': method,
        }
        if params:
            notification['params'] = params

        self.process.stdin.write(json.dumps(notification) + '\n')
        self.process.stdin.flush()

    def _initialize(self):
        """Perform MCP initialization handshake."""
        # Send initialize request
        result = self._send_request('initialize', {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'roots': {'listChanged': True},
            },
            'clientInfo': {
                'name': 'HeroAgent',
                'version': '1.0.0',
            }
        })

        # Send initialized notification
        self._send_notification('notifications/initialized')

        # Get available tools
        self._load_tools()

    def _load_tools(self):
        """Load available tools from server."""
        try:
            result = self._send_request('tools/list')
            tools = result.get('tools', [])
            self._tools = [
                MCPTool(
                    name=t['name'],
                    description=t.get('description', ''),
                    input_schema=t.get('inputSchema', {'type': 'object', 'properties': {}})
                )
                for t in tools
            ]
        except Exception:
            self._tools = []

    def list_tools(self) -> List[MCPTool]:
        """Get available tools.

        Returns:
            List of available tools
        """
        return self._tools

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        """Get tool specifications for AI providers.

        Returns:
            List of tool specifications
        """
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'input_schema': tool.input_schema,
            }
            for tool in self._tools
        ]

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Call an MCP tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result as string
        """
        if not self._connected:
            raise MCPError(-1, "Not connected to MCP server")

        result = self._send_request('tools/call', {
            'name': name,
            'arguments': arguments or {},
        })

        # Extract content from result
        content = result.get('content', [])
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'text':
                    texts.append(item.get('text', ''))
                elif isinstance(item, str):
                    texts.append(item)
            return '\n'.join(texts)
        return str(content)

    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._connected and self.process and self.process.poll() is None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class MCPError(Exception):
    """MCP protocol error."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"MCP Error {code}: {message}")


class MCPManager:
    """Manages multiple MCP server connections."""

    def __init__(self, server_configs: Optional[Dict[str, Dict[str, Any]]] = None):
        """Initialize MCP manager.

        Args:
            server_configs: Dictionary of server name -> config
        """
        self.server_configs = server_configs or {}
        self.clients: Dict[str, MCPClient] = {}

    def connect_server(self, name: str) -> MCPClient:
        """Connect to a configured server.

        Args:
            name: Server name from config

        Returns:
            Connected MCP client
        """
        if name in self.clients and self.clients[name].is_connected():
            return self.clients[name]

        config = self.server_configs.get(name)
        if not config:
            raise ValueError(f"Unknown MCP server: {name}")

        client = MCPClient(
            command=config['command'],
            args=config.get('args', []),
            env=config.get('env'),
        )
        client.connect()
        self.clients[name] = client
        return client

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected servers.

        Returns:
            Combined list of tool specifications
        """
        tools = []
        for name, client in self.clients.items():
            if client.is_connected():
                for spec in client.get_tool_specs():
                    # Prefix tool name with server name to avoid conflicts
                    spec_copy = spec.copy()
                    spec_copy['_mcp_server'] = name
                    tools.append(spec_copy)
        return tools

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Call a tool on any connected server.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        # Find which server has this tool
        for name, client in self.clients.items():
            if client.is_connected():
                tool_names = [t.name for t in client.list_tools()]
                if tool_name in tool_names:
                    return client.call_tool(tool_name, arguments)

        raise MCPError(-1, f"Tool not found: {tool_name}")

    def disconnect_all(self):
        """Disconnect all servers."""
        for client in self.clients.values():
            client.disconnect()
        self.clients.clear()
