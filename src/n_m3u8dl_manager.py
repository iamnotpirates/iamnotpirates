"""N_m3u8DL-RE binary manager.

Auto-downloads and caches the N_m3u8DL-RE.exe binary from GitHub releases,
and provides a subprocess wrapper to invoke it for HLS/DASH stream downloading.
"""
import io
import os
import shutil
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

    _print("[bold cyan][1/3] ⚙️ N_m3u8DL-RE tidak ditemukan. Mengunduh dari GitHub Releases...[/bold cyan]")

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

        _print(f"[dim white]⏳ Mengunduh: {zip_url}[/dim white]")
        zip_resp = requests.get(zip_url, impersonate="chrome120")
        if zip_resp.status_code != 200:
            _print(f"[N_m3u8DL-RE] Zip download failed: HTTP {zip_resp.status_code}")
            return None

        # Extract binary from zip
        os.makedirs(os.path.dirname(binary_path), exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
            zf.extract(_BINARY_NAME, path=os.path.dirname(binary_path))

        _print(f"[bold green]✓ N_m3u8DL-RE terpasang di: {binary_path}[/bold green]")
        return binary_path

    except Exception as exc:
        _print(f"[N_m3u8DL-RE] Error during download: {exc}")
        return None





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

    # 1. Batal awal jika file tujuan sudah ada tetapi terkunci oleh proses lain
    expected_file = os.path.join(save_dir, f"{save_name}.mp4")
    if os.path.exists(expected_file):
        try:
            os.remove(expected_file)
        except OSError as exc:
            msg = (
                f"\n[bold red]⚠️ File '{expected_file}' sedang digunakan/dikunci oleh proses lain.[/bold red]\n"
                f"[yellow]Penyebab: File mungkin sedang diputar di VLC/MPC atau di-index oleh Windows Explorer.\n"
                f"Solusi  : Tutup media player atau jendela explorer lalu coba lagi (Detail: {exc})[/yellow]"
            )
            if console:
                console.print(msg)
            else:
                print(msg)
            return False

    # 2. Isolasi direktori temporary ke SSD lokal (mencegah lock segment I/O pada drive Z:)
    import tempfile
    tmp_dir = os.path.join(tempfile.gettempdir(), "iamnotpirates_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    cmd = [
        binary,
        m3u8_url,
        "--save-dir", save_dir,
        "--save-name", save_name,
        "--thread-count", str(thread_count),
        "--auto-select",
        "-M", "format=mp4",
        "--download-retry-count", "3",
        "--tmp-dir", tmp_dir,
        "--no-log",
    ]

    try:
        env = os.environ.copy()
        ffmpeg_bin_dir = os.path.join(os.path.expanduser("~"), ".iamnotpirates", "bin")
        if os.path.exists(ffmpeg_bin_dir):
            env["PATH"] = ffmpeg_bin_dir + os.pathsep + env.get("PATH", "")

        result = subprocess.run(cmd, check=False, env=env)

        # Auto-heal: check if N_m3u8DL-RE finished but left MUX.mp4 due to rename failure on Windows
        mux_file = os.path.join(save_dir, f"{save_name}.MUX.mp4")
        ts_file = os.path.join(save_dir, f"{save_name}.ts")

        if not os.path.exists(expected_file) and os.path.exists(mux_file):
            msg = "[bold yellow]⚠️ Muxing selesai tetapi file belum di-rename. Melakukan auto-heal rename...[/bold yellow]"
            if console:
                console.print(msg)
            else:
                print(msg.replace("[bold yellow]", "").replace("[/bold yellow]", ""))
            
            import time
            move_success = False
            for attempt in range(5):
                try:
                    shutil.move(mux_file, expected_file)
                    move_success = True
                    break
                except Exception as e:
                    if attempt == 4:
                        err_msg = f"[bold red]Gagal auto-heal rename setelah 5 percobaan: {e}[/bold red]"
                        if console:
                            console.print(err_msg)
                        else:
                            print(err_msg.replace("[bold red]", "").replace("[/bold red]", ""))
                    else:
                        time.sleep(1)

            if move_success:
                if os.path.exists(ts_file):
                    try:
                        os.remove(ts_file)
                    except Exception as e:
                        warn_msg = f"[yellow]⚠️ Gagal menghapus file temp .ts: {e}[/yellow]"
                        if console:
                            console.print(warn_msg)
                        else:
                            print(warn_msg.replace("[yellow]", "").replace("[/yellow]", ""))
                return True

        return result.returncode == 0
    except KeyboardInterrupt:
        if console:
            console.print("\n[bold yellow]⚠️ Download dibatalkan oleh pengguna (Ctrl+C).[/bold yellow]")
        return False
    except Exception as exc:
        if console:
            console.print(f"[bold red]Subprocess execution error: {exc}[/bold red]")
        return False

