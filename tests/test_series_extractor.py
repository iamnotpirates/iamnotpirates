import pytest
from unittest.mock import patch, MagicMock
from src.series_extractor import fetch_series_details, extract_episode_sources

def test_fetch_series_details_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "title": "Breaking Bad",
        "year": "2008",
        "seasons": [
            {
                "season": 1,
                "episodes": [
                    {"episode": 1, "title": "Pilot", "id": 101, "slug": "pilot"},
                    {"episode": 2, "title": "Cat's in the Bag...", "id": 102, "slug": "cats-in-the-bag"}
                ]
            }
        ]
    }
    with patch("src.series_extractor.requests.Session.get", return_value=mock_resp):
        res = fetch_series_details("https://z2.idlixku.com/series/breaking-bad")
        assert res["title"] == "Breaking Bad"
        assert res["year"] == "2008"
        assert len(res["seasons"]) == 1
        assert res["seasons"][0]["season_num"] == 1
        assert len(res["seasons"][0]["episodes"]) == 2
        assert res["seasons"][0]["episodes"][0]["title"] == "Pilot"
        assert res["seasons"][0]["episodes"][0]["episode_num"] == 1
        assert res["seasons"][0]["episodes"][0]["media_id"] == 101

def test_fetch_series_details_slug_only():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "title": "Stranger Things",
        "year": 2016,
        "seasons": []
    }
    with patch("src.series_extractor.requests.Session.get", return_value=mock_resp):
        res = fetch_series_details("stranger-things")
        assert res["title"] == "Stranger Things"
        assert res["year"] == "2016"
        assert res["seasons"] == []

def test_fetch_series_details_http_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("src.series_extractor.requests.Session.get", return_value=mock_resp):
        res = fetch_series_details("non-existent-show")
        assert res["title"] == "Non Existent Show"
        assert res["year"] == "N/A"
        assert res["seasons"] == []

def test_extract_episode_sources_success():
    mock_info_resp = MagicMock()
    mock_info_resp.status_code = 200
    mock_info_resp.json.return_value = {
        "gateToken": "gate_123",
        "unlockAt": 0,
        "serverNow": 0
    }

    mock_claim_resp = MagicMock()
    mock_claim_resp.status_code = 200
    mock_claim_resp.json.return_value = {
        "claim": "claim_456",
        "redeemUrl": "https://z2.idlixku.com/api/watch/session/redeem"
    }

    mock_redeem_resp = MagicMock()
    mock_redeem_resp.status_code = 200
    mock_redeem_resp.json.return_value = {
        "url": "https://example.com/master.m3u8",
        "subtitles": [
            {"label": "Indonesian", "path": "https://example.com/id.vtt"},
            {"lang": "English", "path": "https://example.com/en.vtt"}
        ]
    }

    def mock_get(url, **kwargs):
        if "play-info" in url:
            return mock_info_resp
        return MagicMock(status_code=404)

    def mock_post(url, **kwargs):
        if "claim" in url:
            return mock_claim_resp
        if "redeem" in url:
            return mock_redeem_resp
        return MagicMock(status_code=404)

    with patch("src.series_extractor.requests.Session.get", side_effect=mock_get), \
         patch("src.series_extractor.requests.Session.post", side_effect=mock_post), \
         patch("src.series_extractor.time.sleep", return_value=None):
        res = extract_episode_sources(101, "https://z2.idlixku.com/series/breaking-bad")
        assert res["m3u8_urls"] == ["https://example.com/master.m3u8"]
        assert len(res["subtitles"]) == 2
        assert res["subtitles"][0] == {"lang": "Indonesian", "url": "https://example.com/id.vtt"}
        assert res["subtitles"][1] == {"lang": "English", "url": "https://example.com/en.vtt"}

def test_extract_episode_sources_failure():
    mock_info_resp = MagicMock()
    mock_info_resp.status_code = 403

    with patch("src.series_extractor.requests.Session.get", return_value=mock_info_resp):
        res = extract_episode_sources(101, "https://z2.idlixku.com/series/breaking-bad")
        assert res["m3u8_urls"] == []
        assert res["subtitles"] == []
