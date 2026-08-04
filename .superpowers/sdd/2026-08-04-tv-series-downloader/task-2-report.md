# Task 2 Implementation Report: Enhance Downloader Helper for Jellyfin Paths & Subtitles (`src/downloader.py`)

## Executive Summary
- **Status:** DONE
- **Commits:** `16b6d30739c2273da66bf07319b09503312b621a` (`feat: add format_tv_paths and download_subtitles_batch helpers`)
- **Test Summary:** `11 passed in 0.22s` (`uv run pytest tests/test_downloader.py -v`)
- **Concerns:** None.

## Deliverables & Files Modified
1. `src/downloader.py`: Added `format_tv_paths` and `download_subtitles_batch` helper functions for TV series episode path formatting and batch subtitle downloading.
2. `tests/test_downloader.py`: Added comprehensive unit test coverage for Jellyfin TV directory structure formatting and sub_mode batch downloads (`Semua Subtitle Tersedia`, `Indonesia saja`, `English saja`, `Tanpa Subtitle`).

## Verification Evidence
- **Test Command Output (`tests/test_downloader.py`):**
  ```text
  tests/test_downloader.py::test_convert_vtt_to_srt PASSED                 [  9%]
  tests/test_downloader.py::test_get_unique_filepath PASSED                [ 18%]
  tests/test_downloader.py::test_download_subtitle_success PASSED          [ 27%]
  tests/test_downloader.py::test_inspect_stream_qualities_success PASSED   [ 36%]
  tests/test_downloader.py::test_download_media_stream_jellyfin_naming PASSED [ 45%]
  tests/test_downloader.py::test_format_tv_paths_with_year PASSED          [ 54%]
  tests/test_downloader.py::test_format_tv_paths_no_year PASSED            [ 63%]
  tests/test_downloader.py::test_download_subtitles_batch_all PASSED       [ 72%]
  tests/test_downloader.py::test_download_subtitles_batch_indonesia_only PASSED [ 81%]
  tests/test_downloader.py::test_download_subtitles_batch_english_only PASSED [ 90%]
  tests/test_downloader.py::test_download_subtitles_batch_tanpa_subtitle PASSED [100%]
  11 passed in 0.22s
  ```
- **Full Suite Run:** 47 passed in 2.38s.
