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
| `obsidian_add_attachment` | Add PDFs/images to Archive with auto-linking |
| `obsidian_update_daily_note` | Update sections with modification preservation |

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

# Save base64 content (e.g., from API)
obsidian_add_attachment(
    base64_content="<base64 string>",
    filename="chart.png",
    link_to_note="Dashboard"
)
```

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

- Write operations limited to INBOX and Archive folders
- No network access required
- Local execution only
- Safe file operations with atomic writes
- File type validation for attachments
