import os
import pytest
from unittest.mock import patch, MagicMock
from src.downloader import (
    download_media_stream,
    convert_vtt_to_srt,
    get_unique_filepath,
    download_subtitle,
    format_tv_paths,
    download_subtitles_batch
)

def test_convert_vtt_to_srt():
    vtt_text = """WEBVTT

00:00:01.500 --> 00:00:04.200
Hello world!

00:00:05.100 --> 00:00:08.300
Second subtitle.
"""
    srt_result = convert_vtt_to_srt(vtt_text)
    assert "00:00:01,500 --> 00:00:04,200" in srt_result
    assert "Hello world!" in srt_result
    assert "1" in srt_result
    assert "2" in srt_result

def test_get_unique_filepath(tmp_path):
    file1 = tmp_path / "Colony (2026).mp4"
    file1.touch()

    unique1 = get_unique_filepath(str(file1))
    assert unique1.endswith("Colony (2026) (1).mp4")

    # Create file1 (1).mp4 as well
    file2 = tmp_path / "Colony (2026) (1).mp4"
    file2.touch()

    unique2 = get_unique_filepath(str(file1))
    assert unique2.endswith("Colony (2026) (2).mp4")

def test_download_subtitle_success(tmp_path):
    output_srt = str(tmp_path / "Colony (2026).id.srt")
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHalo dunia!\n"

    with patch("curl_cffi.requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.text = vtt_content
        mock_get.return_value = mock_res

        res = download_subtitle("https://example.com/sub.vtt", output_srt)
        assert res is True
        assert os.path.exists(output_srt)
        with open(output_srt, "r", encoding="utf-8") as f:
            text = f.read()
            assert "Halo dunia!" in text

def test_download_media_stream_jellyfin_naming(tmp_path):
    output_dir = str(tmp_path / "downloads")
    with patch("src.downloader.download_with_re") as mock_re, patch("src.downloader.is_already_downloaded") as mock_is_dl:
        mock_is_dl.return_value = False
        mock_re.return_value = True

        video_path = download_media_stream(
            m3u8_url="https://example.com/stream.m3u8",
            output_dir=output_dir,
            title="Colony",
            year="2026",
            quality="720p"
        )
        assert video_path is not None
        assert "Colony (2026)" in video_path
        assert video_path.endswith(".mp4")
        mock_re.assert_called_once()

def test_download_media_stream_already_downloaded(tmp_path):
    output_dir = str(tmp_path / "downloads")
    with patch("src.downloader.download_with_re") as mock_re, patch("src.downloader.is_already_downloaded") as mock_is_dl:
        mock_is_dl.return_value = True

        video_path = download_media_stream(
            m3u8_url="https://example.com/stream.m3u8",
            output_dir=output_dir,
            title="Colony",
            year="2026"
        )
        assert video_path is not None
        assert "Colony (2026)" in video_path
        mock_re.assert_not_called()


def test_format_tv_paths_with_year():
    season_dir, base_file = format_tv_paths(
        show_title="Breaking Bad",
        year="2008",
        season_num=1,
        episode_num=5,
        target_dir="/downloads"
    )
    expected_season_dir = os.path.join("/downloads", "Breaking Bad (2008)", "Season 01")
    assert season_dir == expected_season_dir
    assert base_file == "Breaking Bad - S01E05"

def test_format_tv_paths_no_year():
    season_dir, base_file = format_tv_paths(
        show_title="The Office",
        year="N/A",
        season_num=2,
        episode_num=12,
        target_dir="/downloads"
    )
    expected_season_dir = os.path.join("/downloads", "The Office", "Season 02")
    assert season_dir == expected_season_dir
    assert base_file == "The Office - S02E12"

def test_download_subtitles_batch_all(tmp_path):
    subtitles = [
        {"lang": "Indonesian", "url": "https://example.com/id.vtt"},
        {"lang": "English", "url": "https://example.com/en.vtt"}
    ]
    base_video_path = str(tmp_path / "The Office - S01E01.mp4")
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nTest sub\n"

    with patch("curl_cffi.requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.text = vtt_content
        mock_get.return_value = mock_res

        paths = download_subtitles_batch(subtitles, base_video_path, "Semua Subtitle Tersedia")
        assert len(paths) == 2
        assert any(p.endswith(".id.srt") for p in paths)
        assert any(p.endswith(".en.srt") for p in paths)
        for p in paths:
            assert os.path.exists(p)

def test_download_subtitles_batch_indonesia_only(tmp_path):
    subtitles = [
        {"lang": "Indonesian", "url": "https://example.com/id.vtt"},
        {"lang": "English", "url": "https://example.com/en.vtt"}
    ]
    base_video_path = str(tmp_path / "The Office - S01E01.mp4")
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nTest sub\n"

    with patch("curl_cffi.requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.text = vtt_content
        mock_get.return_value = mock_res

        paths = download_subtitles_batch(subtitles, base_video_path, "Indonesia saja")
        assert len(paths) == 1
        assert paths[0].endswith(".id.srt")
        assert os.path.exists(paths[0])

def test_download_subtitles_batch_english_only(tmp_path):
    subtitles = [
        {"lang": "Indonesian", "url": "https://example.com/id.vtt"},
        {"lang": "English", "url": "https://example.com/en.vtt"}
    ]
    base_video_path = str(tmp_path / "The Office - S01E01.mp4")
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nTest sub\n"

    with patch("curl_cffi.requests.get") as mock_get:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.text = vtt_content
        mock_get.return_value = mock_res

        paths = download_subtitles_batch(subtitles, base_video_path, "English saja")
        assert len(paths) == 1
        assert paths[0].endswith(".en.srt")
        assert os.path.exists(paths[0])

def test_download_subtitles_batch_tanpa_subtitle(tmp_path):
    subtitles = [
        {"lang": "Indonesian", "url": "https://example.com/id.vtt"},
        {"lang": "English", "url": "https://example.com/en.vtt"}
    ]
    base_video_path = str(tmp_path / "The Office - S01E01.mp4")

    paths = download_subtitles_batch(subtitles, base_video_path, "Tanpa Subtitle")
    assert paths == []

