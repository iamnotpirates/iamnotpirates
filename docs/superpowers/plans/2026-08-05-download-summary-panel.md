# Download Summary Rich Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a Rich-formatted summary panel and table at the end of movie/TV series downloads detailing success, failure, and skipped status for video and subtitle files.

**Architecture:** Add `format_download_summary_table` and `print_download_summary` helper functions in `src/ui.py`. Integrate summary data collection into `handle_item_download` in `src/main.py` so that batch TV series and single movie downloads present an aggregate summary report upon completion.

**Tech Stack:** Python 3.10+, rich (Console, Panel, Table), pytest

## Global Constraints

- Preserve all existing logging functionality in `src/download_log.py`.
- Ensure clean visual formatting with Rich without breaking existing error/success UI output.

---

### Task 1: Add Download Summary Rich UI Components

**Files:**
- Modify: `src/ui.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Produces: `format_download_summary_table(summary_items: list[dict]) -> Table`
- Produces: `print_download_summary(summary_data: dict, console: Console | None = None) -> None`

- [ ] **Step 1: Write failing tests for summary UI**

Write unit tests in `tests/test_ui.py` verifying table and panel formatting for summary data:

```python
from rich.console import Console
from src.ui import format_download_summary_table, print_download_summary

def test_format_download_summary_table():
    items = [
        {
            "title": "Movie 1",
            "video_status": "SUCCESS",
            "video_error": None,
            "subtitles": [{"lang": "id", "status": "SUCCESS"}]
        },
        {
            "title": "Movie 2",
            "video_status": "FAILED",
            "video_error": "Connection error",
            "subtitles": []
        }
    ]
    table = format_download_summary_table(items)
    assert table.title == "[bold cyan]Download Detail Result[/bold cyan]"
    assert len(table.rows) == 2

def test_print_download_summary(capsys):
    console = Console(record=True)
    summary_data = {
        "total_items": 2,
        "video_success": 1,
        "video_failed": 1,
        "video_skipped": 0,
        "sub_success": 1,
        "sub_failed": 0,
        "items": [
            {
                "title": "Episode 1",
                "video_status": "SUCCESS",
                "video_error": None,
                "subtitles": [{"lang": "id", "status": "SUCCESS"}]
            },
            {
                "title": "Episode 2",
                "video_status": "FAILED",
                "video_error": "No m3u8",
                "subtitles": []
            }
        ]
    }
    print_download_summary(summary_data, console=console)
    output = console.export_text()
    assert "DOWNLOAD SUMMARY" in output
    assert "Episode 1" in output
    assert "Episode 2" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui.py -k "test_format_download_summary_table or test_print_download_summary"`
Expected: FAIL with `ImportError: cannot import name 'format_download_summary_table'`

- [ ] **Step 3: Implement `format_download_summary_table` and `print_download_summary` in `src/ui.py`**

Add implementation to `src/ui.py`:

```python
def format_download_summary_table(summary_items: list[dict]) -> Table:
    """Formats a rich.table.Table summarizing video and subtitle download results."""
    table = Table(
        title="[bold cyan]Download Detail Result[/bold cyan]",
        header_style="bold magenta",
        show_header=True,
        expand=True,
    )
    table.add_column("No", justify="right", style="cyan", no_wrap=True)
    table.add_column("Item Title", style="bold white")
    table.add_column("Video", justify="center")
    table.add_column("Subtitles", justify="center")
    table.add_column("Details / Error", style="dim white")

    for idx, item in enumerate(summary_items, start=1):
        title = item.get("title", "N/A")
        v_status = item.get("video_status", "UNKNOWN")
        v_err = item.get("video_error")

        if v_status == "SUCCESS":
            v_text = "[bold green]✓ SUCCESS[/bold green]"
        elif v_status == "SKIPPED":
            v_text = "[bold yellow]⏭ SKIPPED[/bold yellow]"
        else:
            v_text = "[bold red]✗ FAILED[/bold red]"

        subs = item.get("subtitles", [])
        if not subs:
            sub_text = "[dim]N/A[/dim]"
        else:
            ok_count = sum(1 for s in subs if s.get("status") == "SUCCESS")
            total_count = len(subs)
            if ok_count == total_count:
                sub_text = f"[bold green]✓ {ok_count}/{total_count}[/bold green]"
            elif ok_count > 0:
                sub_text = f"[bold yellow]⚠️ {ok_count}/{total_count}[/bold yellow]"
            else:
                sub_text = f"[bold red]✗ 0/{total_count}[/bold red]"

        details = v_err if v_err else "-"
        table.add_row(str(idx), title, v_text, sub_text, details)

    return table

