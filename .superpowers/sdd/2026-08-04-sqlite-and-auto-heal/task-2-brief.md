# Task 2: FFmpeg Binary Manager & Media Integrity Verifier (`src/ffmpeg_manager.py`)

## Objective
Create `src/ffmpeg_manager.py` to auto-download static Windows builds of `ffmpeg.exe` and `ffprobe.exe` into `~/.iamnotpirates/bin/`, and provide a media verification function to detect corrupted MP4 files and missing subtitles.

## Cache Location
`~/.iamnotpirates/bin/ffmpeg.exe`
`~/.iamnotpirates/bin/ffprobe.exe`

## Download Sources
Can use GitHub releases or reliable static zip endpoints:
- e.g., BtbN / FFmpeg-Builds static release API or direct zip URL (`https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip` or similar fallback zip).

## Functions to Implement in `src/ffmpeg_manager.py`

### `get_ffmpeg_paths() -> tuple[str, str]`
Returns `(ffmpeg_path, ffprobe_path)` in `~/.iamnotpirates/bin/`.

### `ensure_ffmpeg(console=None) -> tuple[str | None, str | None]`
- Checks if `ffmpeg.exe` and `ffprobe.exe` exist.
- If missing, downloads static Windows build zip, extracts `ffmpeg.exe` and `ffprobe.exe` to `~/.iamnotpirates/bin/`.
- Returns `(ffmpeg_path, ffprobe_path)` or `(None, None)` if failed.

### `verify_media_file(video_path: str, required_sub_mode: str = "Tanpa Subtitle") -> dict`
Checks the video file and its associated subtitles.
Returns dict:
```python
{
    "video_status": "HEALTHY" | "CORRUPTED" | "MISSING",
    "missing_subtitles": True | False,
    "error_message": None | str
}
```

Logic:
1. If `video_path` does not exist or size < 1MB -> `video_status`: `"MISSING"`.
2. Run `ffprobe` command:
   `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "<video_path>"`
   - If ffprobe fails / returncode != 0 / duration invalid -> `video_status`: `"CORRUPTED"`.
3. Check Subtitles based on `required_sub_mode`:
   - If `required_sub_mode` != `"Tanpa Subtitle"`:
     - Check if matching `.srt` files exist (e.g. `.id.srt`, `.en.srt`, or `.srt`).
     - If expected subtitle files do NOT exist -> `missing_subtitles`: `True`, else `False`.
4. If video is healthy and subtitles are present -> `video_status`: `"HEALTHY"`, `missing_subtitles`: `False`.

## Tests to write in `tests/test_ffmpeg_manager.py`
Use mocks for subprocess / requests / zipfile:
1. `test_get_ffmpeg_paths` — verify path strings in `~/.iamnotpirates/bin/`.
2. `test_ensure_ffmpeg_existing` — mock `os.path.exists` True, verify no download.
3. `test_verify_media_file_missing` — non-existent file -> `video_status == "MISSING"`.
4. `test_verify_media_file_corrupted` — mock `subprocess.run` returncode=1 -> `video_status == "CORRUPTED"`.
5. `test_verify_media_file_healthy_with_subs` — mock `subprocess.run` returncode=0 with valid duration, mock `.srt` exists -> `HEALTHY`, `missing_subtitles == False`.
6. `test_verify_media_file_healthy_missing_subs` — mock `subprocess.run` returncode=0, no `.srt` file -> `HEALTHY`, `missing_subtitles == True`.

## TDD Steps
1. Write failing tests in `tests/test_ffmpeg_manager.py`.
2. Implement `src/ffmpeg_manager.py`.
3. Run `uv run pytest tests/test_ffmpeg_manager.py` — verify PASS.
4. `git add` and `git commit -m "feat: add FFmpeg manager and media integrity verifier"`.
