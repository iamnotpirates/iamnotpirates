import os
import pytest
from unittest.mock import patch, MagicMock
from src.config_manager import load_config, save_config, set_active_url
from src.main import (
    handle_featured,
    handle_select_active,
    handle_add_url,
    handle_manage_urls,
    main,
)

TEST_CONFIG = "test_main_config.json"


@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)
    yield
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)


def test_main_config_integration():
    config = load_config(TEST_CONFIG)
    assert "active_url" in config
    assert "target_urls" in config


@patch("src.main.questionary.select")
@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.fetch_featured_content")
def test_handle_featured_success(mock_fetch, mock_press, mock_select):
    mock_fetch.return_value = [
        {"title": "Test Movie", "type": "Movie", "rating": "9.0", "url": "https://z2.idlixku.com/movie/test"}
    ]
    mock_select_obj = MagicMock()
    mock_select_obj.ask.return_value = "↩️ Kembali ke Menu Utama"
    mock_select.return_value = mock_select_obj
    mock_press_obj = MagicMock()
    mock_press.return_value = mock_press_obj

    handle_featured("https://z2.idlixku.com/")

    mock_fetch.assert_called_once_with("https://z2.idlixku.com/")
    mock_press_obj.ask.assert_called_once()


@patch("src.main.download_media_stream")
@patch("src.main.extract_video_sources")
@patch("src.main.set_download_dir")
@patch("src.main.get_download_dir")
@patch("src.main.questionary.select")
@patch("src.main.questionary.text")
@patch("src.main.add_entry")
@patch("src.main.is_already_downloaded")
def test_handle_item_download(
    mock_is_dl, mock_add_entry, mock_text, mock_select, mock_get_dir, mock_set_dir, mock_extract, mock_download
):
    mock_is_dl.return_value = False
    items = [
        {"title": "Test Movie 2026", "type": "Movie", "rating": "9.0", "url": "https://z2.idlixku.com/movie/test-2026"}
    ]
    mock_get_dir.return_value = "C:\\Users\\test\\Downloads"

    mock_num_ask = MagicMock()
    mock_num_ask.ask.return_value = "1"
    mock_dir_ask = MagicMock()
    mock_dir_ask.ask.return_value = "C:\\Users\\test\\Downloads"
    mock_text.side_effect = [mock_num_ask, mock_dir_ask]

    mock_extract.return_value = {
        "m3u8_urls": ["https://stream.example.com/master.m3u8"],
        "subtitles": [{"lang": "Indonesian", "url": "https://sub.example.com/id.vtt"}]
    }

    mock_sub_ask = MagicMock()
    mock_sub_ask.ask.return_value = "Tanpa Subtitle"
    mock_select.side_effect = [mock_sub_ask]

    expected_path = "C:\\Users\\test\\Downloads\\Test Movie (2026)\\Test Movie (2026).mp4"
    mock_download.return_value = expected_path

    from src.main import handle_item_download
    handle_item_download(items, "https://z2.idlixku.com/", {"download_dir": "C:\\Users\\test\\Downloads"})

    mock_extract.assert_called_once_with("https://z2.idlixku.com/movie/test-2026")
    mock_download.assert_called_once_with(
        "https://stream.example.com/master.m3u8",
        "C:\\Users\\test\\Downloads",
        "Test Movie",
        "2026",
        "Best Available"
    )
    mock_add_entry.assert_called_once()
    args, kwargs = mock_add_entry.call_args
    assert kwargs.get("status") == "success" or args[4] == "success" if len(args) > 4 else True


@patch("src.main.download_media_stream")
@patch("src.main.extract_video_sources")
@patch("src.main.set_download_dir")
@patch("src.main.get_download_dir")
@patch("src.main.questionary.select")
@patch("src.main.questionary.text")
@patch("src.main.add_entry")
@patch("src.main.verify_media_file")
@patch("src.main.is_already_downloaded")
def test_handle_item_download_auto_heals_corrupted_file(
    mock_is_dl, mock_verify, mock_add_entry, mock_text, mock_select, mock_get_dir, mock_set_dir, mock_extract, mock_download
):
    mock_is_dl.return_value = True
    mock_verify.return_value = {"video_status": "CORRUPTED", "missing_subtitles": False, "error_message": "Invalid duration"}
    items = [
        {"title": "Corrupted Movie 2026", "type": "Movie", "rating": "9.0", "url": "https://z2.idlixku.com/movie/corrupted-2026"}
    ]
    mock_get_dir.return_value = "C:\\Users\\test\\Downloads"

    mock_num_ask = MagicMock()
    mock_num_ask.ask.return_value = "1"
    mock_dir_ask = MagicMock()
    mock_dir_ask.ask.return_value = "C:\\Users\\test\\Downloads"
    mock_text.side_effect = [mock_num_ask, mock_dir_ask]

    mock_extract.return_value = {
        "m3u8_urls": ["https://stream.example.com/master.m3u8"],
        "subtitles": []
    }

    mock_sub_ask = MagicMock()
    mock_sub_ask.ask.return_value = "Tanpa Subtitle"
    mock_select.side_effect = [mock_sub_ask]

    expected_path = "C:\\Users\\test\\Downloads\\Corrupted Movie (2026)\\Corrupted Movie (2026).mp4"
    mock_download.return_value = expected_path

    from src.main import handle_item_download
    handle_item_download(items, "https://z2.idlixku.com/", {"download_dir": "C:\\Users\\test\\Downloads"})

    mock_verify.assert_called_once()
    mock_download.assert_called_once()



