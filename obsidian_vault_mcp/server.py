"""MCP server implementation for Obsidian vault access."""

import logging
import urllib.parse
from pathlib import Path
from typing import Any, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
from pydantic import BaseModel, Field

from .config import VaultConfig, load_config
from .vault import VaultReader
from .tasks import get_folder_task_stats, get_project_activity


# Configure logging
logger = logging.getLogger("obsidian_vault_mcp")


# Tool parameter models
class ReadNoteParams(BaseModel):
    """Parameters for obsidian_read_note tool."""

    path: Optional[str] = Field(
        None,
        description="Absolute or vault-relative path to the note"
    )
    title: Optional[str] = Field(
        None,
        description="Note title (case-insensitive)"
    )
    resolve_links: bool = Field(
        False,
        description="Include linked note titles in response"
    )


class SearchNotesParams(BaseModel):
    """Parameters for obsidian_search_notes tool."""

    query: str = Field(
        description="Search term or phrase"
    )
    para_location: Optional[str] = Field(
        None,
        description="Filter by PARA location (inbox, projects, areas, resources, archive)"
    )
    folder: Optional[str] = Field(
        None,
        description="Limit to specific folder path"
    )
    limit: int = Field(
        20,
        description="Maximum number of results"
    )


class ListNotesParams(BaseModel):
    """Parameters for obsidian_list_notes tool."""

    para_location: Optional[str] = Field(
        None,
        description="Filter by PARA location"
    )
    folder: Optional[str] = Field(
        None,
        description="Specific folder path"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Filter by tags (AND logic)"
    )
    created_after: Optional[str] = Field(
        None,
        description="ISO date string (e.g., '2024-01-01')"
    )
    created_before: Optional[str] = Field(
        None,
        description="ISO date string"
    )
    limit: int = Field(
        50,
        description="Maximum number of results"
    )


class GetBacklinksParams(BaseModel):
    """Parameters for obsidian_get_backlinks tool."""

    note_title: str = Field(
        description="Title of the note to find backlinks for"
    )


class ResolveLinkParams(BaseModel):
    """Parameters for obsidian_resolve_link tool."""

    link: str = Field(
        description="Wikilink text (e.g., '[[Project Dashboard]]' or 'Project Dashboard')"
    )


class GetTaskStatsParams(BaseModel):
    """Parameters for obsidian_get_task_stats tool."""

    folder_path: str = Field(
        description="Folder to scan for tasks (e.g., '1 - Projects/PBSWI')"
    )
    lookback_days: int = Field(
        default=7,
        description="Days to look back for recent completions (default: 7)"
    )


class GetProjectActivityParams(BaseModel):
    """Parameters for obsidian_get_project_activity tool."""

    folder_path: str = Field(
        description="Project folder to scan (e.g., '1 - Projects/PBSWI')"
    )


