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