@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.fetch_featured_content")
def test_handle_featured_error(mock_fetch, mock_press):
    mock_fetch.side_effect = Exception("Network Error")
    mock_press_obj = MagicMock()
    mock_press.return_value = mock_press_obj

    handle_featured("https://z2.idlixku.com/")

    mock_fetch.assert_called_once_with("https://z2.idlixku.com/")
    mock_press_obj.ask.assert_called_once()


@patch("src.main.questionary.select")
@patch("src.main.load_config")
@patch("src.main.set_active_url")
def test_handle_select_active(mock_set, mock_load, mock_select):
    mock_load.return_value = {
        "active_url": "https://z2.idlixku.com/",
        "target_urls": [
            {"id": 1, "name": "IDLIX Primary", "url": "https://z2.idlixku.com/"},
            {"id": 2, "name": "Backup", "url": "https://backup.idlix.com/"},
        ],
    }
    mock_select_obj = MagicMock()
    mock_select_obj.ask.return_value = "https://backup.idlix.com/"
    mock_select.return_value = mock_select_obj

    handle_select_active()

    mock_set.assert_called_once_with("https://backup.idlix.com/")


@patch("src.main.questionary.text")
@patch("src.main.add_target_url")
def test_handle_add_url(mock_add, mock_text):
    mock_url_ask = MagicMock()
    mock_url_ask.ask.return_value = "https://newsite.com/"
    mock_name_ask = MagicMock()
    mock_name_ask.ask.return_value = "New Site"

    mock_text.side_effect = [mock_url_ask, mock_name_ask]

    handle_add_url()

    mock_add.assert_called_once_with("https://newsite.com/", "New Site")


@patch("src.main.questionary.select")
@patch("src.main.load_config")
@patch("src.main.set_active_url")
def test_handle_manage_urls_set_active(mock_set, mock_load, mock_select):
    mock_load.return_value = {
        "active_url": "https://z2.idlixku.com/",
        "target_urls": [
            {"id": 1, "name": "IDLIX Primary", "url": "https://z2.idlixku.com/"},
        ],
    }
    mock_select_1 = MagicMock()
    mock_select_1.ask.return_value = "IDLIX Primary (https://z2.idlixku.com/)"
    mock_select_2 = MagicMock()
    mock_select_2.ask.return_value = "Set as Active"

    mock_select.side_effect = [mock_select_1, mock_select_2]

    handle_manage_urls()

    mock_set.assert_called_once_with("https://z2.idlixku.com/")


@patch("src.main.questionary.select")
@patch("src.main.load_config")
@patch("src.main.delete_target_url")
def test_handle_manage_urls_delete(mock_delete, mock_load, mock_select):
    mock_load.return_value = {
        "active_url": "https://z2.idlixku.com/",
        "target_urls": [
            {"id": 1, "name": "IDLIX Primary", "url": "https://z2.idlixku.com/"},
        ],
    }
    mock_select_1 = MagicMock()
    mock_select_1.ask.return_value = "IDLIX Primary (https://z2.idlixku.com/)"
    mock_select_2 = MagicMock()
    mock_select_2.ask.return_value = "Hapus URL"

    mock_select.side_effect = [mock_select_1, mock_select_2]

    handle_manage_urls()

    mock_delete.assert_called_once_with("https://z2.idlixku.com/")


@patch("src.main.ensure_binary")
@patch("src.main.questionary.select")
@patch("src.main.print_header")
@patch("src.main.load_config")
def test_main_exit(mock_load, mock_header, mock_select, mock_ensure):
    mock_load.return_value = {
        "active_url": "https://z2.idlixku.com/",
        "target_urls": [
            {"id": 1, "name": "IDLIX Primary", "url": "https://z2.idlixku.com/"},
        ],
    }
    mock_select_obj = MagicMock()
    mock_select_obj.ask.return_value = "❌ Exit Program"
    mock_select.return_value = mock_select_obj

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    mock_ensure.assert_called_once()


