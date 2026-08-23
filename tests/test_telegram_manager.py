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


from src.telegram_manager import scan_backups, build_caption


class FakeDoc:
    def __init__(self, attributes):
        self.attributes = attributes


class FakeAttr:
    def __init__(self, file_name):
        self.file_name = file_name


class FakeMsg:
    def __init__(self, msg_id, caption=None, file_name=None):
        self.id = msg_id
        self.message = caption
        self.document = FakeDoc([FakeAttr(file_name)]) if file_name else FakeDoc([])


VIDEO_META = {"kind": "video", "title": "Film A", "year": "2024", "media_type": "movie",
              "season": None, "episode": None, "file_size": 300, "part_count": 2,
              "subtitles": ["Film A.id.srt"]}
SUB_META = {"kind": "subtitle", "filename": "Film A.id.srt", "parent_title": "Film A"}


class FakeClient:
    def __init__(self, messages_by_target):
        self._messages_by_target = messages_by_target
        self.iter_calls = []

    def iter_messages(self, target, reverse=None, limit=None):
        self.iter_calls.append((target, reverse, limit))
        return iter(self._messages_by_target.get(target, []))


DESTS = [{"type": "saved", "target": "me"}]


def test_scan_groups_parts_subs_and_skips_foreign():
    messages = [
        FakeMsg(1, caption=build_caption(VIDEO_META), file_name="Film A.part001"),
        FakeMsg(2),  # part 2 tanpa caption app
        FakeMsg(3, caption=build_caption(SUB_META), file_name="Film A.id.srt"),
        FakeMsg(99, caption="caption orang lain", file_name="other.bin"),  # dilewati
    ]
    client = FakeClient({"me": messages})
    items = scan_backups(client, DESTS)
    assert client.iter_calls == [("me", True, None)]
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "Film A"
    assert item["video_msg_ids"] == [1, 2]
    assert item["sub_msg_ids"] == [3]
    assert item["subtitles"] == ["Film A.id.srt"]
    assert item["chat"] == "me"


def test_part_cap_rejects_extra_uncaptioned_doc():
    messages = [
        FakeMsg(1, caption=build_caption(VIDEO_META), file_name="Film A.part001"),
        FakeMsg(2),
        FakeMsg(3, caption=build_caption(SUB_META), file_name="Film A.id.srt"),
        FakeMsg(99, caption="caption orang lain", file_name="other.bin"),
        FakeMsg(4),
    ]
    items = scan_backups(FakeClient({"me": messages}), DESTS)
    assert len(items) == 1
    assert items[0]["video_msg_ids"] == [1, 2]


def test_skips_messages_without_document():
    bare = type("Bare", (), {"id": 9, "message": None})()
    messages = [
        FakeMsg(1, caption=build_caption(VIDEO_META), file_name="Film A.part001"),
        bare,
        FakeMsg(2),
    ]
    items = scan_backups(FakeClient({"me": messages}), DESTS)
    assert len(items) == 1
    assert items[0]["video_msg_ids"] == [1, 2]


def test_scan_all_destinations_no_dedupe_between_targets():
    ch_meta = dict(VIDEO_META)
    msgs_me = [
        FakeMsg(3, caption=build_caption(ch_meta), file_name="p1"),
        FakeMsg(4),
    ]
    msgs_channel = [
        FakeMsg(55, caption=build_caption(ch_meta), file_name="p1"),
        FakeMsg(56),
    ]
    client = FakeClient({"me": msgs_me, "@c": msgs_channel})
    items = scan_backups(client, [
        {"type": "saved", "target": "me"},
        {"type": "channel", "target": "@c"},
    ])
    chats = sorted(it["chat"] for it in items)
    assert chats == ["@c", "me"]
    assert len(items) == 2


def test_scan_returns_empty_without_destination():
    assert scan_backups(FakeClient({}), []) == []


