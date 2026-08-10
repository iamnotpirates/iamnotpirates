"""Unit tests for src/playwright_manager.py."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.playwright_manager import (
    ensure_playwright,
    get_playwright_browsers_path,
    is_chromium_installed,
)


def test_get_playwright_browsers_path(monkeypatch, tmp_path):
    # Test default LOCALAPPDATA path
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    expected_default = os.path.join(str(tmp_path), "ms-playwright")
    assert get_playwright_browsers_path() == expected_default

    # Test custom env var path
    custom_path = str(tmp_path / "custom_playwright")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", custom_path)
    assert get_playwright_browsers_path() == custom_path


def test_is_chromium_installed_returns_bool(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    res = is_chromium_installed()
    assert isinstance(res, bool)
    assert res is False

    # Create dummy chromium dir with chrome.exe
    chrome_dir = tmp_path / "chromium-1234" / "chrome-win"
    chrome_dir.mkdir(parents=True)
    (chrome_dir / "chrome.exe").write_text("dummy binary")

    res_after = is_chromium_installed()
    assert isinstance(res_after, bool)
    assert res_after is True


def test_is_chromium_installed_win64(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    chrome_dir = tmp_path / "chromium-1234" / "chrome-win64"
    chrome_dir.mkdir(parents=True)
    (chrome_dir / "chrome.exe").write_text("dummy binary")

    res = is_chromium_installed()
    assert res is True


def test_is_chromium_installed_ignores_bak_and_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    bak_dir = tmp_path / "chromium-1234.bak" / "chrome-win64"
    bak_dir.mkdir(parents=True)
    (bak_dir / "chrome.exe").write_text("dummy binary")

    res = is_chromium_installed()
    assert res is False


def test_ensure_playwright_when_already_installed():
    with patch("src.playwright_manager.is_chromium_installed", return_value=True):
        console = MagicMock()
        result = ensure_playwright(console=console)
        assert result is True
        console.print.assert_not_called()


def test_ensure_playwright_downloads_when_missing(monkeypatch, tmp_path):
    custom_path = str(tmp_path / "ms-playwright")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", custom_path)

    with patch("src.playwright_manager.is_chromium_installed", side_effect=[False, True]) as mock_is_installed, \
         patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        console = MagicMock()
        result = ensure_playwright(console=console)

        assert result is True
        console.print.assert_called_once_with(
            "[bold cyan][Playwright] Menyiapkan browser scraper Chromium untuk pertama kali...[/bold cyan]"
        )
        mock_run.assert_called_once_with(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
        )
        assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == custom_path


def test_ensure_playwright_fallback_when_primary_fails(monkeypatch, tmp_path):
    custom_path = str(tmp_path / "ms-playwright")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", custom_path)

    with patch("src.playwright_manager.is_chromium_installed", side_effect=[False, True]), \
         patch("subprocess.run", side_effect=[MagicMock(returncode=1), MagicMock(returncode=0)]) as mock_run, \
         patch("playwright._impl._driver.compute_driver_executable", return_value=("node.exe", "cli.js")):
        console = MagicMock()
        result = ensure_playwright(console=console)

        assert result is True
        assert mock_run.call_count == 2
        mock_run.assert_any_call([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        mock_run.assert_any_call(["node.exe", "cli.js", "install", "chromium"], check=False)
