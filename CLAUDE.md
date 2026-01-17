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
