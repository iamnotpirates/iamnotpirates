# Design Spec: Rich Live Progress Bar for N_m3u8DL-RE

**Date:** 2026-08-04  
**Project:** IAmNotPirates CLI  
**Status:** Approved by User  

## 1. Overview
Replace raw subprocess text output during N_m3u8DL-RE downloads with an interactive, real-time Rich Progress Bar (`rich.progress.Progress`).

## 2. Progress Bar Visual UI
Format:
`[Spinner] [Title/Description] [ProgressBar 0-100%] [Segments / Speed] [TimeRemaining]`

Example rendered bar:
`⠋ Downloading A Shop for Killers - S01E01.mp4 ━━━━━━━━━━━━━━━━━━━━━━━╸━━━━━━━━━━━━━━━━ 64% 952/1489 segs (12.4 MB/s) 00:00:15`

## 3. Technical Design (`src/n_m3u8dl_manager.py`)

### Update `download_with_re()`:
- Use `subprocess.Popen` instead of `subprocess.run` to capture `stdout` / `stderr` in real-time line-by-line.
- Parse N_m3u8DL-RE terminal output patterns using Regex:
  - Total segments: `(\d+)\s+Segments`
  - Current segment index / percentage: `(\d+)/(\d+)` or `(\d+\.\d+)%`
  - Download Speed: `(\d+\.?\d*\s+[KMG]B/s)`
- Initialize `rich.progress.Progress` with custom columns:
  - `SpinnerColumn()`
  - `TextColumn("[bold cyan]{task.description}")`
  - `BarColumn(bar_width=40)`
  - `TaskProgressColumn()`
  - `TextColumn("[yellow]{task.fields[info]}[/yellow]")`
  - `TimeRemainingColumn()`
- Update `Progress` object on each parsed line.
- Graceful Fallback: If parsing fails or output is unformatted, display an animated spinner until subprocess completes.

## 4. Testing Plan
1. Unit tests in `tests/test_n_m3u8dl_manager.py`: Test line parsing helper functions with sample N_m3u8DL-RE stdout lines.
2. Integration test in `tests/test_n_m3u8dl_manager.py`: Mock `subprocess.Popen` stdout stream and verify Progress bar updates without raising errors.
3. Run full test suite: `uv run pytest`.