def test_scan_subtitle_before_any_video_is_ignored():
    messages = [FakeMsg(1, caption=build_caption(SUB_META), file_name="x.srt")]
    assert scan_backups(FakeClient({"me": messages}), DESTS) == []


import json

from src.telegram_manager import upload_backup


class RecordingClient:
    """Fake Telethon client yang merekam send_file/forward_messages."""

    def __init__(self):
        self.sent = []
        self.forwards = []
        self._id = 100

    def send_file(self, target, path, caption="", force_document=False,
                  supports_streaming=False, progress_callback=None):
        self._id += 1
        self.sent.append({
            "target": target, "path": path, "caption": caption,
            "force_document": force_document, "supports_streaming": supports_streaming,
        })
        msg = MagicMock()
        msg.id = self._id
        return msg

    def forward_messages(self, target, ids, from_peer):
        self.forwards.append((target, list(ids), from_peer))
        return [MagicMock() for _ in ids]


def _make_big_file(tmp_path, size):
    path = tmp_path / "Big Movie.mp4"
    path.write_bytes(b"x" * size)
    return str(path)


META = {"title": "Film B", "year": "2025", "media_type": "movie",
        "season": None, "episode": None, "subtitles": []}
UPLOAD_DESTS = [{"type": "saved", "target": "me"}, {"type": "channel", "target": "@c"}]


def test_upload_single_part_streams_and_forwards(tmp_path):
    src = _make_big_file(tmp_path, 1000)
    client = RecordingClient()
    result = upload_backup(client, src, [], dict(META), UPLOAD_DESTS)
    assert len(client.sent) == 1
    sent = client.sent[0]
    assert sent["force_document"] is False
    assert sent["supports_streaming"] is True
    assert '"kind": "video"' in sent["caption"].replace("'", '"')
    assert '"part_count": 1' in sent["caption"].replace("'", '"')
    assert result["video_msg_ids"] == [101]
    assert result["forwarded_to"] == ["@c"]
    assert client.forwards == [("@c", [101], "me")]


def test_upload_multi_part_splits_captions_first_part_only_and_cleans_temp(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "PART_SIZE", 1300)
    src = _make_big_file(tmp_path, 2500)
    parts_dir = tmp_path / "parts"
    client = RecordingClient()
    result = upload_backup(client, src, [], dict(META),
                           [UPLOAD_DESTS[0]], progress_callback=None, tmp_dir=str(parts_dir))
    assert len(client.sent) == 2
    caps = [s["caption"] for s in client.sent]
    first_meta = json.loads(caps[0].split("```json")[1].strip().strip("`"))
    assert first_meta["part_count"] == 2
    assert first_meta["file_size"] == 2500
    assert caps[1] == ""
    assert all(s["force_document"] for s in client.sent)
    assert parts_dir.exists()
    assert list(parts_dir.glob("*")) == []
    assert len(result["video_msg_ids"]) == 2


def test_upload_subtitles_as_documents_with_marker_caption(tmp_path):
    src = _make_big_file(tmp_path, 100)
    sub = tmp_path / "Film B.id.srt"
    sub.write_text("SUB")
    client = RecordingClient()
    upload_backup(client, src, [str(sub)], dict(META), [UPLOAD_DESTS[0]])
    assert len(client.sent) == 2
    sub_sent = client.sent[1]
    assert sub_sent["force_document"] is True
    assert '"kind": "subtitle"' in sub_sent["caption"].replace("'", '"')
    assert "Film B.id.srt" in sub_sent["caption"]


