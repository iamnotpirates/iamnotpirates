from curl_cffi import requests
import re

def inspect_watch_api():
    url = "https://z2.idlixku.com/_next/static/chunks/3cdyt0j5i8qdj.js?dpl=20260802113945-abf3801f7174"
    r = requests.get(url, impersonate="chrome120")
    if r.status_code == 200:
        text = r.text
        idx = text.find('"watchApi"')
        if idx != -1:
            print("--- WATCH API DEFINITION ---")
            print(text[idx:idx+1500])

if __name__ == "__main__":
    inspect_watch_api()
