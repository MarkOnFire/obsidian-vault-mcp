"""Markdown and frontmatter parsing for Obsidian notes."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import frontmatter


class Note:
    """Represents an Obsidian note with metadata."""

    def __init__(self, path: Path, content: str):
        """
        Initialize note from file path and content.

        Args:
            path: Absolute path to the note file
            content: Full file content including frontmatter
        """
        self.path = path
        self.title = path.stem

        # Parse frontmatter and content
        try:
            parsed = frontmatter.loads(content)
            self.metadata = dict(parsed.metadata)
            self.content = parsed.content
        except Exception:
            # No frontmatter or invalid format
            self.metadata = {}
            self.content = content

        # Extract common metadata fields
        self.tags = self._extract_tags()
        self.created = self._extract_created()
        self.modified = self._get_modified_time()
        self.para_location = self.metadata.get("para")

    def _get_modified_time(self) -> Optional[datetime]:
        """Get modification time from file system."""
        try:
            mtime = self.path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except (OSError, ValueError):
            return None

    def _extract_tags(self) -> List[str]:
        """Extract tags from frontmatter."""
        tags = self.metadata.get("tags", [])

        if isinstance(tags, str):
            # Handle comma-separated or space-separated tags
            tags = [t.strip() for t in re.split(r"[,\s]+", tags) if t.strip()]
        elif isinstance(tags, list):
            # Already a list
            tags = [str(t).strip() for t in tags if t]
        else:
            tags = []

        return [t.lstrip("#") for t in tags]  # Remove leading # if present

    def _extract_created(self) -> Optional[datetime]:
        """Extract creation date from frontmatter."""
        created = self.metadata.get("created")

        if not created:
            return None

        # Handle different date formats
        if isinstance(created, datetime):
            return created

        if isinstance(created, str):
            # Try common formats
            for fmt in [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y%m%d",
            ]:
                try:
                    return datetime.strptime(created, fmt)
                except ValueError:
                    continue

        return None

    def get_wikilinks(self) -> List[str]:
        """
        Extract all wikilinks from the note content.

        Returns:
            List of linked note titles (without [[ ]])
        """
        # Match [[link]], [[link|alias]], [[folder/link]]
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        matches = re.findall(pattern, self.content)

        # Extract just the note title (remove folder path if present)
        links = []
        for match in matches:
            if "/" in match:
                links.append(match.split("/")[-1])
            else:
                links.append(match)

        return links

    def contains_text(self, query: str, case_sensitive: bool = False) -> bool:
        """
        Check if note contains search query.

        Args:
            query: Search term
            case_sensitive: Whether to match case

        Returns:
            True if query found in content or title
        """
        search_content = f"{self.title}\n{self.content}"

        if not case_sensitive:
            search_content = search_content.lower()
            query = query.lower()

        return query in search_content

    def matches_criteria(
        self,
        para_location: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> bool:
        """
        Check if note matches filter criteria.

        Args:
            para_location: Required PARA location
            tags: Required tags (AND logic - all must be present)
            created_after: Minimum creation date
            created_before: Maximum creation date

        Returns:
            True if all criteria match
        """
        # Check PARA location
        if para_location and self.para_location != para_location:
            return False

        # Check tags (all required tags must be present)
        if tags:
            note_tags_lower = [t.lower() for t in self.tags]
            for required_tag in tags:
                if required_tag.lower() not in note_tags_lower:
                    return False

        # Check creation date
        if self.created:
            if created_after and self.created < created_after:
                return False
            if created_before and self.created > created_before:
                return False

        return True

    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        """
        Convert note to dictionary representation.

        Args:
            include_content: Whether to include full content

        Returns:
            Dictionary with note data
        """
        data = {
            "title": self.title,
            "path": str(self.path),
            "tags": self.tags,
            "para_location": self.para_location,
            "metadata": self.metadata,
        }

        if self.created:
            data["created"] = self.created.isoformat()

        if self.modified:
            data["modified"] = self.modified.isoformat()

        if include_content:
            data["content"] = self.content

        return data


def parse_note(file_path: Path) -> Optional[Note]:
    """
    Parse a note file into a Note object.

    Args:
        file_path: Path to the note file

    Returns:
        Note object or None if parsing failed
    """
    if not file_path.exists() or file_path.suffix != ".md":
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return Note(file_path, content)
    except Exception as e:
        # Log error but don't crash
        print(f"Error parsing {file_path}: {e}")
        return None


def resolve_wikilink(link: str, vault_path: Path) -> Optional[Path]:
    """
    Resolve a wikilink to its target file path.

    Args:
        link: Wikilink text (with or without [[ ]])
        vault_path: Path to vault root

    Returns:
        Absolute path to target note or None if not found
    """
    # Remove [[ ]] if present
    link = link.strip("[]").strip()

    # Remove alias if present (e.g., "Note|Alias" -> "Note")
    if "|" in link:
        link = link.split("|")[0].strip()

    # Handle folder paths (e.g., "Folder/Note")
    if "/" in link:
        # Try exact path
        target = vault_path / f"{link}.md"
        if target.exists():
            return target

    # Search for note by title
    note_name = link.split("/")[-1]  # Get just the note name

    # Recursive search through vault
    for md_file in vault_path.rglob(f"{note_name}.md"):
        # Exclude .obsidian and .trash folders
        if ".obsidian" not in md_file.parts and ".trash" not in md_file.parts:
            return md_file

    return None
