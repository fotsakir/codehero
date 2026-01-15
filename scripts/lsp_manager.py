#!/usr/bin/env python3
"""
LSP Manager - Language Server Protocol Manager for CodeHero
Manages language server processes and handles JSON-RPC communication.
"""

import subprocess
import threading
import json
import os
import sys
import time
import queue
from typing import Dict, Optional, Callable, Any

# Language server configurations
LANGUAGE_SERVERS = {
    # Python - pylsp (python-lsp-server)
    'python': {
        'command': ['pylsp'],
        'extensions': ['.py', '.pyw'],
        'language_id': 'python',
    },
    # JavaScript - typescript-language-server
    'javascript': {
        'command': ['typescript-language-server', '--stdio'],
        'extensions': ['.js', '.jsx', '.mjs'],
        'language_id': 'javascript',
    },
    # TypeScript - typescript-language-server
    'typescript': {
        'command': ['typescript-language-server', '--stdio'],
        'extensions': ['.ts', '.tsx'],
        'language_id': 'typescript',
    },
    # HTML - vscode-html-language-server
    'html': {
        'command': ['vscode-html-language-server', '--stdio'],
        'extensions': ['.html', '.htm'],
        'language_id': 'html',
    },
    # CSS - vscode-css-language-server
    'css': {
        'command': ['vscode-css-language-server', '--stdio'],
        'extensions': ['.css'],
        'language_id': 'css',
    },
    # SCSS/LESS - vscode-css-language-server
    'scss': {
        'command': ['vscode-css-language-server', '--stdio'],
        'extensions': ['.scss', '.less'],
        'language_id': 'scss',
    },
    # JSON - vscode-json-language-server
    'json': {
        'command': ['vscode-json-language-server', '--stdio'],
        'extensions': ['.json', '.jsonc'],
        'language_id': 'json',
    },
    # PHP - intelephense
    'php': {
        'command': ['intelephense', '--stdio'],
        'extensions': ['.php', '.phtml'],
        'language_id': 'php',
    },
    # Java - jdtls (Eclipse JDT Language Server)
    'java': {
        'command': ['jdtls'],
        'extensions': ['.java'],
        'language_id': 'java',
    },
    # C# - omnisharp
    'csharp': {
        'command': ['omnisharp', '-lsp'],
        'extensions': ['.cs'],
        'language_id': 'csharp',
    },
    # Kotlin - kotlin-language-server
    'kotlin': {
        'command': ['kotlin-language-server'],
        'extensions': ['.kt', '.kts'],
        'language_id': 'kotlin',
    },
}

