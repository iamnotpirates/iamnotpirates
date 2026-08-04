import time
from curl_cffi import requests

def fetch_series_details(page_url_or_slug: str) -> dict:
    """Fetches TV series metadata including seasons and episode lists from IDLIX API."""
    slug = page_url_or_slug.rstrip("/").split("/")[-1]
    session = requests.Session(impersonate="chrome120")
    headers = {
        "Origin": "https://z2.idlixku.com",
        "Referer": f"https://z2.idlixku.com/series/{slug}",
        "Accept": "application/json, text/plain, */*",
    }
    endpoint = f"https://z2.idlixku.com/api/series/{slug}"
    try:
        r = session.get(endpoint, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            title = data.get("title", slug.replace("-", " ").title())
            year = str(data.get("year", "N/A"))
            seasons_raw = data.get("seasons", [])
            seasons = []
            for s in seasons_raw:
                s_num = s.get("season", 1)
                eps = []
                for ep in s.get("episodes", []):
                    eps.append({
                        "season_num": s_num,
                        "episode_num": ep.get("episode", 1),
                        "title": ep.get("title", f"Episode {ep.get('episode', 1)}"),
                        "media_id": ep.get("id", ""),
                        "slug": ep.get("slug", "")
                    })
                seasons.append({
                    "season_num": s_num,
                    "episodes": eps
                })
            return {"title": title, "year": year, "seasons": seasons}
    except Exception as e:
        print(f"[Series Extractor Error]: {e}")
    return {"title": slug.replace("-", " ").title(), "year": "N/A", "seasons": []}

def extract_episode_sources(episode_media_id: str | int, page_url: str) -> dict:
    """Extracts m3u8 playlist URL and subtitles for a specific TV episode via IDLIX Next.js API."""
    session = requests.Session(impersonate="chrome120")
    headers = {
        "Origin": "https://z2.idlixku.com",
        "Referer": page_url,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }
    try:
        play_info_url = f"https://z2.idlixku.com/api/watch/play-info/series/{episode_media_id}"
        r_info = session.get(play_info_url, headers=headers)
        if r_info.status_code != 200:
            return {"m3u8_urls": [], "subtitles": []}

        info_data = r_info.json()
        gate_token = info_data.get("gateToken")
        if not gate_token:
            return {"m3u8_urls": [], "subtitles": []}

        unlock_at = info_data.get("unlockAt", 0) / 1000.0
        server_now = info_data.get("serverNow", 0) / 1000.0
        wait_sec = max(0, unlock_at - server_now) + 0.5
        if wait_sec > 0:
            time.sleep(wait_sec)

        r_claim = session.post("https://z2.idlixku.com/api/watch/session/claim", json={"gateToken": gate_token}, headers=headers)
        if r_claim.status_code != 200:
            return {"m3u8_urls": [], "subtitles": []}

        claim_data = r_claim.json()
        claim_token = claim_data.get("claim")
        redeem_url = claim_data.get("redeemUrl")
        if not claim_token or not redeem_url:
            return {"m3u8_urls": [], "subtitles": []}

        r_redeem = session.post(redeem_url, json={"claim": claim_token}, headers=headers)
        if r_redeem.status_code != 200:
            return {"m3u8_urls": [], "subtitles": []}

        final_data = r_redeem.json()
        m3u8_master = final_data.get("url")
        sub_list = final_data.get("subtitles", [])
        subtitles = [{"lang": s.get("label", s.get("lang", "Subtitle")), "url": s.get("path", "")} for s in sub_list]
        return {"m3u8_urls": [m3u8_master] if m3u8_master else [], "subtitles": subtitles}
    except Exception as e:
        print(f"[Episode Extractor Warning]: {e}")
    return {"m3u8_urls": [], "subtitles": []}
