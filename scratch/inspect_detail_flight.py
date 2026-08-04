from curl_cffi import requests
import re
import json

def find_player_links():
    url = "https://z2.idlixku.com/movie/colony-2026"
    res = requests.get(url, impersonate="chrome120")
    print(f"Status Code: {res.status_code}, Length: {len(res.text)}")
    
    # 1. Search iframe / embed links via regex
    embed_urls = re.findall(r'https?://[^\s"\'<>]+(?:embed|player|govid|vidhide|filemoon|dood|stream)[^\s"\'<>]*', res.text, re.IGNORECASE)
    print("Embedded player URLs found:", set(embed_urls))
    
    # 2. Search m3u8 playlist URLs
    m3u8_urls = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', res.text, re.IGNORECASE)
    print("Direct m3u8 URLs found:", set(m3u8_urls))
    
    # 3. Search Next.js flight data strings
    matches = re.findall(r'self\.__next_f\.push\((.*?)\)', res.text)
    print(f"Total Flight payload chunks: {len(matches)}")
    for idx, fm in enumerate(matches, 1):
        if any(k in fm.lower() for k in ["iframe", "player", "govid", "vidhide", "filemoon", "embed", "m3u8", "src"]):
            print(f"\n--- FLIGHT MATCH #{idx} (length {len(fm)}) ---")
            # Find any URLs inside this flight chunk
            urls = re.findall(r'https?:\\?/\\?/[^"\']+', fm)
            print("URLs in flight chunk:", set(urls))

if __name__ == "__main__":
    find_player_links()
