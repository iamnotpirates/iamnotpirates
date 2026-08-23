from unittest.mock import MagicMock, patch

import pytest

import src.main as main_mod
from src.main import handle_telegram_menu, require_telegram_ready


def test_require_telegram_ready_runs_login_when_not_logged_in():
    config = {"tg_api_id": "1", "tg_api_hash": "h"}
    with patch.object(main_mod, "ensure_telethon", return_value=True), \
         patch.object(main_mod, "is_configured", return_value=True), \
         patch.object(main_mod, "is_logged_in", return_value=False), \
         patch.object(main_mod, "login_flow", return_value=True) as mock_login:
        assert require_telegram_ready(config) is True
        mock_login.assert_called_once()


def test_require_telegram_ready_false_when_setup_declined():
    config = {}
    with patch.object(main_mod, "ensure_telethon", return_value=True), \
         patch.object(main_mod, "is_configured", return_value=False), \
         patch.object(main_mod, "login_flow", return_value=False):
        assert require_telegram_ready(config) is False


@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.questionary.select")
def test_handle_telegram_menu_back_immediately(mock_select, mock_press):
    ask = MagicMock()
    ask.ask.return_value = "⬅ Kembali / Back"
    mock_select.return_value = ask
    handle_telegram_menu("https://x/", {})
    ask.ask.assert_called_once()


@patch("src.main.questionary.select")
@patch("src.main.load_config", return_value={"active_url": "u", "target_urls": [{"url": "u"}]})
@patch("src.main.ensure_playwright")
@patch("src.main.ensure_ffmpeg")
@patch("src.main.ensure_binary")
@patch("src.main.is_chromium_installed", return_value=True)
@patch("src.main.get_ffmpeg_paths", return_value=("f", "fp"))
@patch("src.main.get_binary_path", return_value="b")
@patch("src.main.print_header")
@patch("src.main.init_db")
@patch("src.main.handle_telegram_menu")
def test_main_routes_option_nine_then_exit(
    mock_tg, _init_db, _header, _gbp, _gfp, _chrom, _eb, _ef, _ep, _lc,
    mock_select
):
    from src.main import main as main_fn

    mock_select.return_value = MagicMock(ask=MagicMock(side_effect=[
        "9. 📡 Telegram Backup / Kelola Backup Telegram",
        "⬅ Kembali / Back",
        "10. ❌ Exit / Keluar",
    ]))
    with pytest.raises(SystemExit):
        main_fn()
    mock_tg.assert_called_once()


SCAN_ITEMS = [
    {"title": "Film A", "year": "2024", "media_type": "movie", "season": None,
     "episode": None, "file_size": 10, "part_count": 1, "subtitles": [],
     "video_msg_ids": [1], "sub_msg_ids": [], "chat": "me"},
    {"title": "Series B", "year": "2023", "media_type": "episode", "season": 1,
     "episode": 2, "file_size": 20, "part_count": 1, "subtitles": [],
     "video_msg_ids": [2], "sub_msg_ids": [], "chat": "me"},
]


@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.scan_with_spinner", return_value=SCAN_ITEMS)
@patch("src.main.require_telegram_ready", return_value=True)
def test_handle_telegram_lists_all_backups(mock_ready, mock_scan, mock_press, capsys):
    from src.main import handle_telegram_list
    handle_telegram_list({})
    out = capsys.readouterr().out
    assert "Film A" in out and "Series B" in out
    mock_scan.assert_called_once()


@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.questionary.confirm")
@patch("src.main.restore_backup", return_value="C:/out/Film A.mp4")
@patch("src.main.create_client")
@patch("src.main.questionary.text")
@patch("src.main.scan_with_spinner", return_value=SCAN_ITEMS)
@patch("src.main.require_telegram_ready", return_value=True)
def test_handle_telegram_search_restores_selected(
    mock_ready, mock_scan, mock_text, mock_client, mock_restore, mock_confirm, mock_press
):
    from src.main import handle_telegram_search_restore

    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=[
        "film a",  # query pencarian
        "1",       # pilih nomor item hasil filter
    ]))
    mock_confirm.return_value = MagicMock(ask=MagicMock(return_value=True))
    handle_telegram_search_restore({})
    mock_restore.assert_called_once()
    called_item = mock_restore.call_args[0][1]
    assert called_item["title"] == "Film A"


@patch("src.main.restore_backup")
@patch("src.main.questionary.text")
@patch("src.main.scan_with_spinner", return_value=SCAN_ITEMS)
@patch("src.main.require_telegram_ready", return_value=True)
def test_handle_telegram_search_superscript_pick_cancels_gracefully(
    mock_ready, mock_scan, mock_text, mock_restore, capsys
):
    from src.main import handle_telegram_search_restore

    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=[
        "film a",  # query pencarian
        "²",       # nomor unicode-superscript: harus batal, bukan crash
    ]))
    handle_telegram_search_restore({})
    assert "Restore dibatalkan" in capsys.readouterr().out
    mock_restore.assert_not_called()


LOCAL_ENTRIES = [
    {"title": "Safe Film", "year": "2024", "media_type": "movie", "season": None,
     "episode": None, "output_path": "C:/safe.mp4", "file_size": 5, "backed": True,
     "key": "safefilm|2024||"},
    {"title": "Risky Film", "year": "2025", "media_type": "movie", "season": None,
     "episode": None, "output_path": "C:/risky.mp4", "file_size": 6, "backed": False,
     "key": "riskyfilm|2025||"},
]


