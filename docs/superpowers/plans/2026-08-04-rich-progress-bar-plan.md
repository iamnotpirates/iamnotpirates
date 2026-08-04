# Implementation Plan: Rich Live Progress Bar

## Task 1: Add output parsing helper and update `download_with_re()` in `src/n_m3u8dl_manager.py`

### Objectives:
1. Add `parse_re_log_line(line: str) -> dict` helper function to extract progress, total segments, percentage, and speed from N_m3u8DL-RE stdout lines.
2. Refactor `download_with_re()` to spawn subprocess via `subprocess.Popen(..., stdout=subprocess.PIPE, stderr=subprocess.STDOUT)`.
3. Wrap execution in `rich.progress.Progress` with custom columns.

### Steps:
1. Write failing unit tests in `tests/test_n_m3u8dl_manager.py`:
   - `test_parse_re_log_line()` with sample stdout lines.
   - `test_download_with_re_live_progress()` with mocked Popen stream.
2. Implement `parse_re_log_line` and update `download_with_re` in `src/n_m3u8dl_manager.py`.
3. Verify pytest passes: `uv run pytest tests/test_n_m3u8dl_manager.py`.
4. Run full test suite: `uv run pytest`.
5. Commit changes to git.
