# Task 5 Brief: Interactive Perpetual CLI Main Loop

## Requirements
1. Create `src/main.py` assembling `config_manager`, `scraper`, `ui`, and `questionary` into an interactive perpetual main loop:
   - Initial onboarding prompt to add default URL if `config.json` is missing or has no targets.
   - Perpetual loop (`while True`) with menu choices:
     - `🚀 Scrape Featured Content`: Fetches & displays featured table from active URL. Pressing Enter returns to main menu.
     - `🌐 Pilih / Ganti Active Target URL`: Selects active target URL from list.
     - `➕ Tambah URL Target Baru`: Prompts for new URL & optional label.
     - `⚙️  Manage List URL (Edit/Delete)`: Manage existing target URLs (Set Active / Delete / Back).
     - `❌ Exit Program`: Exits program cleanly (`sys.exit(0)`).
2. Create `tests/test_main.py` testing config integration.
3. Run `uv run pytest` to ensure full test suite passes.

## Report File
Write execution report to `.superpowers/sdd/2026-08-03-idlix-cli-scraper/task-5-report.md`.
