# IDLIX CLI Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Python CLI tool using `uv`, `curl_cffi`, `rich`, and `questionary` for target URL management (CRUD) and scraping featured movies/TV shows from WordPress/DooPlay streaming sites like IDLIX.

**Architecture:** A modular Python CLI architecture where `config_manager.py` handles persistent JSON storage, `scraper.py` uses `curl_cffi` for TLS fingerprint Cloudflare bypass and `BeautifulSoup4` for extraction, `ui.py` handles `rich` rendering, and `main.py` runs a perpetual interactive menu loop.

**Tech Stack:** Python 3.10+, `uv`, `curl_cffi`, `beautifulsoup4`, `rich`, `questionary`, `pytest`.

## Global Constraints
- Target URL default: `https://z2.idlixku.com/`
- Data config path: `config.json`
- CLI loop MUST be perpetual (does not exit on menu action; exits only on explicit `Exit` choice)
- Cloudflare bypass using `curl_cffi` (Chrome impersonation)

---

### Task 1: Environment & Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Test: `tests/test_env.py`

**Interfaces:**
- Produces: `uv` package environment with dependencies `curl-cffi`, `beautifulsoup4`, `rich`, `questionary`, `pytest`.

- [ ] **Step 1: Write test for environment setup**

Create `tests/test_env.py`:
```python
def test_imports():
    import curl_cffi
    import bs4
    import rich
    import questionary
    assert True
```

- [ ] **Step 2: Create `pyproject.toml`**

Create `pyproject.toml`:
```toml
[project]
name = "idlix-cli-scraper"
version = "0.1.0"
description = "Interactive CLI scraper for IDLIX streaming sites"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "curl-cffi>=0.7.0",
    "beautifulsoup4>=4.12.0",
    "rich>=13.7.0",
    "questionary>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]
```

- [ ] **Step 3: Run `uv sync` and run pytest**

Run: `uv run pytest tests/test_env.py`
Expected: PASS

---

### Task 2: Config Manager (Target URLs CRUD)

**Files:**
- Create: `src/config_manager.py`
- Test: `tests/test_config_manager.py`

**Interfaces:**
- Produces:
  - `load_config(config_path: str = "config.json") -> dict`
  - `save_config(config: dict, config_path: str = "config.json") -> None`
  - `add_target_url(url: str, name: str = "", config_path: str = "config.json") -> dict`
  - `set_active_url(url: str, config_path: str = "config.json") -> dict`
  - `delete_target_url(url: str, config_path: str = "config.json") -> dict`

- [ ] **Step 1: Write test for ConfigManager**

Create `tests/test_config_manager.py`:
```python
import os
import pytest
from src.config_manager import load_config, save_config, add_target_url, set_active_url, delete_target_url

TEST_CONFIG = "test_config.json"

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)
    yield
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)

def test_load_default_config():
    config = load_config(TEST_CONFIG)
    assert config["active_url"] == "https://z2.idlixku.com/"
    assert len(config["target_urls"]) == 1

def test_add_and_set_active_url():
    load_config(TEST_CONFIG)
    add_target_url("https://idlix.example.com", name="Backup", config_path=TEST_CONFIG)
    config = set_active_url("https://idlix.example.com", config_path=TEST_CONFIG)
    assert config["active_url"] == "https://idlix.example.com"
    assert len(config["target_urls"]) == 2

def test_delete_url():
    load_config(TEST_CONFIG)
    add_target_url("https://to-delete.com", config_path=TEST_CONFIG)
    config = delete_target_url("https://to-delete.com", config_path=TEST_CONFIG)
    assert len(config["target_urls"]) == 1
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_config_manager.py`
Expected: FAIL (module `src.config_manager` not found)

- [ ] **Step 3: Implement `src/config_manager.py`**

Create `src/config_manager.py`:
```python
import json
import os

DEFAULT_CONFIG = {
    "active_url": "https://z2.idlixku.com/",
    "target_urls": [
        {
            "id": 1,
            "name": "IDLIX Primary",
            "url": "https://z2.idlixku.com/"
        }
    ]
}

def load_config(config_path: str = "config.json") -> dict:
    if not os.path.exists(config_path):
        save_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG.copy()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config: dict, config_path: str = "config.json") -> None:
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def add_target_url(url: str, name: str = "", config_path: str = "config.json") -> dict:
    config = load_config(config_path)
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not url.endswith("/"):
        url += "/"
    
    existing_urls = [item["url"] for item in config["target_urls"]]
    if url not in existing_urls:
        new_id = len(config["target_urls"]) + 1
        display_name = name.strip() if name else f"Target #{new_id}"
        config["target_urls"].append({
            "id": new_id,
            "name": display_name,
            "url": url
        })
        save_config(config, config_path)
    return config

def set_active_url(url: str, config_path: str = "config.json") -> dict:
    config = load_config(config_path)
    config["active_url"] = url
    save_config(config, config_path)
    return config

def delete_target_url(url: str, config_path: str = "config.json") -> dict:
    config = load_config(config_path)
    config["target_urls"] = [item for item in config["target_urls"] if item["url"] != url]
    if config["active_url"] == url:
        config["active_url"] = config["target_urls"][0]["url"] if config["target_urls"] else ""
    save_config(config, config_path)
    return config
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_config_manager.py`
Expected: PASS

