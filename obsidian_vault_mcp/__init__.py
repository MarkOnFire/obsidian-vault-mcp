"""Obsidian Vault MCP Server - Read access to Obsidian notes."""

__version__ = "0.1.0"

# Core components (always available)
from .config import VaultConfig, load_config
from .vault import VaultReader

__all__ = [
    "VaultConfig",
    "load_config",
    "VaultReader",
]

# MCP server components (optional - requires mcp package)
# This allows using VaultReader without installing the full mcp dependency
try:
    from .server import create_server, run_server
    __all__.extend(["create_server", "run_server"])
except ImportError:
    pass  # mcp package not installed - server functions not available
