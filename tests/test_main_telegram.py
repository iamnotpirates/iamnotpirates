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
    mock_select, monkeypatch
):
    from src.main import main as main_fn

    monkeypatch.setattr("sys.argv", ["iamnotpirates"])

    mock_select.return_value = MagicMock(ask=MagicMock(side_effect=[
        "9. 📡 Telegram Backup / Kelola Backup Telegram",
        "⬅ Kembali / Back",
        "10. ❌ Exit / Keluar",
    ]))
    with pytest.raises(SystemExit):
        main_fn()
    mock_tg.assert_called_once()


@patch("src.main.save_config_key")
@patch("src.main.load_config", return_value={})
@patch("src.main.questionary.select")
@patch("src.main.questionary.password")
@patch("src.main.questionary.text")
def test_settings_api_hash_uses_password_prompt(mock_text, mock_pw, mock_select, mock_load, mock_save):
    def strict_text(_prompt, **kwargs):
        unexpected = set(kwargs) - {"default"}
        if unexpected:
            raise TypeError(f"text() got unexpected kwargs: {unexpected}")
        return MagicMock(ask=MagicMock(return_value="38489027"))

    mock_text.side_effect = strict_text
    mock_pw.return_value = MagicMock(ask=MagicMock(return_value="h"))
    mock_select.return_value = MagicMock(ask=MagicMock(side_effect=[
        "🔑 Isi Ulang API ID / Hash",
        "⬅ Kembali / Back",
    ]))

    from src.main import handle_telegram_settings
    handle_telegram_settings({})

    assert mock_pw.called
    assert mock_pw.return_value.ask.called
    saved = {call.args[0]: call.args[1] for call in mock_save.call_args_list}
    assert saved.get("tg_api_id") == "38489027"
    assert saved.get("tg_api_hash") == "h"
    assert mock_text.call_count == 1


SCAN_ITEMS = [
    {"title": "Film A", "year": "2024", "media_type": "movie", "season": None,
     "episode": None, "file_size": 10, "part_count": 1, "subtitles": [],
     "video_msg_ids": [1], "sub_msg_ids": [], "chat": "me"},
    {"title": "Series B", "year": "2023", "media_type": "episode", "season": 1,
     "episode": 2, "file_size": 20, "part_count": 1, "subtitles": [],
     "video_msg_ids": [2], "sub_msg_ids": [], "chat": "me"},
]


class DisconnectedFakeClient:
    def __init__(self):
        self.calls = []
        self._connected = False
        self.loop = self

    def run_until_complete(self, coro):
        if coro == "coro-connect":
            self._connected = True
            self.calls.append("connect")
        elif coro == "coro-disconnect":
            self.calls.append("disconnect")
            self._connected = False
        return coro

    def connect(self):
        return "coro-connect"

    def disconnect(self):
        return "coro-disconnect"

    def is_user_authorized(self):
        return True

    def send_file(self, *a, **k):
        if not self._connected:
            raise RuntimeError("Cannot send requests while disconnected")
        return MagicMock(id=1)

    def iter_messages(self, target, reverse=None, limit=None):
        if not self._connected:
            raise RuntimeError("Cannot send requests while disconnected")
        self.calls.append("iter")
        return iter([])


@patch("src.main.get_destinations",
       return_value=[{"type": "saved", "target": "me", "topic": None}])
def test_scan_with_spinner_connects_client(mock_dests, monkeypatch):
    fake = DisconnectedFakeClient()
    monkeypatch.setattr(main_mod, "create_client", lambda cfg: fake)
    main_mod.scan_with_spinner({})
    assert fake.calls[0] == "connect"
    assert "iter" in fake.calls
    assert fake.calls[-1] == "disconnect"


@patch("src.main.restore_backup", return_value="C:/ok/Film A.mp4")
@patch("src.main.get_destinations",
       return_value=[{"type": "saved", "target": "me", "topic": None}])
def test_restore_helper_connects_client(mock_dests, mock_restore, monkeypatch):
    fake = DisconnectedFakeClient()
    monkeypatch.setattr(main_mod, "create_client", lambda cfg: fake)
    out = main_mod._restore_from_telegram({}, dict(SCAN_ITEMS[0]))
    assert out == "C:/ok/Film A.mp4"
    assert fake.calls[0] == "connect"
    assert fake.calls[-1] == "disconnect"


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


TWIN_ITEMS = [
    {"title": "Film A", "year": "2024", "media_type": "movie", "season": None,
     "episode": None, "file_size": 10, "part_count": 1, "subtitles": [],
     "video_msg_ids": [1], "sub_msg_ids": [], "chat": "me"},
    {"title": "Film A", "year": "2024", "media_type": "movie", "season": None,
     "episode": None, "file_size": 10, "part_count": 1, "subtitles": [],
     "video_msg_ids": [9], "sub_msg_ids": [], "chat": "@c"},
]


