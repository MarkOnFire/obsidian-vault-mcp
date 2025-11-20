# Obsidian Vault MCP Server

Model Context Protocol (MCP) server that provides Claude for Desktop with read access to your Obsidian vault.

## Features

- **Read Notes**: Access any note's content by path or title
- **Search Content**: Full-text search across all notes
- **List Notes**: Browse by folder, PARA location, or tags
- **Query Metadata**: Filter by frontmatter properties, tags, dates
- **Follow Links**: Resolve wikilinks and find backlinks
- **PARA-Aware**: Understands your PARA organizational structure

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
  "tags": ["pbswi"],
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

## Installation

### 1. Install Dependencies

```bash
cd /Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Claude for Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "/Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp/venv/bin/python",
      "args": [
        "-m",
        "obsidian_vault_mcp"
      ],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain"
      }
    }
  }
}
```

### 3. Restart Claude for Desktop

The tools will be available automatically in your conversations.

## Configuration

### Environment Variables

- `OBSIDIAN_VAULT_PATH` (required): Absolute path to your Obsidian vault
- `OBSIDIAN_VAULT_LOG_LEVEL` (optional): Logging level (DEBUG, INFO, WARNING, ERROR)

### Config File (Optional)

Create `config.json` in the server directory:

```json
{
  "vault_path": "/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain",
  "para_folders": {
    "inbox": "0 - INBOX",
    "projects": "1 - Projects",
    "areas": "2 - AREAS",
    "resources": "3 - RESOURCES",
    "archive": "4 - ARCHIVE"
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
> "Show me all notes in my PBSWI project folder created this month"

**Follow wikilinks**:
> "Read my Weekly 1-on-1 note and also read any linked project notes"

**Find backlinks**:
> "Which notes link to my 'Career Development' note?"

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
python test_operations.py
```

### Logging

Logs are written to:
```
/Users/mriechers/Developer/obsidian-config/logs/obsidian-vault-mcp.log
```

Set log level via environment variable:
```bash
export OBSIDIAN_VAULT_LOG_LEVEL=DEBUG
```

## Architecture

```
obsidian-vault-mcp/
├── __init__.py              # Package initialization
├── __main__.py              # MCP server entry point
├── server.py                # MCP server implementation
├── vault.py                 # Vault operations (read, search, index)
├── parser.py                # Markdown and frontmatter parsing
├── config.py                # Configuration management
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── tests/
    ├── test_vault.py       # Vault operation tests
    ├── test_parser.py      # Parser tests
    └── test_server.py      # MCP server tests
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
3. Check logs: `/Users/mriechers/Developer/obsidian-config/logs/obsidian-vault-mcp.log`
4. Verify vault path is correct and accessible

### Search Not Finding Notes

1. Ensure notes have proper markdown extensions (.md)
2. Check `exclude_folders` config isn't filtering them out
3. Verify notes contain readable text (not just frontmatter)

### Permission Errors

1. Ensure vault path is readable
2. Check iCloud sync status (vault must be downloaded)
3. Verify Python has disk access permissions (System Preferences → Security)

## Related Tools

- **Codex MCP Server**: Code review and analysis with OpenAI
- **Quick PARA Plugin**: Automatic PARA tagging and organization
- **Google Docs Sync Plugin**: Bidirectional sync with Google Docs (in development)

## License

MIT License - Part of the obsidian-config repository
