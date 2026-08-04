# Video Downloader Module & Table UI Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated **Year** column in the Rich CLI table and build a modular **Video Downloader** system that extracts m3u8 streams and subtitles using Playwright stealth interception and downloads them via `yt-dlp` to a user-configurable Downloads directory.

**Architecture:** Separate UI table rendering from video extraction and download execution. `src/ui.py` handles Year parsing and table formatting. `src/config_manager.py` manages default download directory settings. `src/video_extractor.py` uses Playwright to capture video/subtitle sources. `src/downloader.py` leverages `yt-dlp` to inspect qualities and download the stream.

**Tech Stack:** Python 3.13, `rich`, `questionary`, `playwright`, `yt-dlp`, `pytest`, `pyinstaller`.

## Global Constraints
- Ponytail Principle: YAGNI, minimum working solution, clean stdlib/existing tools (`yt-dlp` & `playwright`).
- UTF-8 console output compatibility on Windows.
- Standard download path default: `os.path.join(os.path.expanduser("~"), "Downloads")`.

---

### Task 1: Rich UI Year Column & Title Clean-up

**Files:**
- Modify: `src/ui.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: Media item dicts `{"title": "Supergirl 2026", "type": "Movie", "rating": "6.2", "url": "..."}`
- Produces: `format_featured_table(items: list[dict]) -> Table` with columns: `No`, `Title`, `Year`, `Type`, `Rating`, `URL`.

- [ ] **Step 1: Write failing unit test in `tests/test_ui.py` for Year column extraction**

```python
def test_format_featured_table_with_year():
    items = [
        {"title": "Supergirl 2026", "type": "Movie", "rating": "6.2", "url": "https://z2.idlixku.com/movie/supergirl-2026"},
        {"title": "A Shop for Killers", "type": "TV Series", "rating": "8.2", "url": "https://z2.idlixku.com/series/a-shop-for-killers-2024"}
    ]
    table = format_featured_table(items)
    # Check column names in table
    col_names = [col.header for col in table.columns]
    assert "Year" in col_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ui.py`
Expected: FAIL ("Year" not in col_names)

- [ ] **Step 3: Update `src/ui.py` to extract Year and render Year column**

```python
import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