def create_server(config: VaultConfig) -> Server:
    """
    Create and configure MCP server.

    Args:
        config: VaultConfig instance

    Returns:
        Configured MCP Server
    """
    server = Server("obsidian-vault")
    vault = VaultReader(config)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="obsidian_read_note",
                description=(
                    "Read the full content of an Obsidian note by path or title. "
                    "Returns note content, metadata, tags, and optionally linked notes."
                ),
                inputSchema=ReadNoteParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_search_notes",
                description=(
                    "Search note contents with full-text search. "
                    "Can filter by PARA location, folder, and limit results. "
                    "Returns matching notes with metadata but not full content."
                ),
                inputSchema=SearchNotesParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_list_notes",
                description=(
                    "List notes matching specific criteria. "
                    "Filter by PARA location, folder, tags, creation dates. "
                    "Returns note metadata without full content."
                ),
                inputSchema=ListNotesParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_get_backlinks",
                description=(
                    "Find all notes that link to a specific note. "
                    "Returns list of notes containing wikilinks to the target note."
                ),
                inputSchema=GetBacklinksParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_resolve_link",
                description=(
                    "Resolve a wikilink to its target note. "
                    "Returns note metadata for the linked note."
                ),
                inputSchema=ResolveLinkParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_get_task_stats",
                description=(
                    "Get aggregated task statistics for all notes in a folder. "
                    "Returns counts for total, completed, active, blocked, overdue, and due soon tasks. "
                    "Includes detailed lists of tasks in each category with completion dates and content. "
                    "Perfect for generating meeting prep reports with structured task data."
                ),
                inputSchema=GetTaskStatsParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_get_project_activity",
                description=(
                    "Get activity summary for each project note in a folder. "
                    "Returns per-project breakdown with task stats and last activity date. "
                    "Identifies stale projects (no activity in last 7 days). "
                    "Ideal for project portfolio reviews and identifying inactive work."
                ),
                inputSchema=GetProjectActivityParams.model_json_schema(),
            ),
        ]

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available note resources."""
        # Use internal index directly to bypass config limits for resources
        # and get Note objects directly. Limit to 1000 recent notes.
        notes = vault.index.list_notes(limit=1000)
        resources = []
        
        for note in notes:
            try:
                # Create relative path URI
                # note.path is already a Path object
                rel_path = note.path.relative_to(config.vault_path)
                uri = f"note://internal/{urllib.parse.quote(str(rel_path))}"
                
                resources.append(Resource(
                    uri=uri,
                    name=note.title,
                    mimeType="text/markdown",
                    description=f"Obsidian note: {note.title}"
                ))
            except Exception as e:
                logger.warning(f"Failed to create resource for {getattr(note, 'title', 'unknown')}: {e}")
                continue
                
        return resources

    @server.read_resource()
    async def read_resource(uri: Any) -> str:
        """Read a note resource."""
        uri_str = str(uri)
        prefix = "note://internal/"
        
        if not uri_str.startswith(prefix):
            raise ValueError(f"Unknown resource URI: {uri_str}")
            
        # Extract and decode path
        path = urllib.parse.unquote(uri_str[len(prefix):])
        
        result = vault.read_note(path=path)
        if not result:
             raise ValueError(f"Note not found: {path}")
             
        return result['content']

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        """Handle tool calls."""
        try:
            if name == "obsidian_read_note":
                params = ReadNoteParams(**arguments)
                result = vault.read_note(
                    path=params.path,
                    title=params.title,
                    resolve_links=params.resolve_links,
                )

                if not result:
                    return [
                        TextContent(
                            type="text",
                            text=f"Note not found (path={params.path}, title={params.title})"
                        )
                    ]

                # Format response
                response = f"# {result['title']}\n\n"

                if result.get('para_location'):
                    response += f"**PARA**: {result['para_location']}\n"

                if result.get('tags'):
                    response += f"**Tags**: {', '.join(result['tags'])}\n"

                if result.get('created'):
                    response += f"**Created**: {result['created']}\n"

                if result.get('links'):
                    response += f"**Links**: {', '.join(result['links'])}\n"

                response += f"\n---\n\n{result['content']}"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_search_notes":
                params = SearchNotesParams(**arguments)
                results = vault.search_notes(
                    query=params.query,
                    para_location=params.para_location,
                    folder=params.folder,
                    limit=params.limit,
                )

                if not results:
                    return [
                        TextContent(
                            type="text",
                            text=f"No notes found matching '{params.query}'"
                        )
                    ]

                # Format response
                response = f"Found {len(results)} note(s) matching '{params.query}':\n\n"

                for note in results:
                    response += f"- **{note['title']}**"

                    if note.get('para_location'):
                        response += f" ({note['para_location']})"

                    if note.get('tags'):
                        response += f" | Tags: {', '.join(note['tags'])}"

                    response += f"\n  Path: {note['path']}\n"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_list_notes":
                params = ListNotesParams(**arguments)
                results = vault.list_notes(
                    para_location=params.para_location,
                    folder=params.folder,
                    tags=params.tags,
                    created_after=params.created_after,
                    created_before=params.created_before,
                    limit=params.limit,
                )

                if not results:
                    return [
                        TextContent(
                            type="text",
                            text="No notes found matching criteria"
                        )
                    ]

                # Format response
                filters = []
                if params.para_location:
                    filters.append(f"PARA={params.para_location}")
                if params.folder:
                    filters.append(f"folder={params.folder}")
                if params.tags:
                    filters.append(f"tags={', '.join(params.tags)}")

                filter_str = f" ({', '.join(filters)})" if filters else ""
                response = f"Found {len(results)} note(s){filter_str}:\n\n"

                for note in results:
                    response += f"- **{note['title']}**"

                    if note.get('created'):
                        response += f" (created {note['created'][:10]})"

                    if note.get('tags'):
                        response += f"\n  Tags: {', '.join(note['tags'])}"

                    response += f"\n  Path: {note['path']}\n"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_get_backlinks":
                params = GetBacklinksParams(**arguments)
                results = vault.get_backlinks(params.note_title)

                if not results:
                    return [
                        TextContent(
                            type="text",
                            text=f"No backlinks found for '{params.note_title}'"
                        )
                    ]

                # Format response
                response = f"Found {len(results)} note(s) linking to '{params.note_title}':\n\n"

                for note in results:
                    response += f"- **{note['title']}**"

                    if note.get('para_location'):
                        response += f" ({note['para_location']})"

                    response += f"\n  Path: {note['path']}\n"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_resolve_link":
                params = ResolveLinkParams(**arguments)
                result = vault.resolve_link(params.link)

                if not result:
                    return [
                        TextContent(
                            type="text",
                            text=f"Could not resolve link: {params.link}"
                        )
                    ]

                # Format response
                response = f"Link '{params.link}' resolves to:\n\n"
                response += f"**{result['title']}**\n"

                if result.get('para_location'):
                    response += f"PARA: {result['para_location']}\n"

                if result.get('tags'):
                    response += f"Tags: {', '.join(result['tags'])}\n"

                response += f"Path: {result['path']}"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_get_task_stats":
                params = GetTaskStatsParams(**arguments)
                import json

                result = get_folder_task_stats(
                    vault_reader=vault,
                    folder_path=params.folder_path,
                    lookback_days=params.lookback_days
                )

                # Format response with structured data
                stats = result['stats']
                response = f"# Task Statistics for {result['folder']}\n\n"
                response += f"**Notes Scanned**: {result['notes_scanned']}\n\n"

                response += "## Summary\n\n"
                response += f"- **Total Tasks**: {stats['total_tasks']}\n"
                response += f"- **Completed This Week**: {stats['completed_this_week']}\n"
                response += f"- **Active**: {stats['active']}\n"
                response += f"- **Blocked**: {stats['blocked']}\n"
                response += f"- **Overdue**: {stats['overdue']}\n"
                response += f"- **Due Soon**: {stats['due_soon']}\n"
                response += f"- **High Priority**: {stats['high_priority']}\n\n"

                # Completed tasks
                if stats['completed_tasks']:
                    response += "## Recently Completed Tasks\n\n"
                    for task in stats['completed_tasks']:
                        response += f"- ✅ {task['content']} (completed {task['completion_date']})\n"
                        response += f"  - Source: {task['source_file']}:{task['source_line']}\n"
                    response += "\n"

                # Active tasks (limit to first 20)
                if stats['active_tasks']:
                    response += f"## Active Tasks ({len(stats['active_tasks'])} shown)\n\n"
                    for task in stats['active_tasks'][:20]:
                        response += f"- [ ] {task['content']}\n"
                        if task.get('due_date'):
                            response += f"  - Due: {task['due_date']}\n"
                        if task.get('priority'):
                            response += f"  - Priority: {task['priority']}\n"
                        response += f"  - Source: {task['source_file']}:{task['source_line']}\n"
                    response += "\n"

                # Blocked tasks
                if stats['blocked_tasks']:
                    response += "## Blocked Tasks\n\n"
                    for task in stats['blocked_tasks']:
                        response += f"- 🚧 {task['content']}\n"
                        response += f"  - Source: {task['source_file']}:{task['source_line']}\n"
                    response += "\n"

                # Overdue tasks
                if stats['overdue_tasks']:
                    response += "## Overdue Tasks\n\n"
                    for task in stats['overdue_tasks']:
                        response += f"- ⚠️ {task['content']} (due {task['due_date']})\n"
                        response += f"  - Source: {task['source_file']}:{task['source_line']}\n"
                    response += "\n"

                # Due soon tasks
                if stats['due_soon_tasks']:
                    response += "## Due Soon\n\n"
                    for task in stats['due_soon_tasks']:
                        response += f"- 📅 {task['content']} (due {task['due_date']})\n"
                        response += f"  - Source: {task['source_file']}:{task['source_line']}\n"
                    response += "\n"

                # Add raw JSON for programmatic access
                response += "---\n\n"
                response += "**Raw JSON Data** (for programmatic access):\n\n"
                response += f"```json\n{json.dumps(result, indent=2)}\n```"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_get_project_activity":
                params = GetProjectActivityParams(**arguments)
                import json

                projects = get_project_activity(
                    vault_reader=vault,
                    folder_path=params.folder_path
                )

                if not projects:
                    return [
                        TextContent(
                            type="text",
                            text=f"No projects found in {params.folder_path}"
                        )
                    ]

                # Format response
                response = f"# Project Activity for {params.folder_path}\n\n"
                response += f"**Total Projects**: {len(projects)}\n\n"

                # Active projects
                active = [p for p in projects if not p['is_stale']]
                stale = [p for p in projects if p['is_stale']]

                if active:
                    response += f"## Active Projects ({len(active)})\n\n"
                    for project in active:
                        response += f"### {project['title']}\n\n"
                        response += f"- **Last Activity**: {project['last_activity']}\n"
                        response += f"- **Total Tasks**: {project['task_stats']['total']}\n"
                        response += f"- **Completed This Week**: {project['task_stats']['completed_this_week']}\n"
                        response += f"- **Active**: {project['task_stats']['active']}\n"
                        response += f"- **Blocked**: {project['task_stats']['blocked']}\n"
                        response += f"- **Overdue**: {project['task_stats']['overdue']}\n"
                        response += f"- **Path**: {project['path']}\n\n"

                if stale:
                    response += f"## Stale Projects ({len(stale)})\n\n"
                    for project in stale:
                        response += f"### {project['title']}\n\n"
                        response += f"- **Last Activity**: {project['last_activity']}\n"
                        response += f"- **Active Tasks**: {project['task_stats']['active']}\n"
                        response += f"- **Status**: No activity in last 7 days\n"
                        response += f"- **Path**: {project['path']}\n\n"

                # Add raw JSON
                response += "---\n\n"
                response += "**Raw JSON Data** (for programmatic access):\n\n"
                response += f"```json\n{json.dumps(projects, indent=2)}\n```"

                return [TextContent(type="text", text=response)]

            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )
                ]

        except Exception as e:
            logger.error(f"Error in {name}: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]

    return server


def run_server():
    """Run the MCP server."""
    # Load configuration
    config = load_config()

    # Configure logging
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                "/Users/mriechers/Developer/obsidian-config/logs/obsidian-vault-mcp.log"
            ),
            logging.StreamHandler(),
        ],
    )

    logger.info(f"Starting Obsidian Vault MCP server for: {config.vault_path}")

    # Create and run server
    server = create_server(config)

    # Import and run with asyncio
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())
