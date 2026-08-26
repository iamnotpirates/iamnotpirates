import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Optional

from src.db_manager import save_config_key
from src.sevenzip_manager import ensure_7z, compress_archive, extract_archive

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
    if meta.get("media_type") == "episode":
        season = meta.get("season")
        episode = meta.get("episode")
        se = "S" + (f"{int(season):02d}" if season is not None else "??")
        se += "E" + (f"{int(episode):02d}" if episode is not None else "??")
        title_line += f" {se}"
    kind = meta.get("kind", "")
    if kind == "subtitle":
        title_line = f"💬 {meta.get('filename', '')}"

    payload = {"app": APP_MARKER, "v": CAPTION_VERSION}
    payload.update(meta)

    # Telegram caption limit is 1024 chars. Stay under 1000.
    caption = f"{title_line}\n\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    if len(caption) > 1000:
        # Step 1: Truncate subtitle list to max 3 items or empty if needed
        subs = payload.get("subtitles")
        if isinstance(subs, list) and len(subs) > 3:
            payload["subtitles"] = subs[:3]
            caption = f"{title_line}\n\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"

        if len(caption) > 1000 and isinstance(payload.get("subtitles"), list):
            payload["subtitles"] = []
            caption = f"{title_line}\n\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"

        # Step 2: Truncate filename if present
        if len(caption) > 1000 and payload.get("filename"):
            payload["filename"] = payload["filename"][:50] + "..."
            caption = f"{title_line}\n\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"

        # Step 3: Truncate title in payload & title_line
        if len(caption) > 1000:
            if len(title_line) > 100:
                title_line = title_line[:97] + "..."
            if len(str(payload.get("title", ""))) > 100:
                payload["title"] = str(payload["title"])[:97] + "..."
            caption = f"{title_line}\n\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"

        # Final safety net: strictly cut caption at 1024
        if len(caption) > 1024:
            caption = caption[:1024]

    return caption


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


def tg_connect(client):
    return client.connect()


def tg_disconnect(client):
    return client.disconnect()


def logout_session() -> None:
    for suffix in ("", ".session", ".session-journal"):
        path = SESSION_PATH + suffix
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def parse_destination_input(raw: str) -> list:
    tokens = [t.strip() for t in re.split(r"[,\s]+", (raw or "").strip()) if t.strip()]
    valid = []
    for token in tokens:
        lowered = token.lower()
        link = re.search(r"t\.me/c/(\d+)(?:/(\d+))?(?:/(\d+))?", lowered)
        if link:
            chat, second, third = link.group(1), link.group(2), link.group(3)
            group_id = f"-100{chat}"
            if third is not None and second is not None:
                valid.append(f"group:{group_id}:{second}")
            else:
                valid.append(f"group:{group_id}")
        elif lowered == "saved":
            valid.append("saved")
        elif lowered.startswith("channel:") and lowered[8:].strip():
            valid.append(f"channel:{token[8:].strip()}")
        elif lowered.startswith("group:"):
            parts = token.split(":")
            group_id = parts[1].strip() if len(parts) > 1 else ""
            topic = parts[2].strip() if len(parts) > 2 else ""
            if group_id and (not topic or topic.isdigit()):
                valid.append(f"group:{group_id}:{topic}" if topic else f"group:{group_id}")
    return valid or ["saved"]


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
        token = str(name).strip()
        lowered = token.lower()
        if lowered == "saved":
            destinations.append({"type": "saved", "target": "me", "topic": None})
        elif lowered == "channel":
            channel_id = (config.get("tg_channel_id") or "").strip()
            if channel_id:
                destinations.append({"type": "channel", "target": channel_id, "topic": None})
        elif lowered.startswith("channel:") and token[8:].strip():
            destinations.append({"type": "channel", "target": token[8:].strip(), "topic": None})
        elif lowered.startswith("group:") and len(token.split(":")) >= 2 and token.split(":")[1].strip():
            parts = token.split(":")
            target = parts[1].strip()
            topic_text = parts[2].strip() if len(parts) > 2 else ""
            topic = int(topic_text) if topic_text.isdigit() else None
            destinations.append({"type": "group", "target": target, "topic": topic})
    return destinations


