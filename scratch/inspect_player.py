from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os, time

def inspect_media_player():
    user_ms_pw = os.path.expanduser("~\\AppData\\Local\\ms-playwright")
    if os.path.exists(user_ms_pw):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_ms_pw
        
    url = "https://z2.idlixku.com/movie/colony-2026"
    captured_requests = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        def handle_res(res):
            req_url = res.url
            if ".m3u8" in req_url or "playlist" in req_url or "master" in req_url or "stream" in req_url:
                print(f"[Captured Network Stream]: {req_url}")
                captured_requests.append(req_url)
                
        page.on("response", handle_res)
        print(f"Navigating to {url}...")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        
        # Take screenshot of detail page
        page.screenshot(path="scratch/media_detail_page.png")
        print("Saved detail page screenshot to scratch/media_detail_page.png")
        
        # Check all iframes
        soup = BeautifulSoup(page.content(), "html.parser")
        iframes = soup.find_all("iframe")
        print(f"Total iframes on page: {len(iframes)}")
        for idx, iframe in enumerate(iframes, 1):
            print(f" iFrame #{idx}: src={iframe.get('src')} | id={iframe.get('id')}")
            
        # Check play buttons or server options
        player_buttons = page.query_selector_all('button, div[class*="play"], iframe, .player')
        print(f"Player / Play elements count: {len(player_buttons)}")
        
        # Click any play button or iframe overlay if present
        play_btn = page.query_selector('.play-btn, button[aria-label*="Play"], .hero-content-overlay button, div.relative iframe')
        if play_btn:
            try:
                print("Clicking play button / player element...")
                play_btn.click()
                page.wait_for_timeout(4000)
            except Exception as e:
                print("Click error:", e)
                
        print(f"\nTotal stream requests captured: {len(captured_requests)}")
        browser.close()

if __name__ == "__main__":
    inspect_media_player()
