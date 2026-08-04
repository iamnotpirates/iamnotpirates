import json
from bs4 import BeautifulSoup
from curl_cffi import requests


def parse_featured_html(html: str, base_url: str = "") -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen_urls = set()

    # Strategy 1: JSON-LD Schema ItemList (Featured Movies & TV Series)
    ld_scripts = soup.find_all("script", type="application/ld+json")
    for s in ld_scripts:
        if not s.string:
            continue
        try:
            data = json.loads(s.string)
            if isinstance(data, list):
                for obj in data:
                    if obj.get("@type") == "ItemList" and "Featured" in obj.get("name", ""):
                        for elem in obj.get("itemListElement", []):
                            url = elem.get("url", "")
                            title = elem.get("name", "")
                            if not url or url in seen_urls:
                                continue
                            full_url = url
                            if base_url and url.startswith("/"):
                                full_url = base_url.rstrip("/") + url
                            is_tv = "/series/" in url or "/tvshows/" in url
                            seen_urls.add(url)
                            items.append({
                                "title": title,
                                "url": full_url,
                                "rating": "N/A",
                                "type": "TV Series" if is_tv else "Movie",
                                "quality": "WEB-DL",
                                "poster": ""
                            })
        except Exception:
            pass

    # Strategy 2: Hero Carousel / Featured Content section in Next.js layout
    if not items:
        hero_sections = soup.select(
            'section[aria-label="Featured content"], section[aria-label="Konten Pilihan"], section.hero-height, .hero-content-overlay'
        )
        for hero in hero_sections:
            link_tag = hero.select_one("a[href*='/movie/'], a[href*='/series/'], a[href*='/tvshows/'], a[href]")
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            if not href or href in seen_urls:
                continue

            img_tag = hero.select_one("img[alt]")
            title = img_tag.get("alt", "") if img_tag else link_tag.get_text(strip=True)
            if not title:
                title = href.strip("/").split("/")[-1].replace("-", " ").title()

            type_span = hero.select_one("span")
            type_text = type_span.get_text(strip=True).upper() if type_span else ""
            if "SERIES" in type_text or "TV" in type_text or "/series/" in href:
                content_type = "TV Series"
            else:
                content_type = "Movie"

            rating = "N/A"
            for span in hero.select("span"):
                txt = span.get_text(strip=True)
                if txt and (txt.replace(".", "", 1).isdigit() or "★" in txt):
                    rating = txt
                    break

            poster = img_tag.get("src", "") if img_tag else ""

            full_url = href
            if base_url and href.startswith("/"):
                full_url = base_url.rstrip("/") + href

            seen_urls.add(href)
            items.append(
                {
                    "title": title,
                    "url": full_url,
                    "rating": rating,
                    "type": content_type,
                    "poster": poster,
                }
            )

    # Strategy 3: Try finding featured section or general item cards in DooPlay/WordPress theme
    if not items:
        containers = soup.select(
            "#featured-titles article.item, div.items article.item, #archive-content article.item, article.item"
        )
        for article in containers:
            title_tag = article.select_one("h3 a, .data h3 a, .title a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")

            rating_tag = article.select_one(".rating, .imdb")
            rating = rating_tag.get_text(strip=True) if rating_tag else "N/A"

            img_tag = article.select_one("img")
            poster = img_tag.get("src", "") if img_tag else ""

            article_classes = article.get("class", [])
            is_tv = "tvshows" in link or "tvshows" in article_classes or "tv" in article_classes or "series" in link
            content_type = "TV Series" if is_tv else "Movie"

            if link and link not in seen_urls:
                seen_urls.add(link)
                items.append(
                    {
                        "title": title,
                        "url": link,
                        "rating": rating,
                        "type": content_type,
                        "poster": poster,
                    }
                )

    # Strategy 4: Next.js / Dynamic catalog fallback
    if not items:
        movie_series_links = soup.find_all(
            "a", href=lambda h: h and ("/movie/" in h or "/series/" in h or "/tvshows/" in h)
        )
        for a_tag in movie_series_links:
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            if not title or href in seen_urls:
                continue

            full_url = href
            if base_url and href.startswith("/"):
                full_url = base_url.rstrip("/") + href

            is_tv = "/series/" in href or "/tvshows/" in href
            content_type = "TV Series" if is_tv else "Movie"

            seen_urls.add(href)
            items.append(
                {
                    "title": title,
                    "url": full_url,
                    "rating": "N/A",
                    "type": content_type,
                    "poster": "",
                }
            )

    return items


