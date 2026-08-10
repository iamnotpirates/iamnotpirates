"""Integration tests for Playwright Chromium auto-installer across main, scraper, and video_extractor."""
import os
from unittest.mock import MagicMock, patch

import pytest

from src.main import main
from src.playwright_manager import get_playwright_browsers_path
from src.scraper import fetch_featured_with_playwright
from src.video_extractor import extract_video_sources


@patch("src.main.ensure_playwright")
@patch("src.main.ensure_ffmpeg")
@patch("src.main.ensure_binary")
@patch("src.main.init_db")
@patch("src.main.load_config")
@patch("src.main.questionary.select")
def test_main_calls_ensure_playwright(mock_select, mock_load, mock_init, mock_binary, mock_ffmpeg, mock_pw):
    mock_load.return_value = {
        "active_url": "https://z2.idlixku.com/",
        "target_urls": [{"id": 1, "name": "IDLIX", "url": "https://z2.idlixku.com/"}],
    }
    mock_select_obj = MagicMock()
    mock_select_obj.ask.return_value = "❌ Exit Program"
    mock_select.return_value = mock_select_obj

    with pytest.raises(SystemExit):
        main()

    mock_pw.assert_called_once()


@patch("src.playwright_manager.ensure_playwright")
@patch("playwright.sync_api.sync_playwright")
def test_fetch_featured_with_playwright_calls_ensure_playwright(mock_sync_pw, mock_ensure_pw):
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_sync_pw.return_value.__enter__.return_value = mock_pw
    mock_pw.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_page.query_selector_all.return_value = []
    mock_page.content.return_value = "<html></html>"

    res = fetch_featured_with_playwright("https://example.com")

    mock_ensure_pw.assert_called_once()
    assert os.environ.get("PLAYWRIGHT_BROWSERS_PATH") == get_playwright_browsers_path()


@patch("src.video_extractor.extract_video_sources_via_api")
@patch("src.playwright_manager.ensure_playwright")
@patch("playwright.sync_api.sync_playwright")
def test_extract_video_sources_fallback_calls_ensure_playwright(mock_sync_pw, mock_ensure_pw, mock_api):
    mock_api.return_value = None
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_sync_pw.return_value.__enter__.return_value = mock_pw
    mock_pw.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    res = extract_video_sources("https://example.com/movie/test")

    mock_api.assert_called_once_with("https://example.com/movie/test")
    mock_ensure_pw.assert_called_once()
    assert os.environ.get("PLAYWRIGHT_BROWSERS_PATH") == get_playwright_browsers_path()