def print_download_summary(summary_data: dict, console: Console | None = None) -> None:
    """Prints aggregate download summary panel and detailed results table."""
    if console is None:
        console = Console()

    tot = summary_data.get("total_items", 0)
    v_ok = summary_data.get("video_success", 0)
    v_fail = summary_data.get("video_failed", 0)
    v_skip = summary_data.get("video_skipped", 0)
    s_ok = summary_data.get("sub_success", 0)
    s_fail = summary_data.get("sub_failed", 0)

    stats_str = (
        f"[bold white]Total Items Processed:[/bold white] [cyan]{tot}[/cyan]\n"
        f"[bold white]Video Downloads:[/bold white] [green]✓ {v_ok} Success[/green]  |  "
        f"[yellow]⏭ {v_skip} Skipped[/yellow]  |  "
        f"[red]✗ {v_fail} Failed[/red]\n"
        f"[bold white]Subtitle Downloads:[/bold white] [green]✓ {s_ok} Success[/green]  |  "
        f"[red]✗ {s_fail} Failed[/red]"
    )

    panel = Panel(
        stats_str,
        title="[bold green]📊 DOWNLOAD SUMMARY REPORT[/bold green]",
        border_style="cyan",
        expand=True,
    )

    console.print()
    console.print(panel)
    if summary_data.get("items"):
        table = format_download_summary_table(summary_data["items"])
        console.print(table)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui.py -k "test_format_download_summary_table or test_print_download_summary"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui.py tests/test_ui.py
git commit -m "feat: add download summary panel and table components"
```

---

### Task 2: Integrate Summary Data Collection and Presentation in `main.py`

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `print_download_summary` from `src/ui.py`
- Modifies: `handle_item_download` in `src/main.py` to record summary metrics and render `print_download_summary` at the end of TV series and movie download loops.

- [ ] **Step 1: Write failing integration test for summary in `handle_item_download`**

Write a unit test in `tests/test_main.py` checking that `print_download_summary` is called with accurate summary counters:

```python
from unittest.mock import patch, MagicMock
from src.main import handle_item_download

@patch("src.main.print_download_summary")
@patch("src.main.download_media_stream")
@patch("src.main.extract_video_sources")
@patch("src.main.questionary")
def test_handle_movie_download_summary(mock_q, mock_extract, mock_download, mock_print_summary, tmp_path):
    mock_q.text.return_value.ask.side_effect = ["1", str(tmp_path)]
    mock_q.select.return_value.ask.return_value = "Tanpa Subtitle"
    mock_extract.return_value = {"m3u8_urls": ["http://test.m3u8"], "subtitles": []}
    mock_download.return_value = str(tmp_path / "Movie.mp4")

    items = [{"title": "Test Movie", "url": "http://test.com/movie", "type": "Movie"}]
    handle_item_download(items, "http://test.com", {})

    assert mock_print_summary.called
    summary_arg = mock_print_summary.call_args[0][0]
    assert summary_arg["total_items"] == 1
    assert summary_arg["video_success"] == 1
    assert summary_arg["items"][0]["video_status"] == "SUCCESS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -k "test_handle_movie_download_summary"`
Expected: FAIL with `AssertionError: assert False (mock_print_summary not called)`

- [ ] **Step 3: Update `handle_item_download` in `src/main.py`**

Import `print_download_summary` in `src/main.py` and collect download item statuses across TV series and Movies, calling `print_download_summary(summary)` before returning from `handle_item_download`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: display rich download summary report upon download completion"
```
