"""Tests for download_log.py"""
import os
import pytest
from unittest.mock import patch

from src.download_log import (
    load_log,
    save_log,
    add_entry,
    update_entry,
    get_failed_entries,
    is_already_downloaded,
    format_log_table,
    _get_log_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_log_path(tmp_path):
    """Return a context manager that redirects log path to tmp_path."""
    log_file = str(tmp_path / "downloads.json")
    return patch("src.download_log._get_log_path", return_value=log_file)


def _make_entry(**kwargs):
    defaults = {
        "type": "movie",
        "title": "Test Movie",
        "year": "2024",
        "season": None,
        "episode": None,
        "m3u8_url": "https://example.com/test.m3u8",
        "output_path": "/tmp/test.mp4",
        "status": "success",
        "error": None,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadLog:
    def test_load_log_returns_empty_list_if_missing(self, tmp_path):
        with _patch_log_path(tmp_path):
            result = load_log()
        assert result == []


class TestAddAndLoad:
    def test_add_and_load_entry(self, tmp_path):
        entry = _make_entry(title="Inception", status="success")
        with _patch_log_path(tmp_path):
            add_entry(entry)
            entries = load_log()

        assert len(entries) == 1
        loaded = entries[0]
        assert loaded["title"] == "Inception"
        assert loaded["status"] == "success"
        # auto-generated fields
        assert "id" in loaded and loaded["id"]
        assert "timestamp" in loaded and loaded["timestamp"]


class TestUpdateEntry:
    def test_update_entry(self, tmp_path):
        entry = _make_entry(title="Dune", status="failed")
        with _patch_log_path(tmp_path):
            add_entry(entry)
            entries = load_log()
            entry_id = entries[0]["id"]

            update_entry(entry_id, {"status": "success", "error": None})
            updated_entries = load_log()

        assert updated_entries[0]["status"] == "success"
        assert updated_entries[0]["error"] is None


class TestGetFailedEntries:
    def test_get_failed_entries(self, tmp_path):
        with _patch_log_path(tmp_path):
            add_entry(_make_entry(title="Movie A", status="success"))
            add_entry(_make_entry(title="Movie B", status="failed"))
            add_entry(_make_entry(title="Movie C", status="failed"))

            failed = get_failed_entries()

        assert len(failed) == 2
        assert all(e["status"] == "failed" for e in failed)


class TestIsAlreadyDownloaded:
    def test_is_already_downloaded_true(self, tmp_path):
        # Create a file larger than 1MB
        big_file = tmp_path / "big.mp4"
        big_file.write_bytes(b"x" * 1_100_000)  # 1.1 MB
        assert is_already_downloaded(str(big_file)) is True

    def test_is_already_downloaded_false_missing(self, tmp_path):
        missing = str(tmp_path / "nonexistent.mp4")
        assert is_already_downloaded(missing) is False

    def test_is_already_downloaded_false_too_small(self, tmp_path):
        small_file = tmp_path / "small.mp4"
        small_file.write_bytes(b"x" * 500_000)  # 0.5 MB
        assert is_already_downloaded(str(small_file)) is False


class TestFormatLogTable:
    def test_format_log_table_returns_rich_table(self):
        from rich.table import Table
        entries = [
            _make_entry(title="Movie A", status="success"),
            _make_entry(title="Movie B", status="failed"),
            _make_entry(title="Series X", type="episode", season=1, episode=3, status="skipped"),
        ]
        # Add fake id/timestamp to simulate loaded entries
        for i, e in enumerate(entries):
            e["id"] = f"uuid-{i}"
            e["timestamp"] = "2026-08-04T10:00:00"

        table = format_log_table(entries)
        assert isinstance(table, Table)
        # Check column titles are present
        col_names = [col.header for col in table.columns]
        assert "No" in col_names
        assert "Status" in col_names
        assert "Title" in col_names
