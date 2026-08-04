import os
import pytest
import sqlite3
import rich.table
from src import db_manager


def test_init_db_creates_file_and_tables_and_seeds_defaults(tmp_path):
    db_file = tmp_path / "test_data.db"
    db_manager.init_db(db_path=str(db_file))

    assert db_file.exists()

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Verify tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "configs" in tables
    assert "target_urls" in tables
    assert "downloads" in tables

    # Verify default configs
    cursor.execute("SELECT key, value FROM configs")
    configs = dict(cursor.fetchall())
    assert configs["active_url"] == "https://z2.idlixku.com/"
    assert configs["organize_mode"] == "separate"
    assert configs["movies_dir"] == os.path.join(os.path.expanduser("~"), "Downloads", "Movies")
    assert configs["series_dir"] == os.path.join(os.path.expanduser("~"), "Downloads", "TV Series")
    assert configs["combined_dir"] == os.path.join(os.path.expanduser("~"), "Downloads")
    assert configs["download_dir"] == os.path.join(os.path.expanduser("~"), "Downloads")

    # Verify default target_urls
    cursor.execute("SELECT id, name, url FROM target_urls")
    urls = cursor.fetchall()
    assert len(urls) == 1
    assert urls[0] == (1, "IDLIX Primary", "https://z2.idlixku.com/")

    conn.close()


def test_load_config_and_update_operations(tmp_path):
    db_file = str(tmp_path / "test_data.db")
    db_manager.init_db(db_path=db_file)

    cfg = db_manager.load_config(db_path=db_file)
    assert cfg["active_url"] == "https://z2.idlixku.com/"
    assert len(cfg["target_urls"]) == 1
    assert cfg["target_urls"][0]["name"] == "IDLIX Primary"

    # Test set_organize_mode
    cfg = db_manager.set_organize_mode(cfg, "combined", db_path=db_file)
    assert cfg["organize_mode"] == "combined"
    reloaded = db_manager.load_config(db_path=db_file)
    assert reloaded["organize_mode"] == "combined"

    # Test set_download_dir in combined mode
    cfg = db_manager.set_download_dir(cfg, "/path/combined", media_type="movie", db_path=db_file)
    assert cfg["combined_dir"] == "/path/combined"
    assert cfg["download_dir"] == "/path/combined"
    assert db_manager.get_download_dir(cfg, "movie") == "/path/combined"

    # Test set_download_dir in separate mode
    cfg = db_manager.set_organize_mode(cfg, "separate", db_path=db_file)
    cfg = db_manager.set_download_dir(cfg, "/path/movies", media_type="movie", db_path=db_file)
    cfg = db_manager.set_download_dir(cfg, "/path/series", media_type="series", db_path=db_file)
    assert db_manager.get_download_dir(cfg, "movie") == "/path/movies"
    assert db_manager.get_download_dir(cfg, "series") == "/path/series"


def test_target_urls_operations(tmp_path):
    db_file = str(tmp_path / "test_data.db")
    db_manager.init_db(db_path=db_file)

    # Test add_target_url
    cfg = db_manager.add_target_url("https://newsite.com/", name="New Site", db_path=db_file)
    assert len(cfg["target_urls"]) == 2
    assert cfg["target_urls"][1]["url"] == "https://newsite.com/"
    assert cfg["target_urls"][1]["name"] == "New Site"

    # Test add duplicate target url does not create duplicate
    cfg = db_manager.add_target_url("https://newsite.com/", name="New Site Duplicate", db_path=db_file)
    assert len(cfg["target_urls"]) == 2

    # Test set_active_url
    cfg = db_manager.set_active_url("https://newsite.com/", db_path=db_file)
    assert cfg["active_url"] == "https://newsite.com/"

    # Test delete_target_url (when active URL is deleted, active_url falls back to first target_url)
    cfg = db_manager.delete_target_url("https://newsite.com/", db_path=db_file)
    assert len(cfg["target_urls"]) == 1
    assert cfg["active_url"] == "https://z2.idlixku.com/"


def test_download_log_operations(tmp_path):
    db_file = str(tmp_path / "test_data.db")
    db_manager.init_db(db_path=db_file)

    # Test add_entry with dict
    entry1 = {
        "media_type": "movie",
        "title": "Inception",
        "status": "success",
        "m3u8_url": "http://example.com/inception.m3u8",
        "output_path": "/path/Inception.mp4"
    }
    db_manager.add_entry(entry1, db_path=db_file)

    # Test add_entry with kwargs
    db_manager.add_entry(
        media_type="episode",
        title="Breaking Bad",
        season=1,
        episode=1,
        status="failed",
        error="Network error",
        db_path=db_file
    )

    logs = db_manager.load_log(db_path=db_file)
    assert len(logs) == 2
    assert logs[0]["title"] == "Inception"
    assert logs[0]["status"] == "success"
    assert logs[1]["title"] == "Breaking Bad"
    assert logs[1]["status"] == "failed"
    assert logs[1]["error"] == "Network error"

    failed = db_manager.get_failed_entries(db_path=db_file)
    assert len(failed) == 1
    assert failed[0]["title"] == "Breaking Bad"

    # Test update_entry
    failed_id = failed[0]["id"]
    db_manager.update_entry(failed_id, {"status": "success", "error": None}, db_path=db_file)

    failed_after = db_manager.get_failed_entries(db_path=db_file)
    assert len(failed_after) == 0

    logs_after = db_manager.load_log(db_path=db_file)
    updated_item = [item for item in logs_after if item["id"] == failed_id][0]
    assert updated_item["status"] == "success"
    assert updated_item["error"] is None

    # Test format_log_table
    table = db_manager.format_log_table(logs_after)
    assert isinstance(table, rich.table.Table)
