"""
download_log.py — Persistent JSON log for all download attempts.

Log file location: ~/.iamnotpirates/downloads.json
"""

import json
import os
import uuid
from datetime import datetime

from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_log_path() -> str:
    """Returns the path to the downloads log file."""
    return os.path.join(os.path.expanduser("~"), ".iamnotpirates", "downloads.json")


# ---------------------------------------------------------------------------
# Core I/O
# ---------------------------------------------------------------------------


def load_log() -> list[dict]:
    """Load and return all entries from the log file. Returns [] if missing."""
    path = _get_log_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def save_log(entries: list[dict]) -> None:
    """Save full entries list to log file using atomic write."""
    path = _get_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Entry operations
# ---------------------------------------------------------------------------


def add_entry(entry: dict) -> None:
    """Append a new entry. Generates id and timestamp automatically if missing."""
    entry = dict(entry)  # avoid mutating caller's dict
    if not entry.get("id"):
        entry["id"] = str(uuid.uuid4())
    if not entry.get("timestamp"):
        entry["timestamp"] = datetime.now().isoformat()
    entries = load_log()
    entries.append(entry)
    save_log(entries)


def update_entry(entry_id: str, updates: dict) -> None:
    """Update a specific entry by id with the given updates dict."""
    entries = load_log()
    for entry in entries:
        if entry.get("id") == entry_id:
            entry.update(updates)
            break
    save_log(entries)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def get_failed_entries() -> list[dict]:
    """Return all entries where status == 'failed'."""
    return [e for e in load_log() if e.get("status") == "failed"]


def is_already_downloaded(output_path: str, min_size_bytes: int = 1_000_000) -> bool:
    """
    Return True if:
    - File exists at output_path, AND
    - File size >= min_size_bytes (1MB default)
    """
    if not os.path.exists(output_path):
        return False
    return os.path.getsize(output_path) >= min_size_bytes


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------


def format_log_table(entries: list[dict]) -> Table:
    """
    Return a Rich Table of entries with columns:
    No | Type | Title | Season | Episode | Status | Timestamp

    Color coding:
    - success → green
    - failed  → red
    - skipped → yellow
    """
    STATUS_COLORS = {
        "success": "green",
        "failed": "red",
        "skipped": "yellow",
    }

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("No", style="dim", width=4, justify="right")
    table.add_column("Type", width=8)
    table.add_column("Title")
    table.add_column("Season", justify="center", width=7)
    table.add_column("Episode", justify="center", width=8)
    table.add_column("Status", width=9)
    table.add_column("Timestamp", width=20)

    for i, entry in enumerate(entries, start=1):
        status = entry.get("status", "")
        color = STATUS_COLORS.get(status, "white")
        status_text = Text(status, style=color)

        season = entry.get("season")
        episode = entry.get("episode")

        table.add_row(
            str(i),
            entry.get("type", ""),
            entry.get("title", ""),
            str(season) if season is not None else "-",
            str(episode) if episode is not None else "-",
            status_text,
            entry.get("timestamp", ""),
        )

    return table
