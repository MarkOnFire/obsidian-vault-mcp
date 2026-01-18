# CLAUDE.md

> **See [AGENTS.md](./AGENTS.md)** for complete project instructions.

## Claude-Specific Notes

### Available MCP Servers

When working in this project, you have access to these MCP servers:

- **obsidian-vault**: This server itself - provides read/write access to Obsidian vaults
- **cli-agent**: Multi-LLM queries and code review
- **the-library**: External documentation access

### Claude Code Features

- Use TodoWrite for tracking multi-step development tasks
- PARA methodology awareness helps filter by project/area context
- Write operations available for notes and attachments

### Write Operations

The server supports these write operations:

| Tool | Purpose |
|------|---------|
| `obsidian_create_daily_note` | Create/append to daily notes in INBOX |
| `obsidian_create_inbox_note` | Create new notes in INBOX for processing |
| `obsidian_create_note` | Create notes directly in projects/areas/resources/archive |
| `obsidian_add_attachment` | Add PDFs/images to Archive with auto-linking |
| `obsidian_update_daily_note` | Update sections with modification preservation |

#### Direct Note Creation (Automation Workflows)

Use `obsidian_create_note` when syncing from external sources or automation workflows where notes should go directly to their final location:

```python
# Create a project note
obsidian_create_note(
    title="API Redesign",
    para_location="projects",
    subfolder="PBSWI",
    content="# API Redesign\n\nProject notes...",
    tags=["project", "api"]
)
# Result: 1 - Projects/PBSWI/API Redesign.md

# Create a brainstorm note
obsidian_create_note(
    title="Voice UI Ideas",
    para_location="projects",
    subfolder="brainstorming",
    content="# Voice UI Ideas\n\n- Idea 1..."
)
# Result: 1 - Projects/brainstorming/Voice UI Ideas.md

# Create an area note
obsidian_create_note(
    title="Team Standup Notes",
    para_location="areas",
    subfolder="Work/Meetings"
)
# Result: 2 - AREAS/Work/Meetings/Team Standup Notes.md
```

**When to use which tool:**
- `obsidian_create_inbox_note` - Quick captures, ideas, content needing review
- `obsidian_create_note` - Automation, sync workflows, notes with known destination

### Daily Journal Tools

| Tool | Purpose |
|------|---------|
| `obsidian_get_unarchived_daily_notes` | Find notes not yet archived to month folders |
| `obsidian_extract_note_tasks` | Parse tasks with section context and completion dates |
| `obsidian_update_daily_note` | Smart section updates preserving user edits |

#### Daily Journal Workflow

```python
# Find unarchived daily notes
unarchived = obsidian_get_unarchived_daily_notes()

# Extract tasks from a note
tasks = obsidian_extract_note_tasks(
    note_path="0 - INBOX/DAILY JOURNAL/2026-01-15.md",
    sections=["Action Items", "Quick Captures"]
)

# Update sections (preserves user modifications)
obsidian_update_daily_note(
    date="2026-01-15",
    sections={
        "Calendar": "## Today's Events\n- Meeting at 10am",
        "Tasks": "## Action Items\n- [ ] Review PR"
    }
)
```

#### Attachment Workflow

**Platform-Specific Notes:**

| Platform | File Access | Recommended Workflow |
|----------|-------------|---------------------|
| Claude Code (CLI) | Full local filesystem | Use `source_path` directly |
| Claude Desktop | Files uploaded to Anthropic servers | Save file locally first, then use `source_path` |
| Claude Mobile | No MCP support | N/A |

**Why Claude Desktop requires extra steps:** Files uploaded to Claude Desktop exist on Anthropic's servers at paths like `/mnt/user-data/uploads/...`, which the local MCP server cannot access. The MCP server only has access to your local filesystem.

**Claude Desktop Workflow:**
1. Save the file you want to attach to a local folder (e.g., `~/Downloads/`)
2. Tell Claude the local path: "Attach `~/Downloads/report.pdf` to my Project Notes"
3. Claude calls `obsidian_add_attachment(source_path="~/Downloads/report.pdf", link_to_note="Project Notes")`

**Claude Code Workflow (recommended):**
```python
# Copy a file and link it to a note
obsidian_add_attachment(
    source_path="~/Downloads/report.pdf",
    link_to_note="Project Notes"
)

# Add an image with inline embedding
obsidian_add_attachment(
    source_path="~/Desktop/screenshot.png",
    link_to_note="Bug Report",
    embed=True  # renders as ![[screenshot.png]]
)

# Save base64 content (e.g., from API responses)
obsidian_add_attachment(
    base64_content="<base64 string>",
    filename="chart.png",
    link_to_note="Dashboard"
)
```

**Default Attachment Destination:** Files are saved to `4 - ARCHIVE` in your vault (configurable via `attachment_folder` in config).

### Development Tips

- Set `OBSIDIAN_VAULT_PATH` to your test vault
- Logs are written to `~/.local/share/obsidian-vault-mcp/server.log`
- Use `OBSIDIAN_VAULT_LOG_LEVEL=DEBUG` for verbose logging
- iCloud-synced vaults must be downloaded locally

### Configuration Options

```json
{
  "daily_journal_folder": "0 - INBOX/DAILY JOURNAL",
  "daily_journal_archive_pattern": "JANUARY|FEBRUARY|...|DECEMBER",
  "attachment_folder": "4 - ARCHIVE",
  "supported_attachment_types": ["pdf", "png", "jpg", "jpeg", "gif", "webp", "svg", "mp3", "mp4", "wav", "mov"],
  "max_attachment_size_mb": 100
}
```

### Security Considerations

- Write operations limited to configured PARA folders (no arbitrary paths)
- `create_note` validates para_location and blocks `..` path traversal
- Subfolders are created automatically if they don't exist
- No network access required
- Local execution only
- Safe file operations with atomic writes
- File type validation for attachments