class LSPServer:
    """Manages a single language server process."""

    def __init__(self, language: str, root_path: str, on_message: Callable[[dict], None]):
        self.language = language
        self.root_path = root_path
        self.on_message = on_message
        self.process: Optional[subprocess.Popen] = None
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False
        self.request_id = 0
        self.pending_requests: Dict[int, queue.Queue] = {}
        self.initialized = False
        self.capabilities = {}

    def start(self) -> bool:
        """Start the language server process."""
        if self.language not in LANGUAGE_SERVERS:
            print(f"[LSP] Unknown language: {self.language}")
            return False

        config = LANGUAGE_SERVERS[self.language]
        command = config['command']

        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            self.running = True

            # Start reader thread
            self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.reader_thread.start()

            # Initialize the server
            self._initialize()

            print(f"[LSP] Started {self.language} server for {self.root_path}")
            return True

        except FileNotFoundError:
            print(f"[LSP] Command not found: {command[0]}")
            return False
        except Exception as e:
            print(f"[LSP] Failed to start {self.language} server: {e}")
            return False

    def stop(self):
        """Stop the language server process."""
        self.running = False
        if self.process:
            try:
                # Send shutdown request
                self._send_request('shutdown', {})
                self._send_notification('exit', {})
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
        print(f"[LSP] Stopped {self.language} server")

    def _initialize(self):
        """Send initialize request to the server."""
        params = {
            'processId': os.getpid(),
            'rootPath': self.root_path,
            'rootUri': f'file://{self.root_path}',
            'capabilities': {
                'textDocument': {
                    'completion': {
                        'completionItem': {
                            'snippetSupport': True,
                            'documentationFormat': ['markdown', 'plaintext'],
                        }
                    },
                    'hover': {
                        'contentFormat': ['markdown', 'plaintext']
                    },
                    'signatureHelp': {
                        'signatureInformation': {
                            'documentationFormat': ['markdown', 'plaintext']
                        }
                    },
                    'definition': {},
                    'references': {},
                    'documentHighlight': {},
                    'documentSymbol': {},
                    'formatting': {},
                    'publishDiagnostics': {
                        'relatedInformation': True
                    }
                },
                'workspace': {
                    'workspaceFolders': True
                }
            },
            'workspaceFolders': [
                {'uri': f'file://{self.root_path}', 'name': os.path.basename(self.root_path)}
            ]
        }

        response = self._send_request('initialize', params, timeout=10)
        if response and 'result' in response:
            self.capabilities = response['result'].get('capabilities', {})
            self._send_notification('initialized', {})
            self.initialized = True
            print(f"[LSP] {self.language} server initialized")
        else:
            print(f"[LSP] Failed to initialize {self.language} server")

    def _send_request(self, method: str, params: dict, timeout: float = 5.0) -> Optional[dict]:
        """Send a request and wait for response."""
        self.request_id += 1
        request_id = self.request_id

        message = {
            'jsonrpc': '2.0',
            'id': request_id,
            'method': method,
            'params': params
        }

        response_queue = queue.Queue()
        self.pending_requests[request_id] = response_queue

        self._send_message(message)

        try:
            response = response_queue.get(timeout=timeout)
            return response
        except queue.Empty:
            print(f"[LSP] Request timeout: {method}")
            return None
        finally:
            del self.pending_requests[request_id]

    def _send_notification(self, method: str, params: dict):
        """Send a notification (no response expected)."""
        message = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params
        }
        self._send_message(message)

    def _send_message(self, message: dict):
        """Send a JSON-RPC message to the server."""
        if not self.process or not self.process.stdin:
            return

        content = json.dumps(message)
        header = f'Content-Length: {len(content)}\r\n\r\n'

        try:
            self.process.stdin.write(header.encode('utf-8'))
            self.process.stdin.write(content.encode('utf-8'))
            self.process.stdin.flush()
        except Exception as e:
            print(f"[LSP] Failed to send message: {e}")

    def _read_loop(self):
        """Read messages from the server."""
        while self.running and self.process and self.process.stdout:
            try:
                # Read headers
                headers = {}
                while True:
                    line = self.process.stdout.readline().decode('utf-8')
                    if not line or line == '\r\n':
                        break
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip()] = value.strip()

                if 'Content-Length' not in headers:
                    continue

                # Read content
                content_length = int(headers['Content-Length'])
                content = self.process.stdout.read(content_length).decode('utf-8')

                message = json.loads(content)
                self._handle_message(message)

            except Exception as e:
                if self.running:
                    print(f"[LSP] Read error: {e}")
                break

    def _handle_message(self, message: dict):
        """Handle incoming message from server."""
        # Response to our request
        if 'id' in message and message['id'] in self.pending_requests:
            self.pending_requests[message['id']].put(message)
            return

        # Notification from server (e.g., diagnostics)
        if 'method' in message:
            self.on_message(message)

    # Public API for LSP requests

    def did_open(self, uri: str, language_id: str, text: str):
        """Notify server that a document was opened."""
        self._send_notification('textDocument/didOpen', {
            'textDocument': {
                'uri': uri,
                'languageId': language_id,
                'version': 1,
                'text': text
            }
        })

    def did_change(self, uri: str, version: int, text: str):
        """Notify server of document changes."""
        self._send_notification('textDocument/didChange', {
            'textDocument': {'uri': uri, 'version': version},
            'contentChanges': [{'text': text}]
        })

    def did_save(self, uri: str, text: str = None):
        """Notify server that document was saved."""
        params = {'textDocument': {'uri': uri}}
        if text:
            params['text'] = text
        self._send_notification('textDocument/didSave', params)

    def did_close(self, uri: str):
        """Notify server that document was closed."""
        self._send_notification('textDocument/didClose', {
            'textDocument': {'uri': uri}
        })

    def completion(self, uri: str, line: int, character: int) -> Optional[dict]:
        """Request completion at position."""
        return self._send_request('textDocument/completion', {
            'textDocument': {'uri': uri},
            'position': {'line': line, 'character': character}
        })

    def hover(self, uri: str, line: int, character: int) -> Optional[dict]:
        """Request hover info at position."""
        return self._send_request('textDocument/hover', {
            'textDocument': {'uri': uri},
            'position': {'line': line, 'character': character}
        })

    def definition(self, uri: str, line: int, character: int) -> Optional[dict]:
        """Request go-to-definition."""
        return self._send_request('textDocument/definition', {
            'textDocument': {'uri': uri},
            'position': {'line': line, 'character': character}
        })

    def references(self, uri: str, line: int, character: int) -> Optional[dict]:
        """Request find references."""
        return self._send_request('textDocument/references', {
            'textDocument': {'uri': uri},
            'position': {'line': line, 'character': character},
            'context': {'includeDeclaration': True}
        })

    def signature_help(self, uri: str, line: int, character: int) -> Optional[dict]:
        """Request signature help."""
        return self._send_request('textDocument/signatureHelp', {
            'textDocument': {'uri': uri},
            'position': {'line': line, 'character': character}
        })


