# Task 3 Brief: Integrate TV Series Workflow in `src/main.py`

**Files:**
- Modify: `src/main.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `fetch_series_details`, `extract_episode_sources` from `src/series_extractor.py`, `format_tv_paths`, `download_subtitles_batch` from `src/downloader.py`.
- Produces: Updated `handle_item_download` in `src/main.py` supporting both Movies and TV Series.

**Requirements:**
1. Check if `selected_item.get("type") == "TV Series"` or `"/series/" in item_url`.
2. If TV Series:
   - Call `fetch_series_details(item_url)` to fetch seasons and episodes.
   - Prompt user to select a Season via `questionary.select`.
   - Prompt user to multi-select Episode(s) via `questionary.checkbox` (map episode titles with checkboxes).
   - Prompt Target Directory (default from config).
   - Prompt Video Quality once for batch.
   - Prompt Subtitle choice once (`Semua Subtitle Tersedia`, `Indonesia saja`, `English saja`, `Tanpa Subtitle`).
   - Loop over selected episodes sequentially (1 by 1):
     - Wrap download of each episode in `try-except` so a failure in 1 episode does not crash the entire batch.
     - Extract stream with `extract_episode_sources(ep["media_id"], item_url)`.
     - Get Jellyfin paths using `format_tv_paths(clean_title, year, season_num, ep["episode_num"], target_dir)`.
     - Download video with `download_media_stream(...)`.
     - Download subtitles with `download_subtitles_batch(subtitles, video_path, sub_choice)`.
     - Output success/error for each episode.

**Global Constraints:**
- Test command: `uv run pytest tests/test_main.py -v`
- Folder structure must follow Jellyfin standard.

**Report File Contract:**
- Write full report to: `C:\Users\aldinal21\workspaces\projects\iamnotpirates\.superpowers\sdd\2026-08-04-tv-series-downloader\task-3-report.md`
- Return status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED. Include commits, short test summary, and any concerns.

---

### Implementation Steps (TDD):

1. Write failing tests in `tests/test_main.py` for TV series download workflow branch.
2. Run `uv run pytest tests/test_main.py -v` to verify failure.
3. Modify `src/main.py` to add TV series handling inside `handle_item_download`.
4. Run `uv run pytest tests/test_main.py -v` to verify pass.
5. Commit changes: `git add src/main.py tests/test_main.py` and `git commit -m "feat: add interactive TV series multi-episode batch download to main CLI"`.
