# Playwright Chromium Auto-Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-detect and programmatically download Playwright Chromium browser binaries for non-IT users on application startup and fallback points.

**Architecture:** Create `src/playwright_manager.py` following the existing `ffmpeg_manager.py` / `n_m3u8dl_manager.py` auto-healing manager pattern. Integrate `ensure_playwright(console)` into `main.py` startup and as a guard in `scraper.py` and `video_extractor.py`.

**Tech Stack:** Python 3.9+, Playwright, Rich Console, PyTest.

## Global Constraints

- Preserve clean UI experience with Rich Console progress messages.
- Ensure zero-configuration setup for non-IT users running `IAmNotPirates.exe`.
- Do not break existing API-first video source extraction logic.

---

### Task 1: Create `src/playwright_manager.py` and Unit Tests

**Files:**
- Create: `src/playwright_manager.py`
- Create: `tests/test_playwright_manager.py`

**Interfaces:**
- Produces:
  - `is_chromium_installed() -> bool`: Returns `True` if Chromium binary exists in `%LOCALAPPDATA%\ms-playwright` or `PLAYWRIGHT_BROWSERS_PATH`.
  - `ensure_playwright(console=None) -> bool`: Checks Chromium presence, downloads via Playwright driver CLI if missing, configures environment variables, returns `True` on success.

- [ ] **Step 1: Write the failing unit test**

```python
# tests/test_playwright_manager.py
import os
from unittest.mock import patch, MagicMock
from src.playwright_manager import is_chromium_installed, ensure_playwright

def test_is_chromium_installed_returns_bool():
    result = is_chromium_installed()
    assert isinstance(result, bool)

@patch("src.playwright_manager.is_chromium_installed")
def test_ensure_playwright_when_already_installed(mock_installed):
    mock_installed.return_value = True
    console = MagicMock()
    success = ensure_playwright(console)
    assert success is True
    console.print.assert_not_called()

@patch("subprocess.run")
@patch("src.playwright_manager.is_chromium_installed")
def test_ensure_playwright_downloads_when_missing(mock_installed, mock_run):
    mock_installed.side_effect = [False, True]
    mock_run.return_value = MagicMock(returncode=0)
    console = MagicMock()
    success = ensure_playwright(console)
    assert success is True
    assert mock_run.called
    console.print.assert_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_playwright_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.playwright_manager'"

- [ ] **Step 3: Write minimal implementation in `src/playwright_manager.py`**

```python
"""Playwright Chromium binary manager.

Auto-checks and downloads Chromium browser binaries for Playwright
to ensure zero-configuration execution on non-IT user machines.
"""
import os
import sys
import subprocess
from pathlib import Path

def get_playwright_browsers_path() -> str:
    """Return the active ms-playwright path."""
    user_ms_pw = os.path.expanduser("~\\AppData\\Local\\ms-playwright")
    if os.path.exists(user_ms_pw):
        return user_ms_pw
    custom_env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom_env and os.path.exists(custom_env):
        return custom_env
    return user_ms_pw

def is_chromium_installed() -> bool:
    """Check if Chromium browser binary exists."""
    browsers_path = get_playwright_browsers_path()
    if not os.path.exists(browsers_path):
        return False
    
    # Check for chromium-* directory containing chrome.exe
    for entry in os.listdir(browsers_path):
        if entry.startswith("chromium-"):
            chrome_exe = os.path.join(browsers_path, entry, "chrome-win", "chrome.exe")
            if os.path.exists(chrome_exe):
                return True
    return False

def ensure_playwright(console=None) -> bool:
    """Ensure Chromium browser binary is available for Playwright.
    
    Downloads Chromium if missing, configuring PLAYWRIGHT_BROWSERS_PATH.
    """
    browsers_path = get_playwright_browsers_path()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
    
    if is_chromium_installed():
        return True
        
    def _print(msg: str) -> None:
        if console is not None:
            console.print(msg)
        else:
            print(msg)
            
    _print("[bold cyan]🎭 [Playwright] Menyiapkan browser scraper Chromium untuk pertama kali...[/bold cyan]")
    
    try:
        # Use Python's sys.executable -m playwright install chromium
        cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and is_chromium_installed():
            _print("[bold green]✔ [Playwright] Browser Chromium berhasil terpasang![/bold green]")
            return True
            
        # Fallback to driver node.exe if available
        from playwright._impl._driver import compute_driver_executable
        driver_exe, cli_js = compute_driver_executable()
        if os.path.exists(driver_exe) and os.path.exists(cli_js):
            res_driver = subprocess.run([driver_exe, cli_js, "install", "chromium"], capture_output=True, text=True, check=False)
            if res_driver.returncode == 0 and is_chromium_installed():
                _print("[bold green]✔ [Playwright] Browser Chromium berhasil terpasang![/bold green]")
                return True

        _print(f"[bold red]❌ [Playwright] Gagal memasang Chromium: {res.stderr}[/bold red]")
        return False
    except Exception as exc:
        _print(f"[bold red]❌ [Playwright] Error saat memasang Chromium: {exc}[/bold red]")
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_playwright_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src/playwright_manager.py tests/test_playwright_manager.py`
Run: `git commit -m "feat: add playwright_manager auto-healing module"`

---

### Task 2: Integrate `ensure_playwright` into `main.py`, `scraper.py`, and `video_extractor.py`

**Files:**
- Modify: `src/main.py:660-666`
- Modify: `src/scraper.py:159-170`
- Modify: `src/video_extractor.py:92-96`
- Test: `tests/test_main_playwright_integration.py`

**Interfaces:**
- Consumes: `src.playwright_manager.ensure_playwright`

- [ ] **Step 1: Write integration tests**

```python
# tests/test_main_playwright_integration.py
from unittest.mock import patch

@patch("src.main.ensure_playwright")
@patch("src.main.ensure_ffmpeg")
@patch("src.main.ensure_binary")
@patch("src.main.init_db")
@patch("src.main.load_config")
@patch("sys.exit")
def test_main_calls_ensure_playwright(mock_exit, mock_config, mock_db, mock_binary, mock_ffmpeg, mock_pw):
    from src.main import main
    mock_config.side_effect = SystemExit(0)
    try:
        main()
    except SystemExit:
        pass
    assert mock_pw.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main_playwright_integration.py -v`
Expected: FAIL with assertion error (`assert mock_pw.called` is False)

- [ ] **Step 3: Modify `src/main.py`, `src/scraper.py`, and `src/video_extractor.py`**

In `src/main.py`:
```python
from src.playwright_manager import ensure_playwright

def main() -> None:
    init_db()
    ensure_binary(console)
    ensure_ffmpeg(console)
    ensure_playwright(console)
    ...
```

In `src/scraper.py`:
```python
def fetch_featured_with_playwright(target_url: str) -> list[dict]:
    import os
    from src.playwright_manager import ensure_playwright, get_playwright_browsers_path

    ensure_playwright()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = get_playwright_browsers_path()
    ...
```

In `src/video_extractor.py`:
```python
def extract_video_sources(page_url: str) -> dict:
    ...
    # Playwright fallback
    from src.playwright_manager import ensure_playwright, get_playwright_browsers_path
    ensure_playwright()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = get_playwright_browsers_path()
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_main_playwright_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src/main.py src/scraper.py src/video_extractor.py tests/test_main_playwright_integration.py`
Run: `git commit -m "feat: integrate ensure_playwright into main startup, scraper, and video extractor"`

---

### Task 3: Full End-to-End Test Suite Verification

- [ ] **Step 1: Run complete pytest test suite**

Run: `uv run pytest`
Expected: All unit and integration tests pass (100% PASS).
