import json
import math
import os
import re
import shutil
import sys
from typing import Optional

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
