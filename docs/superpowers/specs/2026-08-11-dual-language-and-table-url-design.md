# Dual-Language CLI & Rich Table URL Formatting Design Spec

> **Date:** 2026-08-11
> **Status:** Approved
> **Target Release:** v1.1.1 (or minor follow-up)

## Goal

Enhance `IAmNotPirates` CLI user experience by:
1. Converting all CLI interactive menus, prompts, headers, and banners to a simultaneous dual-language format (**English first, Indonesian second**).
2. Optimizing Rich Table rendering in `format_featured_table()` and search result tables so URLs use concise Rich hyperlinks (`[link=FULL_URL]🔗 domain/path...[/link]`). This prevents long URLs from squishing movie titles down to single-character vertical lines.

---

## 1. Dual-Language Formatting (English First / Indonesian Second)

### Banners & Banners (`src/ui.py`)
- Header Panel:
  - Title: `I AM NOT PIRATES`
  - Text: `I AM NOT PIRATES CLI v1.1.0\nTarget URL / URL Target: <url>`
  - Subtitle: `Streaming & Media Explorer / Penjelajah Media & Streaming v1.1.0`

### Interactive Main Menu (`src/main.py`)
- Menu options:
  1. `🔍 Search Movie & TV Series / Cari Film & TV Series`
  2. `🔥 Browse Featured Content / Lihat Content Populer`
  3. `📋 Download Log & Retry / Log & Retry Download Gagal`
  4. `🛠️  Settings / Pengaturan (Folder & Mode)`
  5. `🌐 Switch Target URL / Pilih Active Target URL`
  6. `➕ Add New Target URL / Tambah Target URL Baru`
  7. `⚙️  Manage Target URLs / Kelola Daftar Target URL`
  8. `❌ Exit / Keluar`

### Submenu Prompts & Confirmations (`src/main.py`, `src/downloader.py`, `src/scraper.py`, `src/series_extractor.py`)
- Standardized dual-language prompt text:
  - Input prompts: `Enter search keyword / Masukkan kata kunci pencarian:`
  - Selection prompts: `Select Season / Pilih Season:`, `Select Episode / Pilih Episode:`
  - Confirmation prompts: `Are you sure? / Apakah Anda yakin?`
  - Success/Error alerts: `Success: Download completed / Sukses: Download selesai`

---

## 2. Rich Table URL Optimization (`src/ui.py`)

### Problem
Currently, `format_featured_table()` sets `table.add_column("URL", style="blue underline", no_wrap=True)` with full un-truncated URL strings (~70 chars). Under `expand=True`, Rich allocates nearly all terminal width to the URL column, forcing the `Title` column to compress down to 1-2 characters per line.

### Solution
1. **Truncated Display Text with Hyperlink**:
   Format item URLs as `[link=FULL_URL]🔗 <domain>/<shortened_path>[/link]`.
   Display text is truncated to ~25 characters (e.g., `🔗 idlix.vip/movie/avatar...`), while preserving the full target URL inside the OSC 8 `[link=...]` tag.
2. **Column Constraints**:
   - `No`: `justify="right"`, `style="cyan"`, `no_wrap=True`
   - `Title / Judul`: `style="bold white"`, `ratio=3`, `no_wrap=False`
   - `Year / Tahun`: `justify="center"`, `style="yellow"`, `no_wrap=True`
   - `Type / Tipe`: `style="green"`, `justify="center"`, `no_wrap=True`
   - `Quality / Kualitas`: `justify="center"`, `style="bold green"`, `no_wrap=True`
   - `Rating`: `justify="center"`, `style="yellow"`, `no_wrap=True`
   - `URL / Link`: `style="blue underline"`, `ratio=2`, `no_wrap=True`

---

## 3. Testing Strategy & Verification Plan

1. **Unit Tests**:
   - Update `tests/test_ui.py` to verify new table header names (`Title / Judul`, `URL / Link`) and truncated hyperlink formatting.
   - Update `tests/test_main.py` and `tests/test_workflows.py` to match dual-language menu choices.
2. **Full Regression Suite**:
   - Ensure all 100+ tests pass with `uv run pytest -v`.
3. **Coverage Check**:
   - Run `uv run --with pytest-cov pytest --cov=src` to verify code coverage remains >90%.
