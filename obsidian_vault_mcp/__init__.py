"""Obsidian Vault MCP Server - Read access to Obsidian notes."""

__version__ = "0.1.0"

from .config import VaultConfig, load_config
from .vault import VaultReader
from .server import create_server, run_server

__all__ = [
    "VaultConfig",
    "load_config",
    "VaultReader",
    "create_server",
    "run_server",
]
