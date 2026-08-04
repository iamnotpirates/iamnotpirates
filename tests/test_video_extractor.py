from unittest.mock import patch, MagicMock
import os
from src.video_extractor import extract_video_sources

def test_extract_video_sources_basic_mock():
    with patch("src.video_extractor.sync_playwright") as mock_pw:
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_pw.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        def fake_goto(url, **kwargs):
            # Find response handlers attached to page
            for call in mock_page.on.call_args_list:
                event_name, handler = call[0]
                if event_name == "response":
                    mock_resp1 = MagicMock()
                    mock_resp1.url = "https://stream.example.com/playlist.m3u8"
                    handler(mock_resp1)
                    mock_resp2 = MagicMock()
                    mock_resp2.url = "https://subtitles.example.com/ind.vtt"
                    handler(mock_resp2)

        mock_page.goto.side_effect = fake_goto

        result = extract_video_sources("https://idlixku.com/movie/test")

        assert "m3u8_urls" in result
        assert "subtitles" in result
        assert "https://stream.example.com/playlist.m3u8" in result["m3u8_urls"]
        assert len(result["subtitles"]) == 1
        assert result["subtitles"][0]["lang"] == "Indonesian"
        assert result["subtitles"][0]["url"] == "https://subtitles.example.com/ind.vtt"

def test_extract_video_sources_iframe_fallback():
    with patch("src.video_extractor.sync_playwright") as mock_pw:
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_sub_page = MagicMock()

        mock_pw.return_value.__enter__.return_value = mock_playwright
        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.side_effect = [mock_page, mock_sub_page]

        mock_page.content.return_value = '<html><body><iframe src="https://govid.me/player/123"></iframe></body></html>'

        def fake_sub_goto(url, **kwargs):
            for call in mock_sub_page.on.call_args_list:
                event_name, handler = call[0]
                if event_name == "response":
                    mock_resp = MagicMock()
                    mock_resp.url = "https://govid.me/hls/stream.m3u8"
                    handler(mock_resp)

        mock_sub_page.goto.side_effect = fake_sub_goto

        result = extract_video_sources("https://idlixku.com/movie/test-iframe")

        assert "https://govid.me/hls/stream.m3u8" in result["m3u8_urls"]
        mock_context.new_page.assert_called()

def test_extract_video_sources_exception_handling():
    with patch("src.video_extractor.sync_playwright") as mock_pw:
        mock_pw.side_effect = Exception("Playwright crash test")
        result = extract_video_sources("https://idlixku.com/movie/error")
        assert result == {"m3u8_urls": [], "subtitles": []}
