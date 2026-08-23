# Telegram Backup Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menambahkan Telegram sebagai platform backup/restore film & episode (manual + otomatis), pencarian hybrid IDLIX+Telegram, dan penghapusan file lokal ber-pengaman.

**Architecture:** Modul baru `src/telegram_manager.py` membungkus semua interaksi Telethon (login session, scan caption, upload/split/forward, restore/merge). Telegram adalah sumber data langsung — tanpa tabel indeks lokal; hanya penambahan config keys di tabel `configs`. Integrasi UI lewat menu baru `📡 Telegram Backup`, kolom Sumber pada search, dan hook auto-backup pasca-download sukses.

**Tech Stack:** Python 3.9+, Telethon (MTProto user-account), SQLite (configs existing), Rich, questionary, pytest.

**Spec:** `docs/superpowers/specs/2026-08-23-telegram-backup-design.md`

## Global Constraints

- Library akun-user MTProto: `telethon`. DILARANG memakai Bot API (batas 50MB).
- Batas upload per pesan 2GB → part maksimum `int(1.9 * 1024**3)` byte.
- Session disimpan di `~/.iamnotpirates/telegram/session`; folder temp split `~/.iamnotpirates/tmp_split`.
- Tanpa tabel SQLite baru; hanya config keys: `tg_api_id`, `tg_api_hash`, `tg_auto_backup` (`"0"`/`"1"`), `tg_destinations` (JSON array, elemen pertama = tujuan utama), `tg_channel_id`.
- Caption metadata: blok ```json dengan field `"app": "iamnotpirates"`, `"v": 1`; `kind` ∈ `"video"` | `"subtitle"`.
- Semua label UI dual-language pola `Label ID / Label EN`; tabel memakai Rich; prompt memakai questionary.
- Scan/pencarian Telegram selalu tampilkan spinner `📡 Mencari di Telegram...`.
- Kegagalan auto-backup TIDAK boleh mengubah status sukses unduhan.
- Jalankan test dengan `uv run pytest`.
- Gaya kode: tanpa komentar kecuali diminta; ikuti pola modul existing (`db_manager.py`, `playwright_manager.py`).

---

### Task 1: Dependensi telethon + config keys seeding

**Files:**
- Modify: `pyproject.toml:7-16` (dependencies array)
- Modify: `src/db_manager.py:96-103` (default_configs dict)
- Test: `tests/test_db_manager.py`

**Interfaces:**
- Consumes: `init_db(db_path)`, `load_config(db_path)` (existing).
- Produces: config keys `tg_api_id=""`, `tg_api_hash=""`, `tg_auto_backup="0"`, `tg_destinations='["saved"]'`, `tg_channel_id=""` selalu ada hasil `init_db()`.

- [ ] **Step 1: Write the failing test**

Tambahkan di akhir `tests/test_db_manager.py`:

```python
def test_init_db_seeds_telegram_config_keys(tmp_path):
    import sqlite3
    db = str(tmp_path / "t.db")
    init_db(db_path=db)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM configs WHERE key LIKE 'tg_%'")
    rows = dict(cursor.fetchall())
    conn.close()
    assert rows["tg_api_id"] == ""
    assert rows["tg_api_hash"] == ""
    assert rows["tg_auto_backup"] == "0"
    assert rows["tg_destinations"] == '["saved"]'
    assert rows["tg_channel_id"] == ""


def test_load_config_contains_telegram_defaults(tmp_path):
    db = str(tmp_path / "t.db")
    cfg = load_config(db_path=db)
    assert cfg.get("tg_auto_backup") == "0"
    assert cfg.get("tg_destinations") == '["saved"]'
```

(Sesuaikan import di bagian atas file bila `load_config` belum diimport.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db_manager.py -k telegram -v`
Expected: FAIL (KeyError / assertion) karena keys belum di-seed.

- [ ] **Step 3: Write minimal implementation**

Di `pyproject.toml` dependencies tambahkan (urut alfabetis dalam list yang ada):

```toml
    "telethon>=1.36.0",
```

Di `src/db_manager.py` `default_configs` tambahkan:

```python
        "tg_api_id": "",
        "tg_api_hash": "",
        "tg_auto_backup": "0",
        "tg_destinations": '["saved"]',
        "tg_channel_id": "",
```

Lalu jalankan `uv lock` agar `uv.lock` ikut ter-update.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_db_manager.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/db_manager.py tests/test_db_manager.py
git commit -m "feat: add telethon dependency and telegram config keys"
```

---

### Task 2: Caption build/parse roundtrip

**Files:**
- Create: `src/telegram_manager.py`
- Test: `tests/test_telegram_manager.py`

**Interfaces:**
- Consumes: tidak ada (fungsi murni).
- Produces:
  - `APP_MARKER: str` (`"iamnotpirates"`), `CAPTION_VERSION: int` (`1`)
  - `build_caption(meta: dict) -> str`
  - `parse_caption(text: str | None) -> dict | None` (None bila bukan caption milik app / JSON rusak)
  - Konvensi meta video minimal: `{"kind":"video","title":str,"year":str,"media_type":"movie"|"episode","season":int|None,"episode":int|None,"file_size":int,"part_count":int,"subtitles":list[str]}`
  - Meta subtitle: `{"kind":"subtitle","filename":str,"parent_title":str}`

- [ ] **Step 1: Write the failing test**

Buat `tests/test_telegram_manager.py`:

```python
from src.telegram_manager import build_caption, parse_caption


def test_build_caption_contains_human_line_and_json_block():
    meta = {"kind": "video", "title": "Judul Film", "year": "2024",
            "media_type": "movie", "season": None, "episode": None,
            "file_size": 1000, "part_count": 1, "subtitles": []}
    caption = build_caption(meta)
    assert caption.startswith("🎬 Judul Film (2024)")
    assert '"app": "iamnotpirates"' in caption.replace("'iamnotpirates'", '"iamnotpirates"').replace('": "', '": "') or '"app"' in caption
    assert "```json" in caption


def test_parse_caption_roundtrip_video():
    meta = {"kind": "video", "title": "Judul Film", "year": "2024",
            "media_type": "movie", "season": None, "episode": None,
            "file_size": 12345, "part_count": 2, "subtitles": ["a.srt"]}
    parsed = parse_caption(build_caption(meta))
    assert parsed == {"app": "iamnotpirates", "v": 1, **meta}


def test_parse_caption_roundtrip_subtitle():
    meta = {"kind": "subtitle", "filename": "Film.id.srt", "parent_title": "Film"}
    parsed = parse_caption(build_caption(meta))
    assert parsed["kind"] == "subtitle"
    assert parsed["filename"] == "Film.id.srt"


def test_parse_caption_returns_none_for_foreign_or_broken_text():
    assert parse_caption("just a normal caption") is None
    assert parse_caption("") is None
    assert parse_caption(None) is None
    assert parse_caption("```json\n{broken\n```") is None
    assert parse_caption('```json\n{"app": "other"}\n```') is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.telegram_manager'`.

- [ ] **Step 3: Write minimal implementation**

Buat `src/telegram_manager.py`:

```python
import json
import math
import os
import re
import shutil
import sys
from typing import Callable, Optional

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_manager.py tests/test_telegram_manager.py
git commit -m "feat: add caption build/parse for telegram backup metadata"
```

---

### Task 3: Split/merge file + human_size

**Files:**
- Modify: `src/telegram_manager.py`
- Modify: `src/ui.py` (helper `human_size`)
- Test: `tests/test_telegram_manager.py`, `tests/test_ui.py`

**Interfaces:**
- Consumes: konstanta `TMP_SPLIT_DIR`, `PART_SIZE` dari Task 2.
- Produces:
  - `split_file(path: str, part_size: int = PART_SIZE, tmp_dir: str | None = None) -> list[str]` — daftar path part berurutan.
  - `merge_files(part_paths: list[str], output_path: str) -> None`
  - `cleanup_parts(part_paths: list[str]) -> None` (abaikan error per-file)
  - `human_size(num_bytes: float) -> str` di `src/ui.py`.

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_telegram_manager.py`:

```python
import os
from src.telegram_manager import split_file, merge_files, cleanup_parts, PART_SIZE


def test_split_and_merge_small_file_roundtrip(tmp_path):
    src = tmp_path / "movie.mp4"
    payload = os.urandom(5000)
    src.write_bytes(payload)

    parts = split_file(str(src), part_size=2000, tmp_dir=str(tmp_path / "parts"))
    assert len(parts) == 3
    assert all(os.path.exists(p) for p in parts)

    out = tmp_path / "merged.mp4"
    merge_files(parts, str(out))
    assert out.read_bytes() == payload


def test_split_exact_multiple_makes_no_empty_part(tmp_path):
    src = tmp_path / "f.bin"
    src.write_bytes(b"x" * 4000)
    parts = split_file(str(src), part_size=2000, tmp_dir=str(tmp_path / "p2"))
    assert len(parts) == 2


def test_merge_creates_missing_parent_dirs(tmp_path):
    p1 = tmp_path / "a.part1"
    p1.write_bytes(b"hello ")
    p2 = tmp_path / "a.part2"
    p2.write_bytes(b"world")
    out = tmp_path / "deep" / "nested" / "out.txt"
    merge_files([str(p1), str(p2)], str(out))
    assert out.read_bytes() == b"hello world"


def test_cleanup_parts_removes_files_and_tolerates_missing(tmp_path):
    p1 = tmp_path / "x.part1"
    p1.write_bytes(b"a")
    cleanup_parts([str(p1), str(tmp_path / "ghost.part2")])
    assert not p1.exists()


def test_part_size_below_two_gb_limit():
    assert 0 < PART_SIZE < 2 * 1024 * 1024 * 1024
```

Tambahkan ke `tests/test_ui.py`:

```python
from src.ui import human_size