class LSPManager:
    """Manages multiple language servers for different projects."""

    def __init__(self):
        # Key: (project_path, language) -> LSPServer
        self.servers: Dict[tuple, LSPServer] = {}
        self.lock = threading.Lock()
        self.message_handlers: Dict[str, Callable[[str, dict], None]] = {}

    def get_language_for_file(self, file_path: str) -> Optional[str]:
        """Determine language from file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        for lang, config in LANGUAGE_SERVERS.items():
            if ext in config['extensions']:
                return lang
        return None

    def get_server(self, project_path: str, language: str) -> Optional[LSPServer]:
        """Get or create a language server for the project/language."""
        key = (project_path, language)

        with self.lock:
            if key in self.servers:
                server = self.servers[key]
                if server.running:
                    return server
                else:
                    del self.servers[key]

            # Create new server
            def on_message(msg):
                self._handle_server_message(project_path, language, msg)

            server = LSPServer(language, project_path, on_message)
            if server.start():
                self.servers[key] = server
                return server
            return None

    def stop_server(self, project_path: str, language: str):
        """Stop a specific language server."""
        key = (project_path, language)
        with self.lock:
            if key in self.servers:
                self.servers[key].stop()
                del self.servers[key]

    def stop_all(self):
        """Stop all language servers."""
        with self.lock:
            for server in self.servers.values():
                server.stop()
            self.servers.clear()

    def register_message_handler(self, session_id: str, handler: Callable[[str, dict], None]):
        """Register a handler for server notifications."""
        self.message_handlers[session_id] = handler

    def unregister_message_handler(self, session_id: str):
        """Unregister a message handler."""
        if session_id in self.message_handlers:
            del self.message_handlers[session_id]

    def _handle_server_message(self, project_path: str, language: str, message: dict):
        """Handle notification from language server."""
        # Forward diagnostics and other notifications to all handlers
        for handler in self.message_handlers.values():
            try:
                handler(language, message)
            except Exception as e:
                print(f"[LSP] Handler error: {e}")


# Global LSP Manager instance
lsp_manager = LSPManager()


if __name__ == '__main__':
    # Test the LSP Manager
    import tempfile

    # Create a test Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('import os\n\nos.path.join("a", "b")\n')
        test_file = f.name

    test_dir = os.path.dirname(test_file)

    def on_notification(lang, msg):
        print(f"Notification from {lang}: {msg.get('method')}")

    manager = LSPManager()
    manager.register_message_handler('test', on_notification)

    server = manager.get_server(test_dir, 'python')
    if server:
        uri = f'file://{test_file}'

        # Open document
        with open(test_file) as f:
            content = f.read()
        server.did_open(uri, 'python', content)

        time.sleep(1)

        # Test completion
        result = server.completion(uri, 2, 8)  # After "os.path."
        if result and 'result' in result:
            items = result['result']
            if isinstance(items, dict):
                items = items.get('items', [])
            print(f"Completions: {[item.get('label') for item in items[:5]]}")

        # Test hover
        result = server.hover(uri, 0, 8)  # On "os"
        if result and 'result' in result:
            print(f"Hover: {result['result']}")

        server.did_close(uri)

    manager.stop_all()
    os.unlink(test_file)
    print("Test completed!")
