# TV Series Downloader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive TV Series downloader functionality with Season/Episode selection, batch downloading, resilient error handling, and Jellyfin standard folder/file naming.

**Architecture:** Create a dedicated `src/series_extractor.py` module to parse series structure and extract episode streams via IDLIX Next.js API endpoints. Enhance `src/downloader.py` with Jellyfin path formatting and multi-subtitle capabilities. Integrate TV Series workflow branching into `src/main.py`.

**Tech Stack:** Python 3.13, `curl_cffi`, `BeautifulSoup4`, `questionary`, `rich`, `pytest`, `PyInstaller`, `uv`.

## Global Constraints

- Must follow Jellyfin naming format: `Downloads/<Show Title> (<Year>)/Season <0X>/<Show Title> - S<0X>E<0Y>.<ext>`
- All unit test runs must use `uv run pytest`.
- Rely entirely on IDLIX Next.js API (`/api/series/<slug>`, `/api/watch/play-info/series/<id>`, etc.) without external TMDb dependencies.

---

### Task 1: Create Series Extractor Module (`src/series_extractor.py`)

**Files:**
- Create: `src/series_extractor.py`
- Test: `tests/test_series_extractor.py`

**Interfaces:**
- Consumes: IDLIX series URL or slug (e.g. `https://z2.idlixku.com/series/breaking-bad` or `breaking-bad`).
- Produces: 
  - `fetch_series_details(page_url_or_slug: str) -> dict`: Returns `{"title": str, "year": str, "seasons": list[dict]}` where each season contains episodes with `season_num`, `episode_num`, `title`, and `media_id` / `slug`.
  - `extract_episode_sources(episode_media_id: str | int, page_url: str) -> dict`: Returns `{"m3u8_urls": list[str], "subtitles": list[dict]}`.

- [ ] **Step 1: Write failing tests for series extractor**

```python
# tests/test_series_extractor.py
import pytest
from unittest.mock import patch, MagicMock
from src.series_extractor import fetch_series_details, extract_episode_sources

def test_fetch_series_details_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "title": "Breaking Bad",
        "year": "2008",
        "seasons": [
            {
                "season": 1,
                "episodes": [
                    {"episode": 1, "title": "Pilot", "id": 101},
                    {"episode": 2, "title": "Cat's in the Bag...", "id": 102}
                ]
            }
        ]
    }
    with patch("src.series_extractor.requests.Session.get", return_value=mock_resp):
        res = fetch_series_details("https://z2.idlixku.com/series/breaking-bad")
        assert res["title"] == "Breaking Bad"
        assert len(res["seasons"]) == 1
        assert len(res["seasons"][0]["episodes"]) == 2
        assert res["seasons"][0]["episodes"][0]["title"] == "Pilot"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_series_extractor.py -v`  
Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement minimal code in `src/series_extractor.py`**

