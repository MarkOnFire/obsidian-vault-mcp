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
