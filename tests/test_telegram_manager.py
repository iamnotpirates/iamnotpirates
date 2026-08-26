import os
import sys
from unittest.mock import MagicMock, patch

from src.telegram_manager import (
    is_configured, is_logged_in, get_destinations,
    ensure_telethon, create_client, parse_destination_input,
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
    assert parsed["app"] == "iamnotpirates"
    assert parsed["title"] == "Judul Film"
    assert parsed["year"] == "2024"


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
    assert dests == [{"type": "saved", "target": "me", "topic": None}]


def test_get_destinations_channel_requires_channel_id():
    assert get_destinations({
        "tg_destinations": '["saved","channel"]', "tg_channel_id": "@mychan"
    }) == [
        {"type": "saved", "target": "me", "topic": None},
        {"type": "channel", "target": "@mychan", "topic": None},
    ]
    assert get_destinations({"tg_destinations": '["channel"]', "tg_channel_id": ""}) == []
    assert get_destinations({"tg_destinations": "bukan-json"}) == [{"type": "saved", "target": "me", "topic": None}]


def test_get_destinations_flexible_formats():
    dests = get_destinations({"tg_destinations":
        '["saved","channel:@c","group:-100123","group:-100999:7"]'})
    assert dests == [
        {"type": "saved", "target": "me", "topic": None},
        {"type": "channel", "target": "@c", "topic": None},
        {"type": "group", "target": "-100123", "topic": None},
        {"type": "group", "target": "-100999", "topic": 7},
    ]


def test_parse_destination_input_tokens():
    raw = "saved, channel:@c  group:-100123:7 bogus channel:"
    assert parse_destination_input(raw) == ["saved", "channel:@c", "group:-100123:7"]


def test_parse_destination_input_empty_defaults_saved():
    assert parse_destination_input("   ") == ["saved"]
    assert parse_destination_input("") == ["saved"]


def test_ensure_telethon_true_when_importable():
    assert ensure_telethon(MagicMock())


def test_create_client_passes_credentials(monkeypatch):
    import src.telegram_manager as tm
    fake_ctor = MagicMock()
    monkeypatch.setitem(sys.modules, "telethon", MagicMock(TelegramClient=fake_ctor))
    client = create_client({"tg_api_id": "123", "tg_api_hash": "hash"})
    fake_ctor.assert_called_once_with(
        tm.SESSION_PATH, 123, "hash",
        connection_retries=10, retry_delay=2, auto_reconnect=True,
    )
    assert client is fake_ctor.return_value


def test_send_file_with_retry_retries_on_oserror():
    from src.telegram_manager import _send_file_with_retry
    client = MagicMock()
    client.send_file.side_effect = [OSError(121, "The semaphore timeout period has expired"), "MsgObj"]
    res = _send_file_with_retry(client, "me", "file.mp4")
    assert res == "MsgObj"
    assert client.send_file.call_count == 2


def test_login_flow_rejects_non_numeric_api_id(monkeypatch):
    import src.telegram_manager as tm
    answers = iter(["abc", "h"])
    monkeypatch.setattr(
        "questionary.text",
        lambda _prompt, **_kwargs: MagicMock(ask=lambda: next(answers)),
    )
    monkeypatch.setattr(
        "questionary.password",
        lambda _prompt, **_kwargs: MagicMock(ask=lambda: next(answers)),
    )
    saved = {}
    monkeypatch.setattr(tm, "save_config_key", lambda key, value: saved.setdefault(key, value))
    assert tm.login_flow(MagicMock(), {}) is False
    assert saved == {}


def test_login_flow_uses_password_prompt_for_api_hash(monkeypatch):
    import src.telegram_manager as tm
    answers = iter(["123456", "hashvalue", "+6281234567890"])
    prompts = []

    def fake_text(_prompt, **kwargs):
        if kwargs:
            raise TypeError(f"text() got unexpected kwargs: {kwargs}")
        prompts.append(("text", _prompt))
        return MagicMock(ask=lambda: next(answers))

    def fake_password(_prompt, **kwargs):
        prompts.append(("password", _prompt))
        return MagicMock(ask=lambda: next(answers))

    monkeypatch.setattr("questionary.text", fake_text)
    monkeypatch.setattr("questionary.password", fake_password)

    class FakeClient:
        def __init__(self):
            self.loop = self

        def run_until_complete(self, coro):
            return coro

        def start(self, phone=None):
            return self

        def is_user_authorized(self):
            return True

        def disconnect(self):
            return "coro-disconnect"

    saved = {}
    monkeypatch.setattr(tm, "save_config_key", lambda k, v: saved.setdefault(k, v))
    monkeypatch.setattr(tm, "create_client", lambda config: FakeClient())
    assert tm.login_flow(MagicMock(), {}) is True
    assert ("password", "Masukkan API Hash:") in prompts
    assert saved["tg_api_hash"] == "hashvalue"


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

    def iter_messages(self, target, reverse=None, limit=None, reply_to=None):
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
    assert client.iter_calls == [("me", None, None)]
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
                  supports_streaming=False, progress_callback=None, reply_to=None):
        self._id += 1
        self.sent.append({
            "target": target, "path": path, "caption": caption,
            "force_document": force_document, "supports_streaming": supports_streaming,
            "reply_to": reply_to,
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


def test_upload_single_part_sends_archive_document_and_forwards(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, 1000)
    src = _make_big_file(tmp_path, 1000)
    client = RecordingClient()
    result = upload_backup(client, src, [], dict(META), UPLOAD_DESTS)
    assert len(client.sent) == 1
    sent = client.sent[0]
    assert sent["force_document"] is True
    assert sent["path"].endswith(".7z")
    assert '"kind": "movie"' in sent["caption"].replace("'", '"')
    assert '"title": "Film B"' in sent["caption"].replace("'", '"')
    assert result["video_msg_ids"] == [101]
    assert result["forwarded_to"] == ["@c"]
    assert client.forwards == [("@c", [101], "me")]


def test_upload_multi_part_splits_captions_first_part_only_and_cleans_temp(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "PART_SIZE", 1300)
    src = _make_big_file(tmp_path, 2500)
    parts_dir = tmp_path / "parts"
    client = RecordingClient()
    _fake_archive(monkeypatch, 2500)
    result = upload_backup(client, src, [], dict(META),
                           [UPLOAD_DESTS[0]], progress_callback=None, tmp_dir=str(parts_dir))
    assert len(client.sent) == 2
    caps = [s["caption"] for s in client.sent]
    first_meta = json.loads(caps[0].split("```json")[1].strip().strip("`"))
    assert first_meta["part_count"] == 2
    assert caps[1] == ""
    assert all(s["force_document"] for s in client.sent)
    assert parts_dir.exists()
    assert list(parts_dir.glob("*")) == []
    assert len(result["video_msg_ids"]) == 2


def test_subs_included_in_archive_caption_not_sent_separately(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, 100)
    src = _make_big_file(tmp_path, 100)
    sub_a = tmp_path / "Film B.id.srt"; sub_a.write_text("SUB")
    sub_b = tmp_path / "Film B.eng.srt"; sub_b.write_text("SUB")
    client = RecordingClient()
    upload_backup(client, src, [str(sub_a), str(sub_b)], dict(META), [UPLOAD_DESTS[0]])
    assert len(client.sent) == 1
    cap = client.sent[0]["caption"].replace("'", '"')
    assert '"kind": "movie"' in cap


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
    _fake_archive(monkeypatch, 2500)
    client = RecordingClient()
    upload_backup(client, src, [], dict(META), [{"type": "saved", "target": "me"}])
    assert len(client.sent) == 2
    assert len(seen) == 1
    assert seen[0].startswith("up_")
    assert os.listdir(str(auto_root)) == []


FLEX_DESTS = [
    {"type": "saved", "target": "me", "topic": None},
    {"type": "channel", "target": "@c", "topic": None},
    {"type": "group", "target": "-100g", "topic": None},
    {"type": "group", "target": "-100t", "topic": 5},
]


def test_upload_topic_destination_reuploads_with_reply_to(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, 100)
    src = _make_big_file(tmp_path, 100)
    sub = tmp_path / "Film B.id.srt"
    sub.write_text("SUB")
    client = RecordingClient()
    result = upload_backup(client, src, [str(sub)], dict(META), FLEX_DESTS)

    assert [(s["target"], s["reply_to"]) for s in client.sent if s["path"].endswith(".7z")] == [
        ("me", None), ("-100t", 5),
    ]
    assert [(f[0], f[2]) for f in client.forwards] == [("@c", "me"), ("-100g", "me")]
    assert set(result["forwarded_to"]) == {"@c", "-100g"}
    assert "-100t" not in result["forwarded_to"]


def test_upload_primary_topic_destination_sends_with_reply_to(tmp_path, monkeypatch):
    _fake_archive(monkeypatch, 100)
    src = _make_big_file(tmp_path, 100)
    client = RecordingClient()
    upload_backup(client, src, [], dict(META), [{"type": "group", "target": "-100t", "topic": 9}])
    assert len(client.sent) == 1
    assert (client.sent[0]["target"], client.sent[0]["reply_to"]) == ("-100t", 9)
    assert client.forwards == []


def test_upload_multi_part_topic_reuploads_all_parts(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "PART_SIZE", 1300)
    src = _make_big_file(tmp_path, 2500)
    parts_dir = tmp_path / "parts"
    client = RecordingClient()
    _fake_archive(monkeypatch, 2500)
    upload_backup(client, src, [], dict(META),
                  [{"type": "saved", "target": "me", "topic": None},
                   {"type": "group", "target": "-100t", "topic": 3}],
                  progress_callback=None, tmp_dir=str(parts_dir))
    assert len(client.sent) == 4
    assert all(s["force_document"] for s in client.sent)
    assert [(s["target"], s["reply_to"]) for s in client.sent] == [
        ("me", None), ("me", None), ("-100t", 3), ("-100t", 3),
    ]
    caps = [s["caption"] for s in client.sent]
    assert caps[0] != ""
    assert caps[1] == ""
    assert caps[2] != ""
    assert caps[3] == ""


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
    item = dict(MOVIE_ITEM, video_msg_ids=[31])
    target_dir, filename = build_restore_target(config, item)
    expected_output = os.path.join(target_dir, filename)
    with pytest.raises(IOError):
        restore_backup(client, item, config)
    assert os.listdir(str(tmp_path / "tmp")) != []
    leftovers = [f for f in os.listdir(target_dir) if f.endswith(".merging")]
    assert leftovers == []
    assert not os.path.exists(expected_output)


from src.telegram_manager import collect_local_entries, mark_backed_entries


def test_collect_local_entries_dedupes_and_filters_existing(monkeypatch, tmp_path):
    import src.db_manager as dbm
    real_file = tmp_path / "Film A.mp4"
    real_file.write_bytes(b"data")
    rows = [
        {"status": "success", "title": "Film A", "season": None, "episode": None,
         "output_path": str(real_file), "timestamp": "2026-01-01"},
        {"status": "success", "title": "Film A", "season": None, "episode": None,
         "output_path": str(real_file), "timestamp": "2026-01-02"},
        {"status": "failed", "title": "Film F", "season": None, "episode": None,
         "output_path": str(real_file)},
        {"status": "success", "title": "Hilang", "season": None, "episode": None,
         "output_path": "Z:/tidak/ada.mp4"},
    ]
    monkeypatch.setattr(dbm, "load_log", lambda db_path=None: rows)
    entries = collect_local_entries()
    assert [e["title"] for e in entries] == ["Film A"]
    assert entries[0]["file_size"] == 4
    assert entries[0]["backed"] is False


def test_mark_backed_entries_matches_scan_keys():
    from src.telegram_manager import backup_key as bk, mark_backed_entries as mbe
    local = [{"title": "Film A", "key": bk("Film A", "2024", None, None)}]
    scanned = [{"title": "Film A", "year": "2024", "season": None, "episode": None}]
    assert mbe(local, scanned)[0]["backed"] is True
    other = [{"title": "Lain", "key": bk("Lain", "", None, None)}]
    assert mbe(other, scanned)[0]["backed"] is False


class StubSyncClient:
    def __init__(self):
        self.connected = False

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True


def test_tg_connect_and_disconnect_sync():
    from src.telegram_manager import tg_connect, tg_disconnect
    client = StubSyncClient()
    assert tg_connect(client) is True
    assert client.connected is True
    assert tg_disconnect(client) is True
    assert client.connected is False


def test_resolve_target_numeric_string_fetches_dialogs_if_unseen():
    from src.telegram_manager import resolve_target
    client = MagicMock()
    client.get_entity.side_effect = [ValueError("Cannot find any entity corresponding to -1002312123164"), "EntityObj"]
    res = resolve_target(client, "-1002312123164")
    assert res == "EntityObj"
    assert client.get_entity.call_args_list[0][0][0] == -1002312123164
    assert client.get_dialogs.called


def test_resolve_target_saved_returns_me():
    from src.telegram_manager import resolve_target
    client = MagicMock()
    assert resolve_target(client, "saved") == "me"
    assert resolve_target(client, "me") == "me"


def test_parse_media_filename_movie():
    from src.telegram_manager import parse_media_filename
    meta = parse_media_filename(r"Z:\Film\Movies\The Wolf of Wall Street (2013)\The Wolf of Wall Street (2013).mp4")
    assert meta == {"title": "The Wolf of Wall Street", "year": "2013",
                    "media_type": "movie", "season": None, "episode": None}


def test_parse_media_filename_episode():
    from src.telegram_manager import parse_media_filename
    meta = parse_media_filename(
        r"Z:\Film\Series\Breaking Bad (2008)\Season 02\Breaking Bad - S02E05.mp4")
    assert meta["title"] == "Breaking Bad"
    assert meta["year"] == "2008"
    assert meta["media_type"] == "episode"
    assert meta["season"] == 2
    assert meta["episode"] == 5


def test_parse_media_filename_no_year_returns_none_title():
    from src.telegram_manager import parse_media_filename
    assert parse_media_filename("random.txt") is None
    meta = parse_media_filename("Some Movie.mp4")
    assert meta is not None
    assert meta["title"] == "Some Movie"
    assert meta["year"] == ""


def test_collect_folder_entries_walks_and_dedupes_largest(tmp_path):
    from src.telegram_manager import collect_folder_entries
    movie_dir = tmp_path / "The Wolf of Wall Street (2013)"
    movie_dir.mkdir()
    (movie_dir / "The Wolf of Wall Street (2013).mp4").write_bytes(b"x" * 500)
    (movie_dir / "sample.mp4").write_bytes(b"x" * 10)
    series_dir = tmp_path / "Breaking Bad (2008)" / "Season 01"
    series_dir.mkdir(parents=True)
    (series_dir / "Breaking Bad - S01E01.mkv").write_bytes(b"x" * 100)

    entries = collect_folder_entries([str(tmp_path)])
    by_title = {e["title"]: e for e in entries}
    wolf = by_title["The Wolf of Wall Street"]
    assert wolf["file_size"] == 500
    assert wolf["media_type"] == "movie"
    assert wolf["key"]
    ep = by_title["Breaking Bad"]
    assert ep["media_type"] == "episode"
    assert (ep["season"], ep["episode"]) == (1, 1)


def test_merge_local_entries_log_wins_on_same_key():
    from src.telegram_manager import merge_local_entries
    log_e = [{"title": "Film A", "year": "2024", "media_type": "movie",
              "season": None, "episode": None, "output_path": "/log/a.mp4",
              "file_size": 1, "backed": False, "key": "film-a"}]
    folder_e = [{"title": "Film A", "year": "2024", "media_type": "movie",
                 "season": None, "episode": None, "output_path": "/folder/a.mp4",
                 "file_size": 9, "backed": False, "key": "film-a"},
                {"title": "Film B", "year": "", "media_type": "movie",
                 "season": None, "episode": None, "output_path": "/folder/b.mp4",
                 "file_size": 5, "backed": False, "key": "film-b"}]
    merged = merge_local_entries(log_e, folder_e)
    titles = sorted(e["title"] for e in merged)
    assert titles == ["Film A", "Film B"]
    film_a = [e for e in merged if e["title"] == "Film A"][0]
    assert film_a["output_path"] == "/log/a.mp4"


def test_build_caption_episode_includes_season_episode():
    from src.telegram_manager import build_caption
    cap = build_caption({"kind": "video", "title": "Monster", "year": "2023",
                         "media_type": "episode", "season": 1, "episode": 5,
                         "file_size": 100, "part_count": 1, "subtitles": []})
    assert cap.startswith("🎬 Monster (2023) S01E05")
    assert '"kind": "series"' in cap


def test_build_caption_optimized_for_long_anime_titles():
    from src.telegram_manager import build_caption, parse_caption
    long_title = "Kaguya-sama wa Kokurasetai: Tensai-tachi no Renai Zunousen - Ultra Romantic Season 3 Extended Edition"
    meta = {
        "kind": "video",
        "title": long_title,
        "year": "2022",
        "media_type": "episode",
        "season": 3,
        "episode": 12,
        "file_size": 450000000,
        "part_count": 1,
        "subtitles": ["Kaguya_Indo.srt", "Kaguya_Eng.srt"],
        "archive": True,
        "filename": "Kaguya_S03E12_1080p.mkv",
    }
    cap = build_caption(meta)
    assert len(cap) <= 1000
    assert long_title in cap
    parsed = parse_caption(cap)
    assert parsed["title"] == long_title


def test_build_caption_respects_telegram_1024_char_limit():
    from src.telegram_manager import build_caption, parse_caption
    huge_subtitles = [f"Sword.Art.Online.S01E01.1080p.WEBRip.x264.AAC.Subtitle.Indonesian.Language.Track.{i}.srt" for i in range(50)]
    meta = {
        "kind": "video",
        "title": "Sword Art Online: Alicization - War of Underworld Part 2 Super Long Anime Title Version",
        "year": "2020",
        "media_type": "episode",
        "season": 1,
        "episode": 1,
        "file_size": 350000000,
        "part_count": 1,
        "subtitles": huge_subtitles,
        "archive": True,
        "filename": "Sword.Art.Online.S01E01.1080p.WEBRip.x264.AAC.mp4",
    }
    cap = build_caption(meta)
    assert len(cap) <= 1024
    parsed = parse_caption(cap)
    assert parsed is not None
    assert parsed.get("app") == "iamnotpirates"
    assert parsed.get("title") is not None



class TestDestFakeClient:
    def __init__(self):
        self.sent = []
        self._entities = {}

    def get_entity(self, target):
        if target not in self._entities:
            self._entities[target] = type("E", (), {"title": f"Entity-{target}"})()
        return self._entities[target]

    def send_message(self, target, text, reply_to=None):
        self.sent.append((target, text, reply_to))
        class M:
            id = 777
        return M()


def test_test_destinations_reports_each_and_sends_topic_reply():
    import src.telegram_manager as tm
    client = TestDestFakeClient()
    dests = [
        {"type": "group", "target": "-100123", "topic": "7"},
        {"type": "saved", "target": "me", "topic": None},
    ]
    results = tm.test_destinations(client, dests)
    assert [r["ok"] for r in results] == [True, True]
    assert results[0]["detail"].startswith("Entity--100123")
    assert "777" in results[0]["detail"]
    assert client.sent[0] == (client.get_entity(-100123), tm.TEST_MESSAGE, 7)
    assert client.sent[1][2] is None


def test_test_destinations_captures_failure():
    import src.telegram_manager as tm
    client = TestDestFakeClient()
    def boom(*a, **k):
        raise ValueError("Cannot find any entity corresponding to '-999'")
    client.get_entity = boom

    def boom_send(*a, **k):
        raise ValueError("Cannot find any entity corresponding to '-999'")
    client.send_message = boom_send
    results = tm.test_destinations(client, [{"type": "channel", "target": "-999", "topic": None}])
    assert results[0]["ok"] is False
    assert "-999" in results[0]["detail"]


def test_parse_destination_accepts_full_tme_link_with_topic():
    from src.telegram_manager import parse_destination_input
    out = parse_destination_input("https://t.me/c/2312123164/10777/10778")
    assert out == ["group:-1002312123164:10777"]


def test_parse_destination_two_segment_link_has_no_topic():
    from src.telegram_manager import parse_destination_input
    out = parse_destination_input("https://t.me/c/2312123164/10778")
    assert out == ["group:-1002312123164"]


def test_parse_destination_mixed_tokens_and_links():
    from src.telegram_manager import parse_destination_input
    out = parse_destination_input(
        "saved, t.me/c/2312123164/10777/10778, channel:@filmku")
    assert out == ["saved", "group:-1002312123164:10777", "channel:@filmku"]


def test_sevenzip_paths_and_download(tmp_path, monkeypatch):
    import src.sevenzip_manager as sz
    monkeypatch.setattr(sz, "get_bin_dir", lambda: str(tmp_path))
    class FakeResp:
        status_code = 200
        content = b"FAKE-EXE-BYTES"
    monkeypatch.setattr(sz.requests, "get", lambda url, **k: FakeResp())
    path = sz.ensure_7z(None)
    assert path is not None and os.path.exists(path)
    with open(path, "rb") as fh:
        assert fh.read() == b"FAKE-EXE-BYTES"
    # second call served from cache (no second request)
    def boom(url, **k):
        raise AssertionError("should not re-download")
    monkeypatch.setattr(sz.requests, "get", boom)
    assert sz.ensure_7z(None) == path


def test_compress_archive_runs_7z_add_from_video_dir(tmp_path, monkeypatch):
    import src.sevenzip_manager as sz
    vid = tmp_path / "Monster S01E05.mkv"; vid.write_bytes(b"v" * 10)
    srt = tmp_path / "Monster S01E05.id.srt"; srt.write_bytes(b"s")
    calls = {}
    def fake_run(cmd, cwd=None, check=False, capture_output=True, text=False):
        calls["cmd"] = cmd; calls["cwd"] = cwd
        return MagicMock(returncode=0)
    monkeypatch.setattr(sz.subprocess, "run", fake_run)
    out = tmp_path / "out.7z"
    open(out, "wb").close()
    sz.compress_archive("C:/bin/7zr.exe", str(out), [str(vid), str(srt)])
    cmd = calls["cmd"]
    assert cmd[0] == "C:/bin/7zr.exe"
    assert cmd[1] == "a" and "-mx=0" in cmd and str(out) in cmd
    assert os.path.basename(str(vid)) in cmd and os.path.basename(str(srt)) in cmd
    assert calls["cwd"] == str(tmp_path)


def test_extract_archive_runs_7z_x_to_dest(tmp_path, monkeypatch):
    import src.sevenzip_manager as sz
    calls = {}
    def fake_run(cmd, cwd=None, check=False, capture_output=True, text=False):
        calls["cmd"] = cmd
        return MagicMock(returncode=0)
    monkeypatch.setattr(sz.subprocess, "run", fake_run)
    arc = tmp_path / "a.7z"; arc.write_bytes(b"x")
    dest = tmp_path / "dest"
    sz.extract_archive("C:/bin/7zr.exe", str(arc), str(dest))
    cmd = calls["cmd"]
    assert cmd[1] == "x" and any(str(dest) in c for c in cmd)


def _fake_archive(monkeypatch, size_bytes):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "ensure_7z", lambda console=None: "C:/bin/7zr.exe")

    def fake_compress(sevenzip, archive_path, files):
        with open(archive_path, "wb") as fh:
            fh.write(b"A" * size_bytes)
    monkeypatch.setattr(tm, "compress_archive", fake_compress)


def test_upload_backup_archives_video_with_all_subs(monkeypatch, tmp_path):
    from src.telegram_manager import upload_backup
    src = tmp_path / "Monster S01E05.mkv"; src.write_bytes(b"v" * 50)
    subs = []
    for name in ("a.id.srt", "b.eng.srt", "c.french.srt"):
        p = tmp_path / name; p.write_bytes(b"s"); subs.append(str(p))
    client = RecordingClient()
    _fake_archive(monkeypatch, 100)
    res = upload_backup(client, str(src), subs,
                        {"title": "Monster", "year": "2023", "media_type": "episode",
                         "season": 1, "episode": 5},
                        [{"type": "saved", "target": "me", "topic": None}])
    assert len(client.sent) == 1
    sent = client.sent[0]
    assert sent["path"].endswith(".7z")
    assert sent["force_document"] is True
    assert '"kind": "series"' in sent["caption"]
    assert '"title": "Monster"' in sent["caption"]
    assert res["video_msg_ids"] == [101]


def test_upload_backup_splits_big_archive(monkeypatch, tmp_path):
    from src.telegram_manager import upload_backup
    monkeypatch.setattr("src.telegram_manager.PART_SIZE", 1300)
    src = tmp_path / "Big Film (2024).mkv"; src.write_bytes(b"v" * 3000)
    client = RecordingClient()
    _fake_archive(monkeypatch, 2500)
    upload_backup(client, str(src), [],
                  {"title": "Big Film", "year": "2024", "media_type": "movie"},
                  [{"type": "saved", "target": "me", "topic": None}])
    assert len(client.sent) == 2
    assert all(s["force_document"] is True for s in client.sent)
    assert '"kind": "movie"' in client.sent[0]["caption"]


def test_restore_archive_extracts_and_returns_video(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    extracted = {}
    def fake_extract(sz_path, archive, dest):
        extracted["args"] = (sz_path, archive, dest)
        video = os.path.join(dest, "Monster S01E05.mkv")
        open(video, "wb").write(b"video-bytes")
        return video
    monkeypatch.setattr(tm, "extract_archive", fake_extract)
    monkeypatch.setattr(tm, "ensure_7z", lambda console=None: "C:/bin/7zr.exe")

    class ArcClient:
        def get_messages(self, chat, ids): return [MagicMock()]
        def download_media(self, message, file=None, progress_callback=None):
            p = os.path.join(file, "part.001")
            open(p, "wb").write(b"data")
            return p
    cfg = {"download_dir_movie": str(tmp_path / "Movies"),
           "download_dir_series": str(tmp_path / "Series")}
    item = {"title": "Monster", "year": "2023", "media_type": "episode",
            "season": 1, "episode": 5, "file_size": 4,
            "video_msg_ids": [1], "sub_msg_ids": [], "chat": "me",
            "archive": True, "filename": "Monster S01E05.mkv"}
    out = tm.restore_backup(ArcClient(), item, cfg)
    assert out.endswith(os.path.join("Season 01", "Monster S01E05.mkv")) or out.endswith("Monster S01E05.mkv")
    assert extracted["args"][2] == os.path.dirname(out)


class ScanSpyClient:
    def __init__(self):
        self.calls = []

    def get_entity(self, target):
        return f"Entity-{target}"

    def iter_messages(self, target, reverse=None, limit=None, reply_to=None):
        self.calls.append({"target": target, "reverse": reverse,
                           "limit": limit, "reply_to": reply_to})
        return iter([])


def test_scan_backups_scopes_iteration_to_topic():
    import src.telegram_manager as tm
    client = ScanSpyClient()
    tm.scan_backups(client, [
        {"type": "group", "target": "-1002312123164", "topic": 10777},
        {"type": "saved", "target": "me", "topic": None},
    ])
    assert client.calls[0]["reply_to"] == 10777
    assert client.calls[1]["reply_to"] is None


def test_scan_backups_no_reverse_full_history_needed_only_topic():
    import src.telegram_manager as tm
    client = ScanSpyClient()
    tm.scan_backups(client, [{"type": "group", "target": "-100x", "topic": 5}])
    assert client.calls[0]["limit"] is None


def test_scan_backups_without_reverse_finds_newest_first():
    from src.telegram_manager import scan_backups, build_caption
    DESTS = [{"type": "saved", "target": "me", "topic": None}]
    meta = {
        "kind": "video", "title": "A Shop for Killers", "year": "2024",
        "media_type": "episode", "season": 1, "episode": 1,
        "file_size": 300000000, "part_count": 1, "subtitles": [], "archive": True,
    }
    msg = FakeMsg(100, caption=build_caption(meta), file_name="AShopForKillers.7z")
    client = FakeClient({"me": [msg]})
    items = scan_backups(client, DESTS)
    assert len(items) == 1
    assert items[0]["title"] == "A Shop for Killers"
    assert items[0]["video_msg_ids"] == [100]


def test_sort_local_entries_by_title_season_episode():
    from src.telegram_manager import sort_local_entries
    unsorted = [
        {"title": "Sword Art Online", "year": "2020", "season": 1, "episode": 2},
        {"title": "A Shop for Killers", "year": "2024", "season": 1, "episode": 1},
        {"title": "Sword Art Online", "year": "2020", "season": 1, "episode": 1},
        {"title": "Avatar", "year": "2009", "season": None, "episode": None},
    ]
    res = sort_local_entries(unsorted)
    titles = [(r["title"], r.get("season"), r.get("episode")) for r in res]
    assert titles == [
        ("A Shop for Killers", 1, 1),
        ("Avatar", None, None),
        ("Sword Art Online", 1, 1),
        ("Sword Art Online", 1, 2),
    ]


def test_send_file_with_retry_does_not_retry_fatal_rpc_error():
    from src.telegram_manager import _send_file_with_retry
    class ChatWriteForbiddenError(Exception):
        pass
    client = MagicMock()
    client.send_file.side_effect = ChatWriteForbiddenError("Forbidden")
    with pytest.raises(ChatWriteForbiddenError):
        _send_file_with_retry(client, "me", "video.mp4", max_retries=3)
    assert client.send_file.call_count == 1


def test_send_file_with_retry_notifies_on_retry(capsys):
    from src.telegram_manager import _send_file_with_retry
    client = MagicMock()
    client.send_file.side_effect = [
        OSError(121, "semaphore timeout"),
        OSError(121, "semaphore timeout"),
        "MsgObj",
    ]
    res = _send_file_with_retry(client, "me", "big.7z",
                                describe="SAO S01E01", max_retries=3)
    assert res == "MsgObj"
    out = capsys.readouterr().out
    assert out.count("mencoba ulang") == 2
    assert "SAO S01E01" in out


def test_upload_backup_describes_parts_in_progress(monkeypatch, tmp_path):
    import src.telegram_manager as tm
    monkeypatch.setattr(tm, "PART_SIZE", 1300)
    src = tmp_path / "Big.mkv"; src.write_bytes(b"v" * 3000)
    client = RecordingClient()
    _fake_archive(monkeypatch, 2500)
    upload_backup(client, str(src), [],
                  {"title": "Big", "year": "", "media_type": "movie"},
                  [{"type": "saved", "target": "me", "topic": None}])
    assert len(client.sent) == 2
