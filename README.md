# Obsidian Vault MCP Server

[![Build](https://github.com/MarkOnFire/obsidian-vault-mcp/actions/workflows/build.yml/badge.svg)](https://github.com/MarkOnFire/obsidian-vault-mcp/actions/workflows/build.yml)

A [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server that gives AI assistants full read and write access to your [Obsidian](https://obsidian.md/) vault. Built with first-class support for the [PARA method](https://fortelabs.com/blog/para/) and the [Obsidian Tasks](https://publish.obsidian.md/tasks/Introduction) plugin.

## Features

### Read & Search
- **Read Notes** -- Access any note by path or title, with optional wikilink resolution
- **Full-Text Search** -- Search across all notes with contextual snippets
- **List & Filter** -- Browse notes by PARA location, folder, tags, or date ranges
- **Backlinks & Wikilinks** -- Discover which notes link to a given note and resolve wikilinks
- **Task Statistics** -- Aggregated task stats per folder: completed, active, blocked, overdue, due soon
- **Project Activity** -- Per-project breakdown with staleness detection (no activity in 7 days)
- **Weekly Summary** -- Vault-wide activity report: completions by day, by project, overdue items
- **Topic Gathering** -- Collect everything related to a topic across the vault, grouped by PARA

### Write & Create
- **Create Notes** -- Place notes directly in any PARA location with optional subfolders
- **Inbox Capture** -- Quick-capture notes to INBOX for later processing
- **Daily Notes** -- Create or append to daily notes with automatic frontmatter
- **Attachments** -- Add PDFs, images, and other files to the vault with auto-linking to notes

### Daily Journal
- **Unarchived Note Detection** -- Find daily notes not yet filed into month folders
- **Task Extraction** -- Parse tasks from daily notes with section context and completion metadata
- **Smart Section Updates** -- Update daily note sections while preserving user modifications via hash-based change detection

## Tools

The server exposes 16 MCP tools organized into four categories.

### Read Tools

#### `obsidian_read_note`
Read the full content of a note by path or title.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | — | Absolute or vault-relative path |
| `title` | string | — | Note title (case-insensitive) |
| `resolve_links` | boolean | `false` | Include linked note titles in response |

At least one of `path` or `title` is required.

#### `obsidian_search_notes`
Full-text search across note contents.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | *required* | Search term or phrase |
| `para_location` | string | — | Filter by PARA location |
| `folder` | string | — | Limit to a specific folder |
| `limit` | integer | `20` | Maximum results |
| `include_snippets` | boolean | `false` | Include matching text with surrounding context |

#### `obsidian_list_notes`
List notes matching specific criteria. Returns metadata without full content.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `para_location` | string | — | Filter: `inbox`, `projects`, `areas`, `resources`, `archive` |
| `folder` | string | — | Specific folder path |
| `tags` | string[] | — | Tags to match (AND logic) |
| `created_after` | string | — | ISO date (`YYYY-MM-DD`) |
| `created_before` | string | — | ISO date |
| `modified_after` | string | — | ISO date |
| `modified_before` | string | — | ISO date |
| `limit` | integer | `50` | Maximum results |

#### `obsidian_get_backlinks`
Find all notes that contain wikilinks to a specific note.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `note_title` | string | *required* | Title of the target note |

#### `obsidian_resolve_link`
Resolve a wikilink to its target note and return metadata.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `link` | string | *required* | Wikilink text (e.g., `[[Project Dashboard]]` or `Project Dashboard`) |

### Analytics Tools

#### `obsidian_get_task_stats`
Aggregated task statistics for all notes in a folder. Parses Obsidian Tasks plugin syntax including due dates, priorities, completion dates, and blocked status.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_path` | string | *required* | Folder to scan (e.g., `1 - Projects/PBSWI`) |
| `lookback_days` | integer | `7` | Days to look back for recent completions |

#### `obsidian_get_project_activity`
Per-project activity summary. Identifies stale projects with no activity in the last 7 days.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_path` | string | *required* | Project folder to scan |

#### `obsidian_get_weekly_summary`
Summary of vault activity for a time period. Returns completions by day, by project, overdue tasks, and active task counts.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string | 7 days ago | Start date (`YYYY-MM-DD`) |
| `end_date` | string | today | End date (`YYYY-MM-DD`) |
| `para_location` | string | — | Filter by PARA location |

#### `obsidian_gather_topic`
Gather all information on a topic from the vault. Searches by content and tags, includes backlinks, and groups results by PARA location.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topic` | string | *required* | Search term, tag, or note title |
| `include_backlinks` | boolean | `true` | Include notes that link to matching notes |

### Write Tools

#### `obsidian_create_note`
Create a note in a specific PARA location with optional subfolder placement.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | *required* | Note title (used as filename) |
| `para_location` | string | *required* | `projects`, `areas`, `resources`, or `archive` |
| `content` | string | `""` | Markdown content |
| `subfolder` | string | — | Subfolder within the PARA location (e.g., `PBSWI`) |
| `tags` | string[] | — | Tags (without `#` prefix) |

#### `obsidian_create_inbox_note`
Quick-capture a note to the INBOX folder for later processing.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | *required* | Note title (used as filename) |
| `content` | string | `""` | Markdown content |
| `tags` | string[] | — | Tags (without `#` prefix) |

#### `obsidian_create_daily_note`
Create or append to a daily note. Stored in the configured daily notes folder.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | string | `""` | Markdown content |
| `date` | string | today | Date in `YYYY-MM-DD` format |
| `tags` | string[] | — | Tags (without `#` prefix) |
| `append_if_exists` | boolean | `false` | Append to existing note instead of failing |

#### `obsidian_add_attachment`
Add a file (PDF, image, etc.) to the vault's attachment folder. Optionally link it to an existing note.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_path` | string | — | Path to file on disk |
| `base64_content` | string | — | Base64-encoded file content (alternative to `source_path`) |
| `filename` | string | — | Filename (required when using `base64_content`) |
| `link_to_note` | string | — | Note title or path to append the wikilink to |
| `link_text` | string | — | Display text for the link |
| `embed` | boolean | `false` | Use `![[]]` syntax so images render inline |

Either `source_path` or `base64_content` + `filename` is required.

### Daily Journal Tools

#### `obsidian_get_unarchived_daily_notes`
Find daily journal notes that haven't been moved to month subfolders yet.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `exclude_today` | boolean | `true` | Exclude today's note from results |

#### `obsidian_extract_note_tasks`
Extract tasks from a note with checked/unchecked status, section context, and metadata.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `note_path` | string | *required* | Path to the note (absolute or vault-relative) |
| `sections` | string[] | — | Specific sections to extract from (e.g., `["Action Items"]`). Extracts all if omitted. |

#### `obsidian_update_daily_note`
Update specific sections of a daily note while preserving user-modified content. Uses HTML comment markers (`<!-- SECTION:name:START -->` / `<!-- SECTION:name:END -->`) and hash-based modification detection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | string | *required* | Date (`YYYY-MM-DD`) |
| `sections` | object | *required* | Map of section names to new content |
| `preserve_modified` | boolean | `true` | Skip sections the user has manually edited |
| `create_if_missing` | boolean | `false` | Create the note from a template if it doesn't exist |
| `template` | string | — | Template string for new notes (required if `create_if_missing` is true and the note doesn't exist) |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/MarkOnFire/obsidian-vault-mcp.git
cd obsidian-vault-mcp
```

### 2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Claude for Desktop

Add the server to your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "obsidian-vault": {
      "command": "/path/to/obsidian-vault-mcp/venv/bin/python",
      "args": ["-m", "obsidian_vault_mcp"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/obsidian/vault"
      }
    }
  }
}
```

Replace the paths with your actual locations.

### 4. Restart Claude for Desktop

The 16 tools will be available automatically in your conversations.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Yes | Absolute path to your Obsidian vault |
| `OBSIDIAN_VAULT_LOG_LEVEL` | No | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OBSIDIAN_VAULT_MCP_LOG` | No | Custom log file path |

### Config File

Create `config.json` in the server directory for full control:

```json
{
  "vault_path": "/path/to/your/vault",
  "para_folders": {
    "inbox": "0 - INBOX",
    "projects": "1 - Projects",
    "areas": "2 - AREAS",
    "resources": "3 - RESOURCES",
    "archive": "4 - ARCHIVE"
  },
  "exclude_folders": [".obsidian", ".trash", "node_modules"],
  "max_search_results": 100,
  "daily_notes_folder": "0 - INBOX",
  "daily_notes_format": "%Y-%m-%d",
  "daily_journal_folder": "0 - INBOX/DAILY JOURNAL",
  "daily_journal_archive_pattern": "JANUARY|FEBRUARY|...|DECEMBER",
  "attachment_folder": "4 - ARCHIVE",
  "supported_attachment_types": ["pdf", "png", "jpg", "jpeg", "gif", "webp", "svg", "mp3", "mp4", "wav", "mov"],
  "max_attachment_size_mb": 100
}
```

All fields except `vault_path` have sensible defaults and can be omitted. Environment variables override config file values.

## Usage Examples

### Reading and Searching

> "Read my Project Dashboard note and summarize the current projects."

> "Search my vault for notes about 'authentication' in the projects folder."

> "Show me all notes tagged 'work' that were modified in the last week."

> "Which notes link to my 'Career Development' note?"

### Analytics

> "What's the task status across my Projects folder?"

> "Give me a weekly summary of what I accomplished."

> "Gather everything I have on the topic of 'machine learning'."

> "Which of my projects are stale?"

### Writing

> "Create a new note called 'API Redesign' in my PBSWI project folder."

> "Capture this idea to my inbox: voice-controlled task management."

> "Add today's daily note with my meeting notes."

> "Attach this PDF to my 'Research Paper' note."

### Daily Journal

> "What daily notes haven't been archived yet?"

> "Extract the unchecked tasks from yesterday's daily note."

> "Update today's daily note calendar section with my meeting schedule."

## Development

### Running the Server

```bash
source venv/bin/activate
python -m obsidian_vault_mcp
```

### Running Tests

```bash
source venv/bin/activate
OBSIDIAN_VAULT_PATH=/path/to/test/vault python test_operations.py
OBSIDIAN_VAULT_PATH=/path/to/test/vault python test_task_stats.py
```

### Logging

Logs go to `~/.local/share/obsidian-vault-mcp/server.log` by default.

```bash
# Custom log location
export OBSIDIAN_VAULT_MCP_LOG=/custom/path/server.log

# Verbose logging
export OBSIDIAN_VAULT_LOG_LEVEL=DEBUG
```

## Architecture

```
obsidian-vault-mcp/
├── obsidian_vault_mcp/
│   ├── __init__.py        # Package exports
│   ├── __main__.py        # Entry point
│   ├── server.py          # MCP server, tool definitions, and request handling
│   ├── vault.py           # Vault index, read/write operations, daily journal ops
│   ├── parser.py          # Markdown parsing, frontmatter extraction, wikilink resolution
│   ├── config.py          # Configuration loading and PARA path utilities
│   └── tasks.py           # Task parsing (Obsidian Tasks syntax), stats, activity reports
├── requirements.txt
├── setup.py
└── setup.sh               # Quick setup script
```

**Key classes:**

- `VaultConfig` (config.py) -- Pydantic model holding all configuration with validation
- `VaultIndex` (vault.py) -- In-memory note index for O(1) title lookups and fast search
- `VaultReader` (vault.py) -- High-level API for all vault operations (read, search, write, journal)
- `Note` (parser.py) -- Parsed note with metadata, tags, PARA location, and content
- `TaskParser` / `TaskStats` (tasks.py) -- Obsidian Tasks plugin syntax parsing and aggregation

## Security

- **Local execution only** -- No network access; the server runs entirely on your machine
- **PARA folder restriction** -- Write operations are limited to configured PARA folders
- **Path traversal protection** -- `..` sequences are rejected in subfolder paths
- **Atomic file writes** -- Notes are written to a temp file then renamed, preventing partial writes
- **File type validation** -- Attachments are checked against a configurable allowlist of extensions
- **File size limits** -- Attachments are capped at a configurable maximum (default: 100 MB)

## Troubleshooting

### Server not appearing in Claude

1. Verify the Claude Desktop config is valid JSON
2. Restart Claude for Desktop completely
3. Check logs at `~/.local/share/obsidian-vault-mcp/server.log`
4. Confirm the vault path exists and is accessible

### Search not finding notes

1. Notes must have `.md` extensions
2. Check that `exclude_folders` isn't filtering them out
3. Verify notes contain text content (not just frontmatter)

### Permission errors

1. Ensure the vault path is readable (and writable, for write tools)
2. iCloud-synced vaults must be downloaded locally before use
3. On macOS, grant Python disk access in System Preferences > Security & Privacy

### Write operations failing

1. Confirm the target PARA folder exists in your vault
2. Check that the note title doesn't contain invalid filename characters
3. For attachments, verify the file type is in `supported_attachment_types`

## License

MIT License -- Copyright (c) 2026 Mark Riechers. See [LICENSE](LICENSE) for details.