def test_human_size_units():
    assert human_size(500) == "500.0 B"
    assert human_size(2048) == "2.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"
    assert human_size(3 * 1024 * 1024 * 1024) == "3.0 GB"
    assert human_size(2 * 1024 * 1024 * 1024 * 1024) == "2.0 TB"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py tests/test_ui.py -k "split or merge or cleanup or part_size or human" -v`
Expected: FAIL — ImportError / AttributeError.

- [ ] **Step 3: Write minimal implementation**

Di `src/telegram_manager.py` tambahkan:

```python
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
```

Di `src/ui.py` tambahkan:

```python
def human_size(num_bytes: float) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py tests/test_ui.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_manager.py src/ui.py tests/test_telegram_manager.py tests/test_ui.py
git commit -m "feat: add file split/merge and human_size helpers"
```

---

### Task 4: Matching judul & kunci identitas backup

**Files:**
- Modify: `src/telegram_manager.py`
- Test: `tests/test_telegram_manager.py`

**Interfaces:**
- Consumes: tidak ada.
- Produces:
  - `normalize_title(s: str) -> str`
  - `matches_query(title: str, query: str) -> bool`
  - `backup_key(title: str, year, season, episode) -> str` — kunci unik identitas item; dipakai mencocokkan file lokal vs hasil scan.
  - `entry_backup_key(entry: dict) -> str` — convenience untuk entri log `downloads` (menerima dict dengan key `title`, `year` opsional, `season`, `episode`).

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_telegram_manager.py`:

```python
from src.telegram_manager import normalize_title, matches_query, backup_key, entry_backup_key


def test_normalize_title_strips_case_and_symbols():
    assert normalize_title("Judul: Film-Bagus! 2024") == "judulfilmbagus2024"


def test_matches_query_substring_normalized():
    assert matches_query("The Last of Us (2023)", "last of us")
    assert matches_query("Avengers Endgame", "avengers")
    assert not matches_query("Batman", "superman")


def test_matches_query_empty_query_is_false():
    assert not matches_query("Anything", "")
    assert not matches_query("", "x")


def test_backup_key_consistent_across_season_episode():
    a = backup_key("Film X", "2024", None, None)
    b = entry_backup_key({"title": "Film X", "year": "2024"})
    assert a == b
    ep_a = backup_key("Series Y", "2023", 2, 5)
    ep_b = entry_backup_key({"title": "Series Y", "year": "2023", "season": 2, "episode": 5})
    assert ep_a == ep_b
    assert ep_a != a


def test_entry_backup_key_handles_none_year():
    assert entry_backup_key({"title": "Z"}) == backup_key("Z", None, None, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py -k "normalize or matches or backup_key" -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write minimal implementation**

Di `src/telegram_manager.py` tambahkan:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_manager.py tests/test_telegram_manager.py
git commit -m "feat: add title matching and backup identity key helpers"
```

---

### Task 5: Config/session helpers — is_ready, get_destinations, ensure_telethon, login_flow

**Files:**
- Modify: `src/telegram_manager.py`
- Test: `tests/test_telegram_manager.py`

**Interfaces:**
- Consumes: `save_config_key`, `load_config` dari `src/db_manager.py`; konstanta `SESSION_PATH`, `TELEGRAM_DIR`.
- Produces:
  - `is_configured(config: dict) -> bool` (api_id & api_hash terisi)
  - `is_logged_in() -> bool` (file session ada)
  - `get_destinations(config: dict) -> list[dict]` — misal `[{"type":"saved","target":"me"},{"type":"channel","target":-100xxx}]`
  - `ensure_telethon(console) -> bool` — cek import telethon; tawarkan pip install jika gagal (pola `playwright_manager.ensure_playwright`)
  - `create_client(config: dict)` — kembalikan `TelegramClient(SESSION_PATH, api_id, api_hash)` (lazy import)
  - `login_flow(console, config) -> bool` — panduan my.telegram.org → simpan api keys → minta nomor HP → `client.start(phone=...)` hingga authorized → disconnect → True

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_telegram_manager.py`:

```python
import sys
from unittest.mock import MagicMock, patch

from src.telegram_manager import (
    is_configured, is_logged_in, get_destinations,
    ensure_telethon, create_client,
)


def test_is_configured_requires_both_keys():
    assert is_configured({"tg_api_id": "1", "tg_api_hash": "h"})
    assert not is_configured({"tg_api_id": "", "tg_api_hash": "h"})
    assert not is_configured({})


def test_is_logged_in_checks_session_file(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "SESSION_PATH", str(tmp_path / "session"))
    assert not tm.is_logged_in()
    (tmp_path / "session.session").write_text("x")
    assert tm.is_logged_in()


def test_get_destinations_saved_only_default():
    dests = get_destinations({"tg_destinations": '["saved"]'})
    assert dests == [{"type": "saved", "target": "me"}]


def test_get_destinations_channel_requires_channel_id():
    assert get_destinations({
        "tg_destinations": '["saved","channel"]', "tg_channel_id": "@mychan"
    }) == [
        {"type": "saved", "target": "me"},
        {"type": "channel", "target": "@mychan"},
    ]
    assert get_destinations({"tg_destinations": '["channel"]', "tg_channel_id": ""}) == []
    assert get_destinations({"tg_destinations": "bukan-json"}) == [{"type": "saved", "target": "me"}]


def test_ensure_telethon_true_when_importable():
    assert ensure_telethon(MagicMock())


def test_create_client_passes_credentials(monkeypatch):
    import src.telegram_manager as tm
    fake_ctor = MagicMock()
    monkeypatch.setitem(sys.modules, "telethon", MagicMock(TelegramClient=fake_ctor))
    client = create_client({"tg_api_id": "123", "tg_api_hash": "hash"})
    fake_ctor.assert_called_once_with(tm.SESSION_PATH, 123, "hash")
    assert client is fake_ctor.return_value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py -k "configured or logged_in or destinations or ensure_telethon or create_client" -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write minimal implementation**

Di `src/telegram_manager.py` tambahkan:

```python
import subprocess


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
```

Tambahkan import atas file: `from src.db_manager import save_config_key`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_manager.py tests/test_telegram_manager.py
git commit -m "feat: add telegram config/session helpers and login flow"
```

---

### Task 6: scan_backups — baca indeks langsung dari Telegram

**Files:**
- Modify: `src/telegram_manager.py`
- Test: `tests/test_telegram_manager.py`

**Interfaces:**
- Consumes: `parse_caption` (Task 2), `get_destinations` (Task 5).
- Produces:
  - `scan_backups(client, destinations: list[dict]) -> list[dict]` — sinkron (iterasi sync-mode Telethon `client.iter_messages(target, reverse=True)`).
  - Item hasil scan (dipakai restore/list/search):
    ```python
    {
      "title": str, "year": str, "media_type": str,
      "season": int | None, "episode": int | None,
      "file_size": int, "part_count": int,
      "subtitles": list[str],           # nama file .srt dari metadata
      "video_msg_ids": list[int],       # urut part 1..N
      "sub_msg_ids": list[int],
      "chat": <primary target>,
    }
    ```
  - `_document_name(msg) -> str` — nama file dokumen Telethon (atribut `document.attributes` kelas `DocumentAttributeFilename`) atau `""`.

Aturan pengelompokan (ascending/reverse=True): pesan `kind=video` membuka item baru; dokumen berikutnya TANPA caption app milik item berjalan selama `len(video_msg_ids) < part_count`; pesan `kind=subtitle` dilampirkan ke item dengan `parent_title` sama (terakhir yang cocok).

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_telegram_manager.py`:

```python
from src.telegram_manager import scan_backups, build_caption


class FakeDoc:
    def __init__(self, attributes):
        self.attributes = attributes


class FakeAttr:
    def __init__(self, file_name):
        self.file_name = file_name


class FakeMsg:
    def __init__(self, msg_id, caption=None, file_name=None):
        self.id = msg_id
        self.message = caption
        self.document = FakeDoc([FakeAttr(file_name)]) if file_name else FakeDoc([])


VIDEO_META = {"kind": "video", "title": "Film A", "year": "2024", "media_type": "movie",
              "season": None, "episode": None, "file_size": 300, "part_count": 2,
              "subtitles": ["Film A.id.srt"]}
SUB_META = {"kind": "subtitle", "filename": "Film A.id.srt", "parent_title": "Film A"}


class FakeClient:
    def __init__(self, messages_by_target):
        self._messages_by_target = messages_by_target
        self.iter_calls = []

    def iter_messages(self, target, reverse=None, limit=None):
        self.iter_calls.append((target, reverse, limit))
        return iter(self._messages_by_target.get(target, []))


DESTS = [{"type": "saved", "target": "me"}]
CHANNEL_MSGS_VIDEO_META = dict(VIDEO_META)


def test_scan_groups_parts_subs_and_skips_foreign():
    messages = [
        FakeMsg(1, caption=build_caption(SUB_META), file_name="Film A.id.srt"),
        FakeMsg(2),  # part 2 tanpa caption app
        FakeMsg(3, caption=build_caption(VIDEO_META), file_name="Film A.part001"),
        FakeMsg(99, caption="caption orang lain"),  # dilewati
    ]
    client = FakeClient({"me": messages})
    items = scan_backups(client, DESTS)
    assert client.iter_calls == [("me", True, None)]
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "Film A"
    assert item["video_msg_ids"] == [3, 2]
    assert item["sub_msg_ids"] == [1]
    assert item["subtitles"] == ["Film A.id.srt"]
    assert item["chat"] == "me"


def test_scan_all_destinations_no_dedupe_between_targets():
    ch_meta = dict(VIDEO_META)
    msgs_me = [FakeMsg(3, caption=build_caption(ch_meta), file_name="p1")]
    msgs_channel = [FakeMsg(55, caption=build_caption(ch_meta), file_name="p1")]
    client = FakeClient({"me": msgs_me, "@c": msgs_channel})
    items = scan_backups(client, [
        {"type": "saved", "target": "me"},
        {"type": "channel", "target": "@c"},
    ])
    chats = sorted(it["chat"] for it in items)
    assert chats == ["@c", "me"]
    assert len(items) == 2


def test_scan_returns_empty_without_destination():
    assert scan_backups(FakeClient({}), []) == []


def test_scan_subtitle_before_any_video_is_ignored():
    messages = [FakeMsg(1, caption=build_caption(SUB_META), file_name="x.srt")]
    assert scan_backups(FakeClient({"me": messages}), DESTS) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py -k scan -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write minimal implementation**

Di `src/telegram_manager.py` tambahkan:

```python
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
```

Catatan desain (masuk batasan yang disetujui):
- Scan mengiterasi SEMUA tujuan yang dikonfigurasi. Salinan hasil forward memiliki caption JSON identik, jadi judul sama muncul sebagai baris terpisah per tujuan — ini fitur: kalau restore dari satu tujuan gagal (pesan terhapus), baris duplikatnya di tujuan lain tetap bisa dipilih.
- Pesan asing yang tersisip di antara dua part dapat memutus pengelompokan; verifikasi ukuran saat restore menjadi jaring pengaman (Task 8).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py -k scan -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_manager.py tests/test_telegram_manager.py
git commit -m "feat: add telegram backup scanner reading captions live"
```

