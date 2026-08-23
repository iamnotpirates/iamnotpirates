from src.telegram_manager import build_caption, parse_caption


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
