# Implementation Plan: Basic Search & Menu Updates

## Task 1: Add `search_content()` to `src/scraper.py`
Implement `search_content(target_url: str, query: str) -> list[dict]` using `curl_cffi.requests` to call `/api/search?q=<query>`.

### Steps:
1. Write failing test in `tests/test_scraper.py`: `test_search_content_success` with mocked API response.
2. Implement `search_content` in `src/scraper.py`.
3. Verify test passes: `uv run pytest tests/test_scraper.py`.
4. Commit changes.

## Task 2: Implement `handle_search()` and update Main Menu in `src/main.py`
Add `handle_search(active_url: str, config: dict)` and add `🔍 Cari Film / TV Series` to main choices. Rename `🚀 Scrape Featured Content` to `🔥 Lihat Featured Content`.

### Steps:
1. Write failing tests in `tests/test_main.py`: `test_handle_search_success` and `test_handle_search_no_results`.
2. Update `src/main.py`.
3. Verify test passes: `uv run pytest tests/test_main.py`.
4. Run full test suite: `uv run pytest`.
5. Commit changes.
