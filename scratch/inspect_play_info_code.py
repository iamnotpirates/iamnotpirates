from curl_cffi import requests
import re

def inspect_code():
    url = "https://z2.idlixku.com/_next/static/chunks/3cdyt0j5i8qdj.js?dpl=20260802113945-abf3801f7174"
    r = requests.get(url, impersonate="chrome120")
    if r.status_code == 200:
        text = r.text
        idx = text.find("/watch/play-info")
        if idx != -1:
            print("--- SURROUNDING CODE FOR /watch/play-info ---")
            print(text[max(0, idx-300):min(len(text), idx+300)])

if __name__ == "__main__":
    inspect_code()
