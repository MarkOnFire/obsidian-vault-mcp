#!/usr/bin/env python3
"""Test list_notes method."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from obsidian_vault_mcp.config import load_config
from obsidian_vault_mcp.vault import VaultReader

config = load_config()
vault = VaultReader(config)

print("Testing list_notes...")
print()

# Test 1: List all notes (limited)
print("All notes (limit 10):")
notes = vault.list_notes(limit=10)
print(f"Found {len(notes)} notes")
for note in notes[:5]:
    print(f"  - {note['title']} ({note['path']})")
print()

# Test 2: List notes in PBSWI folder
print("PBSWI folder (1 - PROJECTS/PBSWI):")
notes = vault.list_notes(folder="1 - PROJECTS/PBSWI", limit=100)
print(f"Found {len(notes)} notes")
for note in notes[:10]:
    print(f"  - {note['title']} ({note['path']})")
print()

# Test 3: Check index
print(f"Total indexed notes: {len(vault.index.notes)}")
print(f"Total indexed by path: {len(vault.index.notes_by_path)}")
