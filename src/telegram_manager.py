import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


def logout_session() -> None:
    for suffix in ("", ".session", ".session-journal"):
        path = SESSION_PATH + suffix
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


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


def upload_backup(client, file_path: str, sub_paths: list, meta: dict,
                  destinations: list, progress_callback=None,
                  tmp_dir: Optional[str] = None) -> dict:
    if not destinations:
        raise ValueError("Tujuan backup Telegram belum diatur.")
    primary_target = destinations[0]["target"]
    size = os.path.getsize(file_path)
    part_count = math.ceil(size / PART_SIZE) if size > PART_SIZE else 1
    video_meta = {
        "kind": "video",
        "title": meta.get("title", ""),
        "year": meta.get("year", ""),
        "media_type": meta.get("media_type", "movie"),
        "season": meta.get("season"),
        "episode": meta.get("episode"),
        "file_size": size,
        "part_count": part_count,
        "subtitles": [os.path.basename(p) for p in sub_paths],
    }
    caption = build_caption(video_meta)
    video_msg_ids = []
    part_files = []
    unique_tmp_dir = None
    try:
        if part_count == 1:
            msg = client.send_file(
                primary_target, file_path, caption=caption,
                force_document=False, supports_streaming=True,
                progress_callback=progress_callback,
            )
            video_msg_ids.append(msg.id)
        else:
            if tmp_dir is None:
                os.makedirs(TMP_SPLIT_DIR, exist_ok=True)
                unique_tmp_dir = tempfile.mkdtemp(prefix="up_", dir=TMP_SPLIT_DIR)
                split_dir = unique_tmp_dir
            else:
                split_dir = tmp_dir
            part_files = split_file(file_path, part_size=PART_SIZE, tmp_dir=split_dir)
            for index, part_path in enumerate(part_files):
                msg = client.send_file(
                    primary_target, part_path,
                    caption=caption if index == 0 else "",
                    force_document=True,
                    progress_callback=progress_callback,
                )
                video_msg_ids.append(msg.id)
    finally:
        cleanup_parts(part_files)
        if unique_tmp_dir is not None:
            shutil.rmtree(unique_tmp_dir, ignore_errors=True)

    sub_msg_ids = []
    for sub_path in sub_paths:
        sub_meta = {
            "kind": "subtitle",
            "filename": os.path.basename(sub_path),
            "parent_title": video_meta["title"],
        }
        smsg = client.send_file(
            primary_target, sub_path, caption=build_caption(sub_meta),
            force_document=True,
        )
        sub_msg_ids.append(smsg.id)

    forwarded_to = []
    for destination in destinations[1:]:
        client.forward_messages(destination["target"], video_msg_ids + sub_msg_ids, primary_target)
        forwarded_to.append(destination["target"])

    return {"video_msg_ids": video_msg_ids, "sub_msg_ids": sub_msg_ids, "forwarded_to": forwarded_to}


def collect_local_entries() -> list:
    from src.db_manager import load_log
    best = {}
    for entry in load_log():
        if entry.get("status") != "success":
            continue
        path = entry.get("output_path") or ""
        if not path or not os.path.exists(path):
            continue
        key = entry_backup_key(entry)
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", entry.get("title", ""))
        candidate = {
            "title": entry.get("title", ""),
            "year": entry.get("year") or (year_match.group(1) if year_match else ""),
            "media_type": entry.get("media_type", "movie"),
            "season": entry.get("season"),
            "episode": entry.get("episode"),
            "output_path": path,
            "file_size": os.path.getsize(path),
            "backed": False,
            "_ts": entry.get("timestamp", ""),
            "key": key,
        }
        if key not in best or candidate["_ts"] >= best[key]["_ts"]:
            best[key] = candidate
    result = list(best.values())
    for entry in result:
        entry.pop("_ts", None)
    return result


def mark_backed_entries(local_entries: list, scanned_items: list) -> list:
    scanned_keys = {
        backup_key(it.get("title", ""), it.get("year"), it.get("season"), it.get("episode"))
        for it in scanned_items
    }
    marked = []
    for entry in local_entries:
        clone = dict(entry)
        clone["backed"] = clone.get("key") in scanned_keys
        marked.append(clone)
    return marked


def build_restore_target(config: dict, item: dict) -> tuple:
    from src.config_manager import get_download_dir
    from src.downloader import format_tv_paths
    title = item.get("title", "Unknown")
    year = str(item.get("year") or "").strip()
    if year.upper() == "N/A":
        year = ""
    if item.get("media_type") == "episode":
        base_dir = get_download_dir(config, media_type="series")
        season_dir, base_filename = format_tv_paths(
            title, year, item.get("season") or 1, item.get("episode") or 1, base_dir
        )
        return season_dir, f"{base_filename}.mp4"
    base_dir = get_download_dir(config, media_type="movie")
    folder = f"{title} ({year})" if year else title
    return os.path.join(base_dir, folder), f"{folder}.mp4"


def restore_backup(client, item: dict, config: dict, progress_callback=None) -> str:
    target_dir, filename = build_restore_target(config, item)
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(TMP_SPLIT_DIR, exist_ok=True)
    chat = item.get("chat", "me")

    messages = client.get_messages(chat, ids=list(item["video_msg_ids"]))
    part_files = []
    for message in messages:
        downloaded = client.download_media(
            message, file=TMP_SPLIT_DIR, progress_callback=progress_callback
        )
        part_files.append(downloaded)

    output_path = os.path.join(target_dir, filename)
    merging_path = output_path + ".merging"
    merge_files(part_files, merging_path)

    expected_size = item.get("file_size", 0)
    actual_size = os.path.getsize(merging_path)
    if actual_size != expected_size:
        try:
            os.remove(merging_path)
        except OSError:
            pass
        raise IOError(
            f"Verifikasi ukuran gagal untuk '{filename}': "
            f"diharapkan {expected_size}, didapat {actual_size}. "
            f"File rusak tidak jadi disimpan; part sementara tetap disimpan di {TMP_SPLIT_DIR}."
        )

    os.replace(merging_path, output_path)

    cleanup_parts(part_files)

    sub_ids = list(item.get("sub_msg_ids") or [])
    if sub_ids:
        sub_messages = client.get_messages(chat, ids=sub_ids)
        for sub_message in sub_messages:
            client.download_media(sub_message, file=target_dir)

    return output_path
