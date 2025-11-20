# Obsidian Vault MCP - Quick Start

Get your Obsidian vault connected to Claude for Desktop in 5 minutes.

## Installation

### 1. Install Dependencies

```bash
cd /Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Claude for Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

**Important**: If you already have other MCP servers configured (like `codex`), add the `obsidian-vault` entry inside the existing `mcpServers` object:

```json
{
  "mcpServers": {
    "codex": {
      "command": "...",
      "args": ["..."],
      "env": {"..."}
    },
    "obsidian-vault": {
      "command": "/Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp/venv/bin/python",
      "args": ["-m", "obsidian_vault_mcp"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain"
      }
    }
  }
}
```

### 3. Restart Claude for Desktop

Completely quit and restart Claude for Desktop.

## Test It

### Run Standalone Test

```bash
cd /Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp
source venv/bin/activate
python test_operations.py
```

You should see output showing:
- Number of notes indexed
- Sample search results
- Notes by PARA location
- Backlink examples

### Use in Claude for Desktop

Open a new conversation and try:

**Read a note**:
> "Read my Project Dashboard note"

**Search notes**:
> "Search my vault for notes about 'authentication'"

**List by PARA location**:
> "Show me all notes in my Projects folder"

**Find backlinks**:
> "Which notes link to my Career Development note?"

## Verify It's Working

### Check the Tools Are Available

In Claude for Desktop, ask:
> "What MCP tools do you have access to?"

You should see tools starting with `obsidian_`:
- `obsidian_read_note`
- `obsidian_search_notes`
- `obsidian_list_notes`
- `obsidian_get_backlinks`
- `obsidian_resolve_link`

### Check Logs

```bash
tail -f /Users/mriechers/Developer/obsidian-config/logs/obsidian-vault-mcp.log
```

You should see startup messages when Claude launches the server.

## Troubleshooting

### "MCP tools not showing up"

1. Verify config file is valid JSON (use `python -m json.tool < config_file.json`)
2. Check the Python path is correct: `/Users/mriechers/Developer/obsidian-config/mcp-servers/obsidian-vault-mcp/venv/bin/python`
3. Restart Claude for Desktop completely
4. Check logs for errors

### "Vault path does not exist"

1. Verify the path in config: `/Users/mriechers/Library/Mobile Documents/iCloud~md~obsidian/Documents/MarkBrain`
2. Ensure iCloud Drive is synced (files downloaded locally)
3. Check Finder → iCloud Drive → Obsidian → MarkBrain exists

### "No notes found"

1. Run standalone test to verify indexing works
2. Check `exclude_folders` isn't filtering out your notes
3. Ensure notes have `.md` extension

## Next Steps

- Read the full [README.md](README.md) for all features
- Customize `config.json` for your vault structure
- Try advanced queries with tags and date filters

## Example Queries

```
"Read my weekly 1-on-1 note and summarize action items"

"Search my PBSWI project notes for anything about authentication"

"List all notes created this week in my Projects folder"

"Show me everything tagged 'career' in my Resources folder"

"Read my Project Dashboard and all the linked project notes"

"Which notes link to my 'Authentication System' note?"
```
