# CLAUDE.md

> **See [AGENTS.md](./AGENTS.md)** for complete project instructions.

## Claude-Specific Notes

### Available MCP Servers

When working in this project, you have access to these MCP servers:

- **obsidian-vault**: This server itself - provides read access to Obsidian vaults
- **cli-agent**: Multi-LLM queries and code review
- **the-library**: External documentation access

### Claude Code Features

- Use TodoWrite for tracking multi-step development tasks
- This server is read-only - it cannot modify Obsidian notes
- PARA methodology awareness helps filter by project/area context

### Development Tips

- Set `OBSIDIAN_VAULT_PATH` to your test vault
- Logs are written to `~/.local/share/obsidian-vault-mcp/server.log`
- Use `OBSIDIAN_VAULT_LOG_LEVEL=DEBUG` for verbose logging
- iCloud-synced vaults must be downloaded locally

### Security Considerations

- Read-only access only
- No network access required
- Local execution only
- Safe file operations with proper encoding
