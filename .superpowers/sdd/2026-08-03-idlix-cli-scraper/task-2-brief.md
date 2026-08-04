# Task 2 Brief: Config Manager (Target URLs CRUD)

## Requirements
1. Create `src/config_manager.py` with functions:
   - `load_config(config_path: str = "config.json") -> dict`
   - `save_config(config: dict, config_path: str = "config.json") -> None`
   - `add_target_url(url: str, name: str = "", config_path: str = "config.json") -> dict`
   - `set_active_url(url: str, config_path: str = "config.json") -> dict`
   - `delete_target_url(url: str, config_path: str = "config.json") -> dict`
2. Create `tests/test_config_manager.py` to test loading default config, adding URL, setting active URL, and deleting URL.
3. Run `uv run pytest tests/test_config_manager.py` and verify all tests pass.

## Report File
Write execution report to `.superpowers/sdd/2026-08-03-idlix-cli-scraper/task-2-report.md`.
