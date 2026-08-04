# Task 1: N_m3u8DL-RE Binary Manager

## Objective
Create `src/n_m3u8dl_manager.py` — a module that auto-downloads and manages the
N_m3u8DL-RE binary for Windows.

## Background
N_m3u8DL-RE is a fast HLS/DASH downloader written in C#. We want to replace yt-dlp's
download_media_stream() with N_m3u8DL-RE subprocess calls. The binary must be
auto-downloaded from GitHub releases on first run, cached locally, and callable via
subprocess.

## GitHub Releases URL
- Repo: https://github.com/nilaoda/N_m3u8DL-RE
- Latest release API: https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest
- Asset to download: `N_m3u8DL-RE_*_win-x64_**.zip` (or similar Windows zip)
- The zip contains `N_m3u8DL-RE.exe`

## Cache Location
Store binary at: `~/.iamnotpirates/bin/N_m3u8DL-RE.exe`
i.e., `os.path.join(os.path.expanduser("~"), ".iamnotpirates", "bin", "N_m3u8DL-RE.exe")`

## Functions to implement in `src/n_m3u8dl_manager.py`

### `get_binary_path() -> str`
Returns path to cached binary. Does NOT download.

### `ensure_binary(console=None) -> str | None`
- Check if binary exists at cache path
- If not: auto-download from GitHub releases latest
  - Use `requests` (curl_cffi) to call GitHub API
  - Find the win-x64 zip asset
  - Download zip, extract `N_m3u8DL-RE.exe` to cache dir
  - Print progress with rich Console if provided
- Return path to binary, or None if failed

### `download_with_re(m3u8_url: str, save_dir: str, save_name: str, thread_count: int = 16) -> bool`
- Call `ensure_binary()` first
- Build subprocess command:
  ```
  N_m3u8DL-RE.exe "<m3u8_url>"
    --save-dir "<save_dir>"
    --save-name "<save_name>"
    --thread-count 16
    --auto-select
    -M format=mp4
    --download-retry-count 3
    --no-log
  ```
- Run via `subprocess.run()` with `check=False`
- Return True if returncode == 0, else False

## Tests to write in `tests/test_n_m3u8dl_manager.py`
Use `unittest.mock.patch` — do NOT make real network calls.

1. `test_get_binary_path_returns_expected_location` — check path contains `.iamnotpirates/bin/N_m3u8DL-RE.exe`
2. `test_ensure_binary_returns_path_if_exists` — mock `os.path.exists` True, ensure no download attempted
3. `test_ensure_binary_downloads_if_missing` — mock os.path.exists False, mock requests.get, mock zipfile extraction, verify binary path returned
4. `test_download_with_re_success` — mock ensure_binary + subprocess.run returncode=0 → True
5. `test_download_with_re_failure` — mock ensure_binary + subprocess.run returncode=1 → False

## TDD Steps
1. Write failing tests in `tests/test_n_m3u8dl_manager.py`
2. Run `uv run pytest tests/test_n_m3u8dl_manager.py` — verify FAIL
3. Implement `src/n_m3u8dl_manager.py`
4. Run `uv run pytest tests/test_n_m3u8dl_manager.py` — verify PASS
5. `git add` and `git commit -m "feat: add N_m3u8DL-RE binary manager"`

## Important Notes
- Use `curl_cffi.requests` (already in project) for HTTP calls
- Use `zipfile` stdlib for extraction
- Binary path must use `os.path.join` and `os.path.expanduser("~")`
- Print progress messages using rich Console when provided
