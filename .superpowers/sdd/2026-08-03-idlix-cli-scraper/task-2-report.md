# Task 2 Execution Report: Config Manager (Target URLs CRUD)

**Timestamp**: 2026-08-03T17:49:30+07:00
**Status**: SUCCESS

## Summary of Changes

1. **`src/config_manager.py`**
   - Implemented configuration management module with the following functions:
     - `normalize_url(url: str) -> str`: Normalizes target URLs (trims whitespace, adds `https://` prefix if missing scheme, ensures trailing slash).
     - `load_config(config_path: str = "config.json") -> dict`: Loads configuration JSON; creates default config file (`active_url`: `https://z2.idlixku.com/`) if file does not exist or is invalid.
     - `save_config(config: dict, config_path: str = "config.json") -> None`: Writes configuration dict to JSON with formatting.
     - `add_target_url(url: str, name: str = "", config_path: str = "config.json") -> dict`: Adds new target URL with auto-incremented ID and optional/default display name if not already existing.
     - `set_active_url(url: str, config_path: str = "config.json") -> dict`: Sets the currently active URL.
     - `delete_target_url(url: str, config_path: str = "config.json") -> dict`: Removes target URL from targets list; updates `active_url` fallback if active target was deleted.

2. **`tests/test_config_manager.py`**
   - Implemented unit tests with automated file cleanup fixture:
     - `test_load_default_config()`: Verifies default config structure and initial active URL.
     - `test_add_and_set_active_url()`: Verifies target addition and active URL selection.
     - `test_delete_url()`: Verifies deletion of target URLs.

## Test Execution Results

Command executed: `uv run pytest tests/test_config_manager.py`

Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\aldinal21\workspaces\projects\iamnotpirates
configfile: pyproject.toml
collected 3 items

tests\test_config_manager.py ...                                         [100%]

============================== 3 passed in 0.02s ==============================
```

Full test suite execution (`uv run pytest`):
```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\aldinal21\workspaces\projects\iamnotpirates
configfile: pyproject.toml
collected 4 items

tests\test_config_manager.py ...                                         [ 75%]
tests\test_env.py .                                                      [100%]

============================== 4 passed in 0.58s ==============================
```
