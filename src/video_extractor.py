import os
import time
from bs4 import BeautifulSoup
from curl_cffi import requests
from playwright.sync_api import sync_playwright

def extract_video_sources_via_api(page_url: str) -> dict | None:
    """Extracts master m3u8 playlist URL and subtitle tracks via IDLIX Next.js API endpoints."""
    try:
        parts = page_url.rstrip("/").split("/")
        content_type = parts[-2] if len(parts) >= 2 else "movie"
        slug = parts[-1]

        session = requests.Session(impersonate="chrome120")
        headers = {
            "Origin": "https://z2.idlixku.com",
            "Referer": page_url,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json"
        }

        # 1. Fetch metadata
        meta_endpoint = f"https://z2.idlixku.com/api/{'movies' if content_type == 'movie' else 'series'}/{slug}"
        r_meta = session.get(meta_endpoint)
        if r_meta.status_code != 200:
            return None

        meta_data = r_meta.json()
        media_id = meta_data.get("id")
        if not media_id:
            return None

        # 2. Fetch play-info gate token
        play_info_url = f"https://z2.idlixku.com/api/watch/play-info/{content_type}/{media_id}"
        r_info = session.get(play_info_url, headers=headers)
        if r_info.status_code != 200:
            return None

        info_data = r_info.json()
        gate_token = info_data.get("gateToken")
        if not gate_token:
            return None

        unlock_at = info_data.get("unlockAt", 0) / 1000.0
        server_now = info_data.get("serverNow", 0) / 1000.0
        wait_sec = max(0, unlock_at - server_now) + 0.5

        if wait_sec > 0:
            time.sleep(wait_sec)

        # 3. Claim session
        r_claim = session.post("https://z2.idlixku.com/api/watch/session/claim", json={"gateToken": gate_token}, headers=headers)
        if r_claim.status_code != 200:
            return None

        claim_data = r_claim.json()
        claim_token = claim_data.get("claim")
        redeem_url = claim_data.get("redeemUrl")
        if not claim_token or not redeem_url:
            return None

        # 4. Redeem master playlist URL and subtitles
        r_redeem = session.post(redeem_url, json={"claim": claim_token}, headers=headers)
        if r_redeem.status_code != 200:
            return None

        final_data = r_redeem.json()
        m3u8_master = final_data.get("url")
        sub_list = final_data.get("subtitles", [])

        subtitles = []
        for s in sub_list:
            subtitles.append({
                "lang": s.get("label", s.get("lang", "Subtitle")),
                "url": s.get("path", "")
            })

        if m3u8_master:
            return {"m3u8_urls": [m3u8_master], "subtitles": subtitles}
    except Exception as e:
        print(f"[API Extractor Warning]: {e}")

    return None

def extract_video_sources(page_url: str) -> dict:
    """Extracts m3u8 playlists and subtitle tracks using API endpoint flow with Playwright fallback."""
    # Attempt API extraction first (fast & immune to Cloudflare Turnstile detail page blocks)
    api_res = extract_video_sources_via_api(page_url)
    if api_res and api_res.get("m3u8_urls"):
        return api_res

    # Playwright fallback
    user_ms_pw = os.path.expanduser("~\\AppData\\Local\\ms-playwright")
    if os.path.exists(user_ms_pw):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_ms_pw

    m3u8_urls = []
    subtitles = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            def handle_response(response):
                url = response.url
                if ".m3u8" in url and url not in m3u8_urls:
                    m3u8_urls.append(url)
                if any(ext in url for ext in [".vtt", ".srt", ".ass"]) and url not in [s["url"] for s in subtitles]:
                    lang = "Indonesian" if "id" in url.lower() or "ind" in url.lower() else "English"
                    subtitles.append({"lang": lang, "url": url})

            page.on("response", handle_response)
            page.goto(page_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(4000)

            if not m3u8_urls:
                soup = BeautifulSoup(page.content(), "html.parser")
                for iframe in soup.find_all("iframe"):
                    src = iframe.get("src", "")
                    if src and ("govid" in src or "vidhide" in src or "filemoon" in src or "player" in src):
                        try:
                            sub_page = context.new_page()
                            sub_page.on("response", handle_response)
                            sub_page.goto(src, wait_until="domcontentloaded", timeout=15000)
                            sub_page.wait_for_timeout(3000)
                            sub_page.close()
                        except Exception:
                            pass

            browser.close()
    except Exception as e:
        print(f"[Video Extractor Warning]: {e}")

    return {"m3u8_urls": m3u8_urls, "subtitles": subtitles}
