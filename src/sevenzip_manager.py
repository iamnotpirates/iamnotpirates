"""7-Zip standalone binary manager for archive-based backups.

Downloads the official 7zr.exe standalone console (7z format only) into
~/.iamnotpirates/bin/ on first use, mirroring ffmpeg_manager's pattern.
"""
import os
import subprocess

from curl_cffi import requests

_SEVENZIP_NAME = "7zr.exe"
_DOWNLOAD_URL = "https://www.7-zip.org/a/7zr.exe"


def get_bin_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".iamnotpirates", "bin")


def get_sevenzip_path() -> str:
    return os.path.join(get_bin_dir(), _SEVENZIP_NAME)


def ensure_7z(console=None):
    """Return path to 7zr.exe, downloading it if missing. None on failure."""
    exe_path = get_sevenzip_path()

    def _print(msg: str) -> None:
        if console is not None:
            console.print(msg)
        else:
            print(msg)

    if os.path.exists(exe_path):
        return exe_path

    _print("[bold cyan]📦 7-Zip (7zr) tidak ditemukan. Mengunduh standalone build...[/bold cyan]")
    try:
        bin_dir = get_bin_dir()
        os.makedirs(bin_dir, exist_ok=True)
        resp = requests.get(_DOWNLOAD_URL, impersonate="chrome120")
        if resp.status_code != 200:
            _print(f"[red]Download 7zr gagal: HTTP {resp.status_code}[/red]")
            return None
        with open(exe_path, "wb") as fh:
            fh.write(resp.content)
        if os.path.exists(exe_path):
            _print(f"[bold green]✓ 7zr terpasang di: {exe_path}[/bold green]")
            return exe_path
        return None
    except Exception as exc:
        _print(f"[red]Gagal mengunduh 7zr: {exc}[/red]")
        return None


def compress_archive(sevenzip_path: str, archive_path: str, files: list) -> None:
    """Create a .7z store-mode archive from files that share one directory.

    Runs 7z with cwd set to the files' common directory so stored names are
    relative basenames.
    """
    base_dir = os.path.dirname(os.path.abspath(files[0]))
    cmd = [sevenzip_path, "a", "-t7z", "-mx=0", "-y", os.path.abspath(archive_path)]
    cmd += [os.path.basename(f) for f in files]
    result = subprocess.run(cmd, cwd=base_dir, check=False, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(archive_path):
        raise RuntimeError(f"7z compress failed: {result.stderr.strip() or result.stdout.strip()}")


def extract_archive(sevenzip_path: str, archive_path: str, dest_dir: str) -> None:
    """Extract a .7z archive into dest_dir (created if missing)."""
    os.makedirs(dest_dir, exist_ok=True)
    cmd = [sevenzip_path, "x", "-y", f"-o{os.path.abspath(dest_dir)}",
           os.path.abspath(archive_path)]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"7z extract failed: {result.stderr.strip() or result.stdout.strip()}")
