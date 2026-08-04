# Task 2 Brief: Enhance Downloader Helper for Jellyfin Paths & Subtitles (`src/downloader.py`)

**Files:**
- Modify: `src/downloader.py`
- Modify: `tests/test_downloader.py`

**Interfaces:**
- Consumes: `show_title`, `year`, `season_num`, `episode_num`, `target_dir`
- Produces:
  - `format_tv_paths(show_title: str, year: str, season_num: int, episode_num: int, target_dir: str) -> tuple[str, str]`: returns `(season_dir_path, base_filename)` where season_dir_path is `target_dir/Show Title (Year)/Season 01` and base_filename is `Show Title - S01E01`.
  - `download_subtitles_batch(subtitles: list[dict], base_video_path: str, sub_mode: str) -> list[str]`: downloads `.id.srt`, `.en.srt`, or all available subtitles matching `sub_mode` (`Semua Subtitle Tersedia`, `Indonesia saja`, `English saja`, `Tanpa Subtitle`).

**Global Constraints:**
- Must run test using `uv run pytest tests/test_downloader.py -v`.
- Folder structure must strictly match Jellyfin format: `Downloads/<Show Title> (<Year>)/Season <0X>/<Show Title> - S<0X>E<0Y>.<ext>`

**Report File Contract:**
- Write full report to: `C:\Users\aldinal21\workspaces\projects\iamnotpirates\.superpowers\sdd\2026-08-04-tv-series-downloader\task-2-report.md`
- Return status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED. Include commits, short test summary, and any concerns.

---

### Implementation Steps (TDD):

1. Write failing tests in `tests/test_downloader.py` testing `format_tv_paths` and `download_subtitles_batch`.
2. Run `uv run pytest tests/test_downloader.py -v` to verify failure.
3. Implement `format_tv_paths` and `download_subtitles_batch` in `src/downloader.py`.
4. Run `uv run pytest tests/test_downloader.py -v` to verify pass.
5. Commit changes: `git add src/downloader.py tests/test_downloader.py` and `git commit -m "feat: add format_tv_paths and download_subtitles_batch helpers"`.
