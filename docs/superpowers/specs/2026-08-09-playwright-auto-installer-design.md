# Playwright Chromium Auto-Healing System Design

## 1. Overview & Context

`IAmNotPirates` is a CLI Scraper & Media Explorer for IDLIX. It relies on Playwright Chromium for rendering dynamic JavaScript components (such as the 10-item Hero Featured Carousel on the homepage) and as a fallback mechanism for video/m3u8 source extraction when direct API calls fail.

When non-technical users run `IAmNotPirates.exe` on a computer without pre-installed Playwright browser binaries, Playwright fails with `Executable doesn't exist` error. Currently, this error is caught silently in `scraper.py` and `video_extractor.py`, causing the application to skip dynamic carousel items and fail video extraction without informing or recovering automatically.

This design introduces a self-healing `playwright_manager.py` module that auto-checks and programmatically installs Chromium binaries upon application startup or before Playwright operations, ensuring a zero-configuration experience for non-IT users.

## 2. Architecture & Components

### 2.1 New Module: `src/playwright_manager.py`

Following the design pattern established by `src/ffmpeg_manager.py` and `src/n_m3u8dl_manager.py`:

- **`is_chromium_installed() -> bool`**:
  - Checks if `%LOCALAPPDATA%\ms-playwright` contains a valid `chromium-*` folder with an executable (or checks `PLAYWRIGHT_BROWSERS_PATH` if configured).
  - Can also attempt a lightweight executable path validation.

- **`ensure_playwright(console=None) -> bool`**:
  - Verifies whether Chromium is installed via `is_chromium_installed()`.
  - If missing, displays a clean Rich UI status message: `🎭 [Playwright] Menyiapkan browser scraper Chromium untuk pertama kali...`.
  - Invokes `playwright` driver CLI programmatically via Python (`subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])` or using `playwright._impl._driver` node runner).
  - Configures `os.environ["PLAYWRIGHT_BROWSERS_PATH"]` to ensure PyInstaller binaries find the downloaded Chromium executable seamlessly.
  - Returns `True` if Chromium is present or successfully downloaded, `False` on failure.

### 2.2 Application Integration

#### 1. Startup Sequence (`src/main.py`)
Add `ensure_playwright(console)` to `main()` during application startup alongside `ensure_binary()` (N_m3u8DL-RE) and `ensure_ffmpeg()`:
```python
def main() -> None:
    init_db()
    ensure_binary(console)
    ensure_ffmpeg(console)
    ensure_playwright(console)  # Pre-fetches Chromium browser for seamless scraping
```

#### 2. Guard in Scraper Engine (`src/scraper.py`)
In `fetch_featured_with_playwright(target_url)`:
Call `ensure_playwright()` before initializing `sync_playwright()` to ensure the browser engine is guaranteed to exist before attempting to render the Hero Carousel slides.

#### 3. Guard in Video Extractor Engine (`src/video_extractor.py`)
In `extract_video_sources(page_url)`:
Call `ensure_playwright()` prior to entering the Playwright fallback branch.

## 3. User Experience

1. **First-time Run**:
   - Non-IT user double-clicks `IAmNotPirates.exe`.
   - On startup, the terminal displays: `🎭 [Playwright] Menyiapkan browser scraper Chromium untuk pertama kali...`.
   - The browser package (~150MB) is downloaded automatically from Microsoft CDN into `%LOCALAPPDATA%\ms-playwright`.
   - Execution proceeds to the main menu without any manual command-line interaction required.

2. **Subsequent Runs**:
   - `ensure_playwright()` detects existing Chromium installation instantly (< 0.05s overhead) and proceeds directly.

## 4. Testing & Verification Plan

1. **Unit & Integration Tests**:
   - Add unit tests in `tests/test_playwright_manager.py` to mock `is_chromium_installed` and verify download triggers and error handling.
   - Verify `main.py` startup calls `ensure_playwright`.
2. **Manual Verification**:
   - Temporarily rename `%LOCALAPPDATA%\ms-playwright` and launch `IAmNotPirates.exe` / `uv run python src/main.py`.
   - Verify that Chromium is auto-downloaded, the 10 Hero Featured items are successfully scraped without skipping, and video source fallback functions properly.
