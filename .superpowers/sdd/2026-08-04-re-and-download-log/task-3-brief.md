# Task 3: Integrate RE + Download Log into downloader.py & main.py

## Prerequisites
This task depends on Task 1 and Task 2 being DONE first (check git log).
Wait for both to be committed before starting.

## Objective
1. Update `src/downloader.py`: replace `download_media_stream` with RE-based implementation
2. Update `src/main.py`: remove quality prompt, integrate skip logic + log tracking, add Retry Failed menu

---

## Part A: Update `src/downloader.py`

### Replace `download_media_stream()` entirely:

```python
def download_media_stream(
    m3u8_url: str,
    output_dir: str,
    title: str,
    year: str = "N/A",
    quality: str = "Best Available",   # kept for API compat, ignored by RE (auto-select)
    create_subfolder: bool = True
) -> str | None:
    """Downloads m3u8 video stream using N_m3u8DL-RE.
    Returns target video filepath on success, None on error.
    """
```

Implementation:
1. Build `clean_title`, `target_folder`, `base_filename` same as before
2. Expected output file: `os.path.join(target_folder, f"{base_filename}.mp4")`
3. Check `is_already_downloaded(expected_output)` from download_log → if True, return expected_output (skip)
4. Call `download_with_re(m3u8_url, target_folder, base_filename)` from n_m3u8dl_manager
5. Return `expected_output` if success, None if failed

### Keep all other functions unchanged:
- `convert_vtt_to_srt`
- `get_unique_filepath`
- `download_subtitle`
- `format_tv_paths`
- `download_subtitles_batch`
- `_get_lang_code`

### Remove:
- `inspect_stream_qualities` (no longer needed)
- `import yt_dlp` (no longer needed)

---

## Part B: Update `src/main.py`

### Changes to `handle_item_download`:

**For TV Series path:**
- Remove Step 4 (Pilih Kualitas) entirely — no quality prompt
- In the download loop, after `download_media_stream()`:
  - Call `add_entry()` from download_log with status "success" or "failed"
  - If file skipped (already exists), call `add_entry()` with status "skipped"
  - Print "[yellow]⏭ Episode X sudah ada, di-skip.[/yellow]" when skipped

**For Movie path:**
- Remove quality selection prompt
- After `download_media_stream()`, call `add_entry()` from download_log

**Detect skip**: Check return value of `download_media_stream()` — if it returns a path
but `is_already_downloaded()` was True (i.e. file existed before download), it's a skip.
Actually simpler: call `is_already_downloaded(expected_path)` BEFORE calling download_media_stream,
store as `was_already_downloaded`. Then after, if was_already_downloaded → log "skipped".

### Add new menu item to `main()`:
Add `"📋 Lihat & Retry Download Gagal"` to the main menu choices list.

### Add `handle_retry_failed()` function:
```python
def handle_retry_failed(active_url: str, config: dict) -> None:
    failed = get_failed_entries()   # from download_log
    if not failed:
        console.print("[green]Tidak ada download yang gagal.[/green]")
        return

    table = format_log_table(failed)
    console.print(table)

    action = questionary.select(
        "Pilih Aksi:",
        choices=["🔄 Retry Semua yang Gagal", "↩️ Kembali"]
    ).ask()

    if action != "🔄 Retry Semua yang Gagal":
        return

    for entry in failed:
        console.print(f"\n[bold cyan]Retry: {entry['title']}...[/bold cyan]")
        try:
            m3u8_url = entry["m3u8_url"]
            output_path = entry["output_path"]
            output_dir = os.path.dirname(output_path)
            base_name = os.path.splitext(os.path.basename(output_path))[0]

            success = download_with_re(m3u8_url, output_dir, base_name)
            if success:
                update_entry(entry["id"], {"status": "success", "error": None})
                print_success(f"Berhasil: {output_path}")
            else:
                print_error(f"Masih gagal: {entry['title']}")
        except Exception as e:
            print_error(f"Error retry {entry['title']}: {e}")
```

### Imports to add in main.py:
```python
from src.download_log import add_entry, get_failed_entries, update_entry, format_log_table, is_already_downloaded
from src.n_m3u8dl_manager import download_with_re, ensure_binary
```

### Remove from main.py imports:
- `inspect_stream_qualities` (no longer exported)

### On startup in `main()`:
Call `ensure_binary(console)` once before the main loop to pre-download RE binary.

---

## Tests to update in `tests/test_main.py`

The existing tests mock questionary and downloader functions. Update them:
1. Remove any mock for `inspect_stream_qualities`
2. Update `test_handle_item_download` to not expect quality prompt
3. Update `test_handle_item_download_tv_series_success` similarly
4. Add `test_handle_retry_failed_no_failures` — mock `get_failed_entries` returns [] → prints no failures message
5. Add `test_handle_retry_failed_retries_all` — mock 1 failed entry, mock download_with_re True → update_entry called with success

## TDD Steps
1. Update/add tests in `tests/test_main.py`
2. Run `uv run pytest tests/test_main.py` — verify FAIL on new tests
3. Update `src/downloader.py`
4. Update `src/main.py`
5. Run `uv run pytest` (full suite) — verify ALL PASS
6. `git add -A` and `git commit -m "feat: integrate N_m3u8DL-RE and download log into main flow"`

## Important Notes
- The `quality` param in `download_media_stream` is kept for API compatibility but ignored (RE uses auto-select)
- Existing tests for `downloader.py` may need minor updates since `inspect_stream_qualities` is removed
- `handle_retry_failed` must be wired in `main()` loop: `elif choice == "📋 Lihat & Retry Download Gagal": handle_retry_failed(active_url, config)`
- The log entry for a TV episode must include `season` and `episode` integers, `type="episode"`
- The log entry for a movie must include `type="movie"`, `season=None`, `episode=None`
