from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os, re

def inspect_page():
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
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        
        soup = BeautifulSoup(page.content(), "html.parser")
        
        print("=== ALL BUTTONS ON DETAIL PAGE ===")
        for btn in soup.find_all("button"):
            print(f"Button: text='{btn.get_text(strip=True)}' | class='{btn.get('class')}' | aria-label='{btn.get('aria-label')}'")
            
        print("\n=== ALL IFRAMES / EMBEDS / STREAMS ON PAGE ===")
        for tag in soup.find_all(["iframe", "embed", "video", "source"]):
            print(f"Tag <{tag.name}>: src='{tag.get('src')}' | id='{tag.get('id')}'")
            
        print("\n=== SEARCHING FOR PLAYER LINKS / IFRAMES / EMBED ENDPOINTS ===")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if any(k in href.lower() for k in ["play", "watch", "embed", "player", "govid", "vidhide", "stream"]):
                print(f"A Link: text='{a.get_text(strip=True)}' | href='{href}'")
                
        # Search all script content for player URLs
        scripts = soup.find_all("script")
        for s in scripts:
            if s.string and any(k in s.string.lower() for k in ["govid", "vidhide", "filemoon", "embed", ".m3u8"]):
                print("\nFOUND PLAYER SCRIPT MATCH:")
                print(s.string[:500])
                
        browser.close()

if __name__ == "__main__":
    inspect_page()