---

### Task 7: upload_backup — split, upload, forward

**Files:**
- Modify: `src/telegram_manager.py`
- Test: `tests/test_telegram_manager.py`

**Interfaces:**
- Consumes: `build_caption`, `split_file`, `cleanup_parts`, `get_destinations`, `PART_SIZE`.
- Produces:
  - `upload_backup(client, file_path: str, sub_paths: list[str], meta: dict, destinations: list[dict], progress_callback=None) -> dict`
    - `meta` TANPA `kind/file_size/part_count` — fungsi ini menambahkannya.
    - Return: `{"video_msg_ids": [...], "sub_msg_ids": [...], "forwarded_to": [<targets>]}`.
  - Aturan: tujuan utama = `destinations[0]`; part >1 dikirim `force_document=True` dengan caption hanya di part pertama; file tunggal dikirim sebagai video streaming (`force_document=False, supports_streaming=True`); subtitle selalu document dengan caption `kind=subtitle`; forward sekali ke tiap tujuan sekunder.

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_telegram_manager.py`:

```python
import json
from unittest.mock import MagicMock

from src.telegram_manager import upload_backup


class RecordingClient:
    """Fake Telethon client yang merekam send_file/forward_messages."""

    def __init__(self):
        self.sent = []
        self.forwards = []
        self._id = 100

    def send_file(self, target, path, caption="", force_document=False,
                  supports_streaming=False, progress_callback=None):
        self._id += 1
        self.sent.append({
            "target": target, "path": path, "caption": caption,
            "force_document": force_document, "supports_streaming": supports_streaming,
        })
        msg = MagicMock()
        msg.id = self._id
        return msg

    def forward_messages(self, target, ids, from_peer):
        self.forwards.append((target, list(ids), from_peer))
        return [MagicMock() for _ in ids]


def _make_big_file(tmp_path, size):
    path = tmp_path / "Big Movie.mp4"
    path.write_bytes(b"x" * size)
    return str(path)


META = {"title": "Film B", "year": "2025", "media_type": "movie",
        "season": None, "episode": None, "subtitles": []}
DESTS = [{"type": "saved", "target": "me"}, {"type": "channel", "target": "@c"}]


def test_upload_single_part_streams_and_forwards(tmp_path):
    src = _make_big_file(tmp_path, 1000)
    client = RecordingClient()
    result = upload_backup(client, src, [], dict(META), DESTS)
    assert len(client.sent) == 1
    sent = client.sent[0]
    assert sent["force_document"] is False
    assert sent["supports_streaming"] is True
    assert '"kind": "video"' in sent["caption"].replace("'", '"')
    assert '"part_count": 1' in sent["caption"].replace("'", '"')
    assert result["video_msg_ids"] == [101]
    assert result["forwarded_to"] == ["@c"]
    assert client.forwards == [("@c", [101], "me")]


def test_upload_multi_part_splits_captions_first_part_only_and_cleans_temp(tmp_path):
    src = _make_big_file(tmp_path, 2500)
    parts_dir = tmp_path / "parts"
    client = RecordingClient()
    result = upload_backup(client, src, [], dict(META),
                           [DESTS[0]], progress_callback=None, tmp_dir=str(parts_dir))
    assert len(client.sent) == 2
    caps = [s["caption"] for s in client.sent]
    first_meta = json.loads(caps[0].split("```json")[1].strip().strip("`"))
    assert first_meta["part_count"] == 2
    assert first_meta["file_size"] == 2500
    assert caps[1] == ""
    assert all(s["force_document"] for s in client.sent)
    remaining = list(parts_dir.glob("*")) if parts_dir.exists() else []
    assert remaining == []
    assert len(result["video_msg_ids"]) == 2


def test_upload_subtitles_as_documents_with_marker_caption(tmp_path):
    src = _make_big_file(tmp_path, 100)
    sub = tmp_path / "Film B.id.srt"
    sub.write_text("SUB")
    client = RecordingClient()
    upload_backup(client, src, [str(sub)], dict(META), [DESTS[0]])
    assert len(client.sent) == 2
    sub_sent = client.sent[1]
    assert sub_sent["force_document"] is True
    assert '"kind": "subtitle"' in sub_sent["caption"].replace("'", '"')
    assert "Film B.id.srt" in sub_sent["caption"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py -k upload -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write minimal implementation**

Di `src/telegram_manager.py` tambahkan:

```python
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
    try:
        if part_count == 1:
            msg = client.send_file(
                primary_target, file_path, caption=caption,
                force_document=False, supports_streaming=True,
                progress_callback=progress_callback,
            )
            video_msg_ids.append(msg.id)
        else:
            part_files = split_file(file_path, tmp_dir=tmp_dir)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_manager.py tests/test_telegram_manager.py
git commit -m "feat: add telegram upload with split and auto-forward"
```

---

### Task 8: restore_backup + build_restore_target

**Files:**
- Modify: `src/telegram_manager.py`
- Test: `tests/test_telegram_manager.py`

**Interfaces:**
- Consumes: `merge_files`, `cleanup_parts`, `TMP_SPLIT_DIR`; dari `src/main.py`: `format_tv_paths` (sudah ada, signature `format_tv_paths(clean_title, year, season_num, episode_num, target_dir) -> (dir, base_filename)`); `get_download_dir` dari `src/config_manager.py`.
- Produces:
  - `build_restore_target(config: dict, item: dict) -> tuple[str, str]` — `(target_dir, filename)`; movie → `<movies_dir>/<Title (Year)>/<Title>.mp4`; episode → pakai `format_tv_paths` → `<series_dir>/<Title (Year)>/Season XX/<Title> SxxEyy.mp4`. Import `format_tv_paths` DI DALAM fungsi (hindari circular import `main ↔ telegram_manager`).
  - `restore_backup(client, item: dict, config: dict, progress_callback=None) -> str` — path file utuh hasil restore.
  - Verifikasi ukuran: jika hasil merge ≠ `file_size` → raise `IOError`, part temp DIBIARKAN (tidak dihapus).

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_telegram_manager.py`:

```python
import pytest

from src.telegram_manager import build_restore_target, restore_backup


CONFIG = {
    "organize_mode": "separate",
    "movies_dir": "/tmp-test/Movies",
    "series_dir": "/tmp-test/Series",
}

MOVIE_ITEM = {
    "title": "Film A", "year": "2024", "media_type": "movie",
    "season": None, "episode": None, "file_size": 11, "part_count": 2,
    "subtitles": ["Film A.id.srt"],
    "video_msg_ids": [31, 32], "sub_msg_ids": [33], "chat": "me",
}


def test_build_restore_target_movie_uses_movies_dir():
    target_dir, filename = build_restore_target(CONFIG, MOVIE_ITEM)
    assert target_dir.replace("\\", "/").endswith("/tmp-test/Movies/Film A (2024)")
    assert filename == "Film A.mp4"


def test_build_restore_target_episode_uses_series_paths():
    item = dict(MOVIE_ITEM, media_type="episode", title="Series Z",
                season=2, episode=5, year="2023")
    target_dir, filename = build_restore_target(CONFIG, item)
    assert "Series Z (2023)" in target_dir.replace("\\", "/")
    assert "Season 02" in target_dir.replace("\\", "/")
    assert filename == "Series Z S02E05.mp4"


class RestoreFakeClient:
    def __init__(self, payloads_by_id):
        self.payloads = payloads_by_id
        self.downloaded = []

    def get_messages(self, chat, ids):
        wrapped = []
        for msg_id in ids:
            m = MagicMock()
            m.id = msg_id
            wrapped.append(m)
        return wrapped

    def download_media(self, message, file=None, progress_callback=None):
        msg_id = message.id
        out = os.path.join(file, f"{msg_id}.bin") if os.path.isdir(str(file)) else str(file)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(self.payloads[msg_id])
        self.downloaded.append(out)
        return out


def test_restore_merges_parts_downloads_subs_and_verifies(tmp_path, monkeypatch):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "TMP_SPLIT_DIR", str(tmp_path / "tmp"))
    client = RestoreFakeClient({31: b"hello ", 32: b"world", 33: b"SRTDATA"})
    config = {
        "organize_mode": "separate",
        "movies_dir": str(tmp_path / "Movies"),
        "series_dir": str(tmp_path / "Series"),
    }
    out_path = restore_backup(client, MOVIE_ITEM, config)
    assert os.path.basename(out_path) == "Film A.mp4"
    with open(out_path, "rb") as fh:
        assert fh.read() == b"hello world"
    restored_subs = [f for f in os.listdir(os.path.dirname(out_path)) if f.endswith(".bin")]
    assert len(restored_subs) == 1
    leftovers = [f for f in os.listdir(str(tmp_path / "tmp"))]
    assert leftovers == []


def test_restore_raises_ioerror_on_size_mismatch_keeps_parts(tmp_path, monkeypatch):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "TMP_SPLIT_DIR", str(tmp_path / "tmp"))
    client = RestoreFakeClient({31: b"short", 32: b"", 33: b""})
    config = {
        "organize_mode": "separate",
        "movies_dir": str(tmp_path / "Movies"),
        "series_dir": str(tmp_path / "Series"),
    }
    with pytest.raises(IOError):
        restore_backup(client, dict(MOVIE_ITEM, video_msg_ids=[31]), config)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py -k "restore" -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write minimal implementation**

Di `src/telegram_manager.py` tambahkan:

