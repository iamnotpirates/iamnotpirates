import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich.table import Table
from rich.text import Text

DB_FILE_PATH = os.path.join(os.path.expanduser("~"), ".iamnotpirates", "data", "data.db")


def normalize_url(url: str) -> str:
    """Normalize a given URL by trimming whitespace and ensuring http(s) scheme and trailing slash."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not url.endswith("/"):
        url += "/"
    return url


def get_db_path(db_path: Optional[str] = None) -> str:
    """Return the absolute path to the database file."""
    if db_path:
        return db_path
    return DB_FILE_PATH


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a sqlite3 Connection to the target database file."""
    path = get_db_path(db_path)
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn



def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and seed default config / target URLs if empty."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS target_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id TEXT PRIMARY KEY,
            media_type TEXT,
            title TEXT,
            season INTEGER,
            episode INTEGER,
            status TEXT,
            m3u8_url TEXT,
            output_path TEXT,
            error TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            url TEXT PRIMARY KEY,
            title TEXT,
            type TEXT,
            timestamp TEXT
        )
    """)

    # Check if page_url column exists in downloads, if not ADD it
    try:
        cursor.execute("SELECT page_url FROM downloads LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE downloads ADD COLUMN page_url TEXT")

    conn.commit()

    # Seed default configs if missing
    default_configs = {
        "active_url": "https://z2.idlixku.com/",
        "organize_mode": "separate",
        "movies_dir": os.path.join(os.path.expanduser("~"), "Downloads", "Movies"),
        "series_dir": os.path.join(os.path.expanduser("~"), "Downloads", "TV Series"),
        "combined_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
        "download_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
        "tg_api_id": "",
        "tg_api_hash": "",
        "tg_auto_backup": "0",
        "tg_destinations": '["saved"]',
        "tg_channel_id": "",
    }

    for k, v in default_configs.items():
        cursor.execute("INSERT OR IGNORE INTO configs (key, value) VALUES (?, ?)", (k, v))

    # Seed default target url if target_urls is empty
    cursor.execute("SELECT COUNT(*) FROM target_urls")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO target_urls (id, name, url) VALUES (?, ?, ?)",
            (1, "IDLIX Primary", "https://z2.idlixku.com/")
        )

    conn.commit()
    conn.close()


def load_config(db_path: Optional[str] = None) -> dict:
    """Load configuration dictionary from SQLite database."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM configs")
    cfg = dict(cursor.fetchall())

    cursor.execute("SELECT id, name, url FROM target_urls ORDER BY id ASC")
    target_urls = [{"id": row["id"], "name": row["name"], "url": row["url"]} for row in cursor.fetchall()]
    cfg["target_urls"] = target_urls

    conn.close()
    return cfg


