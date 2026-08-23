import os
import sys
from unittest.mock import MagicMock, patch

from src.telegram_manager import (
    is_configured, is_logged_in, get_destinations,
    ensure_telethon, create_client,
)
from src.telegram_manager import build_caption, parse_caption
from src.telegram_manager import split_file, merge_files, cleanup_parts, PART_SIZE
from src.telegram_manager import normalize_title, matches_query, backup_key, entry_backup_key


def test_build_caption_contains_human_line_and_json_block():
    meta = {"kind": "video", "title": "Judul Film", "year": "2024",
            "media_type": "movie", "season": None, "episode": None,
            "file_size": 1000, "part_count": 1, "subtitles": []}
    caption = build_caption(meta)
    assert caption.startswith("🎬 Judul Film (2024)")
    assert '"app": "iamnotpirates"' in caption.replace("'iamnotpirates'", '"iamnotpirates"').replace('": "', '": "') or '"app"' in caption
    assert "```json" in caption


def test_parse_caption_roundtrip_video():
    meta = {"kind": "video", "title": "Judul Film", "year": "2024",
            "media_type": "movie", "season": None, "episode": None,
            "file_size": 12345, "part_count": 2, "subtitles": ["a.srt"]}
    parsed = parse_caption(build_caption(meta))
    assert parsed == {"app": "iamnotpirates", "v": 1, **meta}


def test_parse_caption_roundtrip_subtitle():
    meta = {"kind": "subtitle", "filename": "Film.id.srt", "parent_title": "Film"}
    parsed = parse_caption(build_caption(meta))
    assert parsed["kind"] == "subtitle"
    assert parsed["filename"] == "Film.id.srt"


def test_parse_caption_returns_none_for_foreign_or_broken_text():
    assert parse_caption("just a normal caption") is None
    assert parse_caption("") is None
    assert parse_caption(None) is None
    assert parse_caption("```json\n{broken\n```") is None
    assert parse_caption('```json\n{"app": "other"}\n```') is None


def test_split_and_merge_small_file_roundtrip(tmp_path):
    src = tmp_path / "movie.mp4"
    payload = os.urandom(5000)
    src.write_bytes(payload)

    parts = split_file(str(src), part_size=2000, tmp_dir=str(tmp_path / "parts"))
    assert len(parts) == 3
    assert all(os.path.exists(p) for p in parts)

    out = tmp_path / "merged.mp4"
    merge_files(parts, str(out))
    assert out.read_bytes() == payload


def test_split_exact_multiple_makes_no_empty_part(tmp_path):
    src = tmp_path / "f.bin"
    src.write_bytes(b"x" * 4000)
    parts = split_file(str(src), part_size=2000, tmp_dir=str(tmp_path / "p2"))
    assert len(parts) == 2


def test_merge_creates_missing_parent_dirs(tmp_path):
    p1 = tmp_path / "a.part1"
    p1.write_bytes(b"hello ")
    p2 = tmp_path / "a.part2"
    p2.write_bytes(b"world")
    out = tmp_path / "deep" / "nested" / "out.txt"
    merge_files([str(p1), str(p2)], str(out))
    assert out.read_bytes() == b"hello world"


def test_cleanup_parts_removes_files_and_tolerates_missing(tmp_path):
    p1 = tmp_path / "x.part1"
    p1.write_bytes(b"a")
    cleanup_parts([str(p1), str(tmp_path / "ghost.part2")])
    assert not p1.exists()


def test_part_size_below_two_gb_limit():
    assert 0 < PART_SIZE < 2 * 1024 * 1024 * 1024


def test_normalize_title_strips_case_and_symbols():
    assert normalize_title("Judul: Film-Bagus! 2024") == "judulfilmbagus2024"


def test_matches_query_substring_normalized():
    assert matches_query("The Last of Us (2023)", "last of us")
    assert matches_query("Avengers Endgame", "avengers")
    assert not matches_query("Batman", "superman")


def test_matches_query_empty_query_is_false():
    assert not matches_query("Anything", "")
    assert not matches_query("", "x")


def test_backup_key_consistent_across_season_episode():
    a = backup_key("Film X", "2024", None, None)
    b = entry_backup_key({"title": "Film X", "year": "2024"})
    assert a == b
    ep_a = backup_key("Series Y", "2023", 2, 5)
    ep_b = entry_backup_key({"title": "Series Y", "year": "2023", "season": 2, "episode": 5})
    assert ep_a == ep_b
    assert ep_a != a


def test_entry_backup_key_handles_none_year():
    assert entry_backup_key({"title": "Z"}) == backup_key("Z", None, None, None)


def test_is_configured_requires_both_keys():
    assert is_configured({"tg_api_id": "1", "tg_api_hash": "h"})
    assert not is_configured({"tg_api_id": "", "tg_api_hash": "h"})
    assert not is_configured({})


def test_is_logged_in_checks_session_file(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "SESSION_PATH", str(tmp_path / "session"))
    assert not tm.is_logged_in()
    (tmp_path / "session.session").write_text("x")
    assert tm.is_logged_in()


def test_get_destinations_saved_only_default():
    dests = get_destinations({"tg_destinations": '["saved"]'})
    assert dests == [{"type": "saved", "target": "me"}]


def test_get_destinations_channel_requires_channel_id():
    assert get_destinations({
        "tg_destinations": '["saved","channel"]', "tg_channel_id": "@mychan"
    }) == [
        {"type": "saved", "target": "me"},
        {"type": "channel", "target": "@mychan"},
    ]
    assert get_destinations({"tg_destinations": '["channel"]', "tg_channel_id": ""}) == []
    assert get_destinations({"tg_destinations": "bukan-json"}) == [{"type": "saved", "target": "me"}]


def test_ensure_telethon_true_when_importable():
    assert ensure_telethon(MagicMock())


def test_create_client_passes_credentials(monkeypatch):
    import src.telegram_manager as tm
    fake_ctor = MagicMock()
    monkeypatch.setitem(sys.modules, "telethon", MagicMock(TelegramClient=fake_ctor))
    client = create_client({"tg_api_id": "123", "tg_api_hash": "hash"})
    fake_ctor.assert_called_once_with(tm.SESSION_PATH, 123, "hash")
    assert client is fake_ctor.return_value


def test_login_flow_rejects_non_numeric_api_id(monkeypatch):
    import src.telegram_manager as tm
    answers = iter(["abc", "h"])
    monkeypatch.setattr(
        "questionary.text",
        lambda _prompt: MagicMock(ask=lambda: next(answers)),
    )
    saved = {}
    monkeypatch.setattr(tm, "save_config_key", lambda key, value: saved.setdefault(key, value))
    assert tm.login_flow(MagicMock(), {}) is False
    assert saved == {}