def ensure_telethon(console) -> bool:
    try:
        import telethon.sync
        return True
    except ImportError:
        console.print("[yellow]Library 'telethon' belum terinstall.[/yellow]")
        import questionary
        answer = questionary.confirm("Install library telethon sekarang?").ask()
        if answer:
            try:
                subprocess.run(["uv", "pip", "install", "telethon"], check=False)
            except OSError:
                pass
            try:
                import telethon.sync
                return True
            except ImportError:
                pass
            console.print("[dim]Jalankan manual: uv pip install telethon (atau pip install telethon)[/dim]")
        console.print("[red]Telethon dibutuhkan untuk fitur ini.[/red]")
        return False


def create_client(config: dict):
    try:
        import telethon.sync
    except ImportError:
        pass
    from telethon import TelegramClient
    return TelegramClient(
        SESSION_PATH,
        int(config["tg_api_id"]),
        config["tg_api_hash"],
        connection_retries=10,
        retry_delay=2,
        auto_reconnect=True,
    )


def _notify_upload_retry(describe: str, attempt: int, max_retries: int, exc: Exception) -> None:
    try:
        from rich.console import Console
        Console().print(
            f"[bold yellow]⚠️ {describe}: koneksi gagal "
            f"({type(exc).__name__}) — mencoba ulang {attempt}/{max_retries}...[/bold yellow]"
        )
    except Exception:
        print(f"⚠️ {describe}: koneksi gagal — mencoba ulang {attempt}/{max_retries}...")


def _is_fatal_rpc_error(exc: Exception) -> bool:
    err_name = type(exc).__name__
    fatal_patterns = (
        "Forbidden", "Private", "Banned", "Invalid", "Closed", "Deleted", "TooLong"
    )
    return any(p in err_name for p in fatal_patterns)


