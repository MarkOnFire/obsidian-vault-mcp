# Obsidian Vault MCP Server - Summary

Quick reference for the Obsidian Vault MCP server integration.

## What It Does

Provides Claude for Desktop with **read-only access** to your Obsidian vault, enabling:
- Reading notes by title or path
- Searching across all vault content
- Filtering by PARA location, tags, and dates
- Following wikilinks and finding backlinks
- Accessing metadata from frontmatter

## Installation Status

✅ **COMPLETE** - Server is built, tested, and configured

- Server implementation: Complete
- Claude Desktop config: Updated
- Dependencies installed: Yes (via `setup.sh`)
- Tests passing: Yes (1,387 notes indexed)
- Documentation: Complete

## Files Created

```
mcp-servers/obsidian-vault-mcp/
├── obsidian_vault_mcp/         # Python package
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # MCP server entry point
│   ├── config.py              # Configuration management
│   ├── parser.py              # Markdown/frontmatter parsing
│   ├── server.py              # MCP server implementation
│   └── vault.py               # Vault operations (read/search)
├── setup.py                    # Package setup
├── requirements.txt            # Dependencies
├── setup.sh                    # Automated setup script
├── test_operations.py          # Standalone tests
├── README.md                   # Complete documentation
├── QUICKSTART.md              # 5-minute setup guide
└── SUMMARY.md                 # This file
```

## Configuration

Added to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
"obsidian-vault": {
  "command": "/Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp/venv/bin/python",
  "args": ["-m", "obsidian_vault_mcp"],
  "env": {
    "OBSIDIAN_VAULT_PATH": "/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain"
  }
}
```

## Next Steps

### 1. Restart Claude for Desktop

**Required** to load the new MCP server.

### 2. Test the Integration

Try these queries in Claude for Desktop:

```
"What MCP tools do you have for Obsidian?"

"Read my Project Dashboard note"

"Search my vault for notes about authentication"

"List all notes in my PBSWI project folder"

"Which notes link to my Career Development note?"
```

### 3. Verify Tools Are Available

Ask Claude:
> "What MCP tools do you have access to?"

You should see:
- `obsidian_read_note`
- `obsidian_search_notes`
- `obsidian_list_notes`
- `obsidian_get_backlinks`
- `obsidian_resolve_link`

### 4. Check Logs (Optional)

```bash
tail -f /Users/mriechers/Developer/obsidian-config/logs/obsidian-vault-mcp.log
```

You should see startup messages when Claude launches the server.

## Usage Patterns

### Reading Notes

```
"Read my [note title] note"
"Show me the content of [note title]"
"What's in my [note title] note?"
```

### Searching

```
"Search my vault for [term]"
"Find notes about [topic] in my Projects folder"
"Search PBSWI notes for [keyword]"
```

### Listing Notes

```
"List all notes in Projects"
"Show me notes tagged with 'career'"
"What notes did I create this week?"
"List all PBSWI project notes"
```

### Following Links

```
"Read [note] and all the notes it links to"
"Which notes link to [note title]?"
"Show me backlinks for [note]"
```

## Architecture

### Components

1. **Config** (`config.py`): Load vault path, PARA folders, exclusions
2. **Parser** (`parser.py`): Parse markdown, frontmatter, extract metadata
3. **Vault** (`vault.py`): Index notes, search, filter, resolve links
4. **Server** (`server.py`): MCP server with 5 tools

### Index

- Builds in-memory index on startup
- Scans entire vault for `.md` files
- Excludes `.obsidian`, `.trash`, `node_modules`
- Indexes ~1,300+ notes in seconds

### Search

- Full-text search across titles and content
- Filter by PARA location, folder, tags
- Date range filtering
- Case-insensitive by default

### PARA Integration

- Understands your PARA folder structure
- Filters by inbox/projects/areas/resources/archive
- Respects frontmatter `para` property
- Compatible with Quick PARA plugin

## Performance

- **Startup**: ~2-3 seconds to index 1,300+ notes
- **Read**: Instant (in-memory index)
- **Search**: <1 second for most queries
- **Memory**: ~50-100MB for typical vault

## Security

- **Read-Only**: Cannot modify, create, or delete notes
- **Local Only**: No network access required
- **Safe Operations**: Proper file encoding, error handling
- **Vault Integrity**: Never writes to vault

## Maintenance

### Update Dependencies

```bash
cd /Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Rebuild Index

The index rebuilds automatically on startup. To force a rebuild, restart Claude for Desktop.

### Run Tests

```bash
cd /Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp
source venv/bin/activate
python test_operations.py
```

## Troubleshooting

See [README.md](README.md#troubleshooting) and [QUICKSTART.md](QUICKSTART.md#troubleshooting) for detailed troubleshooting steps.

Common issues:
- Tools not appearing → Verify config, restart Claude
- Vault not found → Check iCloud sync, verify path
- No notes indexed → Check exclude_folders, ensure .md files exist

## Integration with Other Tools

### Quick PARA Plugin

- Respects `para` frontmatter property
- Compatible with subfolder tags
- Understands PARA folder structure

### Templater

- Can read templates from vault
- Access template variables in frontmatter

### Tasks Plugin

- Can read task blocks from notes
- Search for specific task statuses

## Future Enhancements

Potential additions (not currently implemented):
- Write operations (create/edit notes)
- Task management integration
- Canvas file support
- Plugin settings access
- Real-time file watching

## Resources

- **Full Documentation**: [README.md](README.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Claude Desktop Config**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Logs**: `/Users/mriechers/Developer/obsidian-config/logs/obsidian-vault-mcp.log`
- **Project Instructions**: [CLAUDE.md](../../CLAUDE.md)