```python
def build_restore_target(config: dict, item: dict) -> tuple:
    from src.main import format_tv_paths
    from src.config_manager import get_download_dir
    title = item.get("title", "Unknown")
    year = item.get("year", "") or ""
    if item.get("media_type") == "episode":
        base_dir = get_download_dir(config, media_type="series")
        season_dir, base_filename = format_tv_paths(
            title, year, item.get("season") or 1, item.get("episode") or 1, base_dir
        )
        return season_dir, f"{base_filename}.mp4"
    base_dir = get_download_dir(config, media_type="movie")
    folder = f"{title} ({year})" if year else title
    return os.path.join(base_dir, folder), f"{title}.mp4"


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
    merge_files(part_files, output_path)

    expected_size = item.get("file_size", 0)
    if os.path.getsize(output_path) != expected_size:
        raise IOError(
            f"Verifikasi ukuran gagal untuk '{filename}': "
            f"diharapkan {expected_size}, didapat {os.path.getsize(output_path)}. "
            f"Part sementara tetap disimpan di {TMP_SPLIT_DIR}."
        )

    cleanup_parts(part_files)

    sub_ids = list(item.get("sub_msg_ids") or [])
    if sub_ids:
        sub_messages = client.get_messages(chat, ids=sub_ids)
        for sub_message in sub_messages:
            client.download_media(sub_message, file=target_dir)

    return output_path
```

Perhatian: `format_tv_paths` menghasilkan `base_filename` tanpa ekstensi dan folder `Season NN` — sesuai pemakaian existing di `process_download_item` (`src/main.py:144-146`). Jika ternyata signature/behavior berbeda saat implementasi, sesuaikan `build_restore_target` agar output path konsisten dengan aturan folder existing — jangan ubah `format_tv_paths`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py -v`
Expected: PASS semua. (Jika `format_tv_paths` ternyata menamai file beda dari asumsi test, perbaiki ASUMSI TEST agar mencerminkan perilaku fungsi existing — bukan sebaliknya.)

- [ ] **Step 5: Full-suite regression**

Run: `uv run pytest`
Expected: PASS semua (tidak ada regresi modul lain).

- [ ] **Step 6: Commit**

```bash
git add src/telegram_manager.py tests/test_telegram_manager.py
git commit -m "feat: add restore from telegram with merge and size verification"
```

---

### Task 9: Formatter UI — tabel backup, tabel hapus lokal, tabel hybrid

**Files:**
- Modify: `src/ui.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: `human_size` (Task 3).
- Produces:
  - `format_backup_table(items: list[dict]) -> Table` — kolom: No, Judul, Tahun, Tipe, Season, Episode, Ukuran, Part, Sub.
  - `format_local_delete_table(entries: list[dict]) -> Table` — tiap entry dict berisi `title/year/media_type/season/episode/output_path/file_size/backed: bool`; kolom: No, Judul, Tipe, Ukuran, Status (`✅ Aman di Telegram` hijau / `⚠️ BELUM DIBACKUP` merah), Path.
  - `format_hybrid_results(idlix_items: list[dict], tg_items: list[dict]) -> list[dict]` — gabungkan jadi rows dengan key `__source__` (`"idlix"`/`"telegram"`); idlix rows = item apa adanya + `__source__`; tg rows = item scan + `__source__`.
  - `format_hybrid_table(rows: list[dict]) -> Table` — kolom: No, Sumber (`🌐 IDLIX` / `📡 TELEGRAM`), Judul, Tahun, Tipe, Info.

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_ui.py`:

```python
from rich.console import Console

from src.ui import (
    format_backup_table, format_local_delete_table,
    format_hybrid_results, format_hybrid_table,
)


def _render(table) -> str:
    console = Console(width=200)
    with console.capture() as capture:
        console.print(table)
    return capture.get()


BACKUP_ITEM = {
    "title": "Film A", "year": "2024", "media_type": "movie",
    "season": None, "episode": None, "file_size": 1500000,
    "part_count": 1, "subtitles": ["a.srt"],
}


def test_format_backup_table_shows_core_columns():
    text = _render(format_backup_table([BACKUP_ITEM]))
    assert "Film A" in text
    assert "2024" in text
    assert "1.5 MB" in text
    assert "1" in text


LOCAL_ENTRY = {
    "title": "Film A", "year": "2024", "media_type": "movie",
    "season": None, "episode": None,
    "output_path": "C:/x/Film A.mp4", "file_size": 1500000, "backed": True,
}
LOCAL_ENTRY_UNSAFE = dict(LOCAL_ENTRY, backed=False, output_path="C:/y/B.mp4", title="Film B")


def test_format_local_delete_table_status_markers():
    text = _render(format_local_delete_table([LOCAL_ENTRY, LOCAL_ENTRY_UNSAFE]))
    assert "Aman di Telegram" in text
    assert "BELUM DIBACKUP" in text
    assert "Film B" in text


def test_format_hybrid_results_tags_sources():
    idlix = [{"title": "Film A", "url": "https://x/film-a", "type": "Movie"}]
    tg = [dict(BACKUP_ITEM)]
    rows = format_hybrid_results(idlix, tg)
    sources = [r["__source__"] for r in rows]
    assert sources == ["idlix", "telegram"]
    text = _render(format_hybrid_table(rows))
    assert "IDLIX" in text and "TELEGRAM" in text
    assert "Film A" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ui.py -k "backup_table or delete_table or hybrid" -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write minimal implementation**

Di `src/ui.py` tambahkan:

```python
def format_backup_table(items: list) -> Table:
    table = Table(title="[bold cyan]📚 Daftar Backup Telegram[/bold cyan]",
                  header_style="bold magenta", show_header=True, expand=True)
    table.add_column("No", justify="right", style="cyan")
    table.add_column("Judul", style="bold white")
    table.add_column("Tahun", justify="center", style="yellow")
    table.add_column("Tipe", justify="center", style="green")
    table.add_column("S/E", justify="center")
    table.add_column("Ukuran", justify="right", style="cyan")
    table.add_column("Part", justify="center")
    table.add_column("Sub", justify="center")
    for idx, item in enumerate(items, start=1):
        se = "-"
        if item.get("season") is not None and item.get("episode") is not None:
            se = f"S{item['season']:02d}E{item['episode']:02d}"
        table.add_row(
            str(idx), item.get("title", ""), str(item.get("year", "") or "-"),
            item.get("media_type", ""), se,
            human_size(item.get("file_size", 0)),
            str(item.get("part_count", 1)), str(len(item.get("subtitles", []))),
        )
    return table


def format_local_delete_table(entries: list) -> Table:
    table = Table(title="[bold cyan]🗑️ File Lokal[/bold cyan]",
                  header_style="bold magenta", show_header=True, expand=True)
    table.add_column("No", justify="right", style="cyan")
    table.add_column("Judul", style="bold white")
    table.add_column("Tipe", justify="center")
    table.add_column("Ukuran", justify="right", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Path", style="dim")
    for idx, entry in enumerate(entries, start=1):
        if entry.get("backed"):
            status = "[green]✅ Aman di Telegram[/green]"
        else:
            status = "[red]⚠️ BELUM DIBACKUP[/red]"
        table.add_row(
            str(idx), entry.get("title", ""), entry.get("media_type", ""),
            human_size(entry.get("file_size", 0)), status,
            entry.get("output_path", ""),
        )
    return table


def format_hybrid_results(idlix_items: list, tg_items: list) -> list:
    rows = []
    for item in idlix_items or []:
        rows.append(dict(item, __source__="idlix"))
    for item in tg_items or []:
        rows.append(dict(item, __source__="telegram"))
    return rows


def format_hybrid_table(rows: list) -> Table:
    table = Table(title="[bold cyan]🔍 Hasil Pencarian[/bold cyan]",
                  header_style="bold magenta", show_header=True, expand=True)
    table.add_column("No", justify="right", style="cyan")
    table.add_column("Sumber", justify="center")
    table.add_column("Judul", style="bold white")
    table.add_column("Tahun", justify="center", style="yellow")
    table.add_column("Tipe", justify="center")
    table.add_column("Info", style="dim")
    for idx, row in enumerate(rows, start=1):
        if row.get("__source__") == "telegram":
            source = "[magenta]📡 TELEGRAM[/magenta]"
            info = human_size(row.get("file_size", 0))
            media_type = row.get("media_type", "")
        else:
            source = "[blue]🌐 IDLIX[/blue]"
            info = row.get("url", "")
            media_type = row.get("type", "")
        table.add_row(
            str(idx), source, row.get("title", ""),
            str(row.get("year", "") or "-"), media_type, info,
        )
    return table
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ui.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/ui.py tests/test_ui.py
git commit -m "feat: add rich tables for telegram backups, local deletion, hybrid search"
```

---

### Task 10: Kolektor file lokal + pencocokan backup

**Files:**
- Modify: `src/telegram_manager.py`
- Test: `tests/test_telegram_manager.py`

**Interfaces:**
- Consumes: `load_log` (`src/db_manager.py`), `entry_backup_key`, `backup_key` (Task 4).
- Produces:
  - `collect_local_entries() -> list[dict]` — dari `load_log()` ambil `status == "success"`, dedupe per `entry_backup_key` (simpan entri TERAKHIR), hanya yang `output_path` masih ada; tiap hasil: `{title, year, media_type, season, episode, output_path, file_size, key}` (`file_size` dari `os.path.getsize`).
  - `mark_backed_entries(local_entries: list[dict], scanned_items: list[dict]) -> list[dict]` — set `backed=True` bila `key` ada di set kunci hasil scan (`backup_key(item[title], item[year], item[season], item[episode])`); return list baru.

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_telegram_manager.py`:

```python
from src.telegram_manager import collect_local_entries, mark_backed_entries


def test_collect_local_entries_dedupes_and_filters_existing(monkeypatch, tmp_path):
    import src.db_manager as dbm
    real_file = tmp_path / "Film A.mp4"
    real_file.write_bytes(b"data")
    rows = [
        {"status": "success", "title": "Film A", "season": None, "episode": None,
         "output_path": str(real_file), "timestamp": "2026-01-01"},
        {"status": "success", "title": "Film A", "season": None, "episode": None,
         "output_path": str(real_file), "timestamp": "2026-01-02"},
        {"status": "failed", "title": "Film F", "season": None, "episode": None,
         "output_path": str(real_file)},
        {"status": "success", "title": "Hilang", "season": None, "episode": None,
         "output_path": "Z:/tidak/ada.mp4"},
    ]
    monkeypatch.setattr(dbm, "load_log", lambda db_path=None: rows)
    entries = collect_local_entries()
    assert [e["title"] for e in entries] == ["Film A"]
    assert entries[0]["file_size"] == 4
    assert entries[0]["backed"] is False


