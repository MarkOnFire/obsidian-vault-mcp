#!/usr/bin/env python3
"""Test task statistics functionality with real vault data."""

import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent))

from obsidian_vault_mcp.config import load_config
from obsidian_vault_mcp.vault import VaultReader
from obsidian_vault_mcp.tasks import get_folder_task_stats, get_project_activity
import json


def test_task_stats():
    """Test task statistics for PBSWI folder."""
    print("=" * 80)
    print("Testing Task Statistics")
    print("=" * 80)

    # Load config and create vault reader
    config = load_config()
    vault = VaultReader(config)

    # Test 1: Get task stats for PBSWI folder
    print("\n📊 Task Statistics for PBSWI Projects\n")

    try:
        stats = get_folder_task_stats(
            vault_reader=vault,
            folder_path="1 - PROJECTS/PBSWI",
            lookback_days=7
        )

        print(f"Folder: {stats['folder']}")
        print(f"Notes Scanned: {stats['notes_scanned']}")
        print()

        s = stats['stats']
        print(f"Total Tasks: {s['total_tasks']}")
        print(f"Completed This Week: {s['completed_this_week']}")
        print(f"Active: {s['active']}")
        print(f"Blocked: {s['blocked']}")
        print(f"Overdue: {s['overdue']}")
        print(f"Due Soon: {s['due_soon']}")
        print(f"High Priority: {s['high_priority']}")
        print()

        # Show some completed tasks
        if s['completed_tasks']:
            print("Recently Completed Tasks:")
            for task in s['completed_tasks'][:5]:
                print(f"  ✅ {task['content'][:80]}...")
                print(f"     Completed: {task['completion_date']}")
            print()

        # Show some active tasks
        if s['active_tasks']:
            print("Active Tasks:")
            for task in s['active_tasks'][:5]:
                content = task['content'][:80]
                priority = f" [{task['priority']}]" if task.get('priority') else ""
                print(f"  [ ] {content}{priority}")
            print()

        # Show blocked tasks
        if s['blocked_tasks']:
            print("Blocked Tasks:")
            for task in s['blocked_tasks']:
                print(f"  🚧 {task['content'][:80]}")
            print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Get project activity
    print("\n" + "=" * 80)
    print("Project Activity Summary")
    print("=" * 80)
    print()

    try:
        projects = get_project_activity(
            vault_reader=vault,
            folder_path="1 - PROJECTS/PBSWI"
        )

        if not projects:
            print("No projects with tasks found.")
            return True

        print(f"Total Projects: {len(projects)}")
        print()

        # Active projects
        active = [p for p in projects if not p['is_stale']]
        stale = [p for p in projects if p['is_stale']]

        if active:
            print(f"Active Projects ({len(active)}):")
            for p in active[:10]:
                print(f"\n  {p['title']}")
                print(f"    Last Activity: {p['last_activity']}")
                print(f"    Tasks: {p['task_stats']['total']} total, "
                      f"{p['task_stats']['completed_this_week']} completed this week, "
                      f"{p['task_stats']['active']} active")

        if stale:
            print(f"\n\nStale Projects ({len(stale)}):")
            for p in stale[:10]:
                print(f"\n  {p['title']}")
                print(f"    Last Activity: {p['last_activity']}")
                print(f"    Tasks: {p['task_stats']['active']} active (no recent completions)")

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ All tests completed successfully!")
    return True


if __name__ == "__main__":
    success = test_task_stats()
    sys.exit(0 if success else 1)
