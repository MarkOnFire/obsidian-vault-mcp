"""Setup script for Obsidian Vault MCP server."""

from setuptools import setup, find_packages

setup(
    name="obsidian-vault-mcp",
    version="0.1.0",
    description="MCP server for Obsidian vault access",
    author="Mark Riechers",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "mcp>=1.0.0",
        "pydantic>=2.0.0",
        "python-frontmatter>=1.0.0",
        "markdown>=3.5.0",
    ],
    entry_points={
        "console_scripts": [
            "obsidian-vault-mcp=obsidian_vault_mcp.server:run_server",
        ],
    },
)
