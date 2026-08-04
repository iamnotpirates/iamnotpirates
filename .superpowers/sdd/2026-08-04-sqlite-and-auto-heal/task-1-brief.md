# Task 1: SQLite Database Manager (`src/db_manager.py`)

## Objective
Create `src/db_manager.py` using standard `sqlite3` to manage configuration, target URLs, and download logs in `~/.iamnotpirates/data/data.db`.

## Database Location
`os.path.join(os.path.expanduser("~"), ".iamnotpirates", "data", "data.db")`

## Schema Definitions

### Table 1: `configs`
- `key` TEXT PRIMARY KEY
- `value` TEXT

Default values to seed on first run:
- `active_url`: `"https://z2.idlixku.com/"`
- `organize_mode`: `"separate"`
- `movies_dir`: `os.path.join(os.path.expanduser("~"), "Downloads", "Movies")`
- `series_dir`: `os.path.join(os.path.expanduser("~"), "Downloads", "TV Series")`
- `combined_dir`: `os.path.join(os.path.expanduser("~"), "Downloads")`
- `download_dir`: `os.path.join(os.path.expanduser("~"), "Downloads")`

### Table 2: `target_urls`
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT
- `url` TEXT UNIQUE

Default seed on first run:
- `id`: 1, `name`: `"IDLIX Primary"`, `url`: `"https://z2.idlixku.com/"`

### Table 3: `downloads`
- `id` TEXT PRIMARY KEY (uuid4 string)
- `media_type` TEXT (`movie` or `episode`)
- `title` TEXT
- `season` INTEGER (nullable)
- `episode` INTEGER (nullable)
- `status` TEXT (`success`, `failed`, `skipped`)
- `m3u8_url` TEXT
- `output_path` TEXT
- `error` TEXT (nullable)
- `timestamp` TEXT (ISO format string)

## Functions to Implement in `src/db_manager.py`

### DB Init & Connection
- `get_db_path(db_path=None) -> str`
- `get_connection(db_path=None) -> sqlite3.Connection`
- `init_db(db_path=None) -> None`

### Config Operations (replacing config_manager)
- `load_config(db_path=None) -> dict`
- `save_config_key(key: str, value: str, db_path=None) -> None`
- `get_download_dir(config: dict, media_type: str = "movie") -> str`
- `set_download_dir(config: dict, new_dir: str, media_type: str = "movie", db_path=None) -> dict`
- `set_organize_mode(config: dict, mode: str, db_path=None) -> dict`
- `add_target_url(url: str, name: str = "", db_path=None) -> dict`
- `set_active_url(url: str, db_path=None) -> dict`
- `delete_target_url(url: str, db_path=None) -> dict`

### Download Log Operations (replacing download_log)
- `add_entry(entry: dict | None = None, db_path=None, **kwargs) -> None`
- `update_entry(entry_id: str, updates: dict, db_path=None) -> None`
- `get_failed_entries(db_path=None) -> list[dict]`
- `load_log(db_path=None) -> list[dict]`
- `format_log_table(entries: list[dict]) -> rich.table.Table`

## Tests to write in `tests/test_db_manager.py`
Use temporary sqlite database file (e.g. `tmp_path / "test_data.db"`).
1. Test init_db seeds default configs and default target_urls.
2. Test load_config and set_organize_mode/set_download_dir.
3. Test add_target_url, set_active_url, delete_target_url.
4. Test add_entry (both dict and kwargs), update_entry, get_failed_entries, load_log.

## TDD Steps
1. Write failing tests in `tests/test_db_manager.py`.
2. Implement `src/db_manager.py`.
3. Run `uv run pytest tests/test_db_manager.py` — verify PASS.
4. `git add` and `git commit -m "feat: add SQLite db_manager for configs, urls, and logs"`.