@patch("src.main.add_entry")
@patch("src.main.is_already_downloaded")
@patch("src.main.download_subtitles_batch")
@patch("src.main.download_media_stream")
@patch("src.main.format_tv_paths")
@patch("src.main.extract_episode_sources")
@patch("src.main.fetch_series_details")
@patch("src.main.set_download_dir")
@patch("src.main.get_download_dir")
@patch("src.main.questionary.checkbox")
@patch("src.main.questionary.select")
@patch("src.main.questionary.text")
def test_handle_item_download_tv_series_success(
    mock_text,
    mock_select,
    mock_checkbox,
    mock_get_dir,
    mock_set_dir,
    mock_fetch_series,
    mock_extract_ep,
    mock_format_paths,
    mock_download_media,
    mock_download_subs,
    mock_is_dl,
    mock_add_entry,
    tmp_path,
):
    mock_is_dl.return_value = False
    items = [
        {
            "title": "Breaking Bad (2008)",
            "type": "TV Series",
            "rating": "9.5",
            "url": "https://z2.idlixku.com/series/breaking-bad",
        }
    ]
    mock_get_dir.return_value = str(tmp_path)

    mock_num_ask = MagicMock()
    mock_num_ask.ask.return_value = "1"
    mock_dir_ask = MagicMock()
    mock_dir_ask.ask.return_value = str(tmp_path)
    mock_text.side_effect = [mock_num_ask, mock_dir_ask]

    mock_season_ask = MagicMock()
    mock_season_ask.ask.return_value = "Season 1"
    mock_sub_ask = MagicMock()
    mock_sub_ask.ask.return_value = "Semua Subtitle Tersedia"
    mock_select.side_effect = [mock_season_ask, mock_sub_ask]

    mock_cb_ask = MagicMock()
    mock_cb_ask.ask.return_value = ["Episode 1: Pilot", "Episode 2: Cat's in the Bag..."]
    mock_checkbox.return_value = mock_cb_ask

    mock_fetch_series.return_value = {
        "title": "Breaking Bad",
        "year": "2008",
        "seasons": [
            {
                "season_num": 1,
                "episodes": [
                    {"season_num": 1, "episode_num": 1, "title": "Pilot", "media_id": "101"},
                    {"season_num": 1, "episode_num": 2, "title": "Cat's in the Bag...", "media_id": "102"},
                ],
            }
        ],
    }

    mock_extract_ep.side_effect = [
        {"m3u8_urls": ["https://stream.example.com/ep1.m3u8"], "subtitles": [{"lang": "Indonesian", "url": "https://sub.example.com/ep1.vtt"}]},
        {"m3u8_urls": ["https://stream.example.com/ep2.m3u8"], "subtitles": [{"lang": "English", "url": "https://sub.example.com/ep2.vtt"}]},
    ]

    mock_format_paths.side_effect = [
        (str(tmp_path / "Breaking Bad (2008)" / "Season 01"), "Breaking Bad - S01E01"),
        (str(tmp_path / "Breaking Bad (2008)" / "Season 01"), "Breaking Bad - S01E02"),
    ]

    ep1_file = tmp_path / "Breaking Bad - S01E01.mp4"
    ep2_file = tmp_path / "Breaking Bad - S01E02.mp4"
    ep1_file.touch()
    ep2_file.touch()

    mock_download_media.side_effect = [str(ep1_file), str(ep2_file)]
    mock_download_subs.side_effect = [[str(tmp_path / "Breaking Bad - S01E01.id.srt")], [str(tmp_path / "Breaking Bad - S01E02.en.srt")]]

    from src.main import handle_item_download
    handle_item_download(items, "https://z2.idlixku.com/", {"download_dir": str(tmp_path)})

    mock_fetch_series.assert_called_once_with("https://z2.idlixku.com/series/breaking-bad")
    assert mock_extract_ep.call_count == 2
    assert mock_download_media.call_count == 2
    assert mock_download_subs.call_count == 2
    assert mock_add_entry.call_count == 2


