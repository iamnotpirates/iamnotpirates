from curl_cffi import requests
from bs4 import BeautifulSoup
import re

def search_chunks():
    page_url = "https://z2.idlixku.com/movie/colony-2026"
    res = requests.get(page_url, impersonate="chrome120")
    soup = BeautifulSoup(res.text, "html.parser")
    
    js_srcs = [script.get("src") for script in soup.find_all("script") if script.get("src")]
    print(f"Total JS script tags found: {len(js_srcs)}")
    
    for src in js_srcs:
        full_url = "https://z2.idlixku.com" + src if src.startswith("/") else src
        try:
            r = requests.get(full_url, impersonate="chrome120")
            if r.status_code == 200:
                text = r.text
                if any(k in text.lower() for k in ["iframe", "embed", "govid", "vidhide", "filemoon", "vidsrc", "player", "api/"]):
                    print(f"\n[FOUND MATCH IN JS CHUNK]: {full_url}")
                    # Find any API routes or external player URLs in this JS chunk
                    urls = re.findall(r'https?://[^\s"\'`<>]+', text)
                    api_routes = re.findall(r'/api/[a-zA-Z0-9_/-]+', text)
                    if urls:
                        print(" URLs in chunk:", set(urls[:10]))
                    if api_routes:
                        print(" API routes in chunk:", set(api_routes[:10]))
        except Exception as e:
            print("Error reading JS:", e)

if __name__ == "__main__":
    search_chunks()
