from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os, time

def inspect_detail():
    user_ms_pw = os.path.expanduser("~\\AppData\\Local\\ms-playwright")
    if os.path.exists(user_ms_pw):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_ms_pw
        
    url = "https://z2.idlixku.com/movie/colony-2026"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        print("Navigating to", url)
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(6000)
        
        soup = BeautifulSoup(page.content(), "html.parser")
        print("Page Title:", page.title())
        
        # Check all clickable elements or player wrappers
        player_wrappers = soup.select(".aspect-video, [class*='player'], [class*='video'], [class*='embed']")
        print(f"Player wrappers found: {len(player_wrappers)}")
        for idx, pw in enumerate(player_wrappers, 1):
            print(f" Wrapper #{idx}: {pw}")
            
        # Search for iframe in page.frames
        print(f"Total Frames in page.frames: {len(page.frames)}")
        for idx, frame in enumerate(page.frames, 1):
            print(f" Frame #{idx}: name='{frame.name}' | url='{frame.url}'")
            
        browser.close()

if __name__ == "__main__":
    inspect_detail()
