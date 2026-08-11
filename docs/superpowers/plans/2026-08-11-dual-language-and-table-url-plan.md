# Dual-Language CLI & Rich Table URL Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement simultaneous dual-language UI (English first, Indonesian second) across all CLI menus and prompts, and optimize Rich Table URL rendering using OSC 8 hyperlinks.

**Architecture:** Update `src/ui.py` to format URLs cleanly as `[link=FULL_URL]🔗 domain/path...[/link]` with flexible Title column wrapping. Update `src/main.py` main menu choices and prompts to dual-language strings. Update corresponding unit/integration test assertions.

**Tech Stack:** Python 3.9+, Rich, PyTest.

## Global Constraints

- Menu options and prompts must follow `English First / Indonesian Second` format (e.g., `1. 🔍 Search Movie & TV Series / Cari Film & TV Series`).
- Table URLs must use Rich `[link=FULL_URL]🔗 DISPLAY_TEXT[/link]` hyperlinks without breaking layout in legacy terminals.
- All 100+ tests must pass with 0 failures and >90% code coverage.

---

### Task 1: Rich Table Hyperlink URL Formatting & UI Unit Tests

**Files:**
- Modify: `src/ui.py:21-65`
- Modify: `tests/test_ui.py`

**Interfaces:**
- Consumes: `src/ui.py` `format_featured_table(items: list[dict]) -> Table`
- Produces: Updated `Table` with dual-language headers (`Title / Judul`, `URL / Link`) and truncated `[link=...]` hyperlinks.

- [ ] **Step 1: Write failing UI unit tests**

```python
# In tests/test_ui.py
def test_format_featured_table_hyperlink_url():
    items = [{
        "title": "Avatar: The Way of Water 2022",
        "url": "https://tv5.idlix.vip/movie/avatar-the-way-of-water-2022-sub-indo/",
        "type": "Movie",
        "quality": "WEB-DL",
        "rating": "7.6"
    }]
    table = format_featured_table(items)
    assert table.columns[1].header == "Title / Judul"
    assert table.columns[6].header == "URL / Link"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ui.py -v`
Expected: FAIL (header string mismatch "Title" != "Title / Judul")

- [ ] **Step 3: Update `format_featured_table` in `src/ui.py`**

```python
def format_featured_table(items: list[dict]) -> Table:
    """Returns a styled rich.table.Table with dual-language headers and hyperlink URLs."""
    table = Table(
        title="[bold cyan]Featured Content / Konten Populer[/bold cyan]",
        header_style="bold magenta",
        show_header=True,
        expand=True,
    )
    table.add_column("No", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title / Judul", style="bold white", no_wrap=False, ratio=3)
    table.add_column("Year / Tahun", justify="center", style="yellow", no_wrap=True)
    table.add_column("Type / Tipe", style="green", justify="center", no_wrap=True)
    table.add_column("Quality / Kualitas", justify="center", style="bold green", no_wrap=True)
    table.add_column("Rating", justify="center", style="yellow", no_wrap=True)
    table.add_column("URL / Link", style="blue underline", no_wrap=True, ratio=2)

    for idx, item in enumerate(items, start=1):
        raw_title = item.get("title", "N/A")
        item_url = item.get("url", "")
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", raw_title)
        if year_match:
            year = year_match.group(1)
            clean_title = re.sub(r"\b(19\d\d|20\d\d)\b", "", raw_title).strip()
        else:
            url_year_match = re.search(r"-?(19\d\d|20\d\d)\b", item_url)
            year = url_year_match.group(1) if url_year_match else "N/A"
            clean_title = raw_title

        quality = item.get("quality", "WEB-DL")
        if item_url:
            short_url = item_url.replace("https://", "").replace("http://", "")
            if len(short_url) > 25:
                short_url = short_url[:22] + "..."
            clickable_url = f"[link={item_url}]🔗 {short_url}[/link]"
        else:
            clickable_url = "N/A"

        table.add_row(
            str(idx),
            clean_title,
            year,
            item.get("type", "N/A"),
            quality,
            str(item.get("rating", "N/A")),
            clickable_url,
        )

    return table
```

- [ ] **Step 4: Update all test assertions in `tests/test_ui.py` and run tests**

Run: `uv run pytest tests/test_ui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src/ui.py tests/test_ui.py`
Run: `git commit -m "feat: optimize Rich Table with hyperlink URLs and dual-language column headers"`

---

### Task 2: Dual-Language Main Menu & Prompts

**Files:**
- Modify: `src/main.py:650-700`
- Modify: `tests/test_main.py`
- Modify: `tests/test_workflows.py`

**Interfaces:**
- Consumes: Questionary and Rich CLI menu choices
- Produces: Dual-language menu option strings and prompt texts.

- [ ] **Step 1: Write failing menu unit test**

Update `tests/test_main.py` to expect choice `"1. 🔍 Search Movie & TV Series / Cari Film & TV Series"`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main.py -v`
Expected: FAIL (choice string mismatch)

- [ ] **Step 3: Update `main()` menu choices in `src/main.py`**

```python
        choice = questionary.select(
            "Select Menu / Pilih Menu:",
            choices=[
                "1. 🔍 Search Movie & TV Series / Cari Film & TV Series",
                "2. 🔥 Browse Featured Content / Lihat Content Populer",
                "3. 📋 Download Log & Retry / Log & Retry Download Gagal",
                "4. 🛠️  Settings / Pengaturan (Folder & Mode)",
                "5. 🌐 Switch Target URL / Pilih Active Target URL",
                "6. ➕ Add New Target URL / Tambah Target URL Baru",
                "7. ⚙️  Manage Target URLs / Kelola Daftar Target URL",
                "8. ❌ Exit / Keluar",
            ],
        ).ask()
```

- [ ] **Step 4: Update test assertions in `tests/test_main.py` and `tests/test_workflows.py`**

Update mock return values for `questionary.select` to use the new dual-language string options.

Run: `uv run pytest tests/test_main.py tests/test_workflows.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

Run: `git add src/main.py tests/test_main.py tests/test_workflows.py`
Run: `git commit -m "feat: update CLI main menu and prompts to dual-language format"`

---

### Task 3: Full Suite Regression & Code Coverage Verification

- [ ] **Step 1: Run complete pytest test suite**

Run: `uv run pytest -v`
Expected: 100+ PASS

- [ ] **Step 2: Run code coverage analysis**

Run: `uv run --with pytest-cov pytest --cov=src --cov-report=term-missing`
Expected: Coverage >90%