def fetch_featured_with_playwright(target_url: str) -> list[dict]:
    """Uses Playwright Chromium to render dynamic client-side Hero Carousel and click all slides."""
    import os

    # Ensure Playwright finds system/user installed Chromium when running inside PyInstaller executable
    user_ms_pw = os.path.expanduser("~\\AppData\\Local\\ms-playwright")
    if os.path.exists(user_ms_pw):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_ms_pw
    else:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

    items = []
    seen_urls = set()
    base_url = target_url.rstrip("/")
    try:
        from playwright.sync_api import sync_playwright

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
                locale="id-ID",
            )
            page = context.new_page()
            page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3500)

            buttons = page.query_selector_all(
                'button[aria-label*="slide"], button[aria-label*="Slide"]'
            )
            buttons_count = len(buttons)

            for idx in range(max(1, buttons_count)):
                try:
                    if buttons_count > 0:
                        cur_btns = page.query_selector_all(
                            'button[aria-label*="slide"], button[aria-label*="Slide"]'
                        )
                        if idx < len(cur_btns):
                            cur_btns[idx].click()
                            page.wait_for_timeout(400)

                    soup = BeautifulSoup(page.content(), "html.parser")
                    hero = soup.select_one(
                        'section.hero-height, section[aria-label*="Featured"], section[aria-label*="Pilihan"], .hero-content-overlay'
                    )

                    if hero:
                        img = hero.select_one("img[alt]")
                        title = img.get("alt") if img else ""

                        link = hero.select_one(
                            "a[href*='/movie/'], a[href*='/series/'], a[href*='/tvshows/']"
                        )
                        href = link.get("href") if link else ""

                        type_tag = hero.select_one("span")
                        ctype = type_tag.get_text(strip=True) if type_tag else ""

                        rating = "N/A"
                        for span in hero.select("span"):
                            txt = span.get_text(strip=True)
                            if txt and (txt.replace(".", "", 1).isdigit() or "★" in txt):
                                rating = txt
                                break

                        quality = "WEB-DL"
                        for span in hero.select("span"):
                            txt = span.get_text(strip=True).upper()
                            if any(q in txt for q in ["WEB-DL", "BLURAY", "HDTV", "HD", "CAM", "4K", "1080P", "720P"]):
                                quality = span.get_text(strip=True)
                                break

                        if href and href not in seen_urls:
                            seen_urls.add(href)
                            full_url = (
                                base_url + href if href.startswith("/") else href
                            )
                            is_tv = (
                                "SERIES" in ctype.upper()
                                or "TV" in ctype.upper()
                                or "/series/" in href
                            )
                            items.append(
                                {
                                    "title": (
                                        title
                                        if title
                                        else href.strip("/")
                                        .split("/")[-1]
                                        .replace("-", " ")
                                        .title()
                                    ),
                                    "url": full_url,
                                    "rating": rating,
                                    "type": "TV Series" if is_tv else "Movie",
                                    "quality": quality,
                                    "poster": "",
                                }
                            )
                except Exception:
                    pass

            browser.close()
    except Exception as e:
        print(f"[Playwright Engine Warning]: {e}")

    return items


def fetch_featured_content(target_url: str) -> list[dict]:
    # 1. Primary Engine: Playwright dynamic rendering for exact 10 Hero Featured Carousel items
    pw_items = fetch_featured_with_playwright(target_url)
    if pw_items:
        return pw_items

    # 2. Fallback Engine: Fast HTTP request via curl_cffi
    try:
        response = requests.get(
            target_url,
            impersonate="chrome120",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            },
            timeout=15,
        )
        if response.status_code == 200:
            return parse_featured_html(response.text, base_url=target_url)
        else:
            raise Exception(f"HTTP Status {response.status_code}")
    except Exception as e:
        raise Exception(f"Failed to fetch {target_url}: {str(e)}")
