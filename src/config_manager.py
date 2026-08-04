import os
from typing import Dict, Any

import src.db_manager as db_manager

CONFIG_FILE = "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "active_url": "https://z2.idlixku.com/",
    "target_urls": [
        {
            "id": 1,
            "name": "IDLIX Primary",
            "url": "https://z2.idlixku.com/"
        }
    ],
    "organize_mode": "separate",  # "separate" or "combined"
    "movies_dir": os.path.join(os.path.expanduser("~"), "Downloads", "Movies"),
    "series_dir": os.path.join(os.path.expanduser("~"), "Downloads", "TV Series"),
    "combined_dir": os.path.join(os.path.expanduser("~"), "Downloads"),
    "download_dir": os.path.join(os.path.expanduser("~"), "Downloads")
}


def normalize_url(url: str) -> str:
    """Normalize a given URL by trimming whitespace and ensuring http(s) scheme and trailing slash."""
    return db_manager.normalize_url(url)


def load_config(config_path: str = CONFIG_FILE, db_path: str | None = None) -> dict:
    """Load configuration from database."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    return db_manager.load_config(db_path=target_db)


def save_config(config: dict, config_path: str = CONFIG_FILE, db_path: str | None = None) -> None:
    """Save configuration dictionary to database."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    for k, v in config.items():
        if k != "target_urls" and isinstance(v, (str, int, float, bool)):
            db_manager.save_config_key(k, str(v), db_path=target_db)


def add_target_url(url: str, name: str = "", config_path: str = CONFIG_FILE, db_path: str | None = None) -> dict:
    """Add a target URL to configuration if not already present."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    return db_manager.add_target_url(url, name=name, db_path=target_db)


def set_active_url(url: str, config_path: str = CONFIG_FILE, db_path: str | None = None) -> dict:
    """Set the active URL in configuration."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    return db_manager.set_active_url(url, db_path=target_db)


def delete_target_url(url: str, config_path: str = CONFIG_FILE, db_path: str | None = None) -> dict:
    """Delete a target URL from configuration and update active URL if deleted target was active."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    return db_manager.delete_target_url(url, db_path=target_db)


def get_download_dir(config: dict, media_type: str = "movie") -> str:
    """Get the download directory based on media_type ('movie' or 'series') and organize_mode."""
    return db_manager.get_download_dir(config, media_type=media_type)


def set_download_dir(config: dict, new_dir: str, media_type: str = "movie", config_path: str = CONFIG_FILE, db_path: str | None = None) -> dict:
    """Set the download directory for specific media type or combined, and save to database."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    return db_manager.set_download_dir(config, new_dir, media_type=media_type, db_path=target_db)


def set_organize_mode(config: dict, mode: str, config_path: str = CONFIG_FILE, db_path: str | None = None) -> dict:
    """Set organize_mode ('separate' or 'combined') in config and save."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    return db_manager.set_organize_mode(config, mode, db_path=target_db)


