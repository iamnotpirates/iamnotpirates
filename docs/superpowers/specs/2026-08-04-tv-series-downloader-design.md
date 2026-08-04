# Design Specification: TV Series Downloader Module

Date: 2026-08-04  
Project: IAmNotPirates  
Feature: Interactive TV Series Downloader with Multi-Episode Batch Support & Jellyfin Naming Standard  

---

## 1. Overview
This specification details the addition of a TV Series Downloader module to the IAmNotPirates CLI application. It enables users to browse Seasons and Episodes of TV Series available on IDLIX, select multiple episodes for batch downloading, and automatically organize downloaded media and subtitles according to Jellyfin/Plex standard directory structures.

---

## 2. Requirements & Key Decisions

1. **IDLIX API Metadata Extraction**:
   - Extract season lists, episode lists, episode titles, and episode media IDs directly from IDLIX API endpoints (`https://z2.idlixku.com/api/series/<slug>`).
   - No external TMDb API dependency required.

2. **Interactive CLI Navigation Flow**:
   - Step 1: Detect if selected item is a TV Series.
   - Step 2: Prompt user to select a Season (e.g. `Season 1`, `Season 2`).
   - Step 3: Prompt user to multi-select Episode(s) within the chosen season using `questionary.checkbox` (support "Select All" option).
   - Step 4: Prompt user for Video Quality once for the entire batch.
   - Step 5: Prompt user for Subtitle options:
     - `Semua Subtitle Tersedia` (All available subtitle streams)
     - `Indonesia (id.srt)`
     - `English (en.srt)`
     - `Tanpa Subtitle`

3. **Batch Execution & Error Handling**:
   - Downloads run sequentially (1 episode at a time).
   - Each episode download is wrapped in isolated exception handling. If 1 episode fails, it logs the failure and continues processing the remaining episodes.

4. **Directory Structure & Naming Standard (Jellyfin/Plex)**:
   - Root Folder: `Downloads/<Show Title> (<Year>)/Season <0X>/`
   - Video File: `<Show Title> - S<0X>E<0Y>.<ext>`
   - Subtitle Files: `<Show Title> - S<0X>E<0Y>.<lang_code>.srt` (e.g. `.id.srt`, `.en.srt`).

---

## 3. Architecture & Data Flow

### 3.1 New & Modified Modules

- `src/series_extractor.py` (New):
  - `fetch_series_details(series_url_or_slug: str) -> dict`: Queries `/api/series/<slug>` to return structured Season & Episode hierarchy.
  - `extract_episode_sources(episode_media_id: int | str, series_slug: str) -> dict`: Executes the play-info -> gate token claim -> redeem endpoint sequence to get master m3u8 playlist and subtitle links for an episode.

- `src/downloader.py` (Enhanced):
  - Add helper function `format_tv_paths(show_title: str, year: str, season_num: int, episode_num: int, target_dir: str) -> tuple[str, str]`: Generates directory path and base file name following Jellyfin standards.
  - Add support for downloading all available subtitle tracks (`download_all_subtitles(...)`).

- `src/main.py` (Enhanced):
  - Update `handle_item_download(...)` to branch between Movie download workflow and TV Series download workflow.

---

## 4. Example Output Structure

```text
Downloads/
└── Breaking Bad (2008)/
    └── Season 01/
        ├── Breaking Bad - S01E01.mp4
        ├── Breaking Bad - S01E01.id.srt
        ├── Breaking Bad - S01E01.en.srt
        ├── Breaking Bad - S01E02.mp4
        ├── Breaking Bad - S01E02.id.srt
        └── Breaking Bad - S01E02.en.srt
```

---

## 5. Verification Plan

1. Verify series metadata retrieval from IDLIX API using unit tests / test scripts.
2. Verify interactive season/episode selection and multi-select checkbox UI.
3. Test sequential batch downloading with simulated stream extraction.
4. Verify folder creation and file naming compliance with Jellyfin standards.