```python
# src/series_extractor.py
import time
from curl_cffi import requests

def fetch_series_details(page_url_or_slug: str) -> dict:
    slug = page_url_or_slug.rstrip("/").split("/")[-1]
    session = requests.Session(impersonate="chrome120")
    headers = {
        "Origin": "https://z2.idlixku.com",
        "Referer": f"https://z2.idlixku.com/series/{slug}",
        "Accept": "application/json, text/plain, */*",
    }
    endpoint = f"https://z2.idlixku.com/api/series/{slug}"
    try:
        r = session.get(endpoint, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            title = data.get("title", slug.replace("-", " ").title())
            year = str(data.get("year", "N/A"))
            seasons_raw = data.get("seasons", [])
            seasons = []
            for s in seasons_raw:
                s_num = s.get("season", 1)
                eps = []
                for ep in s.get("episodes", []):
                    eps.append({
                        "episode_num": ep.get("episode", 1),
                        "title": ep.get("title", f"Episode {ep.get('episode', 1)}"),
                        "media_id": ep.get("id", ""),
                        "slug": ep.get("slug", "")
                    })
                seasons.append({
                    "season_num": s_num,
                    "episodes": eps
                })
            return {"title": title, "year": year, "seasons": seasons}
    except Exception as e:
        print(f"[Series Extractor Error]: {e}")
    return {"title": slug.replace("-", " ").title(), "year": "N/A", "seasons": []}

def extract_episode_sources(episode_media_id: str | int, page_url: str) -> dict:
    session = requests.Session(impersonate="chrome120")
    headers = {
        "Origin": "https://z2.idlixku.com",
        "Referer": page_url,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }
    try:
        play_info_url = f"https://z2.idlixku.com/api/watch/play-info/series/{episode_media_id}"
        r_info = session.get(play_info_url, headers=headers)
        if r_info.status_code != 200:
            return {"m3u8_urls": [], "subtitles": []}

        info_data = r_info.json()
        gate_token = info_data.get("gateToken")
        if not gate_token:
            return {"m3u8_urls": [], "subtitles": []}

        unlock_at = info_data.get("unlockAt", 0) / 1000.0
        server_now = info_data.get("serverNow", 0) / 1000.0
        wait_sec = max(0, unlock_at - server_now) + 0.5
        if wait_sec > 0:
            time.sleep(wait_sec)

        r_claim = session.post("https://z2.idlixku.com/api/watch/session/claim", json={"gateToken": gate_token}, headers=headers)
        if r_claim.status_code != 200:
            return {"m3u8_urls": [], "subtitles": []}

        claim_data = r_claim.json()
        claim_token = claim_data.get("claim")
        redeem_url = claim_data.get("redeemUrl")
        if not claim_token or not redeem_url:
            return {"m3u8_urls": [], "subtitles": []}

        r_redeem = session.post(redeem_url, json={"claim": claim_token}, headers=headers)
        if r_redeem.status_code != 200:
            return {"m3u8_urls": [], "subtitles": []}

        final_data = r_redeem.json()
        m3u8_master = final_data.get("url")
        sub_list = final_data.get("subtitles", [])
        subtitles = [{"lang": s.get("label", s.get("lang", "Subtitle")), "url": s.get("path", "")} for s in sub_list]
        return {"m3u8_urls": [m3u8_master] if m3u8_master else [], "subtitles": subtitles}
    except Exception as e:
        print(f"[Episode Extractor Warning]: {e}")
    return {"m3u8_urls": [], "subtitles": []}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_series_extractor.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/series_extractor.py tests/test_series_extractor.py
git commit -m "feat: add series_extractor module for IDLIX TV series API"
```

---

### Task 2: Enhance Downloader Helper for Jellyfin Paths & Subtitles (`src/downloader.py`)

**Files:**
- Modify: `src/downloader.py`
- Modify: `tests/test_downloader.py`

**Interfaces:**
- Consumes: `show_title`, `year`, `season_num`, `episode_num`, `target_dir`
- Produces: 
  - `format_tv_paths(show_title: str, year: str, season_num: int, episode_num: int, target_dir: str) -> tuple[str, str]`: returns `(season_dir_path, base_filename)` where season_dir_path is `target_dir/Show Title (Year)/Season 01` and base_filename is `Show Title - S01E01`.
  - `download_subtitles_batch(subtitles: list[dict], base_filepath: str, sub_mode: str) -> list[str]`: downloads `.id.srt`, `.en.srt`, or all available subtitles matching `sub_mode`.

- [ ] **Step 1: Write failing test in `tests/test_downloader.py`**

```python
from src.downloader import format_tv_paths

def test_format_tv_paths():
    season_dir, base_file = format_tv_paths("Breaking Bad", "2008", 1, 5, "Downloads")
    assert "Breaking Bad (2008)" in season_dir
    assert "Season 01" in season_dir
    assert base_file == "Breaking Bad - S01E05"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_downloader.py::test_format_tv_paths -v`  
Expected: FAIL with `ImportError: cannot import name 'format_tv_paths'`.

