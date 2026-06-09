#!/usr/bin/env python3
"""
Figure KB Location Manager

Handles configuration, initialization, and migration of the figure knowledge base.
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
CONFIG_FILE = CODEX_HOME / "figure-kb-config.json"
LEGACY_CONFIG_FILE = Path.home() / ".claude" / "figure-kb-config.json"
DEFAULT_LOCATION = CODEX_HOME / "figure-kb"
SCRIPT_DISPLAY = "python scripts/kb_location_manager.py"


def _read_config(config_file):
    """Read a KB configuration file; invalid configs are treated as absent."""
    try:
        with open(config_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _env_kb_path():
    """Return the KB path from FIGURE_KB_HOME, if configured."""
    env_path = os.environ.get("FIGURE_KB_HOME")
    if env_path:
        return Path(env_path).expanduser()
    return None


def get_kb_path():
    """Get the configured KB path, or return None if not configured."""
    env_path = _env_kb_path()
    if env_path:
        return env_path

    for config_file in (CONFIG_FILE, LEGACY_CONFIG_FILE):
        if config_file.exists():
            config = _read_config(config_file)
            if config and config.get("kb_path"):
                return Path(config["kb_path"]).expanduser()
    return None


def get_disk_usage(path):
    """Get total size of a directory in bytes."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_disk_usage(entry.path)
    except (PermissionError, FileNotFoundError):
        pass
    return total


def format_size(bytes_size):
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def get_free_space(path):
    """Get free space on the drive containing path."""
    stat = shutil.disk_usage(path)
    return stat.free


def suggest_data_drive_location():
    """Suggest a data-drive location without hard-coding a user-specific path."""
    if os.name == "nt":
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            root = Path(f"{letter}:/")
            if root.exists():
                return root / "figure-kb"
    return Path.home() / "figure-kb"


