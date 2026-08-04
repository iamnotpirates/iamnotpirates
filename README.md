# 🏴‍☠️ I Am Not Pirates — CLI Media Scraper & Downloader

A high-performance, modern interactive Python CLI application to browse, search, and automatically download Movies and TV Series. Powered by the ultra-fast multi-threaded **N_m3u8DL-RE** download engine, SQLite database management, **Jellyfin / Plex** standard media folder structure, automatic subtitle conversion, and a **Smart FFmpeg Auto-Healing System**.

---

## ✨ Key Features

- **🔍 Fast Media Search**: Search for movies or TV series directly by title from the CLI via internal API integration.
- **⚡ High-Speed Downloader (N_m3u8DL-RE)**:
  - Downloads HLS/DASH `.m3u8` streams with 16 parallel threads.
  - Automatically fetches and manages the official `N_m3u8DL-RE.exe` binary under `~/.iamnotpirates/bin/` on first run.
  - Clean cancellation handling via `Ctrl + C`.
- **📺 Jellyfin / Plex Standard Folder Structure**:
  - Automatic organization for TV Series: `TV Series/<Show Title> (<Year>)/Season <0X>/<Show Title> - S<0X>E<0Y>.<ext>`.
  - Fail-safe sequential multi-select episode navigation with a `⬅ Back` option at every step.
- **📝 Automatic Subtitle Conversion**:
  - Downloads multi-language VTT/SRT subtitles (`.id.srt` & `.en.srt`).
  - Automatically associated with media files matching Jellyfin/Plex conventions.
- **🛡️ Smart FFmpeg Auto-Healing System**:
  - Auto-downloads official `ffmpeg.exe` & `ffprobe.exe` binaries to `~/.iamnotpirates/bin/`.
  - **3-Level Health Check**:
    - **Corrupt / 0-Byte Video**: Automatically deletes corrupted files and re-downloads video + subtitles.
    - **Healthy Video, Missing Subtitles**: **Downloads missing subtitles only** without re-downloading existing video files.
    - **Healthy Video & Subtitles**: Instantly skips download.
- **🗃️ Persistent SQLite Database & Download Log**:
  - Stores application settings, target URLs, and download history in `~/.iamnotpirates/data/data.db`.
  - **1-Click Retry All Failed**: Easily retry all failed downloads.
- **🛠️ Custom Directory & Organization Settings**:
  - Choose between `separate` mode (Movies & Series stored in individual folders) or `combined` mode (Single output directory).
  - Configure custom download directories directly from the CLI settings menu.

---

## 🛠️ Prerequisites & Installation

### Using `uv` (Recommended)
This application is managed using **`uv`** (an ultra-fast Python package manager).

1. Clone this repository:
   ```bash
   git clone https://github.com/aldinal21/iamnotpirates.git
   cd iamnotpirates
   ```

2. Run the application directly (dependencies are installed automatically):
   ```bash
   uv run python src/main.py
   ```

---

## 🚀 Usage Guide

### 1. Running Development Mode
```bash
uv run python src/main.py
```

### 2. Interactive Main Menu
Once launched, you will be presented with an interactive CLI menu:

```text
==================================================
 🏴‍☠️ I AM NOT PIRATES — CLI Media Downloader
==================================================
 1. 🔍 Search Movie / TV Series
 2. 🔥 Browse Featured Content
 3. 🔄 Retry All Failed Downloads
 4. 🛠️ Settings (Directories & Mode)
 5. 🌐 Manage IDLIX Target URLs
 6. ❌ Exit
```

- Select **`🔍 Search Movie / TV Series`** and type any keyword (e.g. *"Avatar"* or *"One Piece"*).
- Select your desired episodes or movie; extraction and downloading will process automatically!

---

## 🧪 Unit Testing

This project is built using **Test-Driven Development (TDD)** with complete test coverage.

To run the full test suite (80+ unit tests):
```bash
uv run pytest
```

---

## 📦 Building Standalone Executable (`.exe`)

Compile the application into a single standalone Windows executable binary (no Python installation required):

```bash
uv run pyinstaller IAmNotPirates.spec --clean
```

The output binary will be generated at `dist/IAmNotPirates.exe`.

---

## 📁 Project Directory Structure

```text
iamnotpirates/
├── src/
│   ├── main.py               # CLI entry point & interactive menu loop
│   ├── scraper.py            # Playwright scraper & IDLIX JSON API client
│   ├── video_extractor.py    # HLS stream extractor & claim token handler
│   ├── series_extractor.py   # TV Series episode extractor & season parser
│   ├── downloader.py         # Jellyfin path formatter & batch subtitle downloader
│   ├── n_m3u8dl_manager.py   # N_m3u8DL-RE subprocess wrapper & binary manager
│   ├── ffmpeg_manager.py     # FFmpeg binary manager & media health verifier
│   ├── db_manager.py         # SQLite database & configuration manager
│   └── ui.py                 # Rich console UI & banner helpers
├── tests/                    # 80+ Pytest unit test suite
├── docs/                     # Architecture documentation, SDD specs & plans
├── IAmNotPirates.spec        # PyInstaller build specification
├── pyproject.toml            # Project dependencies & pytest configuration
└── README.md                 # Project documentation
```

---

## ⚖️ License & Disclaimer

This application is created for educational purposes, scraping architecture research, and Proof of Concept (PoC) only. Users assume full responsibility for using this tool in compliance with applicable local laws and service terms.
