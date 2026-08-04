# Task 3 Brief: Scraper Engine (curl_cffi & HTML Parsing)

## Requirements
1. Create `src/scraper.py` with functions:
   - `parse_featured_html(html: str) -> list[dict]`: Parses HTML string using BeautifulSoup4 to extract featured items (title, url, rating, type, poster).
   - `fetch_featured_content(target_url: str) -> list[dict]`: Fetches HTML using `curl_cffi.requests` with Chrome TLS impersonation (`impersonate="chrome120"`), then parses featured items.
2. Create `tests/test_scraper.py` testing HTML parsing logic with mock HTML.
3. Run `uv run pytest tests/test_scraper.py` to verify tests pass.

## Report File
Write execution report to `.superpowers/sdd/2026-08-03-idlix-cli-scraper/task-3-report.md`.
