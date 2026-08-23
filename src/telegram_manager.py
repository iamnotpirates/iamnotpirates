import json
import math
import os
import re
import shutil
import subprocess
import sys
from typing import Optional

from src.db_manager import save_config_key

TELEGRAM_DIR = os.path.join(os.path.expanduser("~"), ".iamnotpirates", "telegram")
SESSION_PATH = os.path.join(TELEGRAM_DIR, "session")
TMP_SPLIT_DIR = os.path.join(os.path.expanduser("~"), ".iamnotpirates", "tmp_split")
PART_SIZE = int(1.9 * 1024 * 1024 * 1024)
APP_MARKER = "iamnotpirates"
CAPTION_VERSION = 1


def build_caption(meta: dict) -> str:
    title_line = f"🎬 {meta.get('title', '')}"
    year = meta.get("year")
    if year and year != "N/A":
        title_line += f" ({year})"
    kind = meta.get("kind", "")
    if kind == "subtitle":
        title_line = f"💬 {meta.get('filename', '')}"
    payload = {"app": APP_MARKER, "v": CAPTION_VERSION}
    payload.update(meta)
    return f"{title_line}\n\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"


def parse_caption(text: Optional[str]) -> Optional[dict]:
    if not text:
        return None
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("app") != APP_MARKER:
        return None
    return data


def split_file(path: str, part_size: int = PART_SIZE, tmp_dir: Optional[str] = None) -> list:
    if tmp_dir is None:
        tmp_dir = TMP_SPLIT_DIR
    os.makedirs(tmp_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    parts = []
    index = 1
    with open(path, "rb") as src:
        while True:
            chunk = src.read(part_size)
            if not chunk:
                break
            part_path = os.path.join(tmp_dir, f"{base}.part{index:03d}")
            with open(part_path, "wb") as dst:
                dst.write(chunk)
            parts.append(part_path)
            index += 1
    return parts


def merge_files(part_paths: list, output_path: str) -> None:
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "wb") as dst:
        for part in part_paths:
            with open(part, "rb") as src:
                shutil.copyfileobj(src, dst)


def cleanup_parts(part_paths: list) -> None:
    for part in part_paths:
        try:
            if os.path.exists(part):
                os.remove(part)
        except OSError:
            pass


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def matches_query(title: str, query: str) -> bool:
    needle = normalize_title(query)
    if not needle:
        return False
    return needle in normalize_title(title)


def backup_key(title: str, year, season, episode) -> str:
    return "|".join([
        normalize_title(title),
        str(year or ""),
        str(season if season is not None else ""),
        str(episode if episode is not None else ""),
    ])


def entry_backup_key(entry: dict) -> str:
    return backup_key(
        entry.get("title", ""),
        entry.get("year"),
        entry.get("season"),
        entry.get("episode"),
    )


def is_configured(config: dict) -> bool:
    return bool(config.get("tg_api_id")) and bool(config.get("tg_api_hash"))


def is_logged_in() -> bool:
    return os.path.exists(SESSION_PATH + ".session")


def get_destinations(config: dict) -> list:
    raw = config.get("tg_destinations") or '["saved"]'
    try:
        names = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        names = ["saved"]
    if not isinstance(names, list) or not names:
        names = ["saved"]
    destinations = []
    for name in names:
        if name == "saved":
            destinations.append({"type": "saved", "target": "me"})
        elif name == "channel":
            channel_id = (config.get("tg_channel_id") or "").strip()
            if channel_id:
                destinations.append({"type": "channel", "target": channel_id})
    return destinations


def ensure_telethon(console) -> bool:
    try:
        import telethon
        return True
    except ImportError:
        console.print("[yellow]Library 'telethon' belum terinstall.[/yellow]")
        import questionary
        answer = questionary.confirm("Install library telethon sekarang?").ask()
        if answer:
            subprocess.run([sys.executable, "-m", "pip", "install", "telethon"], check=False)
            try:
                import telethon
                return True
            except ImportError:
                pass
        console.print("[red]Telethon dibutuhkan untuk fitur ini.[/red]")
        return False


def create_client(config: dict):
    from telethon import TelegramClient
    return TelegramClient(
        SESSION_PATH,
        int(config["tg_api_id"]),
        config["tg_api_hash"],
    )


def login_flow(console, config: dict) -> bool:
    import questionary
    if not is_configured(config):
        console.print("[bold cyan]Panduan sekali saja:[/bold cyan] buka https://my.telegram.org "
                      "-> API development tools -> buat aplikasi -> salin api_id & api_hash.")
        api_id = questionary.text("Masukkan API ID:").ask()
        api_hash = questionary.text("Masukkan API Hash:").ask()
        if not api_id or not api_hash:
            console.print("[red]API ID/Hash wajib diisi.[/red]")
            return False
        api_id = api_id.strip()
        api_hash = api_hash.strip()
        if not api_id.isdigit():
            console.print("[red]API ID harus berupa angka.[/red]")
            return False
        save_config_key("tg_api_id", api_id)
        save_config_key("tg_api_hash", api_hash)
        config["tg_api_id"] = api_id
        config["tg_api_hash"] = api_hash

    phone = questionary.text("Nomor HP Telegram (contoh: +6281234567890):").ask()
    if not phone:
        return False
    os.makedirs(TELEGRAM_DIR, exist_ok=True)
    client = create_client(config)
    try:
        client.start(phone=lambda: phone)
        authorized = client.is_user_authorized()
    finally:
        client.disconnect()
    if authorized:
        console.print("[bold green]✓ Login Telegram berhasil.[/bold green]")
        return True
    console.print("[bold red]Login gagal / tidak selesai.[/bold red]")
    return False


def _document_name(msg) -> str:
    doc = getattr(msg, "document", None)
    if doc is None:
        return ""
    for attr in getattr(doc, "attributes", []) or []:
        name = getattr(attr, "file_name", None)
        if name:
            return name
    return ""


def scan_backups(client, destinations: list) -> list:
    items = []
    for destination in destinations:
        target = destination["target"]
        current = None
        for msg in client.iter_messages(target, reverse=True, limit=None):
            if getattr(msg, "document", None) is None:
                continue
            meta = parse_caption(getattr(msg, "message", None))
            if meta and meta.get("kind") == "video":
                current = {
                    "title": meta.get("title", ""),
                    "year": meta.get("year", ""),
                    "media_type": meta.get("media_type", "movie"),
                    "season": meta.get("season"),
                    "episode": meta.get("episode"),
                    "file_size": meta.get("file_size", 0),
                    "part_count": meta.get("part_count", 1),
                    "subtitles": list(meta.get("subtitles", [])),
                    "video_msg_ids": [msg.id],
                    "sub_msg_ids": [],
                    "chat": target,
                }
                items.append(current)
                continue
            if meta and meta.get("kind") == "subtitle":
                parent_title = meta.get("parent_title", "")
                for item in reversed(items):
                    if item["title"] == parent_title and item["chat"] == target:
                        item["sub_msg_ids"].append(msg.id)
                        name = _document_name(msg)
                        if name and name not in item["subtitles"]:
                            item["subtitles"].append(name)
                        break
                continue
            if current and len(current["video_msg_ids"]) < current.get("part_count", 1):
                current["video_msg_ids"].append(msg.id)
    return items
