from curl_cffi import requests
from bs4 import BeautifulSoup
import re

def decompile():
    res = requests.get("https://z2.idlixku.com/movie/colony-2026", impersonate="chrome120")
    soup = BeautifulSoup(res.text, "html.parser")
    
    js_srcs = [script.get("src") for script in soup.find_all("script") if script.get("src")]
    
    for src in js_srcs:
        url = "https://z2.idlixku.com" + src if src.startswith("/") else src
        r = requests.get(url, impersonate="chrome120")
        if r.status_code == 200:
            content = r.content.decode("utf-8", errors="ignore")
            # Search for api routes, iframe src templates, player endpoints, video servers
            matches = re.findall(r'/(?:api|embed|player|watch|v|stream)/[a-zA-Z0-9_/?=.-]+', content)
            if matches:
                filtered = [m for m in matches if not m.startswith("/_next") and not m.startswith("/api/admin")]
                if filtered:
                    print(f"\n[Matches in {url.split('/')[-1]}]:")
                    print(set(filtered))

if __name__ == "__main__":
    decompile()
