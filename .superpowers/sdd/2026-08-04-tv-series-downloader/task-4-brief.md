# Task 4 Brief: Executable Build & Full Test Verification

**Files:**
- Output Executable: `dist/IAmNotPirates.exe`

**Global Constraints:**
- Full test suite run using `uv run pytest`.
- PyInstaller build command: `uv run pyinstaller IAmNotPirates.spec --clean`

**Report File Contract:**
- Write full report to: `C:\Users\aldinal21\workspaces\projects\iamnotpirates\.superpowers\sdd\2026-08-04-tv-series-downloader\task-4-report.md`
- Return status: DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT, or BLOCKED. Include commits, short test summary, and any concerns.

---

### Implementation Steps:

1. Run `uv run pytest` to verify all tests pass across all test files.
2. Run `uv run pyinstaller IAmNotPirates.spec --clean` to compile the standalone executable.
3. Verify `dist/IAmNotPirates.exe` exists and has non-zero size.
4. Commit build update: `git add .` and `git commit -m "build: rebuild standalone executable with TV series downloader support"`.
