# Design Spec: Download Summary Rich Panel

## Context
When downloading Movies or TV Series episodes, users currently only see line-by-line log outputs. When downloading multiple episodes or items with multiple subtitle options, it is hard to get an overall picture of what succeeded, what failed, or which specific subtitles were missing or failed.

## Proposed Changes

### Component 1: `src/ui.py`
Add functions to build and display a Rich-formatted Download Summary Panel & Table.

- Function `format_download_summary_table(summary_items: list[dict]) -> Table`:
  - Columns: `No`, `Item Title`, `Video`, `Subtitles`, `Status & Details`
  - Visual indicators:
    - Video: `[green]✓ OK[/green]`, `[red]✗ FAILED[/red]`, `[yellow]⏭ SKIPPED[/yellow]`
    - Subtitles: `[green]✓ 2/2[/green]`, `[yellow]⚠️ 1/2[/yellow]`, `[red]✗ 0/1[/red]`, `[dim]N/A[/dim]`
- Function `print_download_summary(summary_data: dict, console: Console | None = None) -> None`:
  - Renders an aggregate metric panel at top (Total Items, Video Success/Failed/Skipped, Subtitle Success/Failed).
  - Displays the detailed result table below the summary metric panel.

### Component 2: `src/main.py`
Collect download attempt metrics during `handle_item_download` loops for both TV Series and Movies, then render `print_download_summary` at the end of the batch operation.

`summary_data` structure:
```python
{
    "total_items": int,
    "video_success": int,
    "video_failed": int,
    "video_skipped": int,
    "sub_success": int,
    "sub_failed": int,
    "items": [
        {
            "title": str,
            "video_status": "SUCCESS" | "FAILED" | "SKIPPED",
            "video_error": str | None,
            "subtitles": [
                {"lang": str, "status": "SUCCESS" | "FAILED", "error": str | None}
            ]
        }
    ]
}
```

## Verification Plan

### Automated Tests
- `tests/test_ui.py`:
  - Test `format_download_summary_table` renders correct columns and rows.
  - Test `print_download_summary` outputs expected panels without exceptions.
- `tests/test_main.py`:
  - Test batch summary data collection correctly tallies mixed download results (success, failure, skipped).

### Manual Verification
- Run CLI, download an episode/movie with subtitles, and verify the summary table displays accurately at the end of the operation.
