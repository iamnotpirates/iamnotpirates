"""N_m3u8DL-RE binary manager.

Auto-downloads and caches the N_m3u8DL-RE.exe binary from GitHub releases,
and provides a subprocess wrapper to invoke it for HLS/DASH stream downloading.
"""
import io
import os
import subprocess
import zipfile

from curl_cffi import requests

GITHUB_API_URL = "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest"
_BINARY_NAME = "N_m3u8DL-RE.exe"
_CACHE_SUBPATH = os.path.join(".iamnotpirates", "bin", _BINARY_NAME)


def get_binary_path() -> str:
    """Return the expected local cache path for the N_m3u8DL-RE binary.

    Does NOT check whether the file actually exists.
    """
    return os.path.join(os.path.expanduser("~"), ".iamnotpirates", "bin", _BINARY_NAME)


def ensure_binary(console=None) -> str | None:
    """Ensure the N_m3u8DL-RE binary is available locally.

    If already cached, returns the path immediately.
    Otherwise downloads the latest Windows x64 release from GitHub,
    extracts the exe, and caches it.

    Args:
        console: Optional rich.console.Console for progress output.

    Returns:
        Absolute path to the binary, or None if download failed.
    """
    binary_path = get_binary_path()

    if os.path.exists(binary_path):
        return binary_path

    def _print(msg: str) -> None:
        if console is not None:
            console.print(msg)
        else:
            print(msg)

    _print("[N_m3u8DL-RE] Binary not found. Downloading from GitHub releases…")

    try:
        # Fetch latest release metadata
        api_resp = requests.get(GITHUB_API_URL, impersonate="chrome120")
        if api_resp.status_code != 200:
            _print(f"[N_m3u8DL-RE] GitHub API request failed: HTTP {api_resp.status_code}")
            return None

        release_data = api_resp.json()
        assets = release_data.get("assets", [])

        # Find win-x64 zip asset
        zip_url = None
        for asset in assets:
            name: str = asset.get("name", "")
            if "win-x64" in name.lower() and name.lower().endswith(".zip"):
                zip_url = asset.get("browser_download_url")
                break

        if zip_url is None:
            _print("[N_m3u8DL-RE] Could not find a win-x64 zip asset in the latest release.")
            return None

        _print(f"[N_m3u8DL-RE] Downloading: {zip_url}")
        zip_resp = requests.get(zip_url, impersonate="chrome120")
        if zip_resp.status_code != 200:
            _print(f"[N_m3u8DL-RE] Zip download failed: HTTP {zip_resp.status_code}")
            return None

        # Extract binary from zip
        os.makedirs(os.path.dirname(binary_path), exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
            zf.extract(_BINARY_NAME, path=os.path.dirname(binary_path))

        _print(f"[N_m3u8DL-RE] Binary cached at: {binary_path}")
        return binary_path

    except Exception as exc:
        _print(f"[N_m3u8DL-RE] Error during download: {exc}")
        return None


import re
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)


def parse_re_log_line(line: str) -> dict:
    """Parses N_m3u8DL-RE stdout line to extract progress, speed, and segment counts."""
    data = {}
    if not line:
        return data

    # Match segment total e.g. "1489 Segments"
    tot_match = re.search(r"(\d+)\s+Segments", line, re.IGNORECASE)
    if tot_match:
        data["total_segments"] = int(tot_match.group(1))

    # Match progress e.g. "450/1000" or "45.0%"
    prog_match = re.search(r"(\d+)\s*/\s*(\d+)", line)
    if prog_match:
        data["current_segments"] = int(prog_match.group(1))
        data["total_segments"] = int(prog_match.group(2))

    # Match speed e.g. "12.5 MB/s" or "800.5 KB/s"
    speed_match = re.search(r"(\d+\.?\d*\s+[KMG]B/s)", line, re.IGNORECASE)
    if speed_match:
        data["speed"] = speed_match.group(1)

    return data


def download_with_re(
    m3u8_url: str,
    save_dir: str,
    save_name: str,
    thread_count: int = 16,
    console=None,
) -> bool:
    """Download an HLS/DASH stream using N_m3u8DL-RE with interactive Rich progress bar.

    Calls ensure_binary() first; if the binary is unavailable returns False.

    Args:
        m3u8_url:     URL of the m3u8 playlist.
        save_dir:     Directory to save the output file.
        save_name:    Base filename (without extension).
        thread_count: Number of parallel download threads (default 16).
        console:      Optional rich Console for progress messages.

    Returns:
        True if the subprocess exited with returncode 0, else False.
    """
    binary = ensure_binary(console=console)
    if binary is None:
        return False

    cmd = [
        binary,
        m3u8_url,
        "--save-dir", save_dir,
        "--save-name", save_name,
        "--thread-count", str(thread_count),
        "--auto-select",
        "-M", "format=mp4",
        "--download-retry-count", "3",
        "--no-log",
    ]

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("[yellow]{task.fields[info]}[/yellow]"),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        with progress:
            task_id = progress.add_task(f"Downloading {save_name}.mp4", total=100, info="")
            total_segs = 0

            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    parsed = parse_re_log_line(line)
                    if "total_segments" in parsed and parsed["total_segments"] > 0:
                        total_segs = parsed["total_segments"]

                    if "current_segments" in parsed and total_segs > 0:
                        cur_segs = parsed["current_segments"]
                        pct = min(100.0, (cur_segs / total_segs) * 100.0)
                        spd = parsed.get("speed", "")
                        info_str = f"{cur_segs}/{total_segs} segs ({spd})" if spd else f"{cur_segs}/{total_segs} segs"
                        progress.update(task_id, completed=pct, info=info_str)

            proc.wait()
            return proc.returncode == 0
    except Exception as exc:
        if console:
            console.print(f"[bold red]Subprocess execution error: {exc}[/bold red]")
        return False

