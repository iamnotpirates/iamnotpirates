"""FFmpeg binary manager and media integrity verifier.

Auto-downloads and caches static Windows builds of ffmpeg.exe and ffprobe.exe
into ~/.iamnotpirates/bin/, and provides a media verification function.
"""
import io
import os
import subprocess
import zipfile

from curl_cffi import requests

_FFMPEG_NAME = "ffmpeg.exe"
_FFPROBE_NAME = "ffprobe.exe"
_DOWNLOAD_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"


def get_ffmpeg_paths() -> tuple[str, str]:
    """Return the expected local cache paths for ffmpeg.exe and ffprobe.exe.

    Does NOT check whether the files actually exist.
    """
    bin_dir = os.path.join(os.path.expanduser("~"), ".iamnotpirates", "bin")
    return os.path.join(bin_dir, _FFMPEG_NAME), os.path.join(bin_dir, _FFPROBE_NAME)


def ensure_ffmpeg(console=None) -> tuple[str | None, str | None]:
    """Ensure ffmpeg.exe and ffprobe.exe are available locally.

    If already cached, returns the paths immediately.
    Otherwise downloads static Windows build zip, extracts ffmpeg.exe and ffprobe.exe
    to ~/.iamnotpirates/bin/.

    Args:
        console: Optional rich.console.Console for progress output.

    Returns:
        Tuple of (ffmpeg_path, ffprobe_path) or (None, None) if download failed.
    """
    ffmpeg_path, ffprobe_path = get_ffmpeg_paths()

    if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
        return ffmpeg_path, ffprobe_path

    def _print(msg: str) -> None:
        if console is not None:
            console.print(msg)
        else:
            print(msg)

    _print("[FFmpeg] Binaries not found. Downloading static build from GitHub releases…")

    try:
        bin_dir = os.path.dirname(ffmpeg_path)
        os.makedirs(bin_dir, exist_ok=True)

        resp = requests.get(_DOWNLOAD_URL, impersonate="chrome120")
        if resp.status_code != 200:
            _print(f"[FFmpeg] Zip download failed: HTTP {resp.status_code}")
            return None, None

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for member in zf.namelist():
                filename = os.path.basename(member)
                if filename in (_FFMPEG_NAME, _FFPROBE_NAME):
                    target_path = os.path.join(bin_dir, filename)
                    with zf.open(member) as source, open(target_path, "wb") as target:
                        target.write(source.read())

        if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
            _print(f"[FFmpeg] Binaries cached at: {bin_dir}")
            return ffmpeg_path, ffprobe_path

        _print("[FFmpeg] Failed to locate binaries in extracted archive.")
        return None, None

    except Exception as exc:
        _print(f"[FFmpeg] Error during download: {exc}")
        return None, None


def verify_media_file(video_path: str, required_sub_mode: str = "Tanpa Subtitle") -> dict:
    """Check the video file and its associated subtitles.

    Returns dict:
    {
        "video_status": "HEALTHY" | "CORRUPTED" | "MISSING",
        "missing_subtitles": True | False,
        "error_message": None | str
    }
    """
    if not os.path.exists(video_path):
        return {
            "video_status": "MISSING",
            "missing_subtitles": False,
            "error_message": f"File does not exist: {video_path}",
        }

    try:
        size = os.path.getsize(video_path)
    except OSError as exc:
        return {
            "video_status": "MISSING",
            "missing_subtitles": False,
            "error_message": f"Error reading file size: {exc}",
        }

    if size < 1024 * 1024:  # < 1MB
        return {
            "video_status": "MISSING",
            "missing_subtitles": False,
            "error_message": f"File size too small ({size} bytes)",
        }

    _, ffprobe_path = get_ffmpeg_paths()
    cmd = [
        ffprobe_path,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            return {
                "video_status": "CORRUPTED",
                "missing_subtitles": False,
                "error_message": f"ffprobe returncode {res.returncode}: {res.stderr.strip()}",
            }
        try:
            duration = float(res.stdout.strip())
            if duration <= 0:
                return {
                    "video_status": "CORRUPTED",
                    "missing_subtitles": False,
                    "error_message": "Invalid duration <= 0",
                }
        except ValueError:
            return {
                "video_status": "CORRUPTED",
                "missing_subtitles": False,
                "error_message": f"Invalid ffprobe output: {res.stdout.strip()}",
            }
    except Exception as exc:
        return {
            "video_status": "CORRUPTED",
            "missing_subtitles": False,
            "error_message": f"Failed to execute ffprobe: {exc}",
        }

    missing_subtitles = False
    if required_sub_mode != "Tanpa Subtitle":
        base_name, _ = os.path.splitext(video_path)
        sub_candidates = [
            f"{base_name}.id.srt",
            f"{base_name}.en.srt",
            f"{base_name}.srt",
        ]
        has_sub = any(os.path.exists(sub) for sub in sub_candidates)
        if not has_sub:
            missing_subtitles = True

    return {
        "video_status": "HEALTHY",
        "missing_subtitles": missing_subtitles,
        "error_message": None,
    }
