import json
import os
from typing import Dict, Any

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
    "download_dir": os.path.join(os.path.expanduser("~"), "Downloads")
}


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


def load_config(config_path: str = CONFIG_FILE) -> dict:
    """Load configuration from JSON file. Create default config if file does not exist."""
    if not os.path.exists(config_path):
        save_config(DEFAULT_CONFIG, config_path)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(config: dict, config_path: str = CONFIG_FILE) -> None:
    """Save configuration dictionary to a JSON file."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def add_target_url(url: str, name: str = "", config_path: str = CONFIG_FILE) -> dict:
    """Add a target URL to configuration if not already present."""
    config = load_config(config_path)
    url = normalize_url(url)
    if not url:
        return config

    existing_urls = [item["url"] for item in config.get("target_urls", [])]
    if url not in existing_urls:
        new_id = len(config.get("target_urls", [])) + 1
        display_name = name.strip() if name and name.strip() else f"Target #{new_id}"
        config.setdefault("target_urls", []).append({
            "id": new_id,
            "name": display_name,
            "url": url
        })
        save_config(config, config_path)
    return config


def set_active_url(url: str, config_path: str = CONFIG_FILE) -> dict:
    """Set the active URL in configuration."""
    config = load_config(config_path)
    url = normalize_url(url)
    config["active_url"] = url
    save_config(config, config_path)
    return config


def delete_target_url(url: str, config_path: str = CONFIG_FILE) -> dict:
    """Delete a target URL from configuration and update active URL if deleted target was active."""
    config = load_config(config_path)
    url = normalize_url(url)
    config["target_urls"] = [item for item in config.get("target_urls", []) if item["url"] != url]
    if config.get("active_url") == url:
        config["active_url"] = config["target_urls"][0]["url"] if config["target_urls"] else ""
    save_config(config, config_path)
    return config


def get_download_dir(config: dict) -> str:
    """Get the download directory from config, defaulting to user's Downloads directory."""
    return config.get("download_dir", os.path.join(os.path.expanduser("~"), "Downloads"))


def set_download_dir(config: dict, new_dir: str, config_path: str = CONFIG_FILE) -> dict:
    """Set the download directory in config and save to file."""
    config["download_dir"] = new_dir
    save_config(config, config_path)
    return config

