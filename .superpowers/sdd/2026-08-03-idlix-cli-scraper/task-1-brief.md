# Task 1 Brief: Environment & Project Setup

## Requirements
1. Create `pyproject.toml` with dependencies:
   - `curl-cffi>=0.7.0`
   - `beautifulsoup4>=4.12.0`
   - `rich>=13.7.0`
   - `questionary>=2.0.0`
   - dev dependency: `pytest>=8.0.0`
2. Create `src/__init__.py`
3. Create `tests/test_env.py` verifying all imports (`curl_cffi`, `bs4`, `rich`, `questionary`).
4. Run `uv run pytest tests/test_env.py` to ensure environment is fully working.

## Report File
Write execution report to `.superpowers/sdd/2026-08-03-idlix-cli-scraper/task-1-report.md`.
