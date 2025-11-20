#!/usr/bin/env python3
"""Standalone test script for vault operations (without MCP)."""

from pathlib import Path
from obsidian_vault_mcp.config import load_config
from obsidian_vault_mcp.vault import VaultReader


def main():
    """Run test operations."""
    print("Loading configuration...")
    config = load_config()
    print(f"✓ Vault path: {config.vault_path}")

    print("\nInitializing vault reader...")
    vault = VaultReader(config)
    print(f"✓ Indexed {len(vault.index.notes)} notes")

    # Test 1: Read a specific note
    print("\n" + "="*60)
    print("TEST 1: Read note by title")
    print("="*60)

    result = vault.read_note(title="Project Dashboard")
    if result:
        print(f"✓ Found: {result['title']}")
        print(f"  PARA: {result.get('para_location', 'N/A')}")
        print(f"  Tags: {', '.join(result.get('tags', []))}")
        print(f"  Content length: {len(result.get('content', ''))} chars")
        if result.get('links'):
            print(f"  Links: {', '.join(result['links'][:5])}...")
    else:
        print("✗ Note not found")

    # Test 2: Search for notes
    print("\n" + "="*60)
    print("TEST 2: Search notes")
    print("="*60)

    results = vault.search_notes(query="meeting", limit=5)
    print(f"✓ Found {len(results)} notes containing 'meeting':")
    for note in results[:3]:
        print(f"  - {note['title']} ({note.get('para_location', 'N/A')})")

    # Test 3: List notes by PARA location
    print("\n" + "="*60)
    print("TEST 3: List notes by PARA location")
    print("="*60)

    for para in ["inbox", "projects", "areas", "resources"]:
        results = vault.list_notes(para_location=para, limit=3)
        print(f"✓ {para}: {len(results)} notes")
        for note in results[:2]:
            print(f"  - {note['title']}")

    # Test 4: Get backlinks
    print("\n" + "="*60)
    print("TEST 4: Get backlinks")
    print("="*60)

    backlinks = vault.get_backlinks("Project Dashboard")
    print(f"✓ Found {len(backlinks)} notes linking to 'Project Dashboard':")
    for note in backlinks[:3]:
        print(f"  - {note['title']}")

    # Test 5: Filter by tags
    print("\n" + "="*60)
    print("TEST 5: Filter by tags")
    print("="*60)

    results = vault.list_notes(tags=["pbswi"], limit=5)
    print(f"✓ Found {len(results)} notes tagged with 'pbswi':")
    for note in results[:3]:
        print(f"  - {note['title']} ({', '.join(note.get('tags', []))})")

    # Test 6: Resolve wikilink
    print("\n" + "="*60)
    print("TEST 6: Resolve wikilink")
    print("="*60)

    result = vault.resolve_link("[[Project Dashboard]]")
    if result:
        print(f"✓ Resolved to: {result['title']}")
        print(f"  Path: {result['path']}")
    else:
        print("✗ Could not resolve link")

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    main()