def _send_file_with_retry(client, target, file_to_send, max_retries: int = 3,
                          describe: str = "", **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return client.send_file(target, file_to_send, **kwargs)
        except (OSError, ConnectionError, Exception) as exc:
            if _is_fatal_rpc_error(exc) or attempt >= max_retries:
                raise
            if describe:
                _notify_upload_retry(describe, attempt + 1, max_retries, exc)
            time.sleep(1 * attempt)
            is_conn = getattr(client, "is_connected", None)
            if is_conn and not is_conn():
                try:
                    tg_connect(client)
                except Exception:
                    pass


def login_flow(console, config: dict) -> bool:
    import questionary
    if not is_configured(config):
        console.print("[bold cyan]Panduan sekali saja:[/bold cyan] buka https://my.telegram.org "
                      "-> API development tools -> buat aplikasi -> salin api_id & api_hash.")
        api_id = questionary.text("Masukkan API ID:").ask()
        api_hash = questionary.password("Masukkan API Hash:").ask()
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
        tg_disconnect(client)
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


def resolve_target(client, target):
    if not target:
        return "me"
    if isinstance(target, str):
        if target.lower() in ("me", "saved"):
            return "me"
        stripped = target.lstrip("-")
        if stripped.isdigit():
            target = int(target)
    get_entity = getattr(client, "get_entity", None)
    if get_entity is None:
        return target
    try:
        return get_entity(target)
    except (ValueError, TypeError):
        get_dialogs = getattr(client, "get_dialogs", None)
        if get_dialogs is not None:
            try:
                get_dialogs()
                return get_entity(target)
            except Exception:
                pass
        return target


def scan_backups(client, destinations: list) -> list:
    items = []
    for destination in destinations:
        raw_target = destination["target"]
        target = resolve_target(client, raw_target)
        topic = destination.get("topic")
        reply_to = int(topic) if topic and str(topic).isdigit() else None
        current = None
        for msg in client.iter_messages(target, reverse=True, limit=None,
                                        reply_to=reply_to):
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
    primary = destinations[0]
    primary_target = resolve_target(client, primary["target"])
    primary_topic = int(primary["topic"]) if primary.get("topic") and str(primary["topic"]).isdigit() else primary.get("topic")

    def _archive_base(meta: dict) -> str:
        base = meta.get("title", "backup")
        year = str(meta.get("year") or "").strip()
        if year and year != "N/A":
            base += f" ({year})"
        if meta.get("media_type") == "episode":
            season, episode = meta.get("season"), meta.get("episode")
            se = "S" + (f"{int(season):02d}" if season is not None else "??")
            se += "E" + (f"{int(episode):02d}" if episode is not None else "??")
            base += f" {se}"
        return re.sub(r'[<>:"/\\|?*]', "_", base)

    staging_dir = tmp_dir
    unique_tmp_dir = None
    if staging_dir is None:
        os.makedirs(TMP_SPLIT_DIR, exist_ok=True)
        staging_dir = tempfile.mkdtemp(prefix="up_", dir=TMP_SPLIT_DIR)
        unique_tmp_dir = staging_dir
    os.makedirs(staging_dir, exist_ok=True)
    sz_path = ensure_7z()
    if not sz_path:
        raise RuntimeError("7zr tidak tersedia; gagal menyiapkan arsip backup.")
    archive_name = _archive_base(meta) + ".7z"
    archive_path = os.path.join(staging_dir, archive_name)
    compress_archive(sz_path, archive_path, [file_path] + list(sub_paths))

    size = os.path.getsize(archive_path)
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
        "archive": True,
        "filename": os.path.basename(file_path),
    }
    caption = build_caption(video_meta)
    video_msg_ids = []
    sub_msg_ids = []
    part_files = []
    try:
        if part_count > 1:
            split_dir = staging_dir
            part_files = split_file(archive_path, part_size=PART_SIZE, tmp_dir=split_dir)

        item_title = meta.get("title", os.path.basename(file_path))
        if meta.get("season") and meta.get("episode"):
            item_title += f" S{int(meta['season']):02d}E{int(meta['episode']):02d}"

        def _send_video(target, reply_to, record):
            ids = []
            if part_count == 1:
                msg = _send_file_with_retry(
                    client, target, archive_path, caption=caption,
                    force_document=True,
                    progress_callback=progress_callback, reply_to=reply_to,
                    describe=item_title,
                )
                ids.append(msg.id)
            else:
                for index, part_path in enumerate(part_files):
                    part_desc = f"{item_title} (part {index + 1}/{part_count})"
                    msg = _send_file_with_retry(
                        client, target, part_path,
                        caption=caption if index == 0 else "",
                        force_document=True,
                        progress_callback=progress_callback, reply_to=reply_to,
                        describe=part_desc,
                    )
                    ids.append(msg.id)
            if record:
                video_msg_ids.extend(ids)
            return ids

        def _send_subs(target, reply_to):
            return []

        _send_video(primary_target, primary_topic, record=True)
        sub_msg_ids = _send_subs(primary_target, primary_topic)

        forwarded_to = []
        all_primary_ids = video_msg_ids + sub_msg_ids
        for destination in destinations[1:]:
            target = resolve_target(client, destination["target"])
            topic = int(destination["topic"]) if destination.get("topic") and str(destination["topic"]).isdigit() else destination.get("topic")
            if topic is not None:
                _send_video(target, topic, record=False)
                _send_subs(target, topic)
            else:
                client.forward_messages(target, all_primary_ids, primary_target)
                forwarded_to.append(destination["target"])

        return {"video_msg_ids": video_msg_ids, "sub_msg_ids": sub_msg_ids, "forwarded_to": forwarded_to}
    finally:
        cleanup_parts(part_files)
        try:
            os.remove(archive_path)
        except OSError:
            pass
        if unique_tmp_dir is not None:
            shutil.rmtree(unique_tmp_dir, ignore_errors=True)

TEST_MESSAGE = "✅ iamnotpirates — tes tujuan backup (boleh dihapus)"


def format_destination(dest: dict) -> str:
    if dest["type"] == "saved":
        return "saved"
    base = f"{dest['type']}:{dest['target']}"
    return f"{base}:{dest['topic']}" if dest.get("topic") else base


def test_destinations(client, destinations: list) -> list:
    results = []
    for dest in destinations:
        entry = {"destination": format_destination(dest), "ok": False, "detail": ""}
        try:
            target = resolve_target(client, dest["target"])
            title = (getattr(target, "title", None)
                     or getattr(target, "username", None) or str(target))
            kwargs = {}
            if dest.get("topic"):
                kwargs["reply_to"] = int(dest["topic"])
            msg = client.send_message(target, TEST_MESSAGE, **kwargs)
            entry["ok"] = True
            entry["detail"] = f"{title} · msg_id={getattr(msg, 'id', '?')}"
        except Exception as exc:
            entry["detail"] = str(exc)
        results.append(entry)
    return results


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


VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".webm", ".mov"}
_SE_EP_RE = re.compile(r"\b[Ss](\d{1,2})\s?[Ee](\d{1,3})\b")
_YEAR_RE = re.compile(r"\b(19\d\d|20\d\d)\b")


