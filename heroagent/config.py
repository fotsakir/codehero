"""
HeroAgent Configuration Loader

Loads configuration from YAML file and environment variables.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


# Default configuration paths
CONFIG_PATHS = [
    '/etc/codehero/heroagent.conf',
    '/opt/codehero/heroagent/heroagent.conf',
    os.path.expanduser('~/.config/heroagent/config.yaml'),
    os.path.expanduser('~/.heroagent.conf'),
]

# Environment file paths
ENV_PATHS = [
    '/etc/codehero/heroagent.env',
    os.path.expanduser('~/.claude/.env'),
    os.path.expanduser('~/.heroagent.env'),
]

# Default configuration
DEFAULT_CONFIG = {
    'default_provider': 'anthropic',
    'default_model': 'sonnet',
    'model_aliases': {
        'opus': 'claude-sonnet-4-20250514',
        'sonnet': 'claude-sonnet-4-20250514',
        'haiku': 'claude-haiku-4-20250514',
    },
    'providers': {
        'anthropic': {
            'api_key': '${ANTHROPIC_API_KEY}',
            'models': [
                'claude-sonnet-4-20250514',
                'claude-haiku-4-20250514',
            ],
        },
        'gemini': {
            'api_key': '${GEMINI_API_KEY}',
            'models': [
                'gemini-2.5-pro',
                'gemini-2.0-flash',
            ],
        },
        'grok': {
            'api_key': '${GROK_API_KEY}',
            'base_url': 'https://api.x.ai/v1',
            'models': [
                'grok-3',
                'grok-3-mini',
            ],
        },
        'openai': {
            'api_key': '${OPENAI_API_KEY}',
            'models': [
                'gpt-4o',
                'gpt-4o-mini',
            ],
        },
        'ollama': {
            'base_url': 'http://localhost:11434',
            'models': [
                'llama3.3',
                'codellama',
                'qwen2.5-coder',
            ],
        },
    },
    'mcp_servers': {
        'codehero': {
            'command': 'python3',
            'args': ['/opt/codehero/scripts/mcp_server.py'],
        },
    },
    'hooks': {
        'permission_hook': '/opt/codehero/scripts/semi_autonomous_hook.py',
    },
    'tools': {
        'bash': {
            'timeout': 120000,
            'max_output': 30000,
        },
        'read': {
            'max_lines': 2000,
        },
        'edit': {
            'backup': False,
        },
    },
    'output': {
        'completion_marker': 'TASK COMPLETED',
        'max_tokens': 16384,
    },
}


def load_env_files():
    """Load environment variables from .env files."""
    for env_path in ENV_PATHS:
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            if key not in os.environ:
                                os.environ[key] = value
            except Exception:
                pass


def expand_env_vars(value: Any) -> Any:
    """Recursively expand environment variables in config values."""
    if isinstance(value, str):
        # Match ${VAR_NAME} pattern
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.environ.get(var_name, '')
            value = value.replace(f'${{{var_name}}}', env_value)
        return value
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    """HeroAgent configuration manager."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Optional path to config file. If not provided,
                        searches default locations.
        """
        # Load environment files first
        load_env_files()

        # Start with default config
        self._config = DEFAULT_CONFIG.copy()

        # Find and load config file
        config_file = self._find_config_file(config_path)
        if config_file:
            self._load_config_file(config_file)

        # Expand environment variables
        self._config = expand_env_vars(self._config)

    def _find_config_file(self, config_path: Optional[str] = None) -> Optional[str]:
        """Find configuration file."""
        if config_path and os.path.exists(config_path):
            return config_path

        for path in CONFIG_PATHS:
            if os.path.exists(path):
                return path

        return None

    def _load_config_file(self, path: str):
        """Load configuration from YAML file."""
        try:
            with open(path, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self._config = deep_merge(self._config, file_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}")

    @property
    def default_provider(self) -> str:
        """Get default provider name."""
        return self._config.get('default_provider', 'anthropic')

    @property
    def default_model(self) -> str:
        """Get default model alias."""
        return self._config.get('default_model', 'sonnet')

    def get_model_name(self, alias: str, provider: Optional[str] = None) -> str:
        """Resolve model alias to actual model name.

        Args:
            alias: Model alias (opus/sonnet/haiku) or direct model name
            provider: Provider name for per-provider aliases

        Returns:
            Actual model name
        """
        aliases = self._config.get('model_aliases', {})

        # Check for per-provider aliases (new format)
        if provider and provider in aliases:
            provider_aliases = aliases[provider]
            if isinstance(provider_aliases, dict) and alias in provider_aliases:
                return provider_aliases[alias]

        # Fall back to flat aliases (old format) or direct model name
        if isinstance(aliases.get(alias), str):
            return aliases[alias]

        return alias

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        providers = self._config.get('providers', {})
        return providers.get(provider, {})

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider."""
        provider_config = self.get_provider_config(provider)
        api_key = provider_config.get('api_key', '')
        return api_key if api_key else None

    def get_mcp_server(self, name: str) -> Optional[Dict[str, Any]]:
        """Get MCP server configuration."""
        servers = self._config.get('mcp_servers', {})
        return servers.get(name)

    def get_hook_script(self, hook_name: str = 'permission_hook') -> Optional[str]:
        """Get hook script path."""
        hooks = self._config.get('hooks', {})
        return hooks.get(hook_name)

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool."""
        tools = self._config.get('tools', {})
        return tools.get(tool_name, {})

    @property
    def completion_marker(self) -> str:
        """Get task completion marker string."""
        output = self._config.get('output', {})
        return output.get('completion_marker', 'TASK COMPLETED')

    @property
    def max_tokens(self) -> int:
        """Get maximum tokens for responses."""
        output = self._config.get('output', {})
        return output.get('max_tokens', 16384)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key path (dot notation)."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def __getitem__(self, key: str) -> Any:
        """Get a configuration value by key."""
        return self.get(key)


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration."""
    global _config
    _config = Config(config_path)
    return _config