def save_config_key(key: str, value: str, db_path: Optional[str] = None) -> None:
    """Save or update a single configuration key-value pair."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_download_dir(config: dict, media_type: str = "movie") -> str:
    """Get the download directory based on media_type ('movie' or 'series') and organize_mode."""
    organize_mode = config.get("organize_mode", "separate")
    if organize_mode == "combined":
        return config.get("combined_dir", config.get("download_dir", os.path.join(os.path.expanduser("~"), "Downloads")))

    if media_type == "series":
        return config.get("series_dir", os.path.join(os.path.expanduser("~"), "Downloads", "TV Series"))
    return config.get("movies_dir", os.path.join(os.path.expanduser("~"), "Downloads", "Movies"))


def set_download_dir(config: dict, new_dir: str, media_type: str = "movie", db_path: Optional[str] = None) -> dict:
    """Set the download directory for specific media type or combined, and save to DB."""
    organize_mode = config.get("organize_mode", "separate")
    if organize_mode == "combined":
        config["combined_dir"] = new_dir
        config["download_dir"] = new_dir
        save_config_key("combined_dir", new_dir, db_path)
        save_config_key("download_dir", new_dir, db_path)
    elif media_type == "series":
        config["series_dir"] = new_dir
        save_config_key("series_dir", new_dir, db_path)
    else:
        config["movies_dir"] = new_dir
        save_config_key("movies_dir", new_dir, db_path)

    return config


def set_organize_mode(config: dict, mode: str, db_path: Optional[str] = None) -> dict:
    """Set organize_mode ('separate' or 'combined') in config and save to DB."""
    if mode in ("separate", "combined"):
        config["organize_mode"] = mode
        save_config_key("organize_mode", mode, db_path)
    return config


def add_target_url(url: str, name: str = "", db_path: Optional[str] = None) -> dict:
    """Add a target URL to database if not already present."""
    url = normalize_url(url)
    if not url:
        return load_config(db_path)

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM target_urls WHERE url = ?", (url,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT COUNT(*) FROM target_urls")
        cnt = cursor.fetchone()[0]
        display_name = name.strip() if name and name.strip() else f"Target #{cnt + 1}"
        cursor.execute("INSERT INTO target_urls (name, url) VALUES (?, ?)", (display_name, url))
        conn.commit()

    conn.close()
    return load_config(db_path)


def set_active_url(url: str, db_path: Optional[str] = None) -> dict:
    """Set active URL in DB and return updated config."""
    url = normalize_url(url)
    save_config_key("active_url", url, db_path)
    return load_config(db_path)


def delete_target_url(url: str, db_path: Optional[str] = None) -> dict:
    """Delete a target URL from database and update active URL if deleted target was active."""
    url = normalize_url(url)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM target_urls WHERE url = ?", (url,))
    conn.commit()

    cursor.execute("SELECT value FROM configs WHERE key = 'active_url'")
    row = cursor.fetchone()
    active_url = row["value"] if row else ""

    if active_url == url:
        cursor.execute("SELECT url FROM target_urls ORDER BY id ASC LIMIT 1")
        first_row = cursor.fetchone()
        new_active = first_row["url"] if first_row else ""
        cursor.execute("INSERT OR REPLACE INTO configs (key, value) VALUES ('active_url', ?)", (new_active,))
        conn.commit()

    conn.close()
    return load_config(db_path)


def add_entry(entry: Optional[dict] = None, db_path: Optional[str] = None, **kwargs) -> None:
    """Append a new download log entry to SQLite table."""
    init_db(db_path)
    data = dict(entry) if entry else {}
    data.update(kwargs)

    entry_id = data.get("id") or str(uuid.uuid4())
    media_type = data.get("media_type") or data.get("type", "movie")
    title = data.get("title", "")
    season = data.get("season")
    episode = data.get("episode")
    status = data.get("status", "skipped")
    m3u8_url = data.get("m3u8_url", "")
    output_path = data.get("output_path", "")
    error = data.get("error")
    timestamp = data.get("timestamp") or datetime.now().isoformat()
    page_url = data.get("page_url", "")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO downloads (id, media_type, title, season, episode, status, m3u8_url, output_path, error, timestamp, page_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (entry_id, media_type, title, season, episode, status, m3u8_url, output_path, error, timestamp, page_url))

    conn.commit()
    conn.close()


def update_entry(entry_id: str, updates: dict, db_path: Optional[str] = None) -> None:
    """Update a specific entry in downloads table by id."""
    if not updates:
        return

    init_db(db_path)
    fields = []
    values = []
    for k, v in updates.items():
        if k == "type":
            k = "media_type"
        fields.append(f"{k} = ?")
        values.append(v)


    values.append(entry_id)

    sql = f"UPDATE downloads SET {', '.join(fields)} WHERE id = ?"

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()
    conn.close()


def load_log(db_path: Optional[str] = None) -> list[dict]:
    """Load and return all download entries as a list of dicts."""
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM downloads ORDER BY timestamp ASC")
    rows = cursor.fetchall()

    entries = []
    for row in rows:
        item = dict(row)
        item["type"] = item["media_type"]
        entries.append(item)

    conn.close()
    return entries


def get_failed_entries(db_path: Optional[str] = None) -> list[dict]:
    """Return all entries where status == 'failed'."""
    entries = load_log(db_path)
    return [e for e in entries if e.get("status") == "failed"]


def delete_log_entry(entry_id: str, db_path: Optional[str] = None) -> None:
    """Delete a specific log entry by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM downloads WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def clear_all_logs(db_path: Optional[str] = None) -> None:
    """Delete all log entries."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM downloads")
    conn.commit()
    conn.close()


def format_log_table(entries: list[dict]) -> Table:
    """Return a Rich Table of entries matching legacy download_log output format."""
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
            entry.get("type", entry.get("media_type", "")),
            entry.get("title", ""),
            str(season) if season is not None else "-",
            str(episode) if episode is not None else "-",
            status_text,
            entry.get("timestamp", ""),
        )

    return table


def add_to_cart(url: str, title: str, media_type: str, db_path: Optional[str] = None) -> bool:
    """Add an item to the cart. Returns True if successfully added, False if it already exists."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO cart (url, title, type, timestamp) VALUES (?, ?, ?, ?)",
            (url, title, media_type, datetime.now().isoformat())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_cart_items(db_path: Optional[str] = None) -> list[dict]:
    """Get all items in the cart."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT url, title, type, timestamp FROM cart ORDER BY timestamp ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def remove_from_cart(url: str, db_path: Optional[str] = None) -> None:
    """Remove an item from the cart by its URL."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE url = ?", (url,))
    conn.commit()
    conn.close()


def clear_cart(db_path: Optional[str] = None) -> None:
    """Clear all items from the cart."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart")
    conn.commit()
    conn.close()


def format_cart_table(items: list[dict]) -> Table:
    """Return a Rich Table of cart items."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("No", style="dim", width=4, justify="right")
    table.add_column("Type", width=12)
    table.add_column("Title")
    table.add_column("URL")
    table.add_column("Date Added", width=20)

    for i, item in enumerate(items, start=1):
        ts = item.get("timestamp", "")
        if ts:
            try:
                ts = ts.split(".")[0].replace("T", " ")
            except Exception:
                pass
        table.add_row(
            str(i),
            item.get("type", ""),
            item.get("title", ""),
            item.get("url", ""),
            ts,
        )
    return table