def parse_media_filename(path: str) -> Optional[dict]:
    if os.path.splitext(os.path.basename(path))[1].lower() not in VIDEO_EXTS:
        return None
    stem = os.path.splitext(os.path.basename(path))[0]
    se = _SE_EP_RE.search(stem)
    year = ""
    if se:
        title_part = stem[:se.start()]
        media_type = "episode"
        season, episode = int(se.group(1)), int(se.group(2))
    else:
        ym = _YEAR_RE.search(stem)
        if ym:
            title_part = stem[:ym.start()]
            year = ym.group(1)
        else:
            title_part = stem
        media_type = "movie"
        season = episode = None
    if not year:
        parent = os.path.dirname(path)
        for ancestor in (parent, os.path.dirname(parent)):
            parent_year = _YEAR_RE.search(os.path.basename(ancestor))
            if parent_year:
                year = parent_year.group(1)
                break
    title = re.sub(r"[\s._\-–(]+$", "", title_part).replace(".", " ").strip()
    title = re.sub(r"\s{2,}", " ", title)
    if not title:
        return None
    return {"title": title, "year": year, "media_type": media_type,
            "season": season, "episode": episode}


def collect_folder_entries(scan_dirs: list) -> list:
    best = {}
    for scan_dir in scan_dirs or []:
        if not os.path.isdir(scan_dir):
            continue
        for root, _dirs, files in os.walk(scan_dir):
            depth = os.path.relpath(root, scan_dir).count(os.sep)
            if depth > 3:
                _dirs[:] = []
                continue
            for fname in files:
                if os.path.splitext(fname)[1].lower() not in VIDEO_EXTS:
                    continue
                full = os.path.join(root, fname)
                meta = parse_media_filename(full)
                if meta is None:
                    continue
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                key = backup_key(meta["title"], meta["year"], meta["season"], meta["episode"])
                candidate = dict(meta, output_path=full, file_size=size,
                                 backed=False, key=key)
                if key not in best or size > best[key]["file_size"]:
                    best[key] = candidate
    return list(best.values())


def merge_local_entries(log_entries: list, folder_entries: list) -> list:
    merged = {e.get("key"): dict(e) for e in log_entries}
    for entry in folder_entries:
        merged.setdefault(entry.get("key"), dict(entry))
    return list(merged.values())


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
    if item.get("archive"):
        return restore_archive_backup(client, item, config, progress_callback)
    target_dir, filename = build_restore_target(config, item)
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(TMP_SPLIT_DIR, exist_ok=True)
    chat_raw = item.get("chat", "me")
    chat = resolve_target(client, chat_raw)

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


def restore_archive_backup(client, item: dict, config: dict, progress_callback=None) -> str:
    """Restore an archive-based backup: merge parts, verify, extract via 7z."""
    target_dir, _filename = build_restore_target(config, item)
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(TMP_SPLIT_DIR, exist_ok=True)
    chat = resolve_target(client, item.get("chat", "me"))

    messages = client.get_messages(chat, ids=list(item["video_msg_ids"]))
    part_files = []
    for message in messages:
        downloaded = client.download_media(
            message, file=TMP_SPLIT_DIR, progress_callback=progress_callback
        )
        part_files.append(downloaded)

    merging_path = os.path.join(TMP_SPLIT_DIR,
                                (item.get("filename") or "archive.7z") + ".merging")
    merge_files(part_files, merging_path)

    expected_size = item.get("file_size", 0)
    actual_size = os.path.getsize(merging_path)
    if actual_size != expected_size:
        raise IOError(
            f"Verifikasi ukuran arsip gagal untuk '{item.get('title', '?')}': "
            f"diharapkan {expected_size}, didapat {actual_size}. "
            f"Part sementara tetap disimpan di {TMP_SPLIT_DIR}."
        )

    sz_path = ensure_7z()
    if not sz_path:
        raise RuntimeError("7zr tidak tersedia; tidak bisa mengekstrak backup.")
    extract_archive(sz_path, merging_path, target_dir)
    os.remove(merging_path)
    cleanup_parts(part_files)

    video_name = item.get("filename") or ""
    if video_name and os.path.exists(os.path.join(target_dir, video_name)):
        return os.path.join(target_dir, video_name)
    files = sorted(
        (os.path.join(target_dir, f) for f in os.listdir(target_dir)),
        key=os.path.getsize, reverse=True,
    )
    return files[0] if files else target_dir
