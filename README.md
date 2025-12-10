# Obsidian Vault MCP Server

[![Build](https://github.com/MarkOnFire/obsidian-vault-mcp/actions/workflows/build.yml/badge.svg)](https://github.com/MarkOnFire/obsidian-vault-mcp/actions/workflows/build.yml)

Model Context Protocol (MCP) server that provides Claude for Desktop with read access to your Obsidian vault.

## Features

- **Read Notes**: Access any note's content by path or title
- **Search Content**: Full-text search across all notes
- **List Notes**: Browse by folder, PARA location, or tags
- **Query Metadata**: Filter by frontmatter properties, tags, dates
- **Follow Links**: Resolve wikilinks and find backlinks
- **PARA-Aware**: Understands your PARA organizational structure
- **Task Stats**: Get aggregated task statistics for project folders

## Tools Provided

### `obsidian_read_note`
Read the full content of a note by path or title.

**Parameters**:
- `path` (optional): Absolute or vault-relative path
- `title` (optional): Note title (searches if multiple matches)
- `resolve_links` (optional): Include linked note titles in response

**Example**:
```json
{
  "title": "Project Dashboard",
  "resolve_links": true
}
```

### `obsidian_search_notes`
Search note contents with full-text search.

**Parameters**:
- `query`: Search term or phrase
- `para_location` (optional): Filter by PARA (inbox, projects, areas, resources, archive)
- `folder` (optional): Limit to specific folder
- `limit` (optional): Maximum results (default: 20)

**Example**:
```json
{
  "query": "meeting notes",
  "para_location": "projects",
  "limit": 10
}
```

### `obsidian_list_notes`
List notes by folder, PARA location, or tags.

**Parameters**:
- `para_location` (optional): Filter by PARA location
- `folder` (optional): Specific folder path
- `tags` (optional): Array of tags (AND logic)
- `created_after` (optional): ISO date string
- `created_before` (optional): ISO date string
- `limit` (optional): Maximum results (default: 50)

**Example**:
```json
{
  "para_location": "projects",
  "tags": ["work"],
  "limit": 20
}
```

### `obsidian_get_backlinks`
Find all notes that link to a specific note.

**Parameters**:
- `note_title`: Title of the note to find backlinks for

**Example**:
```json
{
  "note_title": "Project Dashboard"
}
```

### `obsidian_resolve_link`
Resolve a wikilink to its target note.

**Parameters**:
- `link`: Wikilink text (e.g., "[[Project Dashboard]]" or just "Project Dashboard")

**Example**:
```json
{
  "link": "Project Dashboard"
}
```

### `obsidian_get_task_stats`
Get aggregated task statistics for all notes in a folder.

**Parameters**:
- `folder_path`: Folder to scan for tasks
- `lookback_days` (optional): Days to look back for recent completions (default: 7)

### `obsidian_get_project_activity`
Get activity summary for each project note in a folder.

**Parameters**:
- `folder_path`: Project folder to scan

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/MarkOnFire/obsidian-vault-mcp.git
cd obsidian-vault-mcp
```

### 2. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Claude for Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent config location on your platform:

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "/path/to/obsidian-vault-mcp/venv/bin/python",
      "args": [
        "-m",
        "obsidian_vault_mcp"
      ],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

Replace:
- `/path/to/obsidian-vault-mcp/` with where you cloned this repo
- `/path/to/your/obsidian/vault` with your actual Obsidian vault path

### 4. Restart Claude for Desktop

The tools will be available automatically in your conversations.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Yes | Absolute path to your Obsidian vault |
| `OBSIDIAN_VAULT_LOG_LEVEL` | No | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `OBSIDIAN_VAULT_MCP_LOG` | No | Custom log file path |

### Config File (Optional)

Create `config.json` in the server directory for advanced configuration:

```json
{
  "vault_path": "/path/to/your/vault",
  "para_folders": {
    "inbox": "0 - INBOX",
    "projects": "1 - Projects",
    "areas": "2 - Areas",
    "resources": "3 - Resources",
    "archive": "4 - Archive"
  },
  "exclude_folders": [
    ".obsidian",
    ".trash",
    "node_modules"
  ],
  "max_search_results": 100
}
```

## Usage Examples

### In Claude for Desktop

**Read a specific note**:
> "Can you read my Project Dashboard note and summarize the current projects?"

**Search for information**:
> "Search my vault for notes about 'authentication' in the projects folder"

**List notes by criteria**:
> "Show me all notes in my work project folder created this month"

**Follow wikilinks**:
> "Read my Weekly 1-on-1 note and also read any linked project notes"

**Find backlinks**:
> "Which notes link to my 'Career Development' note?"

**Get task stats**:
> "What's the task status across my Projects folder?"

## Development

### Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

### Manual Testing

```bash
# Test as MCP server
source venv/bin/activate
python -m obsidian_vault_mcp

# Test individual operations
OBSIDIAN_VAULT_PATH=/path/to/vault python test_operations.py
```

### Logging

Logs are written to `~/.local/share/obsidian-vault-mcp/server.log` by default.

Override with:
```bash
export OBSIDIAN_VAULT_MCP_LOG=/custom/path/to/server.log
```

Set log level:
```bash
export OBSIDIAN_VAULT_LOG_LEVEL=DEBUG
```

## Architecture

```
obsidian-vault-mcp/
├── obsidian_vault_mcp/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # MCP server entry point
│   ├── server.py            # MCP server implementation
│   ├── vault.py             # Vault operations (read, search, index)
│   ├── parser.py            # Markdown and frontmatter parsing
│   ├── config.py            # Configuration management
│   └── tasks.py             # Task statistics operations
├── requirements.txt         # Python dependencies
├── setup.py                 # Package setup
├── setup.sh                 # Quick setup script
└── README.md                # This file
```

## Security Considerations

- **Read-Only**: This server provides read-only access to your vault
- **No Modifications**: Cannot create, edit, or delete notes
- **Local Only**: Runs locally, no network access required
- **Vault Integrity**: Uses safe file operations with proper encoding

## Troubleshooting

### Server Not Appearing in Claude

1. Check Claude Desktop config is valid JSON
2. Restart Claude for Desktop completely
3. Check logs: `~/.local/share/obsidian-vault-mcp/server.log`
4. Verify vault path is correct and accessible

### Search Not Finding Notes

1. Ensure notes have proper markdown extensions (.md)
2. Check `exclude_folders` config isn't filtering them out
3. Verify notes contain readable text (not just frontmatter)

### Permission Errors

1. Ensure vault path is readable
2. Check iCloud sync status (vault must be downloaded locally)
3. Verify Python has disk access permissions (System Preferences → Security on macOS)

## Contributing

Contributions welcome! Please open an issue or PR.

## License

MIT License

Copyright (c) 2024 Mark Riechers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
