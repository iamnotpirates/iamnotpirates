"""
download_log.py — Persistent SQLite log for all download attempts (wrapper around db_manager).
"""

import os
from typing import Optional
from rich.table import Table

import src.db_manager as db_manager


def _get_log_path() -> str:
    """Returns legacy path to downloads log file."""
    return os.path.join(os.path.expanduser("~"), ".iamnotpirates", "downloads.json")



def load_log(db_path: Optional[str] = None) -> list[dict]:
    """Load and return all entries from database."""
    return db_manager.load_log(db_path=db_path)


def save_log(entries: list[dict]) -> None:
    """Save full entries list to log file (legacy compatibility, no-op or handled by db_manager)."""
    pass


def add_entry(entry: dict | None = None, db_path: Optional[str] = None, **kwargs) -> None:
    """Append a new entry using db_manager."""
    db_manager.add_entry(entry=entry, db_path=db_path, **kwargs)


def update_entry(entry_id: str, updates: dict, db_path: Optional[str] = None) -> None:
    """Update a specific entry by id with the given updates dict using db_manager."""
    db_manager.update_entry(entry_id, updates, db_path=db_path)


def get_failed_entries(db_path: Optional[str] = None) -> list[dict]:
    """Return all entries where status == 'failed'."""
    return db_manager.get_failed_entries(db_path=db_path)


def delete_log_entry(entry_id: str, db_path: Optional[str] = None) -> None:
    """Delete a specific log entry by ID."""
    db_manager.delete_log_entry(entry_id, db_path=db_path)


def clear_all_logs(db_path: Optional[str] = None) -> None:
    """Delete all log entries."""
    db_manager.clear_all_logs(db_path=db_path)


def is_already_downloaded(output_path: str, min_size_bytes: int = 1_000_000) -> bool:
    """
    Return True if:
    - File exists at output_path, AND
    - File size >= min_size_bytes (1MB default)
    """
    if not os.path.exists(output_path):
        return False
    return os.path.getsize(output_path) >= min_size_bytes


def format_log_table(entries: list[dict]) -> Table:
    """Return a Rich Table of entries."""
    return db_manager.format_log_table(entries)