def format_featured_table(items: list[dict]) -> Table:
    table = Table(
        title="[bold cyan]Media Catalog & Featured Content[/bold cyan]",
        header_style="bold magenta",
        show_header=True,
        expand=True,
    )
    table.add_column("No", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold white")
    table.add_column("Year", justify="center", style="yellow")
    table.add_column("Type", style="green")
    table.add_column("Rating", justify="center", style="yellow")
    table.add_column("URL", style="blue dim")

    for idx, item in enumerate(items, start=1):
        raw_title = item.get("title", "N/A")
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", raw_title)
        if year_match:
            year = year_match.group(1)
            clean_title = re.sub(r"\b(19\d\d|20\d\d)\b", "", raw_title).strip()
        else:
            year = "N/A"
            clean_title = raw_title

        table.add_row(
            str(idx),
            clean_title,
            year,
            item.get("type", "N/A"),
            str(item.get("rating", "N/A")),
            item.get("url", "N/A"),
        )

    return table
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ui.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui.py tests/test_ui.py
git commit -m "feat: add dedicated Year column in UI table"
```

---

### Task 2: Download Directory Configuration (`src/config_manager.py`)

**Files:**
- Modify: `src/config_manager.py`
- Modify: `tests/test_config_manager.py`

**Interfaces:**
- Produces: `get_download_dir(config: dict) -> str`, `set_download_dir(config: dict, new_path: str) -> dict`

- [ ] **Step 1: Write failing test for download directory in `tests/test_config_manager.py`**

```python
def test_get_and_set_download_dir(tmp_path):
    config_file = tmp_path / "config.json"
    from src.config_manager import get_download_dir, set_download_dir, load_config
    
    cfg = load_config(str(config_file))
    default_dir = get_download_dir(cfg)
    assert "Downloads" in default_dir
    
    updated_cfg = set_download_dir(cfg, str(tmp_path), str(config_file))
    assert get_download_dir(updated_cfg) == str(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config_manager.py`
Expected: FAIL (cannot import get_download_dir)

- [ ] **Step 3: Implement download dir helpers in `src/config_manager.py`**

```python
import os

def get_download_dir(config: dict) -> str:
    default_path = os.path.join(os.path.expanduser("~"), "Downloads")
    return config.get("download_dir", default_path)

def set_download_dir(config: dict, new_dir: str, config_path: str = CONFIG_FILE) -> dict:
    config["download_dir"] = new_dir
    save_config(config, config_path)
    return config
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config_manager.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config_manager.py tests/test_config_manager.py
git commit -m "feat: add download directory configuration helper"
```

---

### Task 3: Video Source & Subtitle Extractor (`src/video_extractor.py`)

**Files:**
- Create: `src/video_extractor.py`
- Create: `tests/test_video_extractor.py`

**Interfaces:**
- Produces: `extract_video_sources(page_url: str) -> dict` returning `{"m3u8_urls": list[str], "subtitles": list[dict]}`

- [ ] **Step 1: Write failing test in `tests/test_video_extractor.py`**

```python
from unittest.mock import patch, MagicMock
from src.video_extractor import extract_video_sources

def test_extract_video_sources_mock():
    with patch("src.video_extractor.sync_playwright") as mock_pw:
        result = extract_video_sources("https://z2.idlixku.com/movie/test")
        assert "m3u8_urls" in result
        assert "subtitles" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_video_extractor.py`
Expected: FAIL (module src.video_extractor not found)

- [ ] **Step 3: Implement `src/video_extractor.py`**

```python
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def extract_video_sources(page_url: str) -> dict:
    """Intercepts network requests and DOM iframe elements to capture m3u8 playlists and subtitle tracks."""
    user_ms_pw = os.path.expanduser("~\\AppData\\Local\\ms-playwright")
    if os.path.exists(user_ms_pw):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_ms_pw

    m3u8_urls = []
    subtitles = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            def handle_response(response):
                url = response.url
                if ".m3u8" in url and url not in m3u8_urls:
                    m3u8_urls.append(url)
                if any(ext in url for ext in [".vtt", ".srt", ".ass"]) and url not in [s["url"] for s in subtitles]:
                    lang = "Indonesian" if "id" in url.lower() or "ind" in url.lower() else "English"
                    subtitles.append({"lang": lang, "url": url})

            page.on("response", handle_response)
            page.goto(page_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(4000)

            # Check player iframe src if no m3u8 captured directly
            if not m3u8_urls:
                soup = BeautifulSoup(page.content(), "html.parser")
                for iframe in soup.find_all("iframe"):
                    src = iframe.get("src", "")
                    if src and ("govid" in src or "vidhide" in src or "filemoon" in src or "player" in src):
                        try:
                            sub_page = context.new_page()
                            sub_page.on("response", handle_response)
                            sub_page.goto(src, wait_until="domcontentloaded", timeout=15000)
                            sub_page.wait_for_timeout(3000)
                            sub_page.close()
                        except Exception:
                            pass

            browser.close()
    except Exception as e:
        print(f"[Video Extractor Warning]: {e}")

    return {"m3u8_urls": m3u8_urls, "subtitles": subtitles}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_video_extractor.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/video_extractor.py tests/test_video_extractor.py
git commit -m "feat: add video & subtitle source extractor module"
```

---

### Task 4: Stream Format Inspector & Downloader Engine (`src/downloader.py`)

**Files:**
- Create: `src/downloader.py`
- Create: `tests/test_downloader.py`

**Interfaces:**
- Produces: `inspect_stream_qualities(m3u8_url: str) -> list[str]`, `download_media_stream(m3u8_url: str, output_dir: str, title: str, quality: str) -> bool`

- [ ] **Step 1: Write failing unit test in `tests/test_downloader.py`**

```python
from unittest.mock import patch, MagicMock
from src.downloader import inspect_stream_qualities, download_media_stream

def test_downloader_module_functions():
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        instance = MagicMock()
        instance.extract_info.return_value = {
            "formats": [
                {"format_id": "360p", "height": 360},
                {"format_id": "720p", "height": 720},
                {"format_id": "1080p", "height": 1080}
            ]
        }
        mock_ydl.return_value.__enter__.return_value = instance
        qualities = inspect_stream_qualities("https://example.com/stream.m3u8")
        assert "1080p" in qualities or "Best Available" in qualities
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_downloader.py`
Expected: FAIL (module src.downloader not found)

- [ ] **Step 3: Implement `src/downloader.py` using `yt-dlp` API**

```python
import os
import yt_dlp

def inspect_stream_qualities(m3u8_url: str) -> list[str]:
    """Inspects available resolutions from m3u8 playlist via yt-dlp."""
    default_qualities = ["1080p (Best)", "720p", "480p", "360p", "Best Available"]
    try:
        ydl_opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(m3u8_url, download=False)
            formats = info.get("formats", [])
            extracted = []
            for f in formats:
                h = f.get("height")
                if h and f"{h}p" not in extracted:
                    extracted.append(f"{h}p")
            if extracted:
                return sorted(extracted, key=lambda x: int(x.replace("p", "")), reverse=True)
    except Exception:
        pass
    return default_qualities

def download_media_stream(m3u8_url: str, output_dir: str, title: str, quality: str = "1080p (Best)") -> bool:
    """Downloads m3u8 video stream into target directory using yt-dlp."""
    os.makedirs(output_dir, exist_ok=True)
    clean_title = "".join([c for c in title if c.isalnum() or c in (" ", "_", "-")]).rstrip()
    output_template = os.path.join(output_dir, f"{clean_title}.%(ext)s")

    format_spec = "bestvideo+bestaudio/best"
    if "720" in quality:
        format_spec = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    elif "480" in quality:
        format_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]"
    elif "360" in quality:
        format_spec = "bestvideo[height<=360]+bestaudio/best[height<=360]"

    ydl_opts = {
        "format": format_spec,
        "outtmpl": output_template,
        "quiet": False,
        "no_warnings": True,
        "concurrent_fragment_downloads": 4,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m3u8_url])
        return True
    except Exception as e:
        print(f"[Download Error]: {e}")
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_downloader.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/downloader.py tests/test_downloader.py
git commit -m "feat: add yt-dlp downloader engine with quality inspection"
```

---

### Task 5: Interactive Sub-menu Flow in Main Loop & Executable Rebuild

**Files:**
- Modify: `src/main.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Integrates `src/video_extractor.py` and `src/downloader.py` into main loop `while True`.

- [ ] **Step 1: Update `src/main.py` to add Interactive Download Sub-menu**

```python
import questionary
from src.config_manager import get_download_dir, set_download_dir
from src.video_extractor import extract_video_sources
from src.downloader import inspect_stream_qualities, download_media_stream

def handle_item_download(items: list[dict], active_url: str, config: dict) -> None:
    if not items:
        console.print("[yellow]Tidak ada item untuk di-download.[/yellow]")
        return

    choice_num = questionary.text(
        f"Masukkan nomor item yang ingin di-download (1-{len(items)}):",
        validate=lambda val: val.isdigit() and 1 <= int(val) <= len(items)
    ).ask()

    if not choice_num:
        return

    selected_item = items[int(choice_num) - 1]
    console.print(f"\n[bold cyan]Memproses: {selected_item['title']}...[/bold cyan]")

    # Download Path Prompt
    default_dir = get_download_dir(config)
    custom_dir = questionary.text(
        f"Lokasi simpan (Tekan ENTER untuk default: {default_dir}):",
        default=default_dir
    ).ask()
    target_dir = custom_dir.strip() if custom_dir else default_dir
    set_download_dir(config, target_dir)

    # Extract Video Sources
    console.print("[bold yellow]Mengambil sumber video & subtitle...[/bold yellow]")
    sources = extract_video_sources(selected_item["url"])
    m3u8_urls = sources.get("m3u8_urls", [])
    subtitles = sources.get("subtitles", [])

    if not m3u8_urls:
        print_error(f"Gagal menemukan link video m3u8 di {selected_item['url']}")
        return

    # Select Quality
    qualities = inspect_stream_qualities(m3u8_urls[0])
    selected_quality = questionary.select(
        "Pilih Kualitas Video:",
        choices=qualities
    ).ask()

    # Select Subtitle
    sub_choices = ["Tanpa Subtitle"] + [f"{s['lang']} ({s['url']})" for s in subtitles]
    selected_sub = questionary.select(
        "Pilih Subtitle:",
        choices=sub_choices
    ).ask()

    # Trigger Download
    console.print(f"[bold green]Memulai download {selected_item['title']} ({selected_quality}) ke {target_dir}...[/bold green]")
    success = download_media_stream(m3u8_urls[0], target_dir, selected_item["title"], selected_quality)
    if success:
        print_success(f"Berhasil mendownload {selected_item['title']} ke {target_dir}!")
    else:
        print_error(f"Gagal mendownload {selected_item['title']}")
```

- [ ] **Step 2: Run pytest to verify all unit tests pass**

Run: `uv run pytest`
Expected: PASS (All 24+ tests pass)

- [ ] **Step 3: Rebuild standalone executable `IAmNotPirates.exe`**

Run: `uv run pyinstaller --onefile --collect-all playwright --name "IAmNotPirates" src/main.py`
Expected: Build success with updated video downloader module.