- [ ] **Step 3: Implement `format_tv_paths` and `download_subtitles_batch` in `src/downloader.py`**

Add functions to `src/downloader.py`:
```python
def format_tv_paths(show_title: str, year: str, season_num: int, episode_num: int, target_dir: str) -> tuple[str, str]:
    clean_title = re.sub(r'[\\/*?:"<>|]', "", show_title).strip()
    year_str = f" ({year})" if year and year != "N/A" else ""
    folder_name = f"{clean_title}{year_str}"
    season_folder = f"Season {int(season_num):02d}"
    
    season_dir = os.path.join(target_dir, folder_name, season_folder)
    base_file = f"{clean_title} - S{int(season_num):02d}E{int(episode_num):02d}"
    return season_dir, base_file

def download_subtitles_batch(subtitles: list[dict], base_video_path: str, sub_mode: str) -> list[str]:
    saved_paths = []
    if not subtitles or sub_mode == "Tanpa Subtitle":
        return saved_paths

    base_without_ext = os.path.splitext(base_video_path)[0]

    for s in subtitles:
        lang_raw = s.get("lang", "").lower()
        sub_url = s.get("url", "")
        if not sub_url:
            continue

        is_id = "ind" in lang_raw or "id" in lang_raw
        is_en = "eng" in lang_raw or "en" in lang_raw

        if sub_mode == "Indonesia saja" and not is_id:
            continue
        if sub_mode == "English saja" and not is_en:
            continue

        lang_code = "id" if is_id else ("en" if is_en else "sub")
        target_srt = f"{base_without_ext}.{lang_code}.srt"

        if download_subtitle(sub_url, target_srt):
            saved_paths.append(target_srt)

    return saved_paths
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_downloader.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/downloader.py tests/test_downloader.py
git commit -m "feat: add format_tv_paths and download_subtitles_batch helpers"
```

---

### Task 3: Integrate TV Series Workflow in `src/main.py`

**Files:**
- Modify: `src/main.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `fetch_series_details`, `extract_episode_sources`, `format_tv_paths`, `download_subtitles_batch`
- Produces: Updated `handle_item_download` that handles both Movies and TV Series multi-episode selection with resilient error handling.

- [ ] **Step 1: Write failing test in `tests/test_main.py`**

Add test for TV series download handler branching in `tests/test_main.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main.py -v`

- [ ] **Step 3: Implement TV Series download branching in `src/main.py`**

In `src/main.py`, update `handle_item_download`:
- Detect if item is a TV Series (`selected_item.get("type") == "TV Series"` or `"/series/" in item_url`).
- If TV Series:
  1. Fetch series details (`fetch_series_details`).
  2. Prompt Season selection (`questionary.select`).
  3. Prompt Episode multi-selection (`questionary.checkbox` with `choices` mapped to episode titles).
  4. Prompt Target Directory once.
  5. Inspect quality on the first episode or prompt default (`questionary.select`).
  6. Prompt Subtitle preference (`Semua Subtitle Tersedia`, `Indonesia saja`, `English saja`, `Tanpa Subtitle`).
  7. Loop over selected episodes:
     - Wrap in `try-except`.
     - Extract stream (`extract_episode_sources`).
     - Format paths (`format_tv_paths`).
     - Download video (`download_media_stream`).
     - Download subtitles (`download_subtitles_batch`).
     - Log success/failure per episode.

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_main.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add interactive TV series multi-episode batch download to main CLI"
```

---

### Task 4: Executable Build & Full Test Verification

**Files:**
- Verify build: `dist/IAmNotPirates.exe`

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest`  
Expected: All tests PASS.

- [ ] **Step 2: Build standalone executable using PyInstaller**

Run: `uv run pyinstaller IAmNotPirates.spec --clean`  
Expected: Build succeeds and updates `dist/IAmNotPirates.exe`.

- [ ] **Step 3: Commit final build configuration / executable state**

```bash
git add .
git commit -m "build: rebuild standalone executable with TV series downloader support"
```
