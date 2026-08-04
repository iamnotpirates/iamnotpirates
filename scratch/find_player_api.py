from playwright.sync_api import sync_playwright
import os, time

def find_all_player_network():
    user_ms_pw = os.path.expanduser("~\\AppData\\Local\\ms-playwright")
    if os.path.exists(user_ms_pw):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_ms_pw
        
    url = "https://z2.idlixku.com/movie/colony-2026"
    all_res = []
    
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="id-ID"
        )
        page = context.new_page()
        
        def on_response(response):
            try:
                r_url = response.url
                if response.status == 200 and not any(ext in r_url for ext in [".jpg", ".png", ".css", ".js", ".woff2", ".ico"]):
                    print(f"[RES 200]: {response.request.method} {r_url}")
                    all_res.append(r_url)
            except Exception:
                pass
                
        page.on("response", on_response)
        print("Navigating to", url)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        
        # Click Play / Watch button if present
        print("Searching for play button...")
        play_btn = page.query_selector('a[href*="play"], button:has-text("Watch"), button:has-text("Play"), .play-btn, svg')
        if play_btn:
            print("Found play button, clicking...")
            play_btn.click()
            page.wait_for_timeout(5000)
            
        browser.close()

if __name__ == "__main__":
    find_all_player_network()
