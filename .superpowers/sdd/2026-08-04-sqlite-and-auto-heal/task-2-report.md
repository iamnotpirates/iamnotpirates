# Task 2 Report: FFmpeg Binary Manager & Media Integrity Verifier

## Status
DONE

## Commit Hash
`14fbdd679890b6102307cc44e4980a6d550a504e`

## Test Summary
`tests/test_ffmpeg_manager.py`: 8 passed in 0.11s.

## Overview of Changes
- Created [`src/ffmpeg_manager.py`](file:///C:/Users/aldinal21/workspaces/projects/iamnotpirates/src/ffmpeg_manager.py) to manage static Windows builds of `ffmpeg.exe` and `ffprobe.exe` cached under `~/.iamnotpirates/bin/`.
- Implemented `get_ffmpeg_paths()`, `ensure_ffmpeg()`, and `verify_media_file()`.
- Created [`tests/test_ffmpeg_manager.py`](file:///C:/Users/aldinal21/workspaces/projects/iamnotpirates/tests/test_ffmpeg_manager.py) covering path generation, caching, download extraction logic, missing media, corrupted media, and subtitle check rules.

## Concerns
None.
