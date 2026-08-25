# Instant Local Checks Sebelum Web Scraping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membaca status lokal file (keberadaan dan kesehatan) sebelum melakukan web scraping untuk modul Movies dan TV Series agar performa unduhan instan.

**Architecture:** Memindahkan pemanggilan `is_already_downloaded` dan `verify_media_file` sebelum request web scraper dipanggil. Jika file lokal ada dan lengkap, log skipped ke DB dan langsung kembali/lanjutkan.

**Tech Stack:** Python 3.14, SQLite

## Global Constraints
- Menggunakan database SQLite `~/.iamnotpirates/data/data.db` secara eksklusif.
- Mempertahankan kegunaan `verify_media_file` dan parameter path default.
- Membypas prompt dan scraping jika file lokal sehat.

---

### Task 1: Movie Instant Local Check

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `is_already_downloaded()`, `verify_media_file()`, `add_entry()`
- Produces: `process_download_item()`

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_main.py`:
```python
@patch("src.main.extract_video_sources")
@patch("src.main.verify_media_file")
@patch("src.main.is_already_downloaded")
@patch("src.main.add_entry")
def test_process_download_item_movie_instant_skip(mock_add_entry, mock_is_dl, mock_verify, mock_extract):
    mock_is_dl.return_value = True
    mock_verify.return_value = {"video_status": "HEALTHY", "missing_subtitles": []}
    
    selected_item = {
        "title": "Instant Movie 2026",
        "type": "Movie",
        "url": "https://z2.idlixku.com/movie/instant-movie"
    }
    summary = {
        "total_items": 0,
        "video_success": 0,
        "video_failed": 0,
        "video_skipped": 0,
        "sub_success": 0,
        "sub_failed": 0,
        "items": []
    }
    config = {"movies_dir": "C:\\Downloads"}

    from src.main import process_download_item
    process_download_item(selected_item, "https://z2.idlixku.com/", config, summary, preset_sub_choice="Tanpa Subtitle", preset_download_dir="C:\\Downloads")

    mock_is_dl.assert_called_once()
    mock_verify.assert_called_once()
    mock_extract.assert_not_called()  # Scraper harus di-bypass!
    assert summary["video_skipped"] == 1
    mock_add_entry.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_main.py::test_process_download_item_movie_instant_skip -v`
Expected: FAIL (karena `mock_extract` terpanggil/tidak ter-bypass)

- [ ] **Step 3: Write minimal implementation**

Modifikasi bagian Movie di `process_download_item` dalam `src/main.py`:
```python
    folder_name = f"{clean_title} ({year})" if year and year != "N/A" else clean_title
    expected_path = os.path.join(target_dir, folder_name, f"{folder_name}.mp4")

    # Instant local check
    if is_already_downloaded(expected_path):
        verify_res = verify_media_file(expected_path, required_sub_mode=selected_sub_choice)
        if verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]:
            console.print(f"[yellow]⏭ {clean_title} sudah ada dan sehat secara lokal, di-skip.[/yellow]")
            add_entry(
                title=clean_title,
                media_type="movie",
                season=None,
                episode=None,
                status="skipped",
                m3u8_url="",
                output_path=expected_path,
                page_url=selected_item["url"]
            )
            summary["video_skipped"] += 1
            summary["items"].append({
                "title": clean_title,
                "video_status": "SKIPPED",
                "video_error": None,
                "subtitles": []
            })
            return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_main.py::test_process_download_item_movie_instant_skip -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add movie instant local check before scraping"
```

---

### Task 2: TV Series Episode Instant Local Check

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `is_already_downloaded()`, `verify_media_file()`, `add_entry()`
- Produces: `process_download_item()`

- [ ] **Step 1: Write the failing test**

Tambahkan ke `tests/test_main.py`:
```python
@patch("src.main.extract_episode_sources")
@patch("src.main.verify_media_file")
@patch("src.main.is_already_downloaded")
@patch("src.main.add_entry")
@patch("src.main.fetch_series_details")
def test_process_download_item_series_instant_skip(mock_details, mock_add_entry, mock_is_dl, mock_verify, mock_extract):
    mock_is_dl.return_value = True
    mock_verify.return_value = {"video_status": "HEALTHY", "missing_subtitles": []}
    mock_details.return_value = {
        "seasons": [{"season_num": 1, "episodes": [{"episode_num": 1, "media_id": "1", "title": "Ep 1"}]}]
    }

    selected_item = {
        "title": "Instant Show",
        "type": "TV Series",
        "url": "https://z2.idlixku.com/series/instant-show"
    }
    summary = {
        "total_items": 0,
        "video_success": 0,
        "video_failed": 0,
        "video_skipped": 0,
        "sub_success": 0,
        "sub_failed": 0,
        "items": []
    }
    config = {"series_dir": "C:\\Downloads"}

    from src.main import process_download_item
    # Mocking choices inside questionary checkbox
    with patch("src.main.questionary.checkbox") as mock_chk, \
         patch("src.main.questionary.select") as mock_sel:
        mock_chk_obj = MagicMock()
        mock_chk_obj.ask.return_value = ["Episode 1: Ep 1"]
        mock_chk.return_value = mock_chk_obj

        mock_sel_obj = MagicMock()
        mock_sel_obj.ask.return_value = "Season 1"
        mock_sel.return_value = mock_sel_obj

        process_download_item(selected_item, "https://z2.idlixku.com/", config, summary, preset_sub_choice="Tanpa Subtitle", preset_download_dir="C:\\Downloads")

    mock_is_dl.assert_called_once()
    mock_verify.assert_called_once()
    mock_extract.assert_not_called()  # Scraper episode di-bypass!
    assert summary["video_skipped"] == 1
    mock_add_entry.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest tests/test_main.py::test_process_download_item_series_instant_skip -v`
Expected: FAIL (karena `mock_extract` terpanggil)

- [ ] **Step 3: Write minimal implementation**

Modifikasi loop episode TV Series di `process_download_item` dalam `src/main.py`:
```python
        for ep in selected_episodes:
            console.print(f"\n[bold cyan]Memproses Episode {ep['episode_num']}: {ep['title']}...[/bold cyan]")
            season_dir, base_filename = format_tv_paths(clean_title, year, season_num, ep["episode_num"], target_dir)
            expected_path = os.path.join(season_dir, f"{base_filename}.mp4")
            ep_title = f"{clean_title} S{season_num:02d}E{ep['episode_num']:02d}"

            summary["total_items"] += 1

            # Instant local check
            if is_already_downloaded(expected_path):
                verify_res = verify_media_file(expected_path, required_sub_mode=selected_sub_choice)
                if verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]:
                    console.print(f"[yellow]⏭ Episode {ep['episode_num']} sudah ada dan sehat secara lokal, di-skip.[/yellow]")
                    add_entry(
                        title=ep_title,
                        media_type="episode",
                        season=season_num,
                        episode=ep["episode_num"],
                        status="skipped",
                        m3u8_url="",
                        output_path=expected_path,
                        page_url=item_url
                    )
                    summary["video_skipped"] += 1
                    summary["items"].append({
                        "title": ep_title,
                        "video_status": "SKIPPED",
                        "video_error": None,
                        "subtitles": []
                    })
                    continue
```

Hapus juga pengecekan `is_already_downloaded` lama yang ada di bawah (setelah `extract_episode_sources`).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest tests/test_main.py::test_process_download_item_series_instant_skip -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add TV Series episode instant local check before scraping"
```
