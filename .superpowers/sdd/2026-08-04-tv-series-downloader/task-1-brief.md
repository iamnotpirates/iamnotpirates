# Task 1 Brief: Create Series Extractor Module (`src/series_extractor.py`)

**Files:**
- Create: `src/series_extractor.py`
- Test: `tests/test_series_extractor.py`

**Interfaces:**
- Consumes: IDLIX series URL or slug (e.g. `https://z2.idlixku.com/series/breaking-bad` or `breaking-bad`).
- Produces: 
  - `fetch_series_details(page_url_or_slug: str) -> dict`: Returns `{"title": str, "year": str, "seasons": list[dict]}` where each season contains episodes with `season_num`, `episode_num`, `title`, and `media_id` / `slug`.
  - `extract_episode_sources(episode_media_id: str | int, page_url: str) -> dict`: Returns `{"m3u8_urls": list[str], "subtitles": list[dict]}`.

**Global Constraints:**
- Must run test using `uv run pytest tests/test_series_extractor.py -v`.
- Rely entirely on IDLIX Next.js API (`/api/series/<slug>`, `/api/watch/play-info/series/<id>`, etc.) without external TMDb dependencies.

**Report File Contract:**
- Write full report to: `C:\Users\aldinal21\workspaces\projects\iamnotpirates\.superpowers\sdd\2026-08-04-tv-series-downloader\task-1-report.md`
- Return status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED. Include commits, short test summary, and any concerns.

---

### Implementation Steps (TDD):

1. Write failing tests in `tests/test_series_extractor.py`:
   - Test `fetch_series_details` with mocked HTTP response from `curl_cffi.requests`.
   - Test `extract_episode_sources` with mocked play-info / claim / redeem endpoint flow.
2. Run `uv run pytest tests/test_series_extractor.py -v` to verify tests fail.
3. Implement `src/series_extractor.py` containing `fetch_series_details` and `extract_episode_sources`.
4. Run `uv run pytest tests/test_series_extractor.py -v` to verify tests pass.
5. Commit changes: `git add src/series_extractor.py tests/test_series_extractor.py` and `git commit -m "feat: add series_extractor module for IDLIX TV series API"`.