def test_mark_backed_entries_matches_scan_keys():
    from src.telegram_manager import backup_key as bk, mark_backed_entries as mbe
    local = [{"title": "Film A", "key": bk("Film A", "2024", None, None)}]
    scanned = [{"title": "Film A", "year": "2024", "season": None, "episode": None}]
    assert mbe(local, scanned)[0]["backed"] is True
    other = [{"title": "Lain", "key": bk("Lain", "", None, None)}]
    assert mbe(other, scanned)[0]["backed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_telegram_manager.py -k "collect or marked" -v`
Expected: FAIL — ImportError.

- [ ] **Step 3: Write minimal implementation**

Di `src/telegram_manager.py` tambahkan:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_telegram_manager.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/telegram_manager.py tests/test_telegram_manager.py
git commit -m "feat: add local entry collector with backup matching"
```

---

### Task 11: Menu 📡 Telegram Backup + Pengaturan + wiring main menu

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py` (file baru `tests/test_main_telegram.py` agar fokus)

**Interfaces:**
- Consumes: seluruh API `telegram_manager` (Tasks 5–8), formatter UI (Task 9), `questionary`, `Console`.
- Produces (di `src/main.py`):
  - `require_telegram_ready(config: dict) -> bool` — `ensure_telethon` + `is_configured` + `is_logged_in`; bila belum → tawarkan `login_flow`.
  - `handle_telegram_menu(active_url: str, config: dict) -> None` — sub-menu loop:
    - `"🔍 Cari & Restore dari Telegram / Search & Restore"`
    - `"📚 Daftar Semua Backup / List All Backups"`
    - `"📤 Backup Manual / Manual Backup"`
    - `"🗑️ Hapus File Lokal / Delete Local Files"`
    - `"⚙️ Pengaturan Telegram / Telegram Settings"`
    - `"⬅ Kembali / Back"`
  - `scan_with_spinner(client_factory, config) -> list[dict]` — bungkus `console.status("📡 Mencari di Telegram...")` + `scan_backups(create_client(config), get_destinations(config))` + disconnect.
  - Main-menu choices ditambah `"9. 📡 Telegram Backup / Kelola Backup Telegram"`; Exit menjadi `"10. ❌ Exit / Keluar"`; dispatch `startswith("9.")` → `handle_telegram_menu`, exit `startswith("10.")`.

- [ ] **Step 1: Write the failing test**

Buat `tests/test_main_telegram.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

import src.main as main_mod
from src.main import handle_telegram_menu, require_telegram_ready


def test_require_telegram_ready_runs_login_when_not_logged_in():
    config = {"tg_api_id": "1", "tg_api_hash": "h"}
    with patch.object(main_mod, "ensure_telethon", return_value=True), \
         patch.object(main_mod, "is_configured", return_value=True), \
         patch.object(main_mod, "is_logged_in", return_value=False), \
         patch.object(main_mod, "login_flow", return_value=True) as mock_login:
        assert require_telegram_ready(config) is True
        mock_login.assert_called_once()


def test_require_telegram_ready_false_when_setup_declined():
    config = {}
    with patch.object(main_mod, "ensure_telethon", return_value=True), \
         patch.object(main_mod, "is_configured", return_value=False), \
         patch.object(main_mod, "login_flow", return_value=False):
        assert require_telegram_ready(config) is False


@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.questionary.select")
def test_handle_telegram_menu_back_immediately(mock_select, mock_press):
    ask = MagicMock()
    ask.ask.return_value = "⬅ Kembali / Back"
    mock_select.return_value = ask
    handle_telegram_menu("https://x/", {})
    ask.ask.assert_called_once()


@patch("src.main.questionary.select")
@patch("src.main.load_config", return_value={"active_url": "u", "target_urls": [{"url": "u"}]})
@patch("src.main.ensure_playwright")
@patch("src.main.ensure_ffmpeg")
@patch("src.main.ensure_binary")
@patch("src.main.is_chromium_installed", return_value=True)
@patch("src.main.get_ffmpeg_paths", return_value=("f", "fp"))
@patch("src.main.get_binary_path", return_value="b")
@patch("src.main.print_header")
@patch("src.main.init_db")
@patch("src.main.handle_telegram_menu")
def test_main_routes_option_nine_then_exit(
    mock_tg, _init_db, _header, _gbp, _gfp, _chrom, _eb, _ef, _ep, _lc,
    mock_select
):
    from src.main import main as main_fn

    mock_select.return_value = MagicMock(ask=MagicMock(side_effect=[
        "9. 📡 Telegram Backup / Kelola Backup Telegram",
        "⬅ Kembali / Back",
        "10. ❌ Exit / Keluar",
    ]))
    with pytest.raises(SystemExit):
        main_fn()
    mock_tg.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main_telegram.py -v`
Expected: FAIL — `ImportError: cannot import name 'handle_telegram_menu'`.

- [ ] **Step 3: Write minimal implementation**

Di `src/main.py` tambahkan import:

```python
import json
import src.telegram_manager as tm
from src.config_manager import (
    load_config, save_config, add_target_url, set_active_url, delete_target_url,
    get_download_dir, set_download_dir, set_organize_mode, save_config_key,
)
from src.ui import (
    format_backup_table, format_local_delete_table,
    format_hybrid_results, format_hybrid_table,
)
from src.telegram_manager import (
    ensure_telethon, create_client, login_flow, is_configured, is_logged_in,
    get_destinations, scan_backups, upload_backup, restore_backup,
    collect_local_entries, mark_backed_entries, matches_query,
)
```

Catatan: baris import `config_manager` di atas MENGGABUNGkan dengan import existing di `src/main.py:9-12` (ganti blok lama, jangan duplikat). `save_config_key` sebelumnya tidak diekspor lewat `src/config_manager.py` — tambahkan wrapper kecil ke `src/config_manager.py`:

```python
def save_config_key(key: str, value: str, config_path: str = CONFIG_FILE, db_path: str | None = None) -> None:
    """Save or update a single configuration key-value pair."""
    target_db = db_path if db_path else (config_path if config_path != CONFIG_FILE else None)
    db_manager.save_config_key(key, str(value), db_path=target_db)
```

Tambahkan fungsi:

```python
def require_telegram_ready(config: dict) -> bool:
    if not ensure_telethon(console):
        return False
    if not is_configured(config) or not is_logged_in():
        console.print("[yellow]Telegram belum terhubung. Setup diperlukan sekali saja.[/yellow]")
        return bool(login_flow(console, config))
    return True


def scan_with_spinner(config: dict) -> list:
    with console.status("[bold cyan]📡 Mencari di Telegram... / Searching in Telegram...[/bold cyan]", spinner="dots"):
        client = create_client(config)
        try:
            items = scan_backups(client, get_destinations(config))
        finally:
            client.disconnect()
    return items


def handle_telegram_settings(config: dict) -> None:
    while True:
        fresh = load_config()
        config.update(fresh)
        dests_raw = fresh.get("tg_destinations", '["saved"]')
        console.print(f"\n[bold cyan]⚙️ TELEGRAM SETTINGS[/bold cyan]")
        console.print(f"API ID  : [yellow]{fresh.get('tg_api_id') or '-'}[/yellow]")
        console.print(f"Channel : [yellow]{fresh.get('tg_channel_id') or '-'}[/yellow]")
        console.print(f"Auto-backup : [yellow]{'ON' if fresh.get('tg_auto_backup') == '1' else 'OFF'}[/yellow]")
        console.print(f"Tujuan  : [yellow]{dests_raw}[/yellow]")

        action = questionary.select(
            "Pilih Pengaturan:",
            choices=[
                "🔑 Isi Ulang API ID / Hash",
                "📢 Set Channel Tujuan / Set Target Channel",
                "🎯 Ubah Tujuan Backup (Saved/Channel)",
                "🤖 Toggle Auto-Backup",
                "🚪 Logout (hapus session)",
                "⬅ Kembali / Back",
            ]
        ).ask()
        if not action or action == "⬅ Kembali / Back":
            return
        if action == "🔑 Isi Ulang API ID / Hash":
            api_id = questionary.text("API ID:", default=fresh.get("tg_api_id", "")).ask()
            api_hash = questionary.text("API Hash:", default=fresh.get("tg_api_hash", "")).ask()
            if api_id and api_hash:
                save_config_key("tg_api_id", api_id.strip())
                save_config_key("tg_api_hash", api_hash.strip())
                print_success("API credentials disimpan.")
        elif action == "📢 Set Channel Tujuan / Set Target Channel":
            channel = questionary.text("Username channel (@nama) atau ID (-100...):",
                                       default=fresh.get("tg_channel_id", "")).ask()
            if channel is not None:
                save_config_key("tg_channel_id", channel.strip())
                print_success("Channel disimpan. Pastikan Anda adalah admin/member channel tersebut.")
        elif action == "🎯 Ubah Tujuan Backup (Saved/Channel)":
            picked = questionary.checkbox(
                "Pilih tujuan backup (urutan = prioritas, yang pertama jadi tujuan utama):",
                choices=["saved - Saved Messages", "channel - Channel Privat"],
            ).ask()
            if picked:
                names = [p.split(" ")[0] for p in picked]
                save_config_key("tg_destinations", json.dumps(names))
                print_success(f"Tujuan backup: {names}")
        elif action == "🤖 Toggle Auto-Backup":
            new_val = "0" if fresh.get("tg_auto_backup") == "1" else "1"
            save_config_key("tg_auto_backup", new_val)
            print_success(f"Auto-backup: {'ON' if new_val == '1' else 'OFF'}")
        elif action == "🚪 Logout (hapus session)":
            confirm = questionary.confirm("Hapus session Telegram di PC ini?").ask()
            if confirm:
                tm.logout_session()
                print_success("Session Telegram dihapus.")


def handle_telegram_menu(active_url: str, config: dict) -> None:
    while True:
        action = questionary.select(
            "📡 Telegram Backup — Pilih Aksi:",
            choices=[
                "🔍 Cari & Restore dari Telegram / Search & Restore",
                "📚 Daftar Semua Backup / List All Backups",
                "📤 Backup Manual / Manual Backup",
                "🗑️ Hapus File Lokal / Delete Local Files",
                "⚙️ Pengaturan Telegram / Telegram Settings",
                "⬅ Kembali / Back",
            ]
        ).ask()
        if action is None or action == "⬅ Kembali / Back":
            return
        fresh = load_config()
        config.update(fresh)
        if action.startswith("⚙️"):
            handle_telegram_settings(config)
        elif action.startswith("🔍"):
            handle_telegram_search_restore(fresh)
        elif action.startswith("📚"):
            handle_telegram_list(fresh)
        elif action.startswith("📤"):
            handle_telegram_manual_backup(fresh)
        elif action.startswith("🗑️"):
            handle_telegram_delete_local(fresh)
```

Implementasi `handle_telegram_search_restore`, `handle_telegram_list`, `handle_telegram_manual_backup`, `handle_telegram_delete_local` adalah stub yang memanggil `require_telegram_ready` lalu `console.print("[yellow]Belum diimplementasi di task ini.[/yellow]")` — handler penuh menyusul di Task 12–14. Stub WAJIB sudah memanggil `require_telegram_ready(config)` lebih dulu.

Tambahkan juga di `src/telegram_manager.py`:

```python
def logout_session() -> None:
    for suffix in ("", ".session", ".session-journal"):
        path = SESSION_PATH + suffix
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
```

Ubah `main()` di `src/main.py`: pada `choices` sisipkan sebelum Exit dan ganti nomor Exit:

```python
                "9. 📡 Telegram Backup / Kelola Backup Telegram",
                "10. ❌ Exit / Keluar",
```

Dispatch:

```python
        if choice is None or choice.startswith("10."):
            console.print("[bold yellow]Terima kasih! Sampai jumpa.[/bold yellow]")
            sys.exit(0)
```

dan tambahkan cabang:

```python
        elif choice.startswith("9."):
            handle_telegram_menu(active_url, config)
```

Cek juga `print_header`/teks lain yang menyebut "9. Exit" (tidak ada saat audit, tapi pastikan).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main_telegram.py -v && uv run pytest tests/test_main.py -v`
Expected: PASS. Jika ada test existing yang rusak karena renumbering menu ("9." → "10."), perbaiki ekspektasi test tersebut — perubahan numbering memang bagian task ini.

- [ ] **Step 5: Commit**

```bash
git add src/main.py src/telegram_manager.py tests/test_main_telegram.py
git commit -m "feat: add telegram backup menu, settings, and main menu wiring"
```

---

### Task 12: Handler Daftar Backup & Search-Restore

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main_telegram.py`

**Interfaces:**
- Consumes: `scan_with_spinner`, `format_backup_table`, `format_hybrid_results`, `format_hybrid_table`, `restore_backup`, `matches_query`, `human_size`, `tm.logout_session` (Task 10–11).
- Produces (mengganti stub Task 11):
  - `handle_telegram_list(config)` — `scan_with_spinner` → `format_backup_table` → press-any-key. Kosong → pesan kuning.
  - `handle_telegram_search_restore(config)` — input query → `scan_with_spinner` → filter `matches_query(item["title"], query)` → `format_backup_table(filtered)` → pilih nomor → konfirmasi restore → `restore_backup(client, item, config, progress_cb)` dengan Rich Progress → success panel + tawaran buka folder (`os.startfile` di Windows, guard try/except).

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_main_telegram.py`:

```python
SCAN_ITEMS = [
    {"title": "Film A", "year": "2024", "media_type": "movie", "season": None,
     "episode": None, "file_size": 10, "part_count": 1, "subtitles": [],
     "video_msg_ids": [1], "sub_msg_ids": [], "chat": "me"},
    {"title": "Series B", "year": "2023", "media_type": "episode", "season": 1,
     "episode": 2, "file_size": 20, "part_count": 1, "subtitles": [],
     "video_msg_ids": [2], "sub_msg_ids": [], "chat": "me"},
]


@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.scan_with_spinner", return_value=SCAN_ITEMS)
@patch("src.main.require_telegram_ready", return_value=True)
def test_handle_telegram_lists_all_backups(mock_ready, mock_scan, mock_press, capsys):
    from src.main import handle_telegram_list
    handle_telegram_list({})
    out = capsys.readouterr().out
    assert "Film A" in out and "Series B" in out
    mock_scan.assert_called_once()


@patch("src.main.restore_backup", return_value="C:/out/Film A.mp4")
@patch("src.main.create_client")
@patch("src.main.questionary.text")
@patch("src.main.scan_with_spinner", return_value=SCAN_ITEMS)
@patch("src.main.require_telegram_ready", return_value=True)
def test_handle_telegram_search_restores_selected(
    mock_ready, mock_scan, mock_text, mock_client, mock_restore
):
    from src.main import handle_telegram_search_restore

    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=[
        "film a",  # query pencarian
        "1",       # pilih nomor item hasil filter
    ]))
    handle_telegram_search_restore({})
    mock_restore.assert_called_once()
    called_item = mock_restore.call_args[0][1]
    assert called_item["title"] == "Film A"
