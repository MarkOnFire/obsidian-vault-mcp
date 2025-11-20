"""Configuration management for Obsidian Vault MCP server."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class VaultConfig(BaseModel):
    """Configuration for Obsidian vault access."""

    vault_path: Path = Field(
        description="Absolute path to Obsidian vault"
    )

    para_folders: Dict[str, str] = Field(
        default={
            "inbox": "0 - INBOX",
            "projects": "1 - Projects",
            "areas": "2 - AREAS",
            "resources": "3 - RESOURCES",
            "archive": "4 - ARCHIVE"
        },
        description="PARA method folder mappings"
    )

    exclude_folders: List[str] = Field(
        default=[".obsidian", ".trash", "node_modules"],
        description="Folders to exclude from indexing and search"
    )

    max_search_results: int = Field(
        default=100,
        description="Maximum number of search results to return"
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    class Config:
        extra = "allow"


def load_config(config_path: Optional[Path] = None) -> VaultConfig:
    """
    Load configuration from file or environment variables.

    Priority:
    1. Explicitly provided config file
    2. config.json in server directory
    3. Environment variables
    4. Defaults

    Args:
        config_path: Optional path to config file

    Returns:
        VaultConfig instance

    Raises:
        ValueError: If vault_path is not configured
    """
    config_data = {}

    # Try loading from config file
    if config_path and config_path.exists():
        with open(config_path) as f:
            config_data = json.load(f)
    else:
        # Try default location
        default_config = Path(__file__).parent / "config.json"
        if default_config.exists():
            with open(default_config) as f:
                config_data = json.load(f)

    # Override with environment variables
    vault_path_env = os.getenv("OBSIDIAN_VAULT_PATH")
    if vault_path_env:
        config_data["vault_path"] = vault_path_env

    log_level_env = os.getenv("OBSIDIAN_VAULT_LOG_LEVEL")
    if log_level_env:
        config_data["log_level"] = log_level_env

    # Ensure vault_path is set
    if "vault_path" not in config_data:
        raise ValueError(
            "vault_path must be configured via config.json or "
            "OBSIDIAN_VAULT_PATH environment variable"
        )

    # Convert vault_path to Path object
    config_data["vault_path"] = Path(config_data["vault_path"]).expanduser().resolve()

    # Validate vault exists
    if not config_data["vault_path"].exists():
        raise ValueError(
            f"Vault path does not exist: {config_data['vault_path']}"
        )

    return VaultConfig(**config_data)


def get_para_location(file_path: Path, config: VaultConfig) -> Optional[str]:
    """
    Determine PARA location based on file path.

    Args:
        file_path: Absolute path to the file
        config: VaultConfig instance

    Returns:
        PARA location key (inbox, projects, areas, resources, archive) or None
    """
    try:
        relative_path = file_path.relative_to(config.vault_path)
    except ValueError:
        return None

    # Check each PARA folder
    for para_key, para_folder in config.para_folders.items():
        if str(relative_path).startswith(para_folder):
            return para_key

    return None


def is_excluded(file_path: Path, config: VaultConfig) -> bool:
    """
    Check if file path should be excluded from indexing.

    Args:
        file_path: Absolute path to check
        config: VaultConfig instance

    Returns:
        True if file should be excluded
    """
    try:
        relative_path = file_path.relative_to(config.vault_path)
    except ValueError:
        return True

    # Check if any part of the path matches excluded folders
    for part in relative_path.parts:
        if part in config.exclude_folders:
            return True

    return False
