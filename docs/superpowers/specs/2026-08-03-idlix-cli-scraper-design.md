# Design Spec: IDLIX CLI Scraper Tool

## Overview
An interactive Python command-line interface (CLI) application for managing target video streaming URLs (WordPress/DooPlay based like IDLIX) and scraping featured movies/TV shows. Built using `uv` environment, `curl_cffi` (for Cloudflare TLS fingerprint bypass), `BeautifulSoup4`, `rich`, and `questionary`.

## Requirements & Scope
1. **Target URL Management (CRUD)**
   - Persistent storage in `config.json`.
   - Ability to select active target URL, add new target URLs, edit, and delete URLs.
   - Initial onboarding prompt to add a target URL if `config.json` is missing or empty (default: `https://z2.idlixku.com/`).

2. **Featured Content Scraper**
   - Scrapes featured titles (movies/series) from the active target site.
   - Extracts metadata: Title, Details Link, Poster URL, and Type (Movie vs Series).
   - Renders results in a formatted `rich` table in the terminal.

3. **Persistent Main Loop**
   - The CLI operates continuously in an interactive loop until explicitly exited by the user (`Exit` menu choice).
   - Pressing Enter after viewing results returns the user back to the Main Menu.

4. **Bypass & Resilience**
   - Uses `curl_cffi` with Chrome TLS fingerprinting to bypass Cloudflare `403 Forbidden` protection.
   - Graceful error handling for network timeouts or structural changes on the target site.

## Architecture & Components

```
+-------------------------------------------------------------+
|                      main.py (CLI Loop)                      |
+------------------------------+------------------------------+
                               |
       +-----------------------+-----------------------+
       |                                               |
+------v----------------------+             +----------v------------------+
| config_manager.py           |             | scraper.py                  |
| - Read/Write config.json    |             | - Fetch via curl_cffi       |
| - Add/Edit/Delete URLs      |             | - Parse with BeautifulSoup4 |
| - Active URL selection      |             | - Extract Featured items    |
+-----------------------------+             +-----------------------------+
                                                       |
                                            +----------v------------------+
                                            | ui.py                       |
                                            | - Render Rich Tables        |
                                            | - Show Spinners & Alerts    |
                                            +-----------------------------+
```

### Data Schema (`config.json`)
```json
{
  "active_url": "https://z2.idlixku.com/",
  "target_urls": [
    {
      "id": 1,
      "name": "IDLIX Primary",
      "url": "https://z2.idlixku.com/"
    }
  ]
}
```

### Dependencies (`pyproject.toml`)
- `curl_cffi` (Cloudflare bypass HTTP client)
- `beautifulsoup4` (HTML parser)
- `rich` (Terminal UI & Tables)
- `questionary` (Interactive CLI menus)

## Error Handling & Testing Strategy
- Network errors or HTTP status code failures (`403`, `500`) trigger a non-fatal alert message with retry option.
- Validate input URLs to ensure proper HTTP/HTTPS format.

## Spec Self-Review Checklist
- [x] No placeholders or TODOs.
- [x] Internal consistency between CLI loop, storage, and scraper components.
- [x] Focused scope appropriate for initial MVP phase.
- [x] Unambiguous requirements and non-exiting main loop flow.
