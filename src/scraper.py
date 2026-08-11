import json
import time
from bs4 import BeautifulSoup
from curl_cffi import requests


def parse_featured_html(html: str, base_url: str = "") -> list[dict]:
    """Parses Featured Content items strictly from Hero Carousel or Featured Item Cards.
    
    Returns an empty list if no valid featured cards are found (no dummy catalog fallbacks).
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen_urls = set()

    # Strategy 1: Hero Carousel / Featured Content section in Next.js layout (Rich metadata & real ratings)
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

    # Strategy 2: DooPlay/WordPress theme item cards
    if not items:
        containers = soup.select(
            "#featured-titles article.item, div.items article.item, #archive-content article.item, article.item"
        )
        for article in containers:
            title_tag = article.select_one("h3 a, .data h3 a, .title a, a[href]")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")

            rating_tag = article.select_one(".rating, .imdb, .vote")
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

    return items


def fetch_featured_with_playwright(target_url: str) -> list[dict]:
    """Uses Playwright Chromium to render dynamic client-side Hero Carousel and click all slides."""
    import os
    from src.playwright_manager import ensure_playwright, get_playwright_browsers_path

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = get_playwright_browsers_path()
    ensure_playwright()

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


def fetch_featured_content(target_url: str, max_retries: int = 3) -> list[dict]:
    """Fetches Featured Content items with max 3 retries.
    
    Raises an explicit Exception if no real Featured Content items are obtained after max_retries attempts.
    """
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            # 1. Primary Engine: Playwright dynamic rendering for exact 10 Hero Featured Carousel items
            pw_items = fetch_featured_with_playwright(target_url)
            if pw_items:
                return pw_items

            # 2. Fast HTTP request via curl_cffi
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
                parsed_items = parse_featured_html(response.text, base_url=target_url)
                if parsed_items:
                    return parsed_items
            else:
                last_err = f"HTTP Status {response.status_code}"
        except Exception as e:
            last_err = str(e)

        if attempt < max_retries:
            time.sleep(1)

    raise Exception(
        f"Gagal mengambil Featured Content setelah {max_retries}x percobaan "
        f"({last_err or 'Konten populer tidak ditemukan'}). Silakan periksa koneksi internet atau Active Target URL Anda."
    )


def search_content(target_url: str, query: str) -> list[dict]:
    """Searches media content via IDLIX JSON API endpoint."""
    q_clean = query.strip()
    if not q_clean:
        return []

    base_url = target_url.rstrip("/")
    api_url = f"{base_url}/api/search?q={requests.utils.quote(q_clean)}"

    try:
        res = requests.get(
            api_url,
            impersonate="chrome120",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
            timeout=15
        )
        if res.status_code != 200:
            return []

        data = res.json()
        results = data.get("results", [])
        if not isinstance(results, list):
            return []

        items = []
        for item in results:
            title = item.get("title") or item.get("name") or "Unknown"
            slug = item.get("slug", "")
            content_type = item.get("contentType", "")

            is_tv = content_type in ("tv_series", "series", "tvshows") or "/series/" in slug or "/tvshows/" in slug
            type_str = "TV Series" if is_tv else "Movie"

            if is_tv:
                url = f"{base_url}/series/{slug}" if slug else base_url
            else:
                url = f"{base_url}/movie/{slug}" if slug else base_url

            rel_date = str(item.get("releaseDate", "") or item.get("firstAirDate", ""))
            year = rel_date[:4] if rel_date and len(rel_date) >= 4 and rel_date[:4].isdigit() else "N/A"

            rating = item.get("voteAverage")
            rating_str = str(round(float(rating), 1)) if rating is not None else "N/A"

            items.append({
                "title": title,
                "url": url,
                "rating": rating_str,
                "type": type_str,
                "year": year,
                "quality": "WEB-DL",
                "poster": item.get("posterPath", "")
            })

        return items
    except Exception:
        return []