---

### Task 3: Scraper Engine (`curl_cffi` & HTML Extraction)

**Files:**
- Create: `src/scraper.py`
- Test: `tests/test_scraper.py`

**Interfaces:**
- Consumes: Target URL string
- Produces: `fetch_featured_content(url: str) -> list[dict]` where item has keys: `title`, `url`, `rating`, `type`, `poster`

- [ ] **Step 1: Write test for Scraper parser**

Create `tests/test_scraper.py`:
```python
from src.scraper import parse_featured_html

MOCK_HTML = """
<html>
<body>
  <div id="featured-titles">
    <article class="item movies">
      <div class="poster">
        <img src="https://image.tmdb.org/t/p/w185/poster1.jpg" alt="Movie Title 1">
        <div class="rating">8.5</div>
      </div>
      <div class="data">
        <h3><a href="https://z2.idlixku.com/movie/test-movie-1/">Test Movie 1</a></h3>
        <span>2024</span>
      </div>
    </article>
  </div>
</body>
</html>
"""

def test_parse_featured_html():
    items = parse_featured_html(MOCK_HTML)
    assert len(items) == 1
    assert items[0]["title"] == "Test Movie 1"
    assert items[0]["url"] == "https://z2.idlixku.com/movie/test-movie-1/"
    assert items[0]["rating"] == "8.5"
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_scraper.py`
Expected: FAIL (module `src.scraper` not found)

- [ ] **Step 3: Implement `src/scraper.py`**

Create `src/scraper.py`:
```python
from bs4 import BeautifulSoup
from curl_cffi import requests

def parse_featured_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    
    # Try finding featured section or general item cards in DooPlay theme
    containers = soup.select("#featured-titles article.item, div.items article.item, #archive-content article.item")
    if not containers:
        containers = soup.select("article.item")
        
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
        
        is_tv = "tvshows" in link or "tv" in article.get("class", [])
        content_type = "TV Series" if is_tv else "Movie"
        
        items.append({
            "title": title,
            "url": link,
            "rating": rating,
            "type": content_type,
            "poster": poster
        })
    return items

def fetch_featured_content(target_url: str) -> list[dict]:
    try:
        response = requests.get(
            target_url,
            impersonate="chrome120",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8"
            },
            timeout=15
        )
        if response.status_code == 200:
            return parse_featured_html(response.text)
        else:
            raise Exception(f"HTTP Status {response.status_code}")
    except Exception as e:
        raise Exception(f"Failed to fetch {target_url}: {str(e)}")
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_scraper.py`
Expected: PASS

---

### Task 4: UI Renderer (`rich` Display & Tables)

**Files:**
- Create: `src/ui.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: Config data, featured content list
- Produces: Functions to print header banner, table of featured movies, and prompt alerts.

- [ ] **Step 1: Write test for UI render functions**

Create `tests/test_ui.py`:
```python
from src.ui import format_featured_table
from rich.table import Table

def test_format_featured_table():
    sample_data = [
        {"title": "Movie 1", "type": "Movie", "rating": "8.0", "url": "https://example.com/1"}
    ]
    table = format_featured_table(sample_data)
    assert isinstance(table, Table)
    assert table.title == "🎬 Featured Content"
```

- [ ] **Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_ui.py`
Expected: FAIL (module `src.ui` not found)

- [ ] **Step 3: Implement `src/ui.py`**

Create `src/ui.py`:
```python
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

def print_header(active_url: str):
    console.clear()
    header_text = Text("🎬 IDLIX SCRAPER CLI v1.0", style="bold cyan")
    sub_text = Text(f"Active Target: {active_url}", style="dim yellow")
    panel = Panel(
        Text.assemble(header_text, "\n", sub_text),
        border_style="cyan",
        expand=False
    )
    console.print(panel)

def format_featured_table(items: list[dict]) -> Table:
    table = Table(title="🎬 Featured Content", show_lines=True, header_style="bold magenta")
    table.add_column("No", style="dim", width=4)
    table.add_column("Title", style="bold white", min_width=25)
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Rating", style="yellow", width=8)
    table.add_column("URL", style="blue", min_width=35)
    
    for idx, item in enumerate(items, 1):
        table.add_row(
            str(idx),
            item.get("title", "N/A"),
            item.get("type", "N/A"),
            item.get("rating", "N/A"),
            item.get("url", "N/A")
        )
    return table

def print_error(msg: str):
    console.print(f"[bold red]❌ Error:[/bold red] {msg}")

def print_success(msg: str):
    console.print(f"[bold green]✔ Success:[/bold green] {msg}")
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_ui.py`
Expected: PASS

