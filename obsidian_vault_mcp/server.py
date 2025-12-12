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
from .tasks import get_folder_task_stats, get_project_activity, get_weekly_summary, gather_topic


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
    include_snippets: bool = Field(
        False,
        description="Include matching text snippets with surrounding context"
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
    modified_after: Optional[str] = Field(
        None,
        description="Filter notes modified after this ISO date (e.g., '2024-01-01')"
    )
    modified_before: Optional[str] = Field(
        None,
        description="Filter notes modified before this ISO date"
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


class GetWeeklySummaryParams(BaseModel):
    """Parameters for obsidian_get_weekly_summary tool."""

    start_date: Optional[str] = Field(
        None,
        description="Start date in ISO format (YYYY-MM-DD). Default: 7 days ago"
    )
    end_date: Optional[str] = Field(
        None,
        description="End date in ISO format (YYYY-MM-DD). Default: today"
    )
    para_location: Optional[str] = Field(
        None,
        description="Filter by PARA location (projects, areas, resources, archive)"
    )


class GatherTopicParams(BaseModel):
    """Parameters for obsidian_gather_topic tool."""

    topic: str = Field(
        description="Topic to gather information about (search term, tag, or note title)"
    )
    include_backlinks: bool = Field(
        True,
        description="Whether to include notes that link to matching notes"
    )


class CreateDailyNoteParams(BaseModel):
    """Parameters for obsidian_create_daily_note tool."""

    content: str = Field(
        default="",
        description="Note content (markdown)"
    )
    date: Optional[str] = Field(
        None,
        description="Date for the note in YYYY-MM-DD format. Defaults to today."
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Tags to add to the note (without # prefix)"
    )
    append_if_exists: bool = Field(
        False,
        description="If True, append content to existing daily note instead of failing"
    )


class CreateInboxNoteParams(BaseModel):
    """Parameters for obsidian_create_inbox_note tool."""

    title: str = Field(
        description="Note title (will be used as filename)"
    )
    content: str = Field(
        default="",
        description="Note content (markdown)"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Tags to add to the note (without # prefix)"
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
                    "Set include_snippets=true to get matching text with context. "
                    "Returns matching notes with metadata and optional snippets."
                ),
                inputSchema=SearchNotesParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_list_notes",
                description=(
                    "List notes matching specific criteria. "
                    "Filter by PARA location, folder, tags, creation dates, or modification dates. "
                    "Use modified_after to find recently updated notes. "
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
            Tool(
                name="obsidian_get_weekly_summary",
                description=(
                    "Get a summary of vault activity for a time period. "
                    "Returns tasks completed, notes with activity, completions by day/project. "
                    "Can filter by PARA location. Default period is last 7 days. "
                    "Perfect for answering 'what did I do last week?' or 'what's my progress?'"
                ),
                inputSchema=GetWeeklySummaryParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_gather_topic",
                description=(
                    "Gather all information on a topic from the vault. "
                    "Searches by content and tags, returns matching notes with excerpts and snippets. "
                    "Includes backlinks and groups results by PARA location. "
                    "Ideal for 'get me everything on X' queries."
                ),
                inputSchema=GatherTopicParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_create_daily_note",
                description=(
                    "Create or append to a daily note. "
                    "Daily notes are stored in the configured daily notes folder (default: 0 - INBOX/Daily). "
                    "If the note exists, use append_if_exists=True to add content with a timestamp. "
                    "Automatically adds PARA location 'inbox' and created date to frontmatter."
                ),
                inputSchema=CreateDailyNoteParams.model_json_schema(),
            ),
            Tool(
                name="obsidian_create_inbox_note",
                description=(
                    "Create a new note in the INBOX folder. "
                    "Use this to capture ideas, tasks, or content that needs to be processed later. "
                    "The title becomes the filename. "
                    "Automatically adds PARA location 'inbox' and created date to frontmatter."
                ),
                inputSchema=CreateInboxNoteParams.model_json_schema(),
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
                    include_snippets=params.include_snippets,
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
                    response += f"### {note['title']}"

                    if note.get('para_location'):
                        response += f" ({note['para_location']})"

                    response += "\n"

                    if note.get('tags'):
                        response += f"**Tags**: {', '.join(note['tags'])}\n"

                    response += f"**Path**: {note['path']}\n"

                    # Include snippets if available
                    if note.get('snippets'):
                        response += "\n**Matching snippets**:\n"
                        for snippet in note['snippets']:
                            response += f"\n> Line {snippet['line']}:\n"
                            snippet_text = snippet['text'][:300]
                            if len(snippet['text']) > 300:
                                snippet_text += "..."
                            response += f"> {snippet_text}\n"

                    response += "\n---\n\n"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_list_notes":
                params = ListNotesParams(**arguments)
                results = vault.list_notes(
                    para_location=params.para_location,
                    folder=params.folder,
                    tags=params.tags,
                    created_after=params.created_after,
                    created_before=params.created_before,
                    modified_after=params.modified_after,
                    modified_before=params.modified_before,
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

            elif name == "obsidian_get_weekly_summary":
                params = GetWeeklySummaryParams(**arguments)
                import json

                result = get_weekly_summary(
                    vault_reader=vault,
                    start_date=params.start_date,
                    end_date=params.end_date,
                    para_location=params.para_location
                )

                # Format response
                response = f"# Weekly Summary\n\n"
                response += f"**Period**: {result['period']['start']} to {result['period']['end']}\n"
                if result['para_location']:
                    response += f"**PARA Location**: {result['para_location']}\n"
                response += "\n"

                summary = result['summary']
                response += "## Summary\n\n"
                response += f"- **Tasks Completed**: {summary['tasks_completed']}\n"
                response += f"- **Notes with Activity**: {summary['notes_with_activity']}\n"
                response += f"- **Active Tasks**: {summary['active_tasks']}\n"
                response += f"- **Blocked Tasks**: {summary['blocked_tasks']}\n"
                response += f"- **Overdue Tasks**: {summary['overdue_tasks']}\n\n"

                # Completions by day
                if result['completions_by_day']:
                    response += "## Completions by Day\n\n"
                    for day, count in sorted(result['completions_by_day'].items()):
                        response += f"- {day}: {count} task(s)\n"
                    response += "\n"

                # Completions by project
                if result['completions_by_project']:
                    response += "## Completions by Project\n\n"
                    for project, tasks in result['completions_by_project'].items():
                        response += f"### {project} ({len(tasks)} completed)\n\n"
                        for task in tasks[:5]:
                            response += f"- {task['content'][:80]}{'...' if len(task['content']) > 80 else ''}\n"
                        if len(tasks) > 5:
                            response += f"- *...and {len(tasks) - 5} more*\n"
                        response += "\n"

                # Overdue tasks
                if result['overdue_tasks']:
                    response += "## Overdue Tasks\n\n"
                    for task in result['overdue_tasks'][:10]:
                        response += f"- {task['content'][:60]} (due {task['due_date']})\n"
                    response += "\n"

                # Add raw JSON
                response += "---\n\n"
                response += "**Raw JSON Data** (for programmatic access):\n\n"
                response += f"```json\n{json.dumps(result, indent=2)}\n```"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_gather_topic":
                params = GatherTopicParams(**arguments)
                import json

                result = gather_topic(
                    vault_reader=vault,
                    topic=params.topic,
                    include_backlinks=params.include_backlinks
                )

                # Format response
                response = f"# Topic: {result['topic']}\n\n"
                response += f"**Total Notes Found**: {result['total_notes']}\n"
                response += f"**Backlink Notes**: {result['total_backlinks']}\n\n"

                # Common tags
                if result['common_tags']:
                    response += "## Common Tags\n\n"
                    for tag, count in result['common_tags']:
                        response += f"- #{tag} ({count} notes)\n"
                    response += "\n"

                # By PARA location
                if result['by_para_location']:
                    response += "## By PARA Location\n\n"
                    for para, titles in result['by_para_location'].items():
                        response += f"### {para.capitalize()} ({len(titles)})\n"
                        for title in titles[:5]:
                            response += f"- {title}\n"
                        if len(titles) > 5:
                            response += f"- *...and {len(titles) - 5} more*\n"
                        response += "\n"

                # Notes with snippets
                response += "## Relevant Notes\n\n"
                for note in result['notes'][:15]:
                    response += f"### {note['title']}\n\n"
                    response += f"**Path**: {note['path']}\n"
                    if note.get('para_location'):
                        response += f"**PARA**: {note['para_location']}\n"
                    if note.get('tags'):
                        response += f"**Tags**: {', '.join(note['tags'])}\n"

                    # Show snippets
                    if note.get('snippets'):
                        response += "\n**Matching snippets**:\n"
                        for snippet in note['snippets'][:3]:
                            response += f"\n> Line {snippet['line']}:\n"
                            response += f"> {snippet['text'][:200]}{'...' if len(snippet['text']) > 200 else ''}\n"
                    else:
                        # Show excerpt if no snippets
                        response += f"\n**Excerpt**: {note['excerpt'][:300]}...\n"

                    response += "\n---\n\n"

                # Backlinks section
                if result['backlink_notes']:
                    response += "## Notes Linking to These Topics\n\n"
                    for bl in result['backlink_notes'][:10]:
                        response += f"- **{bl['title']}** links to *{bl['links_to']}*\n"
                        response += f"  Path: {bl['path']}\n"
                    response += "\n"

                return [TextContent(type="text", text=response)]

            elif name == "obsidian_create_daily_note":
                params = CreateDailyNoteParams(**arguments)
                from datetime import datetime as dt

                # Parse date if provided
                date = None
                if params.date:
                    try:
                        date = dt.strptime(params.date, "%Y-%m-%d")
                    except ValueError:
                        return [
                            TextContent(
                                type="text",
                                text=f"Invalid date format: {params.date}. Use YYYY-MM-DD."
                            )
                        ]

                try:
                    result = vault.create_daily_note(
                        content=params.content,
                        date=date,
                        tags=params.tags,
                        append_if_exists=params.append_if_exists,
                    )

                    # Format response
                    action = "Appended to" if result['action'] == 'appended' else "Created"
                    response = f"# {action} Daily Note\n\n"
                    response += f"**Title**: {result['title']}\n"
                    response += f"**Path**: {result['path']}\n"
                    response += f"**PARA**: {result['para_location']}\n"

                    if result.get('date'):
                        response += f"**Date**: {result['date']}\n"

                    return [TextContent(type="text", text=response)]

                except FileExistsError as e:
                    return [
                        TextContent(
                            type="text",
                            text=f"Daily note already exists. Set append_if_exists=True to append.\n\nDetails: {str(e)}"
                        )
                    ]

            elif name == "obsidian_create_inbox_note":
                params = CreateInboxNoteParams(**arguments)

                try:
                    result = vault.create_inbox_note(
                        title=params.title,
                        content=params.content,
                        tags=params.tags,
                    )

                    # Format response
                    response = f"# Created Inbox Note\n\n"
                    response += f"**Title**: {result['title']}\n"
                    response += f"**Path**: {result['path']}\n"
                    response += f"**PARA**: {result['para_location']}\n"

                    return [TextContent(type="text", text=response)]

                except FileExistsError as e:
                    return [
                        TextContent(
                            type="text",
                            text=f"Note already exists: {str(e)}"
                        )
                    ]
                except ValueError as e:
                    return [
                        TextContent(
                            type="text",
                            text=f"Invalid title: {str(e)}"
                        )
                    ]

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


def get_log_path() -> Path:
    """
    Determine the log file path.

    Priority:
    1. OBSIDIAN_VAULT_MCP_LOG env var (explicit path)
    2. XDG_DATA_HOME/obsidian-vault-mcp/server.log (Linux/macOS standard)
    3. ~/.local/share/obsidian-vault-mcp/server.log (fallback)
    """
    import os

    # Check for explicit log path
    if log_path := os.environ.get("OBSIDIAN_VAULT_MCP_LOG"):
        return Path(log_path)

    # Use XDG_DATA_HOME or default
    data_home = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    log_dir = Path(data_home) / "obsidian-vault-mcp"
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir / "server.log"


def run_server():
    """Run the MCP server."""
    # Load configuration
    config = load_config()

    # Configure logging
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    log_path = get_log_path()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path),
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
