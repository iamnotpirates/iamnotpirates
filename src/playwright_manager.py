"""Playwright Chromium browser manager.

Auto-checks and installs Chromium browser binary for Playwright scraper.
"""
import os
import subprocess
import sys

from rich import print as rprint


def get_playwright_browsers_path() -> str:
    """Return active ms-playwright path.

    Checks os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or defaults to %LOCALAPPDATA%\\ms-playwright.
    """
    env_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env_path:
        return env_path
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return os.path.join(local_appdata, "ms-playwright")
    return os.path.expanduser("~/AppData/Local/ms-playwright")


def is_chromium_installed() -> bool:
    """Check if active ms-playwright path contains a valid chromium-* installation."""
    base_path = get_playwright_browsers_path()
    if not os.path.exists(base_path):
        return False
    try:
        for item in os.listdir(base_path):
            if item.startswith("chromium-") and not item.endswith((".bak", ".tmp", ".old")):
                folder_path = os.path.join(base_path, item)
                if not os.path.isdir(folder_path):
                    continue
                candidates = [
                    os.path.join(folder_path, "chrome-win64", "chrome.exe"),
                    os.path.join(folder_path, "chrome-win", "chrome.exe"),
                    os.path.join(folder_path, "chrome.exe"),
                    os.path.join(folder_path, "INSTALLATION_COMPLETE"),
                ]
                if any(os.path.isfile(c) for c in candidates):
                    return True
    except Exception:
        return False
    return False


def ensure_playwright(console=None) -> bool:
    """Ensure Playwright Chromium browser is installed.

    If missing, prints Rich UI message, sets PLAYWRIGHT_BROWSERS_PATH, and installs Chromium.

    Args:
        console: Optional rich.console.Console for progress output.

    Returns:
        bool: True if Chromium is present or installed successfully, False otherwise.
    """
    if is_chromium_installed():
        return True

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    msg = "[bold cyan][3/3] 🌐 Playwright Chromium tidak ditemukan. Menyiapkan browser scraper...[/bold cyan]"
    if console is not None:
        console.print(msg)
    else:
        try:
            rprint(msg)
        except Exception:
            print("[Playwright] Menyiapkan browser scraper Chromium untuk pertama kali...")

    browsers_path = get_playwright_browsers_path()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path

    success = False

    if not getattr(sys, "frozen", False):
        cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        try:
            res = subprocess.run(cmd, check=False)
            if res.returncode == 0:
                success = True
        except Exception:
            success = False

    if not success:
        try:
            from playwright._impl._driver import compute_driver_executable

            driver_executable, cli_js = compute_driver_executable()
            res = subprocess.run([driver_executable, cli_js, "install", "chromium"], check=False)
            if res.returncode == 0:
                success = True
        except Exception:
            pass

    installed = is_chromium_installed()
    if installed:
        success_msg = f"[bold green]✓ Playwright Chromium terpasang di: {browsers_path}[/bold green]"
        if console is not None:
            console.print(success_msg)
        else:
            try:
                rprint(success_msg)
            except Exception:
                print(f"✓ Playwright Chromium terpasang di: {browsers_path}")
    return installed
