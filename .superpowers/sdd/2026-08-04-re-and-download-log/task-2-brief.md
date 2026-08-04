# Task 2: Download Log Manager

## Objective
Create `src/download_log.py` — a module that tracks all download attempts
(success/failed/skipped) in a persistent JSON log file.

## Log File Location
`~/.iamnotpirates/downloads.json`
i.e., `os.path.join(os.path.expanduser("~"), ".iamnotpirates", "downloads.json")`

## Log Entry Schema
Each entry is a dict:
```json
{
  "id": "uuid4 string",
  "type": "movie" | "episode",
  "title": "Show Title or Movie Title",
  "year": "2024",
  "season": 1,          // null for movies
  "episode": 3,         // null for movies
  "m3u8_url": "https://...",
  "output_path": "/path/to/file.mp4",
  "status": "success" | "failed" | "skipped",
  "timestamp": "2026-08-04T15:00:00",
  "error": null | "error message string"
}
```

## Functions to implement in `src/download_log.py`

### `_get_log_path() -> str`
Returns log file path.

### `load_log() -> list[dict]`
Loads and returns all entries from log file. Returns [] if file missing.

### `save_log(entries: list[dict]) -> None`
Saves full entries list to log file (atomic write).

### `add_entry(entry: dict) -> None`
Appends a new entry. Generates `id` (uuid4) and `timestamp` automatically if missing.

### `update_entry(entry_id: str, updates: dict) -> None`
Updates a specific entry by id.

### `get_failed_entries() -> list[dict]`
Returns all entries where `status == "failed"`.

### `is_already_downloaded(output_path: str, min_size_bytes: int = 1_000_000) -> bool`
Returns True if:
- File exists at output_path, AND
- File size >= min_size_bytes (1MB default)

This is the "file-based check" for skipping already-completed downloads.

### `format_log_table(entries: list[dict]) -> rich.table.Table`
Returns a Rich Table showing entries with columns:
No | Type | Title | Season | Episode | Status | Timestamp

Use color coding:
- status "success" → green
- status "failed" → red  
- status "skipped" → yellow

## Tests to write in `tests/test_download_log.py`
Use `tmp_path` pytest fixture for file I/O — no real filesystem side effects.

1. `test_load_log_returns_empty_list_if_missing`
2. `test_add_and_load_entry` — add entry, load, verify it's there with id+timestamp
3. `test_update_entry` — add entry, update status, verify change
4. `test_get_failed_entries` — add 3 entries (1 success, 2 failed), verify returns 2
5. `test_is_already_downloaded_true` — create real temp file > 1MB, verify True
6. `test_is_already_downloaded_false_missing` — path doesn't exist → False
7. `test_is_already_downloaded_false_too_small` — file exists but < 1MB → False

## TDD Steps
1. Write failing tests in `tests/test_download_log.py`
2. Run `uv run pytest tests/test_download_log.py` — verify FAIL
3. Implement `src/download_log.py`
4. Run `uv run pytest tests/test_download_log.py` — verify PASS
5. `git add` and `git commit -m "feat: add download log manager"`

## Important Notes
- Use `json`, `uuid`, `datetime`, `os` from stdlib only
- For `format_log_table`, import `rich.table.Table` and `rich.text.Text`
- `save_log` must use atomic write: write to `.tmp` file first, then `os.replace()`
- `add_entry` auto-generates `id` with `str(uuid.uuid4())` if not present
- `add_entry` auto-generates `timestamp` with `datetime.now().isoformat()` if not present
