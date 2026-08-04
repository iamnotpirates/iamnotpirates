# Task 4 Brief: UI Renderer (Rich Display & Tables)

## Requirements
1. Create `src/ui.py` with functions:
   - `print_header(active_url: str)`: Clears console and prints header panel with active target URL.
   - `format_featured_table(items: list[dict]) -> Table`: Returns a styled `rich.table.Table` with columns: No, Title, Type, Rating, URL.
   - `print_error(msg: str)`: Prints error message panel/alert.
   - `print_success(msg: str)`: Prints success message.
2. Create `tests/test_ui.py` testing table generation logic.
3. Run `uv run pytest tests/test_ui.py` to verify tests pass.

## Report File
Write execution report to `.superpowers/sdd/2026-08-03-idlix-cli-scraper/task-4-report.md`.