def test_auto_tmp_dir_created_and_removed(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    auto_root = tmp_path / "auto_split"
    auto_root.mkdir()
    monkeypatch.setattr(tm, "TMP_SPLIT_DIR", str(auto_root))
    monkeypatch.setattr(tm, "PART_SIZE", 1300)
    seen = []
    real_split = tm.split_file

    def recording_split(path, part_size, tmp_dir):
        seen.extend(os.listdir(str(auto_root)))
        return real_split(path, part_size=part_size, tmp_dir=tmp_dir)

    monkeypatch.setattr(tm, "split_file", recording_split)
    src = _make_big_file(tmp_path, 2500)
    client = RecordingClient()
    upload_backup(client, src, [], dict(META), [{"type": "saved", "target": "me"}])
    assert len(client.sent) == 2
    assert len(seen) == 1
    assert seen[0].startswith("up_")
    assert os.listdir(str(auto_root)) == []


import pytest

from src.telegram_manager import build_restore_target, restore_backup


RESTORE_CONFIG = {
    "organize_mode": "separate",
    "movies_dir": "/tmp-test/Movies",
    "series_dir": "/tmp-test/Series",
}

MOVIE_ITEM = {
    "title": "Film A", "year": "2024", "media_type": "movie",
    "season": None, "episode": None, "file_size": 11, "part_count": 2,
    "subtitles": ["Film A.id.srt"],
    "video_msg_ids": [31, 32], "sub_msg_ids": [33], "chat": "me",
}


def test_build_restore_target_movie_uses_movies_dir():
    target_dir, filename = build_restore_target(RESTORE_CONFIG, MOVIE_ITEM)
    assert target_dir.replace("\\", "/").endswith("/tmp-test/Movies/Film A (2024)")
    assert filename == "Film A (2024).mp4"


def test_build_restore_target_episode_uses_series_paths():
    item = dict(MOVIE_ITEM, media_type="episode", title="Series Z",
                season=2, episode=5, year="2023")
    target_dir, filename = build_restore_target(RESTORE_CONFIG, item)
    assert "Series Z (2023)" in target_dir.replace("\\", "/")
    assert "Season 02" in target_dir.replace("\\", "/")
    assert filename == "Series Z - S02E05.mp4"


class RestoreFakeClient:
    def __init__(self, payloads_by_id):
        self.payloads = payloads_by_id
        self.downloaded = []

    def get_messages(self, chat, ids):
        wrapped = []
        for msg_id in ids:
            m = MagicMock()
            m.id = msg_id
            wrapped.append(m)
        return wrapped

    def download_media(self, message, file=None, progress_callback=None):
        msg_id = message.id
        out = os.path.join(file, f"{msg_id}.bin") if os.path.isdir(str(file)) else str(file)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as fh:
            fh.write(self.payloads[msg_id])
        self.downloaded.append(out)
        return out


def test_restore_merges_parts_downloads_subs_and_verifies(tmp_path, monkeypatch):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "TMP_SPLIT_DIR", str(tmp_path / "tmp"))
    client = RestoreFakeClient({31: b"hello ", 32: b"world", 33: b"SRTDATA"})
    config = {
        "organize_mode": "separate",
        "movies_dir": str(tmp_path / "Movies"),
        "series_dir": str(tmp_path / "Series"),
    }
    out_path = restore_backup(client, MOVIE_ITEM, config)
    assert os.path.basename(out_path) == "Film A (2024).mp4"
    with open(out_path, "rb") as fh:
        assert fh.read() == b"hello world"
    restored_subs = [f for f in os.listdir(os.path.dirname(out_path)) if f.endswith(".bin")]
    assert len(restored_subs) == 1
    leftovers = [f for f in os.listdir(str(tmp_path / "tmp"))]
    assert leftovers == []


def test_restore_raises_ioerror_on_size_mismatch_keeps_parts(tmp_path, monkeypatch):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "TMP_SPLIT_DIR", str(tmp_path / "tmp"))
    client = RestoreFakeClient({31: b"short", 32: b"", 33: b""})
    config = {
        "organize_mode": "separate",
        "movies_dir": str(tmp_path / "Movies"),
        "series_dir": str(tmp_path / "Series"),
    }
    with pytest.raises(IOError):
        restore_backup(client, dict(MOVIE_ITEM, video_msg_ids=[31]), config)