---

### Task 5: Interactive Perpetual CLI Main Loop (`main.py`)

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Assembles: `config_manager`, `scraper`, `ui`, `questionary` into an interactive perpetual main loop.

- [ ] **Step 1: Write test for main menu options logic**

Create `tests/test_main.py`:
```python
from src.config_manager import load_config

def test_main_config_integration():
    config = load_config("test_main_config.json")
    assert "active_url" in config
    import os
    if os.path.exists("test_main_config.json"):
        os.remove("test_main_config.json")
```

- [ ] **Step 2: Implement `src/main.py`**

Create `src/main.py`:
```python
import sys
import questionary
from rich.console import Console

from src.config_manager import (
    load_config, add_target_url, set_active_url, delete_target_url
)
from src.scraper import fetch_featured_content
from src.ui import print_header, format_featured_table, print_error, print_success

console = Console()

def handle_featured(active_url: str):
    console.print("\n[bold cyan]Fetching featured content...[/bold cyan]")
    try:
        items = fetch_featured_content(active_url)
        if not items:
            console.print("[yellow]No featured content found or website structure differed.[/yellow]")
        else:
            table = format_featured_table(items)
            console.print(table)
    except Exception as e:
        print_error(str(e))
    
    questionary.press_any_key(message="Tekan sebarang tombol untuk kembali ke menu...").ask()

def handle_select_active():
    config = load_config()
    urls = [item["url"] for item in config["target_urls"]]
    if not urls:
        print_error("Belum ada URL tersimpan.")
        return
    
    chosen = questionary.select(
        "Pilih Active Target URL:",
        choices=urls
    ).ask()
    
    if chosen:
        set_active_url(chosen)
        print_success(f"Active URL diubah ke: {chosen}")

def handle_add_url():
    url = questionary.text("Masukkan Target URL baru (misal: https://z2.idlixku.com/):").ask()
    if url:
        name = questionary.text("Label/Nama untuk URL ini (opsional):").ask()
        add_target_url(url, name)
        print_success(f"URL berhasil ditambahkan!")

def handle_manage_urls():
    config = load_config()
    choices = [f"{item['name']} ({item['url']})" for item in config["target_urls"]] + ["⬅ Kembali"]
    
    selected = questionary.select("Pilih URL untuk di-manage:", choices=choices).ask()
    if selected and selected != "⬅ Kembali":
        # Extract target url
        target_item = next(item for item in config["target_urls"] if f"{item['name']} ({item['url']})" == selected)
        
        action = questionary.select(
            f"Aksi untuk {target_item['name']}:",
            choices=["Set as Active", "Hapus URL", "Batal"]
        ).ask()
        
        if action == "Set as Active":
            set_active_url(target_item["url"])
            print_success(f"Active URL diubah ke: {target_item['url']}")
        elif action == "Hapus URL":
            delete_target_url(target_item["url"])
            print_success(f"URL {target_item['url']} berhasil dihapus!")

def main():
    while True:
        config = load_config()
        active_url = config.get("active_url", "")
        
        if not active_url or not config.get("target_urls"):
            console.clear()
            console.print("[yellow]Belum ada target URL tersimpan. Silakan masukkan URL pertama:[/yellow]")
            url = questionary.text("Target URL (default: https://z2.idlixku.com/):", default="https://z2.idlixku.com/").ask()
            if url:
                add_target_url(url, "Primary IDLIX")
                set_active_url(url)
            continue
        
        print_header(active_url)
        
        choice = questionary.select(
            "Pilih Menu:",
            choices=[
                "🚀 Scrape Featured Content",
                "🌐 Pilih / Ganti Active Target URL",
                "➕ Tambah URL Target Baru",
                "⚙️  Manage List URL (Edit/Delete)",
                "❌ Exit Program"
            ]
        ).ask()
        
        if choice == "🚀 Scrape Featured Content":
            handle_featured(active_url)
        elif choice == "🌐 Pilih / Ganti Active Target URL":
            handle_select_active()
        elif choice == "➕ Tambah URL Target Baru":
            handle_add_url()
        elif choice == "⚙️  Manage List URL (Edit/Delete)":
            handle_manage_urls()
        elif choice == "❌ Exit Program" or choice is None:
            console.print("[bold yellow]Terima kasih! Sampai jumpa.[/bold yellow]")
            sys.exit(0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run pytest to verify all tests pass**

Run: `uv run pytest`
Expected: PASS

---

## Self-Review Checklist
- [x] Spec coverage: Covers CRUD config, `curl_cffi` scraper, `rich` UI, and perpetual loop.
- [x] Placeholder scan: No TODO/TBD or missing code snippets.
- [x] Type consistency: Function parameter signatures match across all modules.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-03-idlix-cli-scraper.md`.