@patch("subprocess.Popen")
@patch("src.main.questionary.press_any_key_to_continue")
@patch("src.main.questionary.confirm", return_value=MagicMock(ask=MagicMock(return_value=True)))
@patch("src.main.restore_backup", side_effect=[Exception("boom"), "C:/ok/Film A.mp4"])
@patch("src.main.create_client")
@patch("src.main.get_destinations",
       return_value=[{"type": "saved", "target": "me"}, {"type": "channel", "target": "@c"}])
@patch("src.main.scan_with_spinner", return_value=TWIN_ITEMS)
@patch("src.main.questionary.text")
@patch("src.main.require_telegram_ready", return_value=True)
def test_handle_telegram_search_restores_falls_back_to_twin_chat(
    mock_ready, mock_text, mock_scan, mock_get_dests, mock_client,
    mock_restore, mock_confirm, mock_press, mock_popen, capsys
):
    from src.main import handle_telegram_search_restore

    mock_text.return_value = MagicMock(ask=MagicMock(side_effect=[
        "film a",  # query pencarian
        "1",       # pilih nomor item hasil filter
    ]))
    handle_telegram_search_restore({})

    assert mock_restore.call_count == 2
    second_item = mock_restore.call_args_list[1][0][1]
    assert second_item["chat"] == "@c"
    assert "Restore selesai" in capsys.readouterr().out


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
        if not client._connected:
            raise RuntimeError("Cannot send requests while disconnected")
        uploads.append((path, meta))
        return {"video_msg_ids": [1], "sub_msg_ids": [], "forwarded_to": []}

    monkeypatch.setattr(main_mod, "upload_backup", fake_upload)
    fake_client = DisconnectedFakeClient()
    monkeypatch.setattr(main_mod, "create_client", lambda cfg: fake_client)

    with patch("src.main.questionary.checkbox") as mock_check, \
         patch("src.main.questionary.press_any_key_to_continue"):
        mock_check.return_value = MagicMock(ask=MagicMock(return_value=["1. ✅ Safe Film (duplikat)"]))
        main_mod.handle_telegram_manual_backup({})

    assert len(uploads) == 1
    assert uploads[0][0] == str(real_file)
    assert fake_client.calls[0] == "connect"
    assert fake_client.calls[-1] == "disconnect"


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


def test_auto_backup_disabled_does_nothing(tmp_path):
    video = tmp_path / "V.mp4"
    video.write_bytes(b"x" * 3)
    calls = []
    with patch.object(main_mod, "upload_backup", lambda *a, **k: calls.append(a)):
        main_mod.maybe_auto_backup(str(video), {"tg_auto_backup": "0"}, "V", "2024", "movie")
    assert calls == []


def test_auto_backup_uploads_with_siblings_and_never_raises(tmp_path):
    video = tmp_path / "My Film.mp4"
    video.write_bytes(b"x" * 3)
    (tmp_path / "My Film.id.srt").write_text("srt")
    (tmp_path / "Other.id.srt").write_text("nope")
    captured = {}

    def fake_upload(client, path, subs, meta, dests, progress_callback=None):
        captured.update(path=path, subs=subs, meta=meta)
        return {"video_msg_ids": [1], "sub_msg_ids": [], "forwarded_to": []}

    config = {"tg_auto_backup": "1"}
    with patch.object(main_mod, "is_configured", return_value=True), \
         patch.object(main_mod, "is_logged_in", return_value=True), \
         patch.object(main_mod, "get_destinations", return_value=[{"type": "saved", "target": "me"}]), \
         patch.object(main_mod, "create_client", lambda cfg: MagicMock()), \
         patch.object(main_mod, "upload_backup", fake_upload):
        main_mod.maybe_auto_backup(str(video), config, "My Film", "2024", "movie")
    assert captured["subs"] == [str(tmp_path / "My Film.id.srt")]
    assert captured["meta"]["title"] == "My Film"


def test_auto_backup_swallows_errors(tmp_path):
    video = tmp_path / "Boom.mp4"
    video.write_bytes(b"x")
    with patch.object(main_mod, "is_configured", return_value=True), \
         patch.object(main_mod, "is_logged_in", return_value=True), \
         patch.object(main_mod, "get_destinations", return_value=[{"type": "saved", "target": "me"}]), \
         patch.object(main_mod, "create_client", lambda cfg: MagicMock()), \
         patch.object(main_mod, "upload_backup", side_effect=RuntimeError("boom")):
        main_mod.maybe_auto_backup(str(video), {"tg_auto_backup": "1"}, "Boom", "2024", "movie")