```

Yang diverifikasi: query `"film a"` hanya cocok dengan `Film A` (bukan `Series B`), nomor `"1"` memilihnya, dan `restore_backup` dipanggil dengan item itu.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main_telegram.py -k "lists_all or search_restores" -v`
Expected: FAIL — handler masih stub.

- [ ] **Step 3: Write minimal implementation**

Ganti stub di `src/main.py` dengan:

```python
def handle_telegram_list(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    try:
        items = scan_with_spinner(config)
    except Exception as exc:
        print_error(f"Gagal membaca Telegram: {exc}")
        return
    if not items:
        console.print("[yellow]Belum ada backup di tujuan Telegram yang dikonfigurasi.[/yellow]")
        questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()
        return
    console.print(format_backup_table(items))
    questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()


def handle_telegram_search_restore(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    query = questionary.text("Masukkan judul yang dicari di backup Telegram:").ask()
    if not query or not query.strip():
        return
    try:
        items = scan_with_spinner(config)
    except Exception as exc:
        print_error(f"Gagal membaca Telegram: {exc}")
        return
    filtered = [it for it in items if matches_query(it.get("title", ""), query.strip())]
    if not filtered:
        console.print(f"[yellow]Tidak ada backup cocok untuk \"{query.strip()}\".[/yellow]")
        questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()
        return
    console.print(format_backup_table(filtered))
    raw = questionary.text(f"Pilih nomor untuk restore (1-{len(filtered)}, kosongkan untuk batal):").ask()
    if not raw or not raw.strip().isdigit() or not (1 <= int(raw) <= len(filtered)):
        console.print("[yellow]Restore dibatalkan.[/yellow]")
        return
    chosen = filtered[int(raw) - 1]
    confirm = questionary.confirm(
        f"Restore '{chosen['title']}' ke folder lokal sekarang?"
    ).ask()
    if not confirm:
        return
    try:
        client = create_client(config)
        try:
            with console.status("[bold cyan]⬇️ Mengunduh dari Telegram... / Downloading...[/bold cyan]", spinner="dots"):
                out_path = restore_backup(client, chosen, config)
        finally:
            client.disconnect()
    except Exception as exc:
        print_error(f"Restore gagal: {exc}")
        return
    print_success(f"Restore selesai: {out_path}")
    try:
        import subprocess
        subprocess.Popen(["explorer", "/select,", os.path.normpath(out_path)])
    except Exception:
        pass
    questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main_telegram.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main_telegram.py
git commit -m "feat: implement backup listing and search-restore handlers"
```

---

### Task 13: Handler Backup Manual & Hapus File Lokal ber-pengaman

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main_telegram.py`

**Interfaces:**
- Consumes: `collect_local_entries`, `mark_backed_entries`, `scan_with_spinner`, `upload_backup`, `create_client`, formatter Task 9.
- Produces (mengganti stub):
  - `handle_telegram_manual_backup(config)` — `collect_local_entries()` + spinner-scan + `mark_backed_entries` → tabel lokal (kolom ✅/belum, pakai `format_local_delete_table`) → checkbox pilih → per item: skip bila file hilang; upload dengan Rich Progress; ringkasan sukses/gagal; item ✅ ditandai "(duplikat)" di label tapi tetap bisa dipilih.
  - `handle_telegram_delete_local(config)` — listing sama → checkbox → per item: `backed` → konfirmasi biasa; NOT backed → peringatan merah permanen + konfirmasi ya/tidak + ketik kata `HAPUS` → hapus file; folder kosong ikut dibersihkan (`os.removedirs` guard try).

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_main_telegram.py`:

```python
LOCAL_ENTRIES = [
    {"title": "Safe Film", "year": "2024", "media_type": "movie", "season": None,
     "episode": None, "output_path": "C:/safe.mp4", "file_size": 5, "backed": True,
     "key": "safefilm|2024||"},
    {"title": "Risky Film", "year": "2025", "media_type": "movie", "season": None,
     "episode": None, "output_path": "C:/risky.mp4", "file_size": 6, "backed": False,
     "key": "riskyfilm|2025||"},
]


def test_manual_backup_calls_upload_per_selection(tmp_path, monkeypatch):
    real_file = tmp_path / "Safe Film.mp4"
    real_file.write_bytes(b"x" * 5)
    entries = [dict(LOCAL_ENTRIES[0], output_path=str(real_file))]
    monkeypatch.setattr(main_mod, "collect_local_entries", lambda: entries)
    monkeypatch.setattr(main_mod, "scan_with_spinner", lambda cfg: [])
    monkeypatch.setattr(main_mod, "require_telegram_ready", lambda cfg: True)

    uploads = []

    def fake_upload(client, path, subs, meta, dests, progress_callback=None):
        uploads.append((path, meta))
        return {"video_msg_ids": [1], "sub_msg_ids": [], "forwarded_to": []}

    monkeypatch.setattr(main_mod, "upload_backup", fake_upload)
    monkeypatch.setattr(main_mod, "create_client", lambda cfg: MagicMock())

    with patch("src.main.questionary.checkbox") as mock_check, \
         patch("src.main.questionary.press_any_key_to_continue"):
        mock_check.return_value = MagicMock(ask=MagicMock(return_value=["1. ✅ Safe Film (duplikat)"]))
        main_mod.handle_telegram_manual_backup({})

    assert len(uploads) == 1
    assert uploads[0][0] == str(real_file)


def test_delete_local_requires_typed_confirmation_for_unbacked(tmp_path, monkeypatch):
    real_risky = tmp_path / "Risky Film.mp4"
    real_risky.write_bytes(b"y" * 6)
    entries = [dict(LOCAL_ENTRIES[1], output_path=str(real_risky))]
    monkeypatch.setattr(main_mod, "collect_local_entries", lambda: entries)
    monkeypatch.setattr(main_mod, "scan_with_spinner", lambda cfg: [])
    monkeypatch.setattr(main_mod, "require_telegram_ready", lambda cfg: True)

    with patch("src.main.questionary.checkbox") as mock_check, \
         patch("src.main.questionary.confirm") as mock_confirm, \
         patch("src.main.questionary.text") as mock_text, \
         patch("src.main.questionary.press_any_key_to_continue"):
        mock_check.return_value = MagicMock(ask=MagicMock(return_value=["1. ⚠️ Risky Film (BELUM DIBACKUP)"]))
        mock_confirm.return_value = MagicMock(ask=MagicMock(return_value=True))
        mock_text.return_value = MagicMock(ask=MagicMock(return_value="HAPUS"))
        main_mod.handle_telegram_delete_local({})

    assert not real_risky.exists()


def test_delete_local_wrong_word_aborts(tmp_path, monkeypatch):
    real_risky = tmp_path / "Risky Film.mp4"
    real_risky.write_bytes(b"y" * 6)
    entries = [dict(LOCAL_ENTRIES[1], output_path=str(real_risky))]
    monkeypatch.setattr(main_mod, "collect_local_entries", lambda: entries)
    monkeypatch.setattr(main_mod, "scan_with_spinner", lambda cfg: [])
    monkeypatch.setattr(main_mod, "require_telegram_ready", lambda cfg: True)

    with patch("src.main.questionary.checkbox") as mock_check, \
         patch("src.main.questionary.confirm") as mock_confirm, \
         patch("src.main.questionary.text") as mock_text, \
         patch("src.main.questionary.press_any_key_to_continue"):
        mock_check.return_value = MagicMock(ask=MagicMock(return_value=["1. ⚠️ Risky Film (BELUM DIBACKUP)"]))
        mock_confirm.return_value = MagicMock(ask=MagicMock(return_value=True))
        mock_text.return_value = MagicMock(ask=MagicMock(return_value="salah"))
        main_mod.handle_telegram_delete_local({})

    assert real_risky.exists()
```