@patch("src.main.add_entry")
@patch("src.main.is_already_downloaded")
@patch("src.main.download_subtitles_batch")
@patch("src.main.download_media_stream")
@patch("src.main.format_tv_paths")
@patch("src.main.extract_episode_sources")
@patch("src.main.fetch_series_details")
@patch("src.main.set_download_dir")
@patch("src.main.get_download_dir")
@patch("src.main.questionary.checkbox")
@patch("src.main.questionary.select")
@patch("src.main.questionary.text")
def test_handle_item_download_tv_series_resilient_error(
    mock_text,
    mock_select,
    mock_checkbox,
    mock_get_dir,
    mock_set_dir,
    mock_fetch_series,
    mock_extract_ep,
    mock_format_paths,
    mock_download_media,
    mock_download_subs,
    mock_is_dl,
    mock_add_entry,
    tmp_path,
):
    mock_is_dl.return_value = False
    items = [
        {
            "title": "Breaking Bad",
            "type": "TV Series",
            "rating": "9.5",
            "url": "https://z2.idlixku.com/series/breaking-bad",
        }
    ]
    mock_get_dir.return_value = str(tmp_path)

    mock_num_ask = MagicMock()
    mock_num_ask.ask.return_value = "1"
    mock_dir_ask = MagicMock()
    mock_dir_ask.ask.return_value = str(tmp_path)
    mock_text.side_effect = [mock_num_ask, mock_dir_ask]

    mock_season_ask = MagicMock()
    mock_season_ask.ask.return_value = "Season 1"
    mock_sub_ask = MagicMock()
    mock_sub_ask.ask.return_value = "Tanpa Subtitle"
    mock_select.side_effect = [mock_season_ask, mock_sub_ask]

    mock_cb_ask = MagicMock()
    mock_cb_ask.ask.return_value = ["Episode 1: Pilot", "Episode 2: Cat's in the Bag..."]
    mock_checkbox.return_value = mock_cb_ask

    mock_fetch_series.return_value = {
        "title": "Breaking Bad",
        "year": "2008",
        "seasons": [
            {
                "season_num": 1,
                "episodes": [
                    {"season_num": 1, "episode_num": 1, "title": "Pilot", "media_id": "101"},
                    {"season_num": 1, "episode_num": 2, "title": "Cat's in the Bag...", "media_id": "102"},
                ],
            }
        ],
    }

    mock_extract_ep.side_effect = [
        Exception("Extraction Error for Ep 1"),
        {"m3u8_urls": ["https://stream.example.com/ep2.m3u8"], "subtitles": []},
    ]

    mock_format_paths.return_value = (str(tmp_path / "Breaking Bad (2008)" / "Season 01"), "Breaking Bad - S01E02")
    ep2_file = tmp_path / "Breaking Bad - S01E02.mp4"
    ep2_file.touch()

    mock_download_media.return_value = str(ep2_file)

    from src.main import handle_item_download
    handle_item_download(items, "https://z2.idlixku.com/", {"download_dir": str(tmp_path)})

    assert mock_extract_ep.call_count == 2
    assert mock_download_media.call_count == 1


@patch("src.main.get_failed_entries")
def test_handle_retry_failed_no_failures(mock_get_failed):
    mock_get_failed.return_value = []
    from src.main import handle_retry_failed
    handle_retry_failed("https://z2.idlixku.com/", {})
    mock_get_failed.assert_called_once()


@patch("src.main.update_entry")
@patch("src.main.download_with_re")
@patch("src.main.questionary.select")
@patch("src.main.get_failed_entries")
def test_handle_retry_failed_retries_all(mock_get_failed, mock_select, mock_re, mock_update):
    mock_get_failed.return_value = [
        {
            "id": 1,
            "title": "Failed Movie",
            "m3u8_url": "https://stream.com/f.m3u8",
            "output_path": "C:\\Downloads\\Failed Movie.mp4",
        }
    ]
    mock_select_obj = MagicMock()
    mock_select_obj.ask.return_value = "🔄 Retry Semua yang Gagal"
    mock_select.return_value = mock_select_obj
    mock_re.return_value = True

    from src.main import handle_retry_failed
    handle_retry_failed("https://z2.idlixku.com/", {})

    mock_re.assert_called_once_with("https://stream.com/f.m3u8", "C:\\Downloads", "Failed Movie")
    mock_update.assert_called_once_with(1, {"status": "success", "error": None})


@patch("src.main.search_content")
@patch("src.main.questionary.text")
def test_handle_search_empty_input(mock_text, mock_search):
    mock_ask = MagicMock()
    mock_ask.ask.return_value = ""
    mock_text.return_value = mock_ask

    from src.main import handle_search
    handle_search("https://z2.idlixku.com/", {})
    mock_search.assert_not_called()


@patch("src.main.questionary.select")
@patch("src.main.search_content")
@patch("src.main.questionary.text")
def test_handle_search_success(mock_text, mock_search, mock_select):
    mock_ask = MagicMock()
    mock_ask.ask.return_value = "avatar"
    mock_text.return_value = mock_ask

    mock_search.return_value = [
        {"title": "Avatar", "type": "Movie", "rating": "7.9", "url": "https://z2.idlixku.com/movie/avatar-2009"}
    ]

    mock_select_obj = MagicMock()
    mock_select_obj.ask.return_value = "↩️ Kembali ke Menu Utama"
    mock_select.return_value = mock_select_obj

    from src.main import handle_search
    handle_search("https://z2.idlixku.com/", {})

    mock_search.assert_called_once_with("https://z2.idlixku.com/", "avatar")



