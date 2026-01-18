"""Vault operations for reading and searching Obsidian notes."""

import base64
import hashlib
import logging
import re
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import frontmatter

logger = logging.getLogger("obsidian_vault_mcp")

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

    def create_note(
        self,
        title: str,
        para_location: str,
        content: str = "",
        subfolder: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new note in a specified PARA location.

        This method allows creating notes directly in projects, areas, resources,
        or archive folders, optionally within a subfolder. Useful for automation
        workflows where notes should be placed directly in their final location.

        Args:
            title: Note title (will be used as filename)
            para_location: PARA location - one of "projects", "areas", "resources", "archive"
            content: Note content (markdown)
            subfolder: Optional subfolder path within the PARA location (e.g., "PBSWI" or "brainstorming/Ideas")
            tags: Optional tags to add

        Returns:
            Dictionary with created note info

        Raises:
            FileExistsError: If note with same title exists at target location
            ValueError: If title is invalid or para_location is not allowed
        """
        # Validate para_location (inbox not allowed - use create_inbox_note for that)
        allowed_locations = ["projects", "areas", "resources", "archive"]
        if para_location not in allowed_locations:
            raise ValueError(
                f"Invalid para_location: {para_location}. "
                f"Must be one of: {', '.join(allowed_locations)}. "
                f"Use create_inbox_note() for inbox."
            )

        # Sanitize title for filename
        safe_title = self._sanitize_filename(title)
        if not safe_title:
            raise ValueError(f"Invalid note title: {title}")

        # Get the PARA folder path from config
        para_folder = self.config.para_folders.get(para_location)
        if not para_folder:
            raise ValueError(f"PARA folder not configured for: {para_location}")

        # Build target path
        target_folder = self.config.vault_path / para_folder
        if subfolder:
            # Sanitize subfolder path (allow / for nested folders)
            safe_subfolder = subfolder.strip("/")
            # Basic security check - no parent directory traversal
            if ".." in safe_subfolder:
                raise ValueError(f"Invalid subfolder path: {subfolder}")
            target_folder = target_folder / safe_subfolder

        # Ensure target folder exists
        target_folder.mkdir(parents=True, exist_ok=True)

        file_path = target_folder / f"{safe_title}.md"

        # Check if file already exists
        if file_path.exists():
            raise FileExistsError(f"Note already exists: {file_path}")

        # Build metadata
        metadata = {
            "created": datetime.now().strftime("%Y-%m-%d"),
            "para": para_location,
        }
        if tags:
            metadata["tags"] = tags

        # Create the note
        self._write_note_atomic(file_path, content, metadata)

        # Build relative path for response
        rel_path = file_path.relative_to(self.config.vault_path)

        return {
            "success": True,
            "path": str(rel_path),
            "full_path": str(file_path),
            "title": safe_title,
            "para_location": para_location,
            "subfolder": subfolder,
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

    def add_attachment(
        self,
        source_path: Optional[str] = None,
        base64_content: Optional[str] = None,
        filename: Optional[str] = None,
        link_to_note: Optional[str] = None,
        link_text: Optional[str] = None,
        embed: bool = False,
    ) -> Dict[str, Any]:
        """
        Add an attachment to the vault's attachment folder (Archive).

        Either source_path OR (base64_content AND filename) must be provided.

        Args:
            source_path: Path to file on disk to copy
            base64_content: Base64-encoded file content
            filename: Filename for base64 content (required if using base64)
            link_to_note: Note title or path to append the link to
            link_text: Display text for the link (defaults to filename)
            embed: If True, use ![[]] syntax for embedding (images render inline)

        Returns:
            Dictionary with attachment info and link format

        Raises:
            ValueError: If invalid parameters or unsupported file type
            FileNotFoundError: If source_path doesn't exist
            FileExistsError: If attachment already exists in vault
        """
        # Validate inputs
        if not source_path and not base64_content:
            raise ValueError("Must provide either source_path or base64_content")

        if base64_content and not filename:
            raise ValueError("filename is required when using base64_content")

        # Determine source and target
        if source_path:
            source = Path(source_path).expanduser().resolve()
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")

            attachment_name = source.name
            file_extension = source.suffix.lstrip('.').lower()
            file_size = source.stat().st_size
        else:
            attachment_name = filename
            file_extension = Path(filename).suffix.lstrip('.').lower()
            # Decode to check size
            try:
                decoded = base64.b64decode(base64_content)
                file_size = len(decoded)
            except Exception as e:
                raise ValueError(f"Invalid base64 content: {e}")

        # Validate file type
        if file_extension not in self.config.supported_attachment_types:
            raise ValueError(
                f"Unsupported file type: .{file_extension}. "
                f"Supported: {', '.join(self.config.supported_attachment_types)}"
            )

        # Validate file size
        max_bytes = self.config.max_attachment_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(
                f"File too large: {file_size / (1024*1024):.1f}MB. "
                f"Maximum: {self.config.max_attachment_size_mb}MB"
            )

        # Build target path
        attachment_folder = self.config.vault_path / self.config.attachment_folder
        attachment_folder.mkdir(parents=True, exist_ok=True)
        target_path = attachment_folder / attachment_name

        # Check for existing attachment
        if target_path.exists():
            raise FileExistsError(f"Attachment already exists: {target_path}")

        # Copy or write file
        try:
            if source_path:
                shutil.copy2(source, target_path)
            else:
                with open(target_path, 'wb') as f:
                    f.write(decoded)

            logger.info(f"Added attachment: {target_path}")

        except Exception as e:
            # Clean up on failure
            if target_path.exists():
                target_path.unlink()
            raise OSError(f"Failed to write attachment: {e}")

        # Generate wikilink
        # Obsidian uses just the filename for attachments
        display_text = link_text or attachment_name
        if embed:
            wikilink = f"![[{attachment_name}]]"
        else:
            if link_text and link_text != attachment_name:
                wikilink = f"[[{attachment_name}|{link_text}]]"
            else:
                wikilink = f"[[{attachment_name}]]"

        result = {
            "success": True,
            "path": str(target_path),
            "filename": attachment_name,
            "size_bytes": file_size,
            "wikilink": wikilink,
            "embed_link": f"![[{attachment_name}]]",
        }

        # Append link to note if specified
        if link_to_note:
            try:
                append_result = self._append_link_to_note(
                    note_ref=link_to_note,
                    link=wikilink,
                )
                result["linked_to_note"] = append_result
            except Exception as e:
                logger.warning(f"Failed to append link to note: {e}")
                result["link_error"] = str(e)

        return result

    def _append_link_to_note(
        self,
        note_ref: str,
        link: str,
        section_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Append a link to an existing note.

        Args:
            note_ref: Note title or path
            link: The wikilink to append
            section_header: Optional section header to add link under

        Returns:
            Dictionary with note info

        Raises:
            ValueError: If note not found
        """
        # Find the note
        note = None

        # Try as path first
        if '/' in note_ref or note_ref.endswith('.md'):
            path = Path(note_ref)
            if not path.is_absolute():
                path = self.config.vault_path / note_ref
            note = self.index.get_note_by_path(path)

        # Try as title
        if not note:
            note = self.index.get_note_by_title(note_ref)

        if not note:
            raise ValueError(f"Note not found: {note_ref}")

        # Read current content
        file_path = note.path
        with open(file_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # Parse to preserve frontmatter
        parsed = frontmatter.loads(existing_content)

        # Build the content to append
        if section_header:
            append_content = f"\n\n## {section_header}\n\n{link}"
        else:
            append_content = f"\n\n{link}"

        # Append
        parsed.content = parsed.content.rstrip() + append_content

        # Write back atomically
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".md",
            dir=file_path.parent,
            text=True
        )
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(parsed))
            shutil.move(temp_path, file_path)
        except Exception:
            try:
                Path(temp_path).unlink()
            except OSError:
                pass
            raise

        # Refresh note in index
        refreshed = parse_note(file_path)
        if refreshed:
            self.index.notes[refreshed.title.lower()] = refreshed
            self.index.notes_by_path[file_path] = refreshed

        return {
            "note_title": note.title,
            "note_path": str(file_path),
            "link_added": link,
        }

    # =========================================================================
    # Daily Journal Operations
    # =========================================================================

    def get_unarchived_daily_notes(
        self,
        exclude_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get daily notes that haven't been archived (moved to month subfolders).

        Notes in the daily journal folder root are considered unarchived.
        Notes in subfolders matching the archive pattern (JANUARY, FEBRUARY, etc.)
        are considered archived.

        Args:
            exclude_date: Optional date string (YYYY-MM-DD) to exclude (typically today)

        Returns:
            List of dicts with note info, sorted by date (oldest first)
        """
        journal_folder = self.config.vault_path / self.config.daily_journal_folder

        if not journal_folder.exists():
            logger.warning(f"Daily journal folder not found: {journal_folder}")
            return []

        # Get date pattern from config
        date_format = self.config.daily_notes_format
        # Convert strftime to regex pattern
        date_regex = date_format.replace("%Y", r"\d{4}").replace("%m", r"\d{2}").replace("%d", r"\d{2}")
        date_pattern = re.compile(rf"^{date_regex}\.md$")

        # Use glob (not rglob) to only get files directly in the folder
        unarchived = []

        for note_path in journal_folder.glob("*.md"):
            # Check if filename matches date pattern
            if not date_pattern.match(note_path.name):
                continue

            # Extract date from filename
            date_str = note_path.stem

            # Exclude specified date (typically today)
            if exclude_date and date_str == exclude_date:
                continue

            # Parse the note for metadata
            try:
                with open(note_path, "r", encoding="utf-8") as f:
                    content = f.read()

                parsed = frontmatter.loads(content)

                unarchived.append({
                    "path": str(note_path),
                    "date": date_str,
                    "filename": note_path.name,
                    "frontmatter": dict(parsed.metadata),
                    "content_length": len(parsed.content),
                    "has_section_markers": "<!-- SECTION:" in content,
                })
            except Exception as e:
                logger.warning(f"Could not parse {note_path}: {e}")
                unarchived.append({
                    "path": str(note_path),
                    "date": date_str,
                    "filename": note_path.name,
                    "frontmatter": {},
                    "content_length": 0,
                    "has_section_markers": False,
                    "error": str(e),
                })

        # Sort by date (oldest first)
        unarchived.sort(key=lambda x: x["date"])

        logger.info(f"Found {len(unarchived)} unarchived daily note(s)")
        return unarchived

    def extract_note_tasks(
        self,
        note_path: str,
        sections: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract tasks from a note with status, section info, and metadata.

        Args:
            note_path: Path to the note (absolute or relative to vault)
            sections: Optional list of section names to extract from (e.g., ["Action Items", "Reminders"])
                     If None, extracts from entire note.

        Returns:
            Dict with:
                - checked: list of completed tasks
                - unchecked: list of incomplete tasks
                - total: total count
                - by_section: dict mapping section names to task lists
        """
        path = Path(note_path)
        if not path.is_absolute():
            path = self.config.vault_path / note_path

        if not path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse frontmatter
        parsed = frontmatter.loads(content)
        body = parsed.content
        note_date = path.stem  # Assume filename is the date

        result = {
            "note_path": str(path),
            "note_date": note_date,
            "checked": [],
            "unchecked": [],
            "total": 0,
            "by_section": {},
        }

        def parse_task_line(line: str, section_name: str) -> Optional[Dict[str, Any]]:
            """Parse a single task line and return task dict."""
            # Match: - [x] or - [ ] followed by task text
            checked_match = re.match(r'^-\s*\[x\]\s+(.+?)(?:\s*✅\s*(\d{4}-\d{2}-\d{2}))?$', line, re.IGNORECASE)
            unchecked_match = re.match(r'^-\s*\[ \]\s+(.+)$', line)

            if checked_match:
                task_text = checked_match.group(1).strip()
                completion_date = checked_match.group(2)

                # Extract added date if present: (added Jan 12)
                added_match = re.search(r'\(added\s+([^)]+)\)', task_text)
                added_date = added_match.group(1) if added_match else None

                # Clean task text
                task_text = re.sub(r'\s*\(added[^)]*\)\s*', '', task_text)
                task_text = re.sub(r'\s*✅.*$', '', task_text)
                task_text = re.sub(r'\s*⚠️.*$', '', task_text).strip()

                return {
                    "text": task_text,
                    "completed": True,
                    "completion_date": completion_date,
                    "added_date": added_date,
                    "section": section_name,
                    "source_date": note_date,
                }
            elif unchecked_match:
                task_text = unchecked_match.group(1).strip()

                # Extract added date if present
                added_match = re.search(r'\(added\s+([^)]+)\)', task_text)
                added_date = added_match.group(1) if added_match else None

                # Extract warning/age info
                age_match = re.search(r'⚠️\s*\*?(\d+)\s*days', task_text)
                age_days = int(age_match.group(1)) if age_match else None

                # Clean task text
                task_text = re.sub(r'\s*\(added[^)]*\)\s*', '', task_text)
                task_text = re.sub(r'\s*⚠️.*$', '', task_text).strip()

                return {
                    "text": task_text,
                    "completed": False,
                    "added_date": added_date,
                    "age_days": age_days,
                    "section": section_name,
                    "source_date": note_date,
                }

            return None

        if sections:
            # Extract tasks only from specified sections
            for section_name in sections:
                # Match section headers (### or ####) that contain the section name
                # The header may have additional text like "*(persistent)*"
                # Note: {{3,4}} needed to escape braces in f-string for regex quantifier
                section_pattern = rf'^#{{3,4}}\s+[^\n]*{re.escape(section_name)}[^\n]*\n(.*?)(?=^#{{2,4}}\s|\n---|\Z)'
                matches = re.findall(section_pattern, body, re.DOTALL | re.IGNORECASE | re.MULTILINE)

                section_tasks = {"checked": [], "unchecked": []}

                for section_content in matches:
                    for line in section_content.split('\n'):
                        line = line.strip()
                        if not line.startswith('-'):
                            continue

                        task = parse_task_line(line, section_name)
                        if task:
                            if task["completed"]:
                                section_tasks["checked"].append(task)
                                result["checked"].append(task)
                            else:
                                section_tasks["unchecked"].append(task)
                                result["unchecked"].append(task)

                result["by_section"][section_name] = section_tasks
        else:
            # Extract all tasks from the note
            current_section = "Unknown"

            for line in body.split('\n'):
                line_stripped = line.strip()

                # Track current section
                section_match = re.match(r'^#{2,4}\s+(.+)$', line_stripped)
                if section_match:
                    current_section = section_match.group(1).strip()
                    if current_section not in result["by_section"]:
                        result["by_section"][current_section] = {"checked": [], "unchecked": []}
                    continue

                if not line_stripped.startswith('-'):
                    continue

                task = parse_task_line(line_stripped, current_section)
                if task:
                    if current_section not in result["by_section"]:
                        result["by_section"][current_section] = {"checked": [], "unchecked": []}

                    if task["completed"]:
                        result["by_section"][current_section]["checked"].append(task)
                        result["checked"].append(task)
                    else:
                        result["by_section"][current_section]["unchecked"].append(task)
                        result["unchecked"].append(task)

        result["total"] = len(result["checked"]) + len(result["unchecked"])

        return result

    def update_daily_note(
        self,
        date: str,
        sections: Dict[str, str],
        preserve_modified: bool = True,
        create_if_missing: bool = False,
        template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update specific sections of a daily note while preserving user modifications.

        Uses hash-based modification detection: if a section's current content
        matches its stored hash (from frontmatter), it's safe to regenerate.
        Modified sections are preserved.

        Args:
            date: Date string (YYYY-MM-DD) for the daily note
            sections: Dict mapping section names to new content
            preserve_modified: If True, don't overwrite sections the user has modified
            create_if_missing: If True, create the note if it doesn't exist
            template: Optional template string for new notes (must include section markers)

        Returns:
            Dict with update results including which sections were updated/preserved
        """
        # Build path to daily note
        journal_folder = self.config.vault_path / self.config.daily_journal_folder
        note_path = journal_folder / f"{date}.md"

        result = {
            "path": str(note_path),
            "date": date,
            "created": False,
            "updated_sections": [],
            "preserved_sections": [],
            "new_sections": [],
            "errors": [],
        }

        # Check if note exists
        if not note_path.exists():
            if not create_if_missing:
                raise FileNotFoundError(f"Daily note not found: {note_path}")

            # Create new note from template
            if not template:
                raise ValueError("template is required when create_if_missing=True and note doesn't exist")

            # Ensure directory exists
            journal_folder.mkdir(parents=True, exist_ok=True)

            # Compute hashes for all sections
            section_hashes = {}
            for section_name, content in sections.items():
                section_hashes[section_name] = self._compute_section_hash(content)

            # Format template with sections and hashes
            formatted_content = template.format(
                date=date,
                generated_sections_frontmatter=self._format_section_hashes(section_hashes),
                **{f"section_{k}": self._wrap_section(v, k) for k, v in sections.items()},
                **sections,  # Also provide raw content for templates that don't use wrapped
            )

            note_path.write_text(formatted_content, encoding="utf-8")

            result["created"] = True
            result["updated_sections"] = list(sections.keys())

            logger.info(f"Created daily note: {note_path}")
            return result

        # Note exists - read and update selectively
        with open(note_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # Parse frontmatter to get stored hashes
        parsed = frontmatter.loads(existing_content)
        stored_hashes = self._get_stored_hashes(dict(parsed.metadata))

        # Track new hashes
        new_hashes = dict(stored_hashes)

        # Process each section
        updated_content = existing_content

        for section_name, new_content in sections.items():
            # Compute hash of new content
            new_hash = self._compute_section_hash(new_content)
            new_hashes[section_name] = new_hash

            # Check if section exists in note
            section_start_marker = f"<!-- SECTION:{section_name}:START -->"
            section_end_marker = f"<!-- SECTION:{section_name}:END -->"

            if section_start_marker not in existing_content:
                # Section doesn't exist - this is a new section
                result["new_sections"].append(section_name)
                logger.debug(f"Section '{section_name}' not found in note - skipping")
                continue

            # Extract current section content
            current_content = self._extract_section_content(existing_content, section_name)

            if current_content is None:
                result["errors"].append(f"Could not extract section: {section_name}")
                continue

            # Check if section was modified
            stored_hash = stored_hashes.get(section_name, "")

            if preserve_modified and stored_hash:
                current_hash = self._compute_section_hash(current_content)
                if current_hash != stored_hash:
                    # User modified this section - preserve it
                    result["preserved_sections"].append(section_name)
                    logger.info(f"Preserving modified section: {section_name}")
                    continue

            # Safe to update this section
            wrapped_content = self._wrap_section(new_content, section_name)

            # Replace the section in content
            pattern = rf'{re.escape(section_start_marker)}.*?{re.escape(section_end_marker)}'
            updated_content = re.sub(pattern, wrapped_content, updated_content, flags=re.DOTALL)

            result["updated_sections"].append(section_name)

        # Update frontmatter with new hashes
        updated_content = self._update_frontmatter_hashes(updated_content, new_hashes)

        # Write back atomically
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".md",
            dir=note_path.parent,
            text=True
        )
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.write(updated_content)
            shutil.move(temp_path, note_path)
        except Exception as e:
            try:
                Path(temp_path).unlink()
            except OSError:
                pass
            raise OSError(f"Failed to update daily note: {e}")

        logger.info(
            f"Updated daily note: {len(result['updated_sections'])} updated, "
            f"{len(result['preserved_sections'])} preserved"
        )

        return result

    # =========================================================================
    # Section Hash Helpers
    # =========================================================================

    def _compute_section_hash(self, content: str) -> str:
        """Compute a hash of section content for modification detection."""
        # Normalize whitespace before hashing
        normalized = ' '.join(content.split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]

    def _extract_section_content(self, full_content: str, section_name: str) -> Optional[str]:
        """Extract content between section markers."""
        start_marker = f"<!-- SECTION:{section_name}:START -->"
        end_marker = f"<!-- SECTION:{section_name}:END -->"

        start_idx = full_content.find(start_marker)
        end_idx = full_content.find(end_marker)

        if start_idx == -1 or end_idx == -1:
            return None

        content_start = start_idx + len(start_marker)
        return full_content[content_start:end_idx].strip()

    def _wrap_section(self, content: str, section_name: str) -> str:
        """Wrap content with section markers."""
        return f"<!-- SECTION:{section_name}:START -->\n{content}\n<!-- SECTION:{section_name}:END -->"

    def _get_stored_hashes(self, frontmatter: Dict[str, Any]) -> Dict[str, str]:
        """Extract stored section hashes from frontmatter."""
        hashes_str = frontmatter.get("generated_sections", "")
        if not hashes_str:
            return {}

        hashes = {}
        # Handle inline format: {section: hash, ...}
        if '{' in str(hashes_str):
            try:
                content = str(hashes_str).strip('{}')
                for pair in content.split(','):
                    if ':' in pair:
                        key, value = pair.split(':', 1)
                        hashes[key.strip()] = value.strip()
            except Exception:
                pass

        return hashes

    def _format_section_hashes(self, hashes: Dict[str, str]) -> str:
        """Format section hashes for frontmatter."""
        if not hashes:
            return ""
        hash_str = ", ".join(f"{k}: {v}" for k, v in hashes.items())
        return f"generated_sections: {{{hash_str}}}\n"

    def _update_frontmatter_hashes(self, content: str, hashes: Dict[str, str]) -> str:
        """Update the generated_sections field in note content."""
        hash_str = ", ".join(f"{k}: {v}" for k, v in hashes.items())
        hash_line = f"generated_sections: {{{hash_str}}}"

        # Check if we're in frontmatter
        if not content.startswith('---'):
            return content

        # Find frontmatter boundaries
        parts = content.split('---', 2)
        if len(parts) < 3:
            return content

        fm_content = parts[1]
        body = parts[2]

        # Check if generated_sections already exists
        if "generated_sections:" in fm_content:
            # Replace existing line
            fm_content = re.sub(
                r'generated_sections:.*$',
                hash_line,
                fm_content,
                flags=re.MULTILINE
            )
        else:
            # Add before closing
            fm_content = fm_content.rstrip() + f"\n{hash_line}\n"

        return f"---{fm_content}---{body}"
