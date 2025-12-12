"""Vault operations for reading and searching Obsidian notes."""

import re
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import frontmatter

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
        include_snippets: bool = False,
        context_lines: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Search note contents.

        Args:
            query: Search term
            para_location: Filter by PARA location
            folder: Filter by folder path
            limit: Maximum results
            include_snippets: Include matching text snippets with context
            context_lines: Number of context lines before/after match

        Returns:
            List of note dictionaries
        """
        notes = self.index.search_content(
            query=query,
            para_location=para_location,
            folder=folder,
            limit=min(limit, self.config.max_search_results),
        )

        results = []
        for note in notes:
            result = note.to_dict(include_content=False)

            if include_snippets:
                # Extract matching snippets with context
                snippets = []
                lines = note.content.split('\n')
                query_lower = query.lower()

                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        snippet_text = '\n'.join(lines[start:end])
                        snippets.append({
                            'line': i + 1,
                            'text': snippet_text.strip()
                        })

                        # Limit snippets per note to avoid huge responses
                        if len(snippets) >= 5:
                            break

                result['snippets'] = snippets

            results.append(result)

        return results

    def list_notes(
        self,
        para_location: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        modified_after: Optional[str] = None,
        modified_before: Optional[str] = None,
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
            modified_after: ISO date string for modification time filter
            modified_before: ISO date string for modification time filter
            limit: Maximum results

        Returns:
            List of note dictionaries
        """
        # Parse creation dates
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

        # Parse modification dates
        mod_after_dt = None
        mod_before_dt = None

        if modified_after:
            try:
                mod_after_dt = datetime.fromisoformat(modified_after)
            except ValueError:
                pass

        if modified_before:
            try:
                mod_before_dt = datetime.fromisoformat(modified_before)
            except ValueError:
                pass

        notes = self.index.list_notes(
            para_location=para_location,
            folder=folder,
            tags=tags,
            created_after=after_dt,
            created_before=before_dt,
            limit=min(limit, self.config.max_search_results) * 3,  # Get more for filtering
        )

        # Apply modification date filters if specified
        if mod_after_dt or mod_before_dt:
            filtered_notes = []
            for note in notes:
                if note.modified:
                    if mod_after_dt and note.modified < mod_after_dt:
                        continue
                    if mod_before_dt and note.modified > mod_before_dt:
                        continue
                    filtered_notes.append(note)
                elif note.created:
                    # Fall back to created date if modified not available
                    if mod_after_dt and note.created < mod_after_dt:
                        continue
                    if mod_before_dt and note.created > mod_before_dt:
                        continue
                    filtered_notes.append(note)
            notes = filtered_notes[:limit]
        else:
            notes = notes[:limit]

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

    def _write_note_atomic(
        self,
        file_path: Path,
        content: str,
        metadata: Dict[str, Any],
    ) -> Path:
        """
        Write a note atomically (write to temp, then rename).

        Args:
            file_path: Target file path
            metadata: Frontmatter metadata dict
            content: Note content (without frontmatter)

        Returns:
            Path to the created note

        Raises:
            FileExistsError: If file already exists
            OSError: If write fails
        """
        if file_path.exists():
            raise FileExistsError(f"Note already exists: {file_path}")

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create frontmatter post
        post = frontmatter.Post(content, **metadata)
        note_content = frontmatter.dumps(post)

        # Write atomically: temp file -> rename
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".md",
            dir=file_path.parent,
            text=True
        )
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.write(note_content)
            shutil.move(temp_path, file_path)
        except Exception:
            # Clean up temp file on failure
            try:
                Path(temp_path).unlink()
            except OSError:
                pass
            raise

        # Add to index
        note = parse_note(file_path)
        if note:
            self.index.notes[note.title.lower()] = note
            self.index.notes_by_path[file_path] = note

        return file_path

    def create_daily_note(
        self,
        content: str = "",
        date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        append_if_exists: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a daily note for the specified date.

        Args:
            content: Note content
            date: Date for the note (defaults to today)
            tags: Optional tags to add
            append_if_exists: If True, append to existing note instead of failing

        Returns:
            Dictionary with created note info

        Raises:
            FileExistsError: If note exists and append_if_exists is False
        """
        if date is None:
            date = datetime.now()

        # Generate filename from config format
        filename = date.strftime(self.config.daily_notes_format) + ".md"
        target_folder = self.config.vault_path / self.config.daily_notes_folder
        file_path = target_folder / filename

        # Check if note exists
        if file_path.exists():
            if append_if_exists:
                return self._append_to_note(file_path, content)
            else:
                raise FileExistsError(
                    f"Daily note already exists: {file_path}. "
                    "Use append_if_exists=True to append content."
                )

        # Build metadata
        metadata = {
            "created": date.strftime("%Y-%m-%d"),
            "para": "inbox",
        }
        if tags:
            metadata["tags"] = tags

        # Create the note
        self._write_note_atomic(file_path, content, metadata)

        return {
            "success": True,
            "path": str(file_path),
            "title": file_path.stem,
            "date": date.strftime("%Y-%m-%d"),
            "para_location": "inbox",
            "action": "created",
        }

    def _append_to_note(self, file_path: Path, content: str) -> Dict[str, Any]:
        """
        Append content to an existing note.

        Args:
            file_path: Path to existing note
            content: Content to append

        Returns:
            Dictionary with note info
        """
        # Read existing content
        with open(file_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # Parse to preserve frontmatter
        parsed = frontmatter.loads(existing_content)

        # Append new content with separator
        separator = "\n\n---\n\n"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_section = f"## Added {timestamp}\n\n{content}"
        parsed.content = parsed.content.rstrip() + separator + new_section

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(parsed))

        # Refresh this note in index
        note = parse_note(file_path)
        if note:
            self.index.notes[note.title.lower()] = note
            self.index.notes_by_path[file_path] = note

        return {
            "success": True,
            "path": str(file_path),
            "title": file_path.stem,
            "para_location": note.para_location if note else None,
            "action": "appended",
        }

    def create_inbox_note(
        self,
        title: str,
        content: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new note in the INBOX folder.

        Args:
            title: Note title (will be used as filename)
            content: Note content
            tags: Optional tags to add

        Returns:
            Dictionary with created note info

        Raises:
            FileExistsError: If note with same title exists
            ValueError: If title is invalid
        """
        # Sanitize title for filename
        safe_title = self._sanitize_filename(title)
        if not safe_title:
            raise ValueError(f"Invalid note title: {title}")

        # Get inbox folder path
        inbox_folder = self.config.para_folders.get("inbox", "0 - INBOX")
        target_folder = self.config.vault_path / inbox_folder
        file_path = target_folder / f"{safe_title}.md"

        # Build metadata
        metadata = {
            "created": datetime.now().strftime("%Y-%m-%d"),
            "para": "inbox",
        }
        if tags:
            metadata["tags"] = tags

        # Create the note
        self._write_note_atomic(file_path, content, metadata)

        return {
            "success": True,
            "path": str(file_path),
            "title": safe_title,
            "para_location": "inbox",
            "action": "created",
        }

    def _sanitize_filename(self, title: str) -> str:
        """
        Sanitize a title for use as a filename.

        Args:
            title: Raw title string

        Returns:
            Sanitized filename-safe string
        """
        # Remove or replace problematic characters
        # Keep alphanumeric, spaces, hyphens, underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        sanitized = sanitized.strip()

        # Collapse multiple spaces
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # Limit length (leave room for .md extension)
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()

        return sanitized
