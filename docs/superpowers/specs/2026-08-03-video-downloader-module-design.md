# Design Specification: Modular Video Downloader & Table UI Enhancements

**Date**: 2026-08-03
**Project**: I Am Not Pirates
**Status**: Draft for User Approval

---

## 1. Overview

Enhance **I Am Not Pirates** CLI with a modular media action system. This allows users to:
1. View cleaned media tables with a dedicated **Year** column.
2. Select any media item by its list number from any catalog list (Featured, Search, Categories, etc.).
3. Inspect and select video streaming quality (e.g., 1080p, 720p, 480p, 360p) and available subtitles (e.g., Indonesian, English).
4. Download the video stream directly to a configurable destination directory (defaulting to `C:\Users\<username>\Downloads`).

---

## 2. Component Architecture

```
src/
├── config_manager.py     # Download directory path configuration & persistence
├── scraper.py            # Page & catalog HTML/metadata scraper
├── ui.py                 # Rich UI renderer (Year column split, download prompts, tables)
├── video_extractor.py    # Playwright network interceptor for m3u8 playlists & subtitles
├── downloader.py         # yt-dlp wrapper for format inspection & video downloading
└── main.py               # Perpetual interactive CLI loop with item number selection
```

---

## 3. Key Specifications & Workflows

### 3.1 UI Table Enhancement (`src/ui.py`)
- Separate Year from Title string (e.g., Title: `Supergirl`, Year: `2026`).
- Render clean columns: `No | Title | Year | Type | Rating | URL`.

### 3.2 Dynamic Download Path Prompt (`src/config_manager.py`)
- Default path: `os.path.join(os.path.expanduser("~"), "Downloads")` (e.g. `C:\Users\aldinal21\Downloads`).
- Prompt user to press ENTER to use default or type a custom directory path.

### 3.3 Video Source & Subtitle Extraction (`src/video_extractor.py`)
- Navigates to target media page (`/movie/...` or `/series/...`).
- Intercepts player iframe (`govid`, `vidhide`, `filemoon`, etc.) and captures `.m3u8` master playlist URLs and subtitle URLs (`.vtt`, `.srt`).
- Passes master `.m3u8` to `downloader.py` (powered by `yt-dlp`).

### 3.4 Quality & Subtitle Selection (`src/downloader.py`)
- Queries available video formats (resolutions: 1080p, 720p, 480p, 360p, or Best Available).
- Queries available embedded/external subtitle tracks.
- Presents interactive choices using `questionary`:
  - Select Quality (e.g., `1080p (Best)`, `720p`, `480p`).
  - Select Subtitle (e.g., `Indonesian`, `English`, `None`).
- Downloads stream to chosen folder with Rich progress bar / status updates.

### 3.5 Reusable Sub-menu Flow (`src/main.py`)
- After displaying any media list, present action choices:
  - `📥 Download Film/Series` -> Input item # -> Quality & Subtitle Selection -> Download
  - `↩️ Kembali ke Menu Utama`

---

## 4. Verification Plan

- Unit tests for Year regex extraction in `src/ui.py`.
- Mock tests for `video_extractor.py` and `downloader.py`.
- Verification of default download path resolution (`Downloads` folder).
- Executable rebuild via PyInstaller (`IAmNotPirates.exe`).
