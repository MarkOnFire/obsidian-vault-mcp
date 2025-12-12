"""Task parsing and statistics for Obsidian Tasks plugin syntax."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Task:
    """Represents a single task from an Obsidian note."""

    content: str
    completed: bool
    completion_date: Optional[str]
    due_date: Optional[str]
    priority: Optional[str]  # None, 'low', 'medium', 'high'
    recurrence: Optional[str]
    tags: List[str]
    source_file: str
    source_line: int
    blocked: bool = False

    def is_completed_in_range(self, days: int) -> bool:
        """Check if task was completed in the last N days."""
        if not self.completed or not self.completion_date:
            return False

        try:
            completion = datetime.fromisoformat(self.completion_date)
            cutoff = datetime.now() - timedelta(days=days)
            return completion >= cutoff
        except (ValueError, TypeError):
            return False

    def is_due_soon(self, days: int) -> bool:
        """Check if task is due in the next N days."""
        if not self.due_date or self.completed:
            return False

        try:
            due = datetime.fromisoformat(self.due_date)
            now = datetime.now()
            future = now + timedelta(days=days)
            return now <= due <= future
        except (ValueError, TypeError):
            return False

    def is_overdue(self) -> bool:
        """Check if task is past its due date."""
        if not self.due_date or self.completed:
            return False

        try:
            due = datetime.fromisoformat(self.due_date)
            return due < datetime.now()
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class TaskStats:
    """Aggregated task statistics for a folder or note."""

    total_tasks: int
    completed: int
    active: int
    blocked: int
    overdue: int
    due_soon: int
    completed_this_week: int
    completed_this_month: int
    high_priority: int

    # Task lists for detailed view
    completed_tasks: List[Dict]
    active_tasks: List[Dict]
    blocked_tasks: List[Dict]
    overdue_tasks: List[Dict]
    due_soon_tasks: List[Dict]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class TaskParser:
    """Parse Obsidian Tasks plugin syntax from markdown content."""

    # Task checkbox patterns
    TASK_PATTERN = re.compile(r'^(\s*)- \[([ xX])\] (.+)$', re.MULTILINE)

    # Obsidian Tasks plugin syntax patterns
    COMPLETION_DATE_PATTERN = re.compile(r'✅ (\d{4}-\d{2}-\d{2})')
    DUE_DATE_PATTERN = re.compile(r'📅 (\d{4}-\d{2}-\d{2})')
    PRIORITY_HIGH = re.compile(r'⏫')
    PRIORITY_MEDIUM = re.compile(r'🔼')
    PRIORITY_LOW = re.compile(r'🔽')
    RECURRENCE_PATTERN = re.compile(r'🔁 (.+?)(?:\s|$)')

    # Blocked task indicators
    BLOCKED_KEYWORDS = [
        'blocked', 'waiting', 'waiting on', 'waiting for',
        'needs approval', 'on hold', 'paused'
    ]

    @staticmethod
    def parse_tasks(content: str, source_file: str) -> List[Task]:
        """
        Parse all tasks from markdown content.

        Args:
            content: Markdown content to parse
            source_file: File path for source tracking

        Returns:
            List of Task objects
        """
        tasks = []

        for match in TaskParser.TASK_PATTERN.finditer(content):
            indent = match.group(1)
            checkbox = match.group(2)
            task_content = match.group(3)
            line_num = content[:match.start()].count('\n') + 1

            # Extract task attributes
            completed = checkbox.lower() == 'x'
            completion_date = TaskParser._extract_completion_date(task_content)
            due_date = TaskParser._extract_due_date(task_content)
            priority = TaskParser._extract_priority(task_content)
            recurrence = TaskParser._extract_recurrence(task_content)
            tags = TaskParser._extract_tags(task_content)
            blocked = TaskParser._is_blocked(task_content)

            # Only count as completed if it has completion date
            if completed and not completion_date:
                completed = False

            task = Task(
                content=task_content,
                completed=completed,
                completion_date=completion_date,
                due_date=due_date,
                priority=priority,
                recurrence=recurrence,
                tags=tags,
                source_file=source_file,
                source_line=line_num,
                blocked=blocked
            )

            tasks.append(task)

        return tasks

    @staticmethod
    def _extract_completion_date(content: str) -> Optional[str]:
        """Extract completion date (✅ YYYY-MM-DD)."""
        match = TaskParser.COMPLETION_DATE_PATTERN.search(content)
        return match.group(1) if match else None

    @staticmethod
    def _extract_due_date(content: str) -> Optional[str]:
        """Extract due date (📅 YYYY-MM-DD)."""
        match = TaskParser.DUE_DATE_PATTERN.search(content)
        return match.group(1) if match else None

    @staticmethod
    def _extract_priority(content: str) -> Optional[str]:
        """Extract priority (⏫ high, 🔼 medium, 🔽 low)."""
        if TaskParser.PRIORITY_HIGH.search(content):
            return 'high'
        elif TaskParser.PRIORITY_MEDIUM.search(content):
            return 'medium'
        elif TaskParser.PRIORITY_LOW.search(content):
            return 'low'
        return None

    @staticmethod
    def _extract_recurrence(content: str) -> Optional[str]:
        """Extract recurrence pattern (🔁 pattern)."""
        match = TaskParser.RECURRENCE_PATTERN.search(content)
        return match.group(1) if match else None

    @staticmethod
    def _extract_tags(content: str) -> List[str]:
        """Extract hashtags from task content."""
        return re.findall(r'#(\w+)', content)

    @staticmethod
    def _is_blocked(content: str) -> bool:
        """Check if task contains blocked keywords."""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in TaskParser.BLOCKED_KEYWORDS)

    @staticmethod
    def calculate_stats(tasks: List[Task], lookback_days: int = 7) -> TaskStats:
        """
        Calculate aggregate statistics from task list.

        Args:
            tasks: List of Task objects
            lookback_days: Days to look back for "recent" completions

        Returns:
            TaskStats object with aggregated data
        """
        total = len(tasks)
        completed = [t for t in tasks if t.completed and t.completion_date]
        active = [t for t in tasks if not t.completed and not t.blocked]
        blocked = [t for t in tasks if t.blocked and not t.completed]
        overdue = [t for t in tasks if t.is_overdue()]
        due_soon = [t for t in tasks if t.is_due_soon(lookback_days)]

        completed_this_week = [t for t in completed if t.is_completed_in_range(7)]
        completed_this_month = [t for t in completed if t.is_completed_in_range(30)]

        high_priority = [t for t in tasks if t.priority == 'high' and not t.completed]

        return TaskStats(
            total_tasks=total,
            completed=len(completed),
            active=len(active),
            blocked=len(blocked),
            overdue=len(overdue),
            due_soon=len(due_soon),
            completed_this_week=len(completed_this_week),
            completed_this_month=len(completed_this_month),
            high_priority=len(high_priority),
            completed_tasks=[t.to_dict() for t in completed_this_week],
            active_tasks=[t.to_dict() for t in active[:20]],  # Limit to 20 for brevity
            blocked_tasks=[t.to_dict() for t in blocked],
            overdue_tasks=[t.to_dict() for t in overdue],
            due_soon_tasks=[t.to_dict() for t in due_soon]
        )


def get_folder_task_stats(vault_reader, folder_path: str, lookback_days: int = 7) -> Dict:
    """
    Get task statistics for all notes in a folder.

    Args:
        vault_reader: VaultReader instance
        folder_path: Folder to scan
        lookback_days: Days to look back for recent completions

    Returns:
        Dictionary with task statistics
    """
    from .vault import VaultReader

    # List all notes in folder
    notes = vault_reader.list_notes(folder=folder_path, limit=1000)

    all_tasks = []

    # Parse tasks from each note
    for note_meta in notes:
        try:
            note_data = vault_reader.read_note(path=note_meta['path'])
            if note_data and note_data.get('content'):
                tasks = TaskParser.parse_tasks(note_data['content'], note_meta['path'])
                all_tasks.extend(tasks)
        except Exception as e:
            # Skip files that can't be read
            continue

    # Calculate stats
    stats = TaskParser.calculate_stats(all_tasks, lookback_days)

    return {
        'folder': folder_path,
        'notes_scanned': len(notes),
        'stats': stats.to_dict()
    }


def get_weekly_summary(vault_reader, start_date: Optional[str] = None, end_date: Optional[str] = None, para_location: Optional[str] = None) -> Dict:
    """
    Get a weekly summary of vault activity.

    Args:
        vault_reader: VaultReader instance
        start_date: Start date in ISO format (default: 7 days ago)
        end_date: End date in ISO format (default: today)
        para_location: Optional PARA location filter

    Returns:
        Dictionary with weekly summary data
    """
    # Parse dates
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            end_dt = datetime.now()
    else:
        end_dt = datetime.now()

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            start_dt = end_dt - timedelta(days=7)
    else:
        start_dt = end_dt - timedelta(days=7)

    # Get all notes (optionally filtered by PARA location)
    notes = vault_reader.list_notes(
        para_location=para_location,
        limit=5000
    )

    # Collect all tasks from all notes
    all_tasks = []
    notes_with_activity = []

    for note_meta in notes:
        try:
            note_data = vault_reader.read_note(path=note_meta['path'])
            if not note_data or not note_data.get('content'):
                continue

            tasks = TaskParser.parse_tasks(note_data['content'], note_meta['path'])
            all_tasks.extend(tasks)

            # Check for note activity in date range
            note_modified = note_meta.get('modified') or note_meta.get('created')
            if note_modified:
                try:
                    mod_dt = datetime.fromisoformat(note_modified) if isinstance(note_modified, str) else note_modified
                    if start_dt <= mod_dt <= end_dt:
                        notes_with_activity.append(note_meta)
                except (ValueError, TypeError):
                    pass

        except Exception:
            continue

    # Calculate completed tasks in date range
    completed_in_range = []
    for task in all_tasks:
        if task.completed and task.completion_date:
            try:
                comp_dt = datetime.fromisoformat(task.completion_date)
                if start_dt <= comp_dt <= end_dt:
                    completed_in_range.append(task)
            except (ValueError, TypeError):
                pass

    # Group completions by project/file
    completions_by_project = {}
    for task in completed_in_range:
        project = Path(task.source_file).stem
        if project not in completions_by_project:
            completions_by_project[project] = []
        completions_by_project[project].append(task.to_dict())

    # Group completions by day
    completions_by_day = {}
    for task in completed_in_range:
        if task.completion_date:
            day = task.completion_date[:10]  # YYYY-MM-DD
            if day not in completions_by_day:
                completions_by_day[day] = 0
            completions_by_day[day] += 1

    # Current active tasks
    active_tasks = [t for t in all_tasks if not t.completed and not t.blocked]
    blocked_tasks = [t for t in all_tasks if t.blocked and not t.completed]
    overdue_tasks = [t for t in all_tasks if t.is_overdue()]

    return {
        'period': {
            'start': start_dt.isoformat()[:10],
            'end': end_dt.isoformat()[:10]
        },
        'para_location': para_location,
        'summary': {
            'tasks_completed': len(completed_in_range),
            'notes_with_activity': len(notes_with_activity),
            'active_tasks': len(active_tasks),
            'blocked_tasks': len(blocked_tasks),
            'overdue_tasks': len(overdue_tasks)
        },
        'completions_by_day': completions_by_day,
        'completions_by_project': completions_by_project,
        'completed_tasks': [t.to_dict() for t in completed_in_range],
        'overdue_tasks': [t.to_dict() for t in overdue_tasks],
        'active_notes': [
            {'title': n['title'], 'path': n['path'], 'para_location': n.get('para_location')}
            for n in notes_with_activity[:20]
        ]
    }


def gather_topic(vault_reader, topic: str, include_backlinks: bool = True, max_depth: int = 1) -> Dict:
    """
    Gather all information on a topic from the vault.

    Args:
        vault_reader: VaultReader instance
        topic: Topic to gather (search term, tag, or note title)
        include_backlinks: Whether to include notes that link to matching notes
        max_depth: How deep to follow links (1 = direct links only)

    Returns:
        Dictionary with aggregated topic information
    """
    import re

    # Search for notes containing the topic
    search_results = vault_reader.search_notes(query=topic, limit=50)

    # Also search by tag if it looks like a tag
    tag_results = []
    if not topic.startswith('#'):
        tag_results = vault_reader.list_notes(tags=[topic], limit=50)

    # Combine results, deduplicate by path
    seen_paths = set()
    all_notes = []

    for note in search_results + tag_results:
        if note['path'] not in seen_paths:
            seen_paths.add(note['path'])
            all_notes.append(note)

    # Gather content and snippets from each note
    notes_with_content = []
    for note_meta in all_notes:
        try:
            note_data = vault_reader.read_note(path=note_meta['path'])
            if not note_data:
                continue

            content = note_data.get('content', '')

            # Extract snippets containing the topic
            snippets = []
            lines = content.split('\n')
            topic_lower = topic.lower()

            for i, line in enumerate(lines):
                if topic_lower in line.lower():
                    # Get surrounding context (2 lines before/after)
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    snippet = '\n'.join(lines[start:end])
                    snippets.append({
                        'line': i + 1,
                        'text': snippet.strip()
                    })

            # Get wikilinks from note
            links = []
            link_pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
            for match in re.findall(link_pattern, content):
                link_name = match.split('/')[-1] if '/' in match else match
                links.append(link_name)

            notes_with_content.append({
                'title': note_data['title'],
                'path': note_data['path'],
                'para_location': note_data.get('para_location'),
                'tags': note_data.get('tags', []),
                'snippets': snippets[:5],  # Limit snippets per note
                'links': links[:10],  # Limit links shown
                'excerpt': content[:500] + ('...' if len(content) > 500 else '')
            })

        except Exception:
            continue

    # Gather backlinks if requested
    backlink_notes = []
    if include_backlinks:
        for note in notes_with_content[:10]:  # Limit backlink search
            try:
                backlinks = vault_reader.get_backlinks(note['title'])
                for bl in backlinks:
                    if bl['path'] not in seen_paths:
                        seen_paths.add(bl['path'])
                        backlink_notes.append({
                            'title': bl['title'],
                            'path': bl['path'],
                            'para_location': bl.get('para_location'),
                            'links_to': note['title']
                        })
            except Exception:
                continue

    # Aggregate tags across all notes
    all_tags = {}
    for note in notes_with_content:
        for tag in note.get('tags', []):
            all_tags[tag] = all_tags.get(tag, 0) + 1

    # Group by PARA location
    by_para = {
        'projects': [],
        'areas': [],
        'resources': [],
        'archive': [],
        'other': []
    }
    for note in notes_with_content:
        para = note.get('para_location') or 'other'
        if para in by_para:
            by_para[para].append(note['title'])
        else:
            by_para['other'].append(note['title'])

    return {
        'topic': topic,
        'total_notes': len(notes_with_content),
        'total_backlinks': len(backlink_notes),
        'common_tags': sorted(all_tags.items(), key=lambda x: -x[1])[:10],
        'by_para_location': {k: v for k, v in by_para.items() if v},
        'notes': notes_with_content,
        'backlink_notes': backlink_notes[:20]
    }


def get_project_activity(vault_reader, folder_path: str) -> List[Dict]:
    """
    Get activity summary for each project note in a folder.

    Returns list of projects with their task stats and last activity date.

    Args:
        vault_reader: VaultReader instance
        folder_path: Project folder to scan

    Returns:
        List of dictionaries with project metadata and task stats
    """
    notes = vault_reader.list_notes(folder=folder_path, limit=1000)

    projects = []

    for note_meta in notes:
        try:
            note_data = vault_reader.read_note(path=note_meta['path'])
            if not note_data or not note_data.get('content'):
                continue

            tasks = TaskParser.parse_tasks(note_data['content'], note_meta['path'])

            if not tasks:
                # Skip notes with no tasks
                continue

            stats = TaskParser.calculate_stats(tasks, lookback_days=7)

            # Determine last activity date
            last_activity = note_meta.get('modified', note_meta.get('created'))

            # Check for recent completions
            recent_completions = [t for t in tasks if t.is_completed_in_range(7)]
            if recent_completions:
                # Most recent completion date
                completion_dates = [t.completion_date for t in recent_completions if t.completion_date]
                if completion_dates:
                    last_activity = max(completion_dates)

            projects.append({
                'title': note_meta['title'],
                'path': note_meta['path'],
                'last_activity': last_activity,
                'task_stats': {
                    'total': stats.total_tasks,
                    'completed_this_week': stats.completed_this_week,
                    'active': stats.active,
                    'blocked': stats.blocked,
                    'overdue': stats.overdue
                },
                'is_stale': stats.completed_this_week == 0 and stats.active > 0
            })

        except Exception:
            continue

    # Sort by last activity (most recent first)
    # Handle None values by treating them as very old dates
    projects.sort(key=lambda x: x['last_activity'] or '', reverse=True)

    return projects
