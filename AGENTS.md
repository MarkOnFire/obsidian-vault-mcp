# AGENTS.md

This file provides guidance to AI coding agents working in this repository.

## Repository Purpose

Obsidian Vault MCP Server provides AI agents with access to Obsidian vaults. It enables reading notes, searching content, following wikilinks, querying metadata, creating notes, and adding attachments - all with PARA methodology awareness.

## Architecture Overview

```
obsidian-vault-mcp/
├── obsidian_vault_mcp/
│   ├── __init__.py      # Package initialization
│   ├── __main__.py      # MCP server entry point
│   ├── server.py        # MCP server implementation
│   ├── vault.py         # Vault operations (read, search, index)
│   ├── parser.py        # Markdown and frontmatter parsing
│   ├── config.py        # Configuration management
│   └── tasks.py         # Task statistics operations
├── setup.py             # Package setup
├── requirements.txt     # Python dependencies
├── test_*.py            # Test files
└── README.md            # User documentation
```

## Development Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run MCP server (for testing)
python -m obsidian_vault_mcp

# Run tests
python -m pytest tests/ -v

# Test individual operations
OBSIDIAN_VAULT_PATH=/path/to/vault python test_operations.py

# Validate Python syntax
python3 -m compileall obsidian_vault_mcp/
```

## MCP Tools Provided

### `obsidian_read_note`
Read the full content of a note by path or title. Optionally resolve wikilinks.

### `obsidian_search_notes`
Full-text search across notes with PARA location and folder filtering.

### `obsidian_list_notes`
List notes by folder, PARA location, tags, or date range.

### `obsidian_get_backlinks`
Find all notes that link to a specific note.

### `obsidian_resolve_link`
Resolve a wikilink to its target note path.

### `obsidian_get_task_stats`
Get aggregated task statistics for all notes in a folder.

### `obsidian_get_project_activity`
Get activity summary for each project note in a folder.

### `obsidian_get_weekly_summary`
Get vault activity summary for a time period (default: last 7 days).

### `obsidian_gather_topic`
Gather all information on a topic from the vault with backlinks.

### `obsidian_create_daily_note`
Create or append to a daily note in the configured daily notes folder.

### `obsidian_create_inbox_note`
Create a new note in the INBOX folder for later processing.

### `obsidian_add_attachment`
Add an attachment (PDF, image, etc.) to the Archive folder. Supports:
- Copying from local file path
- Saving base64-encoded content
- Auto-appending wikilink to a specified note
- Embed syntax for images (`![[]]`)

## Coding Conventions

- Python 3.9+ with type hints
- Use pathlib for all path operations
- Handle various markdown formats gracefully
- Respect PARA folder structure conventions
- Write operations use atomic file operations (temp file → rename)
- Write operations limited to INBOX and Archive folders

## Testing Guidelines

- Test with actual Obsidian vaults
- Verify PARA location detection
- Test wikilink resolution with various formats
- Test task parsing in different note structures
- Manual testing via Claude Desktop

## Commit Conventions

This project follows workspace-wide commit conventions.
**See**: `/Users/mriechers/Developer/the-lodge/conventions/COMMIT_CONVENTIONS.md`

## Important Paths

- `obsidian_vault_mcp/server.py` - Main MCP server with tool definitions
- `obsidian_vault_mcp/vault.py` - Core vault operations
- `obsidian_vault_mcp/parser.py` - Markdown and frontmatter parsing
- `config.json` - Optional configuration file

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Yes | Absolute path to Obsidian vault |
| `OBSIDIAN_VAULT_LOG_LEVEL` | No | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `OBSIDIAN_VAULT_MCP_LOG` | No | Custom log file path |

### Config File (Optional)

Create `config.json` for advanced configuration:
```json
{
  "vault_path": "/path/to/vault",
  "para_folders": {
    "inbox": "0 - INBOX",
    "projects": "1 - Projects",
    "areas": "2 - Areas",
    "resources": "3 - Resources",
    "archive": "4 - Archive"
  },
  "exclude_folders": [".obsidian", ".trash"],
  "daily_notes_folder": "0 - INBOX",
  "daily_notes_format": "%Y-%m-%d",
  "attachment_folder": "4 - ARCHIVE",
  "supported_attachment_types": ["pdf", "png", "jpg", "jpeg", "gif", "webp", "svg", "mp3", "mp4", "wav", "mov"],
  "max_attachment_size_mb": 100
}
```

## Common Workflows

### Adding a New Tool

1. Define tool function in `server.py` with `@mcp.tool()` decorator
2. Implement core logic in `vault.py` or appropriate module
3. Add tests in `test_*.py` files
4. Update README.md with new tool documentation

### Updating PARA Detection

1. Modify `config.py` with new folder mappings
2. Update `vault.py` location detection logic
3. Test with vaults using different PARA structures