Label persis di checkbox bergantung implementasi formatter/handler — saat implementasi, samakan string label handler dengan yang di-assert test (ini kontrak UI). Format label wajib: `"{no}. ✅ {title} (duplikat)"` untuk backed, `"{no}. ⚠️ {title} (BELUM DIBACKUP)"` untuk belum.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main_telegram.py -k "manual_backup or delete_local" -v`
Expected: FAIL — handler masih stub.

- [ ] **Step 3: Write minimal implementation**

Ganti kedua stub di `src/main.py`:

```python
def _local_listing_with_backup_status(config: dict) -> list:
    entries = collect_local_entries()
    try:
        scanned = scan_with_spinner(config)
    except Exception:
        scanned = []
        console.print("[yellow]⚠️ Tidak bisa menghubungi Telegram — status backup tidak diketahui.[/yellow]")
    return mark_backed_entries(entries, scanned)


def _rich_progress(total: int, description: str):
    from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn
    progress = Progress(
        TextColumn("[bold blue]" + description + "[/bold blue]"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        console=console,
    )
    task_id = progress.add_task(description, total=total)

    def callback(current: int, total_bytes: int):
        progress.update(task_id, completed=current)

    return progress, callback


def handle_telegram_manual_backup(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    entries = _local_listing_with_backup_status(config)
    if not entries:
        console.print("[yellow]Tidak ada file lokal yang tercatat sukses di log.[/yellow]")
        return
    console.print(format_local_delete_table(entries))
    labels = []
    for idx, entry in enumerate(entries, start=1):
        if entry["backed"]:
            labels.append(f"{idx}. ✅ {entry['title']} (duplikat)")
        else:
            labels.append(f"{idx}. {entry['title']}")
    picked = questionary.checkbox(
        "Pilih item untuk di-backup ke Telegram (SPACE pilih, ENTER lanjut):",
        choices=labels
    ).ask()
    if not picked:
        console.print("[yellow]Tidak ada item dipilih.[/yellow]")
        return
    chosen_indices = [int(label.split(".")[0]) - 1 for label in picked]
    destinations = get_destinations(config)
    if not destinations:
        print_error("Tujuan backup belum valid. Atur di ⚙️ Pengaturan Telegram.")
        return
    success_count = 0
    fail_count = 0
    client = create_client(config)
    try:
        for pos, idx in enumerate(chosen_indices, start=1):
            entry = entries[idx]
            if not os.path.exists(entry["output_path"]):
                print_error(f"File tidak ditemukan, di-skip: {entry['output_path']}")
                fail_count += 1
                continue
            console.print(f"\n[bold cyan]=== Backup {pos}/{len(chosen_indices)}: {entry['title']} ===[/bold cyan]")
            sub_dir = os.path.dirname(entry["output_path"])
            sub_paths = [
                os.path.join(sub_dir, name)
                for name in sorted(os.listdir(sub_dir))
                if name.lower().endswith(".srt") and os.path.splitext(name)[0].startswith(os.path.splitext(os.path.basename(entry["output_path"]))[0])
            ]
            meta = {
                "title": entry["title"], "year": entry["year"],
                "media_type": entry["media_type"], "season": entry["season"],
                "episode": entry["episode"], "subtitles": [],
            }
            try:
                progress, cb = _rich_progress(entry["file_size"], entry["title"])
                with progress:
                    upload_backup(client, entry["output_path"], sub_paths, meta, destinations, progress_callback=cb)
                print_success(f"Berhasil backup: {entry['title']}")
                success_count += 1
            except Exception as exc:
                print_error(f"Gagal backup {entry['title']}: {exc}")
                fail_count += 1
    finally:
        client.disconnect()
    console.print(f"\n[bold]Selesai: {success_count} berhasil, {fail_count} gagal.[/bold]")
    questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()


def handle_telegram_delete_local(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    entries = _local_listing_with_backup_status(config)
    if not entries:
        console.print("[yellow]Tidak ada file lokal yang tercatat sukses di log.[/yellow]")
        return
    console.print(format_local_delete_table(entries))
    labels = []
    for idx, entry in enumerate(entries, start=1):
        if entry["backed"]:
            labels.append(f"{idx}. ✅ {entry['title']} (aman)")
        else:
            labels.append(f"{idx}. ⚠️ {entry['title']} (BELUM DIBACKUP)")
    picked = questionary.checkbox(
        "Pilih file lokal yang ingin DIHAPUS (SPACE pilih, ENTER lanjut):",
        choices=labels
    ).ask()
    if not picked:
        console.print("[yellow]Tidak ada file dipilih.[/yellow]")
        return
    deleted = 0
    for label in picked:
        idx = int(label.split(".")[0]) - 1
        entry = entries[idx]
        path = entry["output_path"]
        if entry["backed"]:
            ok = questionary.confirm(f"Hapus '{path}'? (sudah aman di Telegram)").ask()
            if not ok:
                continue
            os.remove(path)
            deleted += 1
            print_success(f"Dihapus: {path}")
        else:
            console.print(f"\n[bold red]⛔ PERINGATAN: '{entry['title']}' TIDAK ditemukan di Telegram![/bold red]")
            console.print("[bold red]Jika dihapus, file hilang PERMANEN dan tidak bisa dipulihkan![/bold red]")
            ok = questionary.confirm("Saya mengerti risikonya — lanjutkan penghapusan?").ask()
            if not ok:
                console.print("[yellow]Penghapusan dibatalkan.[/yellow]")
                continue
            typed = questionary.text("Ketik HAPUS untuk mengonfirmasi permanen:").ask()
            if typed != "HAPUS":
                console.print("[yellow]Konfirmasi salah — penghapusan dibatalkan.[/yellow]")
                continue
            os.remove(path)
            deleted += 1
            print_success(f"Dihapus permanen: {path}")
        parent = os.path.dirname(path)
        try:
            if parent and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass
    console.print(f"\n[bold]Selesai: {deleted} file dihapus.[/bold]")
    questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main_telegram.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main_telegram.py
git commit -m "feat: implement manual backup and guarded local deletion handlers"
```

---

### Task 14: Search hybrid di Menu 1

**Files:**
- Modify: `src/main.py` (`handle_search`, sekitar baris 935-968)
- Test: `tests/test_main_telegram.py`

**Interfaces:**
- Consumes: `scan_with_spinner`, `format_hybrid_results`, `format_hybrid_table`, `restore_backup`, `create_client` (Tasks 8, 9, 11).
- Produces: `handle_search` menampilkan tabel hybrid; prompt nomor item tunggal; item `__source__ == "telegram"` → alur restore inline (konfirmasi → `restore_backup`); item idlix → `process_download_item` seperti sekarang. Kegagalan scan Telegram TIDAK BOLEH merusak pencarian idlix (try/except → idlix saja + catatan redup).

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_main_telegram.py`:

```python
@patch("src.main.handle_item_download")
@patch("src.main.process_download_item")
@patch("src.main.restore_backup", return_value="C:/r/X.mp4")
@patch("src.main.create_client")
@patch("src.main.scan_with_spinner")
@patch("src.main.search_content")
@patch("src.main.questionary.text")
@patch("src.main.questionary.confirm")
@patch("src.main.questionary.press_any_key_to_continue")
def test_handle_search_routes_telegram_result_to_restore(
    _press, mock_confirm, mock_text, mock_search, mock_scan, mock_client, mock_restore, mock_proc, mock_hid
):
    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=[
        "dupe",      # query pencarian
        "1",         # pilih nomor item hybrid
    ]))
    mock_search.return_value = [{"title": "Dupe Film", "type": "Movie", "url": "https://x/dupe-film"}]
    mock_scan.return_value = [{
        "title": "Dupe Film", "year": "2024", "media_type": "movie",
        "season": None, "episode": None, "file_size": 9, "part_count": 1,
        "subtitles": [], "video_msg_ids": [7], "sub_msg_ids": [], "chat": "me",
    }]
    mock_confirm.return_value = MagicMock(ask=MagicMock(return_value=True))

    main_mod.handle_search("https://z2.idlixku.com/", {"active_url": "https://z2.idlixku.com/"})

    mock_restore.assert_called_once()
    called_item = mock_restore.call_args[0][1]
    assert called_item["__source__"] == "telegram"
    mock_proc.assert_not_called()
    mock_hid.assert_not_called()


@patch("src.main.process_download_item")
@patch("src.main.scan_with_spinner", side_effect=Exception("offline"))
@patch("src.main.search_content")
@patch("src.main.questionary.text")
@patch("src.main.questionary.press_any_key_to_continue")
def test_handle_search_survives_telegram_failure(
    _press, mock_text, mock_search, mock_scan, mock_proc
):
    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=["anything", "1"]))
    mock_search.return_value = [{"title": "Any Film", "type": "Movie", "url": "https://x/any"}]
    main_mod.handle_search("https://z2.idlixku.com/", {"active_url": "u"})
    mock_proc.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main_telegram.py -k "search_routes or survives" -v`
Expected: FAIL — `handle_search` masih alur lama.

- [ ] **Step 3: Write minimal implementation**

Ganti isi `handle_search` di `src/main.py`:

```python
def handle_search(active_url: str, config: dict) -> None:
    while True:
        query = questionary.text("Masukkan judul film/series yang dicari:").ask()
        if not query or not query.strip():
            return

        clean_query = query.strip()
        with console.status(f"[bold cyan]🔍 Mencari \"{clean_query}\" di IDLIX...[/bold cyan]", spinner="dots"):
            idlix_items = search_content(active_url, clean_query)

        tg_items = []
        telegram_failed = False
        try:
            tg_items = [
                it for it in scan_with_spinner(config)
                if matches_query(it.get("title", ""), clean_query)
            ]
        except Exception:
            telegram_failed = True

        for item in tg_items:
            item["__source__"] = "telegram"

        rows = format_hybrid_results(idlix_items, tg_items)
        if not rows:
            console.print(f"[yellow]Tidak ada hasil ditemukan untuk \"{clean_query}\".[/yellow]")
            continue

        if telegram_failed:
            console.print("[dim]ℹ️ Pencarian backup Telegram dilewati (tidak terhubung).[/dim]")
        console.print(format_hybrid_table(rows))

        raw = questionary.text(
            f"Pilih nomor item untuk diproses (1-{len(rows)}, kosongkan untuk kembali):"
        ).ask()
        if not raw or not raw.strip().isdigit() or not (1 <= int(raw) <= len(rows)):
            return
        chosen = rows[int(raw) - 1]

        if chosen.get("__source__") == "telegram":
            if questionary.confirm(f"Restore '{chosen['title']}' dari Telegram ke lokal?").ask():
                try:
                    client = create_client(config)
                    try:
                        out_path = restore_backup(client, chosen, config)
                    finally:
                        client.disconnect()
                    print_success(f"Restore selesai: {out_path}")
                except Exception as exc:
                    print_error(f"Restore gagal: {exc}")
            questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()
            return

        summary = {
            "total_items": 0, "video_success": 0, "video_failed": 0,
            "video_skipped": 0, "sub_success": 0, "sub_failed": 0, "items": [],
        }
        process_download_item(chosen, active_url, config, summary)
        print_download_summary(summary)
        questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali...").ask()
        return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main_telegram.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main_telegram.py
git commit -m "feat: hybrid search combining idlix and telegram backup results"
```

---

### Task 15: Hook auto-backup pasca-download sukses

**Files:**
- Modify: `src/main.py` (`process_download_item` — dua titik success: movie ~baris 407, episode ~baris 220)
- Test: `tests/test_main_telegram.py`

**Interfaces:**
- Consumes: `upload_backup`, `create_client`, `get_destinations`, `is_configured`, `is_logged_in`, `_rich_progress` (Task 13).
- Produces: `maybe_auto_backup(video_path: str, config: dict, title: str, year: str, media_type: str, season=None, episode=None) -> None` — dipanggil SETELAH `add_entry(status="success")` di kedua jalur. Aturan: hanya jalan bila `config.get("tg_auto_backup") == "1"` DAN `is_configured` DAN `is_logged_in`; kumpulkan `.srt` se-namespace di folder video; kegagalan apa pun → warning kuning, TIDAK pernah raise.

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_main_telegram.py`:

```python
def test_auto_backup_disabled_does_nothing(tmp_path):
    video = tmp_path / "V.mp4"
    video.write_bytes(b"x" * 3)
    calls = []
    with patch.object(main_mod, "upload_backup", lambda *a, **k: calls.append(a)):
        main_mod.maybe_auto_backup(str(video), {"tg_auto_backup": "0"}, "V", "2024", "movie")
    assert calls == []


def test_auto_backup_uploads_with_siblings_and_never_raises(tmp_path):
    video = tmp_path / "My Film.mp4"
    video.write_bytes(b"x" * 3)
    (tmp_path / "My Film.id.srt").write_text("srt")
    (tmp_path / "Other.id.srt").write_text("nope")
    captured = {}

    def fake_upload(client, path, subs, meta, dests, progress_callback=None):
        captured.update(path=path, subs=subs, meta=meta)
        return {"video_msg_ids": [1], "sub_msg_ids": [], "forwarded_to": []}

    config = {"tg_auto_backup": "1"}
    with patch.object(main_mod, "is_configured", return_value=True), \
         patch.object(main_mod, "is_logged_in", return_value=True), \
         patch.object(main_mod, "get_destinations", return_value=[{"type": "saved", "target": "me"}]), \
         patch.object(main_mod, "create_client", lambda cfg: MagicMock()), \
         patch.object(main_mod, "upload_backup", fake_upload):
        main_mod.maybe_auto_backup(str(video), config, "My Film", "2024", "movie")
    assert captured["subs"] == [str(tmp_path / "My Film.id.srt")]
    assert captured["meta"]["title"] == "My Film"


def test_auto_backup_swallows_errors(tmp_path):
    video = tmp_path / "Boom.mp4"
    video.write_bytes(b"x")
    with patch.object(main_mod, "is_configured", return_value=True), \
         patch.object(main_mod, "is_logged_in", return_value=True), \
         patch.object(main_mod, "get_destinations", return_value=[{"type": "saved", "target": "me"}]), \
         patch.object(main_mod, "create_client", lambda cfg: MagicMock()), \
         patch.object(main_mod, "upload_backup", side_effect=RuntimeError("boom")):
        main_mod.maybe_auto_backup(str(video), {"tg_auto_backup": "1"}, "Boom", "2024", "movie")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main_telegram.py -k auto_backup -v`
Expected: FAIL — `maybe_auto_backup` belum ada.

- [ ] **Step 3: Write minimal implementation**

Di `src/main.py` tambahkan:

```python
def maybe_auto_backup(video_path: str, config: dict, title: str, year: str,
                      media_type: str, season=None, episode=None) -> None:
    if config.get("tg_auto_backup") != "1":
        return
    if not is_configured(config) or not is_logged_in():
        return
    try:
        destinations = get_destinations(config)
        if not destinations:
            return
        video_dir = os.path.dirname(video_path)
        stem = os.path.splitext(os.path.basename(video_path))[0]
        sub_paths = [
            os.path.join(video_dir, name)
            for name in sorted(os.listdir(video_dir))
            if name.lower().endswith(".srt") and os.path.splitext(name)[0].startswith(stem)
        ]
        meta = {
            "title": title, "year": year, "media_type": media_type,
            "season": season, "episode": episode, "subtitles": [],
        }
        size = os.path.getsize(video_path)
        progress, cb = _rich_progress(size, f"☁️ {title}")
        client = create_client(config)
        try:
            with progress:
                upload_backup(client, video_path, sub_paths, meta, destinations, progress_callback=cb)
        finally:
            client.disconnect()
        print_success(f"Auto-backup Telegram selesai: {title}")
    except Exception as exc:
        console.print(f"[yellow]⚠️ Auto-backup gagal untuk {title}: {exc}[/yellow]")
```

Panggil setelah kedua blok `add_entry(status="success")` di `process_download_item`:

- Episode (setelah baris `summary["items"].append(...)` di blok SUCCESS episode):

```python
                    maybe_auto_backup(video_path, config, ep_title, year, "episode", season=season_num, episode=ep["episode_num"])
```

- Movie (setelah blok subtitle movie, sebelum `summary["items"].append`):

```python
        maybe_auto_backup(video_path, config, clean_title, year, "movie")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main_telegram.py -k auto_backup -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main_telegram.py
git commit -m "feat: automatic telegram backup after successful downloads"
```

---

### Task 15b: Verifikasi akhir & dokumentasi

**Files:**
- Modify: `PROJECT.md` (Feature Inventory + Interface Contracts), `README.md` (bagian fitur)

- [ ] **Step 1: Full test suite**

Run: `uv run pytest`
Expected: PASS semua tanpa warning error baru.

- [ ] **Step 2: Update PROJECT.md**

Tambahkan baris Feature Inventory:

```markdown
| 12| R5.1 Telegram Backup Platform | Login MTProto sekali, backup manual/auto, restore, split >2GB, forward multi-tujuan | Milestone 4 | SPEC telegram-backup |
| 13| R5.2 Hybrid Search & Guarded Delete | Search IDLIX+Telegram satu tabel, hapus lokal dengan peringatan belum-backup | Milestone 4 | SPEC telegram-backup |
```

Dan Interface Contracts:

```markdown
### `src/telegram_manager.py`
- `scan_backups(client, destinations) -> list[dict]`
- `upload_backup(client, file_path, sub_paths, meta, destinations, progress_callback=None, tmp_dir=None) -> dict`
- `restore_backup(client, item, config, progress_callback=None) -> str`
- `handle_telegram_menu(active_url: str, config: dict) -> None` (di `src/main.py`)
```

- [ ] **Step 3: Update README.md**

Tambahkan section singkat "📡 Telegram Backup" berisi: prasyarat (buat aplikasi di my.telegram.org), fitur backup manual/otomatis, restore via menu/search, batas 2GB + split otomatis, pengaman hapus.

- [ ] **Step 4: Commit**

```bash
git add PROJECT.md README.md
git commit -m "docs: document telegram backup platform features"
```

---

## Catatan Eksekusi

- Urutan task bersifat dependen (interface chain 1→15b); jangan loncat.
- Semua test Telegram memakai fake client — TIDAK ADA test yang menyentuh jaringan/akun asli.
- Jika `format_tv_paths` (Task 8) ternyata punya perilaku penamaan berbeda dari asumsi, test MENGIKUTI perilaku existing (spesifikasi folder harus tetap konsisten dengan instant local check).
- Known limitation (dokumentasikan di README bila sempat): pesan asing di antara dua part split dapat memutus pengelompokan scan; verifikasi ukuran saat restore menjadi jaring pengaman.
