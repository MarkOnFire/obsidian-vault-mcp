"""Vault operations for reading and searching Obsidian notes."""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .config import VaultConfig, get_para_location, is_excluded
from .parser import Note, parse_note, resolve_wikilink


class VaultIndex:
    """In-memory index of vault notes for fast searching."""

    def __init__(self, config: VaultConfig):
        """
        Initialize vault index.

        Args:
            config: VaultConfig instance
        """
        self.config = config
        self.notes: Dict[str, Note] = {}  # title -> Note
        self.notes_by_path: Dict[Path, Note] = {}  # path -> Note
        self._build_index()

    def _build_index(self):
        """Build index by scanning vault for markdown files."""
        vault_path = self.config.vault_path

        # Find all .md files
        for md_file in vault_path.rglob("*.md"):
            # Skip excluded folders
            if is_excluded(md_file, self.config):
                continue

            # Parse note
            note = parse_note(md_file)
            if note:
                self.notes[note.title.lower()] = note
                self.notes_by_path[md_file] = note

    def refresh(self):
        """Rebuild the index from disk."""
        self.notes.clear()
        self.notes_by_path.clear()
        self._build_index()

    def get_note_by_title(self, title: str) -> Optional[Note]:
        """
        Get note by title (case-insensitive).

        Args:
            title: Note title

        Returns:
            Note object or None
        """
        return self.notes.get(title.lower())

    def get_note_by_path(self, path: Path) -> Optional[Note]:
        """
        Get note by file path.

        Args:
            path: Absolute or relative path to note

        Returns:
            Note object or None
        """
        # Convert to absolute path
        if not path.is_absolute():
            path = self.config.vault_path / path

        return self.notes_by_path.get(path)

    def search_content(
        self,
        query: str,
        para_location: Optional[str] = None,
        folder: Optional[str] = None,
        case_sensitive: bool = False,
        limit: int = 20,
    ) -> List[Note]:
        """
        Search note contents for query string.

        Args:
            query: Search term
            para_location: Filter by PARA location
            folder: Filter by folder path
            case_sensitive: Whether to match case
            limit: Maximum results

        Returns:
            List of matching notes
        """
        results = []

        for note in self.notes.values():
            # Apply filters
            if para_location and note.para_location != para_location:
                continue

            if folder:
                try:
                    rel_path = note.path.relative_to(self.config.vault_path)
                    if not str(rel_path).startswith(folder):
                        continue
                except ValueError:
                    continue

            # Check content
            if note.contains_text(query, case_sensitive):
                results.append(note)

                if len(results) >= limit:
                    break

        return results

    def list_notes(
        self,
        para_location: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Note]:
        """
        List notes matching criteria.

        Args:
            para_location: Filter by PARA location
            folder: Filter by folder path
            tags: Filter by tags (AND logic)
            created_after: Minimum creation date
            created_before: Maximum creation date
            limit: Maximum results

        Returns:
            List of matching notes
        """
        results = []

        for note in self.notes.values():
            # Folder filter
            if folder:
                try:
                    rel_path = note.path.relative_to(self.config.vault_path)
                    if not str(rel_path).startswith(folder):
                        continue
                except ValueError:
                    continue

            # Other filters via Note.matches_criteria
            if note.matches_criteria(
                para_location=para_location,
                tags=tags,
                created_after=created_after,
                created_before=created_before,
            ):
                results.append(note)

                if len(results) >= limit:
                    break

        # Sort by creation date (newest first)
        results.sort(
            key=lambda n: n.created if n.created else datetime.min,
            reverse=True
        )

        return results

    def get_backlinks(self, note_title: str) -> List[Note]:
        """
        Find all notes that link to the specified note.

        Args:
            note_title: Title of target note

        Returns:
            List of notes containing links to target
        """
        backlinks = []

        for note in self.notes.values():
            links = note.get_wikilinks()
            if note_title in links:
                backlinks.append(note)

        return backlinks


class VaultReader:
    """High-level interface for vault operations."""

    def __init__(self, config: VaultConfig):
        """
        Initialize vault reader.

        Args:
            config: VaultConfig instance
        """
        self.config = config
        self.index = VaultIndex(config)

    def read_note(
        self,
        path: Optional[str] = None,
        title: Optional[str] = None,
        resolve_links: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Read a note by path or title.

        Args:
            path: File path (absolute or vault-relative)
            title: Note title
            resolve_links: Include linked note titles

        Returns:
            Dictionary with note data or None

        Raises:
            ValueError: If neither path nor title provided
        """
        if not path and not title:
            raise ValueError("Must provide either path or title")

        note = None

        if path:
            # Try as absolute path
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.config.vault_path / path

            note = self.index.get_note_by_path(file_path)

        if not note and title:
            note = self.index.get_note_by_title(title)

        if not note:
            return None

        result = note.to_dict(include_content=True)

        if resolve_links:
            links = note.get_wikilinks()
            result["links"] = links

        return result

    def search_notes(
        self,
        query: str,
        para_location: Optional[str] = None,
        folder: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search note contents.

        Args:
            query: Search term
            para_location: Filter by PARA location
            folder: Filter by folder path
            limit: Maximum results

        Returns:
            List of note dictionaries
        """
        notes = self.index.search_content(
            query=query,
            para_location=para_location,
            folder=folder,
            limit=min(limit, self.config.max_search_results),
        )

        return [note.to_dict(include_content=False) for note in notes]

    def list_notes(
        self,
        para_location: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List notes matching criteria.

        Args:
            para_location: Filter by PARA location
            folder: Filter by folder path
            tags: Filter by tags
            created_after: ISO date string
            created_before: ISO date string
            limit: Maximum results

        Returns:
            List of note dictionaries
        """
        # Parse dates
        after_dt = None
        before_dt = None

        if created_after:
            try:
                after_dt = datetime.fromisoformat(created_after)
            except ValueError:
                pass

        if created_before:
            try:
                before_dt = datetime.fromisoformat(created_before)
            except ValueError:
                pass

        notes = self.index.list_notes(
            para_location=para_location,
            folder=folder,
            tags=tags,
            created_after=after_dt,
            created_before=before_dt,
            limit=min(limit, self.config.max_search_results),
        )

        return [note.to_dict(include_content=False) for note in notes]

    def get_backlinks(self, note_title: str) -> List[Dict[str, Any]]:
        """
        Find notes linking to the specified note.

        Args:
            note_title: Title of target note

        Returns:
            List of note dictionaries
        """
        notes = self.index.get_backlinks(note_title)
        return [note.to_dict(include_content=False) for note in notes]

    def resolve_link(self, link: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a wikilink to its target note.

        Args:
            link: Wikilink text

        Returns:
            Note dictionary or None
        """
        target_path = resolve_wikilink(link, self.config.vault_path)

        if not target_path:
            return None

        note = self.index.get_note_by_path(target_path)

        if not note:
            return None

        return note.to_dict(include_content=False)

    def refresh_index(self):
        """Rebuild the note index from disk."""
        self.index.refresh()