def test_manual_backup_calls_upload_per_selection(tmp_path, monkeypatch):
    real_file = tmp_path / "Safe Film.mp4"
    real_file.write_bytes(b"x" * 5)
    entries = [dict(LOCAL_ENTRIES[0], output_path=str(real_file))]
    monkeypatch.setattr(main_mod, "collect_local_entries", lambda: entries)
    monkeypatch.setattr(main_mod, "scan_with_spinner", lambda cfg: [])
    monkeypatch.setattr(main_mod, "require_telegram_ready", lambda cfg: True)

    uploads = []

    def fake_upload(client, path, subs, meta, dests, progress_callback=None):
        uploads.append((path, meta))
        return {"video_msg_ids": [1], "sub_msg_ids": [], "forwarded_to": []}

    monkeypatch.setattr(main_mod, "upload_backup", fake_upload)
    monkeypatch.setattr(main_mod, "create_client", lambda cfg: MagicMock())

    with patch("src.main.questionary.checkbox") as mock_check, \
         patch("src.main.questionary.press_any_key_to_continue"):
        mock_check.return_value = MagicMock(ask=MagicMock(return_value=["1. ✅ Safe Film (duplikat)"]))
        main_mod.handle_telegram_manual_backup({})

    assert len(uploads) == 1
    assert uploads[0][0] == str(real_file)


def test_delete_local_requires_typed_confirmation_for_unbacked(tmp_path, monkeypatch):
    real_risky = tmp_path / "Risky Film.mp4"
    real_risky.write_bytes(b"y" * 6)
    entries = [dict(LOCAL_ENTRIES[1], output_path=str(real_risky))]
    monkeypatch.setattr(main_mod, "collect_local_entries", lambda: entries)
    monkeypatch.setattr(main_mod, "scan_with_spinner", lambda cfg: [])
    monkeypatch.setattr(main_mod, "require_telegram_ready", lambda cfg: True)

    with patch("src.main.questionary.checkbox") as mock_check, \
         patch("src.main.questionary.confirm") as mock_confirm, \
         patch("src.main.questionary.text") as mock_text, \
         patch("src.main.questionary.press_any_key_to_continue"):
        mock_check.return_value = MagicMock(ask=MagicMock(return_value=["1. ⚠️ Risky Film (BELUM DIBACKUP)"]))
        mock_confirm.return_value = MagicMock(ask=MagicMock(return_value=True))
        mock_text.return_value = MagicMock(ask=MagicMock(return_value="HAPUS"))
        main_mod.handle_telegram_delete_local({})

    assert not real_risky.exists()


def test_delete_local_wrong_word_aborts(tmp_path, monkeypatch):
    real_risky = tmp_path / "Risky Film.mp4"
    real_risky.write_bytes(b"y" * 6)
    entries = [dict(LOCAL_ENTRIES[1], output_path=str(real_risky))]
    monkeypatch.setattr(main_mod, "collect_local_entries", lambda: entries)
    monkeypatch.setattr(main_mod, "scan_with_spinner", lambda cfg: [])
    monkeypatch.setattr(main_mod, "require_telegram_ready", lambda cfg: True)

    with patch("src.main.questionary.checkbox") as mock_check, \
         patch("src.main.questionary.confirm") as mock_confirm, \
         patch("src.main.questionary.text") as mock_text, \
         patch("src.main.questionary.press_any_key_to_continue"):
        mock_check.return_value = MagicMock(ask=MagicMock(return_value=["1. ⚠️ Risky Film (BELUM DIBACKUP)"]))
        mock_confirm.return_value = MagicMock(ask=MagicMock(return_value=True))
        mock_text.return_value = MagicMock(ask=MagicMock(return_value="salah"))
        main_mod.handle_telegram_delete_local({})

    assert real_risky.exists()


@patch("src.main.handle_item_download")
@patch("src.main.process_download_item")
@patch("src.main.restore_backup", return_value="C:/r/X.mp4")
@patch("src.main.create_client")
@patch("src.main.scan_with_spinner")
@patch("src.main.search_content")
@patch("src.main.questionary.text")
@patch("src.main.questionary.confirm")
@patch("src.main.questionary.press_any_key_to_continue")
def test_handle_search_routes_telegram_result_to_restore(
    _press, mock_confirm, mock_text, mock_search, mock_scan, mock_client, mock_restore, mock_proc, mock_hid
):
    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=[
        "dupe",      # query pencarian
        "2",         # pilih nomor item hybrid (baris TELEGRAM; idlix selalu baris lebih dulu)
    ]))
    mock_search.return_value = [{"title": "Dupe Film", "type": "Movie", "url": "https://x/dupe-film"}]
    mock_scan.return_value = [{
        "title": "Dupe Film", "year": "2024", "media_type": "movie",
        "season": None, "episode": None, "file_size": 9, "part_count": 1,
        "subtitles": [], "video_msg_ids": [7], "sub_msg_ids": [], "chat": "me",
    }]
    mock_confirm.return_value = MagicMock(ask=MagicMock(return_value=True))

    main_mod.handle_search("https://z2.idlixku.com/", {"active_url": "https://z2.idlixku.com/"})

    mock_restore.assert_called_once()
    called_item = mock_restore.call_args[0][1]
    assert called_item["__source__"] == "telegram"
    mock_proc.assert_not_called()
    mock_hid.assert_not_called()


@patch("src.main.process_download_item")
@patch("src.main.scan_with_spinner", side_effect=Exception("offline"))
@patch("src.main.search_content")
@patch("src.main.questionary.text")
@patch("src.main.questionary.press_any_key_to_continue")
def test_handle_search_survives_telegram_failure(
    _press, mock_text, mock_search, mock_scan, mock_proc
):
    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=["anything", "1"]))
    mock_search.return_value = [{"title": "Any Film", "type": "Movie", "url": "https://x/any"}]
    main_mod.handle_search("https://z2.idlixku.com/", {"active_url": "u"})
    mock_proc.assert_called_once()