def initialize_kb_structure(kb_path):
    """Create KB directory structure."""
    kb_path = Path(kb_path)

    # Create directories
    dirs = [
        kb_path,
        kb_path / "patterns" / "chart-type",
        kb_path / "patterns" / "color-scheme",
        kb_path / "patterns" / "layout-archetype",
        kb_path / "patterns" / "journal",
        kb_path / "reports",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Create empty index if it doesn't exist
    index_file = kb_path / "index.json"
    if not index_file.exists():
        with open(index_file, 'w') as f:
            json.dump([], f)

    print(f"✅ KB structure initialized at: {kb_path}")


def save_config(kb_path, **extra_config):
    """Save KB configuration."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "kb_path": str(kb_path),
        "created_date": datetime.now().isoformat(),
        **extra_config
    }

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    print(f"✅ Configuration saved to: {CONFIG_FILE}")


def count_entries(kb_path):
    """Count total entries in KB."""
    index_file = Path(kb_path) / "index.json"
    if not index_file.exists():
        return 0

    with open(index_file) as f:
        index = json.load(f)
    return len(index)


def migrate_kb(old_path, new_path, mode='move'):
    """
    Migrate KB from old_path to new_path.

    Args:
        old_path: Source KB path
        new_path: Destination KB path
        mode: 'move', 'copy', or 'archive'
    """
    old_path = Path(old_path)
    new_path = Path(new_path)

    if not old_path.exists():
        print(f"❌ Source KB not found: {old_path}")
        return False

    # Get stats
    entry_count = count_entries(old_path)
    kb_size = get_disk_usage(old_path)

    print(f"\n{'='*60}")
    print(f"KB Migration: {mode.upper()}")
    print(f"{'='*60}")
    print(f"Source: {old_path}")
    print(f"Destination: {new_path}")
    print(f"Entries: {entry_count}")
    print(f"Size: {format_size(kb_size)}")
    print(f"{'='*60}\n")

    # Check free space at destination
    new_path.parent.mkdir(parents=True, exist_ok=True)
    free_space = get_free_space(new_path.parent)

    if free_space < kb_size * 1.2:  # Need 20% buffer
        print(f"⚠️  WARNING: Low disk space at destination")
        print(f"   Required: {format_size(kb_size * 1.2)}")
        print(f"   Available: {format_size(free_space)}")
        response = input("Continue anyway? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return False

    try:
        if mode == 'move':
            print("Moving KB...")
            shutil.move(str(old_path), str(new_path))
            print("✅ KB moved successfully")

        elif mode == 'copy':
            print("Copying KB...")
            shutil.copytree(str(old_path), str(new_path), dirs_exist_ok=True)
            print("✅ KB copied successfully")
            print(f"   Original kept at: {old_path}")

        elif mode == 'archive':
            archive_name = f"figure-kb-archive-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            archive_path = old_path.parent / archive_name
            print(f"Archiving KB to: {archive_path}")
            shutil.move(str(old_path), str(archive_path))
            print("✅ KB archived successfully")
            print("   Initializing fresh KB at new location...")
            initialize_kb_structure(new_path)

        # Update config
        save_config(new_path)
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def first_time_setup():
    """Interactive first-time setup wizard."""
    print("\n" + "="*60)
    print("Figure Knowledge Base Setup")
    print("="*60)
    print("\nThis is your first time using nature-figure-learner.")
    print("The figure knowledge base (KB) needs a storage location.\n")
    print("ESTIMATED SPACE USAGE:")
    print("  • Each analyzed figure: ~50-100 KB")
    print("  • 100 figures: ~5-10 MB")
    print("  • 1,000 figures: ~50-100 MB")
    print("  • 10,000 figures: ~500 MB - 1 GB\n")

    env_path = _env_kb_path()
    if env_path:
        print(f"FIGURE_KB_HOME is set: {env_path}")
        initialize_kb_structure(env_path)
        save_config(env_path, source="FIGURE_KB_HOME")
        return env_path

    # Check if KB already exists at default location
    if DEFAULT_LOCATION.exists():
        entry_count = count_entries(DEFAULT_LOCATION)
        kb_size = get_disk_usage(DEFAULT_LOCATION)
        print(f"⚠️  Detected existing KB at default location:")
        print(f"   Path: {DEFAULT_LOCATION}")
        print(f"   Entries: {entry_count}")
        print(f"   Size: {format_size(kb_size)}\n")

    print("Choose storage location:\n")
    print(f"[A] {DEFAULT_LOCATION}")
    print("    ✓ Fast access (SSD)")
    print("    ✓ Keeps Codex agent data together")
    print("    ✗ May fill the home/system drive over time\n")

    data_drive = suggest_data_drive_location()
    print(f"[B] {data_drive}")
    print("    ✓ Larger disk space if a data drive is available")
    print("    ✓ Separate from system drive")
    print("    ✗ Slower if target drive is HDD\n")

    print("[C] Custom path (you specify)\n")
    print("[D] Ask me every time (not recommended)\n")

    while True:
        choice = input("Your choice [A/B/C/D]: ").strip().upper()

        if choice == 'A':
            kb_path = DEFAULT_LOCATION
            break
        elif choice == 'B':
            kb_path = data_drive
            break
        elif choice == 'C':
            custom_path = input("Enter custom path: ").strip()
            kb_path = Path(custom_path)
            if not kb_path.is_absolute():
                print("⚠️  Please provide an absolute path.")
                continue
            break
        elif choice == 'D':
            save_config(DEFAULT_LOCATION, ask_every_time=True)
            print("\n✅ Configuration saved. You'll be prompted on every use.")
            return DEFAULT_LOCATION
        else:
            print("Invalid choice. Please enter A, B, C, or D.")

    # Initialize KB
    print(f"\n📁 Initializing KB at: {kb_path}")
    initialize_kb_structure(kb_path)
    save_config(kb_path)

    print("\n✅ Setup complete!")
    print(f"   KB location: {kb_path}")
    print(f"   Config file: {CONFIG_FILE}\n")

    return kb_path


def reconfigure():
    """Reconfigure KB location with migration support."""
    current_path = get_kb_path()

    if current_path is None:
        print("No existing configuration found.")
        return first_time_setup()

    print("\n" + "="*60)
    print("Reconfigure Figure KB Location")
    print("="*60)
    print(f"\nCurrent location: {current_path}")

    if current_path.exists():
        entry_count = count_entries(current_path)
        kb_size = get_disk_usage(current_path)
        print(f"Current KB size: {format_size(kb_size)} ({entry_count} entries)")
    else:
        print("⚠️  Current location does not exist!")

    print("\n[A] Keep current location")
    print("[B] Move to new location (with data)")
    print("[C] Start fresh at new location (archive old)")
    print("[D] Cancel\n")

    choice = input("Your choice [A/B/C/D]: ").strip().upper()

    if choice == 'A':
        print("Configuration unchanged.")
        return current_path

    elif choice in ['B', 'C']:
        new_path = input("Enter new KB path: ").strip()
        new_path = Path(new_path)

        if choice == 'B':
            mode = 'move'
        else:
            mode = 'archive'

        if migrate_kb(current_path, new_path, mode=mode):
            print("\n✅ Reconfiguration complete!")
            return new_path
        else:
            print("\n❌ Reconfiguration failed. Configuration unchanged.")
            return current_path

    else:
        print("Operation cancelled.")
        return current_path


def show_status():
    """Show current KB status and disk usage."""
    kb_path = get_kb_path()

    if kb_path is None:
        print("❌ KB not configured. Run first-time setup.")
        return

    print("\n" + "="*60)
    print("Figure KB Status")
    print("="*60)
    print(f"Location: {kb_path}")
    print(f"Config file: {CONFIG_FILE}\n")

    if not kb_path.exists():
        print("⚠️  KB directory does not exist!")
        return

    # KB stats
    entry_count = count_entries(kb_path)
    kb_size = get_disk_usage(kb_path)
    free_space = get_free_space(kb_path)

    print(f"Entries: {entry_count}")
    print(f"Disk usage: {format_size(kb_size)}")
    print(f"Free space: {format_size(free_space)}")

    # Warning if low space
    if free_space < 1_000_000_000:  # < 1 GB
        print(f"\n⚠️  WARNING: Only {format_size(free_space)} free space!")
        print("   Consider moving KB to a drive with more space.")
        print(f"   Run: {SCRIPT_DISPLAY} --reconfigure")

    print("\n" + "="*60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--setup":
            first_time_setup()
        elif command == "--reconfigure":
            reconfigure()
        elif command == "--status":
            show_status()
        elif command == "--get-path":
            path = get_kb_path()
            if path:
                print(path)
            else:
                print("NOT_CONFIGURED")
        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print(f"  {SCRIPT_DISPLAY} --setup         # First-time setup")
            print(f"  {SCRIPT_DISPLAY} --reconfigure   # Change location")
            print(f"  {SCRIPT_DISPLAY} --status        # Show current status")
            print(f"  {SCRIPT_DISPLAY} --get-path      # Print KB path")
    else:
        # Interactive mode
        print("\nFigure KB Location Manager\n")
        print("[1] First-time setup")
        print("[2] Reconfigure location")
        print("[3] Show status")
        print("[4] Exit\n")

        choice = input("Choose option [1-4]: ").strip()

        if choice == '1':
            first_time_setup()
        elif choice == '2':
            reconfigure()
        elif choice == '3':
            show_status()
        elif choice == '4':
            print("Goodbye!")
        else:
            print("Invalid choice.")
