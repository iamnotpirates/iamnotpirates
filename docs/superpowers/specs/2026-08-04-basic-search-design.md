# Design Spec: Basic Search & Home Menu Renaming

**Date:** 2026-08-04  
**Project:** IAmNotPirates CLI  
**Status:** Approved by User  

## 1. Overview
This feature introduces a basic media search functionality using the IDLIX internal JSON API (`/api/search?q=<query>`) and renames the home menu items for better clarity.

## 2. Main Menu Changes (`src/main.py`)
Renamed and new options in main menu:
1. `🔍 Cari Film / TV Series` *(New)*
2. `🔥 Lihat Featured Content` *(Renamed from Scrape Featured Content)*
3. `📋 Lihat & Retry Download Gagal`
4. `🛠️  Pengaturan (Folder & Mode)`
5. `🌐 Pilih / Ganti Active Target URL`
6. `➕ Tambah URL Target Baru`
7. `⚙️  Manage List URL (Edit/Delete)`
8. `❌ Exit Program`

## 3. Scraper Module Extensions (`src/scraper.py`)
Add function:
`search_content(target_url: str, query: str) -> list[dict]`

### Logic:
- Perform `GET <target_url>/api/search?q=<query>` using `curl_cffi.requests`.
- Parse response JSON `results` array.
- For each item:
  - `title`: `item.get("title")` or `item.get("name")`
  - `slug`: `item.get("slug")`
  - `contentType`: `"movie"` -> `type`: `"Movie"`, URL: `<target_url>/movie/<slug>`
  - `contentType`: `"tv_series"` -> `type`: `"TV Series"`, URL: `<target_url>/series/<slug>`
  - `year`: Extract from `releaseDate` or `slug` / `title` regex.
  - `rating`: `item.get("voteAverage")` formatted or `"N/A"`
- Returns standard `list[dict]` compatible with `format_featured_table()` and `handle_item_download()`.

## 4. Main Workflow Integration (`src/main.py`)
Add function:
`handle_search(active_url: str, config: dict) -> None`

### Logic:
1. Prompt for search term: `questionary.text("Masukkan judul film/series yang dicari:").ask()`
2. If blank/canceled, return.
3. Fetch results via `search_content()`.
4. If no results, print `[yellow]Tidak ada hasil untuk "<query>".[/yellow]`.
5. If results found, display Rich Table using existing UI formatting.
6. Display options:
   - `📥 Download Film/Series` -> call `handle_item_download(items, active_url, config)`
   - `🔍 Cari Judul Lain` -> loop prompt
   - `↩️ Kembali ke Menu Utama` -> return

## 5. Testing & Verification Plan
1. Unit tests in `tests/test_scraper.py`: mock API response for `/api/search?q=avatar` and verify returned items list structure.
2. Unit tests in `tests/test_main.py`: test `handle_search` flow with search queries.
3. Full test suite execution: `uv run pytest`.
