import os
import re
from curl_cffi import requests
import yt_dlp

def convert_vtt_to_srt(vtt_content: str) -> str:
    """Converts WebVTT subtitle content string to SubRip (SRT) format."""
    lines = vtt_content.splitlines()
    srt_lines = []
    cue_counter = 1

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or line.startswith("STYLE"):
            i += 1
            continue

        if "-->" in line:
            time_match = re.search(r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})", line)
            if time_match:
                start_t, end_t = time_match.group(1), time_match.group(2)
                if len(start_t.split(":")[0]) == 1:
                    start_t = "0" + start_t
                if ":" not in start_t[:-7]:
                    start_t = "00:" + start_t
                if len(end_t.split(":")[0]) == 1:
                    end_t = "0" + end_t
                if ":" not in end_t[:-7]:
                    end_t = "00:" + end_t

                start_t = start_t.replace(".", ",")
                end_t = end_t.replace(".", ",")

                srt_lines.append(str(cue_counter))
                cue_counter += 1
                srt_lines.append(f"{start_t} --> {end_t}")

                i += 1
                while i < len(lines) and lines[i].strip():
                    clean_text = re.sub(r"<[^>]+>", "", lines[i].strip())
                    if clean_text:
                        srt_lines.append(clean_text)
                    i += 1
                srt_lines.append("")
        i += 1

    return "\n".join(srt_lines)

def get_unique_filepath(target_path: str) -> str:
    """If file exists, appends number suffix e.g. 'title (1).mp4' to prevent overwriting."""
    if not os.path.exists(target_path):
        return target_path
    base, ext = os.path.splitext(target_path)
    counter = 1
    while os.path.exists(f"{base} ({counter}){ext}"):
        counter += 1
    return f"{base} ({counter}){ext}"

def download_subtitle(sub_url: str, output_srt_path: str) -> bool:
    """Downloads VTT subtitle from URL, converts to SRT format, and saves to output path."""
    try:
        res = requests.get(sub_url, impersonate="chrome120")
        if res.status_code == 200:
            srt_content = convert_vtt_to_srt(res.text)
            unique_path = get_unique_filepath(output_srt_path)
            os.makedirs(os.path.dirname(unique_path), exist_ok=True)
            with open(unique_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return True
    except Exception as e:
        print(f"[Subtitle Download Error]: {e}")
    return False

def inspect_stream_qualities(m3u8_url: str) -> list[str]:
    """Inspects available resolutions from m3u8 playlist via yt-dlp."""
    default_qualities = ["1080p (Best)", "720p", "480p", "360p", "Best Available"]
    try:
        ydl_opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(m3u8_url, download=False)
            formats = info.get("formats", []) if isinstance(info, dict) else []
            extracted = []
            for f in formats:
                h = f.get("height")
                if h and f"{h}p" not in extracted:
                    extracted.append(f"{h}p")
            if extracted:
                return sorted(extracted, key=lambda x: int(x.replace("p", "")), reverse=True)
    except Exception:
        pass
    return default_qualities

def download_media_stream(m3u8_url: str, output_dir: str, title: str, year: str = "N/A", quality: str = "1080p (Best)") -> str | None:
    """Downloads m3u8 video stream into Jellyfin-formatted folder using yt-dlp.

    Returns target video filepath on success, None on error.
    """
    clean_title = "".join([c for c in title if c.isalnum() or c in (" ", "_", "-")]).strip()
    if not clean_title:
        clean_title = "Downloaded_Media"

    folder_name = f"{clean_title} ({year})" if year and year != "N/A" else clean_title
    target_folder = os.path.join(output_dir, folder_name)
    os.makedirs(target_folder, exist_ok=True)

    target_video_base = os.path.join(target_folder, f"{folder_name}.mp4")
    unique_video_path = get_unique_filepath(target_video_base)
    output_template = unique_video_path.replace(".mp4", ".%(ext)s")

    format_spec = "bestvideo+bestaudio/best"
    if "720" in quality:
        format_spec = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    elif "480" in quality:
        format_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]"
    elif "360" in quality:
        format_spec = "bestvideo[height<=360]+bestaudio/best[height<=360]"

    ydl_opts = {
        "format": format_spec,
        "outtmpl": output_template,
        "quiet": False,
        "no_warnings": True,
        "concurrent_fragment_downloads": 4,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m3u8_url])
        return unique_video_path
    except Exception as e:
        print(f"[Download Error]: {e}")
        return None

def format_tv_paths(show_title: str, year: str, season_num: int, episode_num: int, target_dir: str) -> tuple[str, str]:
    """Formats Jellyfin compliant directory path and base filename for a TV episode.

    Returns (season_dir_path, base_filename).
    Folder format: target_dir/<Show Title> (<Year>)/Season <0X>
    Filename format: <Show Title> - S<0X>E<0Y>
    """
    clean_title = "".join([c for c in show_title if c.isalnum() or c in (" ", "_", "-")]).strip()
    if not clean_title:
        clean_title = "Downloaded_Media"

    year_str = str(year).strip() if year is not None else ""
    if year_str and year_str.upper() != "N/A":
        show_folder = f"{clean_title} ({year_str})"
    else:
        show_folder = clean_title

    season_dir_path = os.path.join(target_dir, show_folder, f"Season {season_num:02d}")
    base_filename = f"{clean_title} - S{season_num:02d}E{episode_num:02d}"

    return season_dir_path, base_filename

def _get_lang_code(lang_name: str) -> str:
    l = lang_name.lower().strip()
    if re.search(r"\b(id|ind|indonesia|indonesian)\b", l):
        return "id"
    if re.search(r"\b(en|eng|english)\b", l):
        return "en"
    cleaned = re.sub(r"[^a-z0-9]", "", l)
    return cleaned if cleaned else "sub"

def download_subtitles_batch(subtitles: list[dict], base_video_path: str, sub_mode: str) -> list[str]:
    """Downloads subtitle files for a video stream based on sub_mode preference.

    sub_mode values:
      - "Tanpa Subtitle": no subtitles are downloaded
      - "Indonesia saja": downloads only Indonesian subtitles
      - "English saja": downloads only English subtitles
      - "Semua Subtitle Tersedia": downloads all available subtitles

    Returns a list of saved subtitle filepaths.
    """
    mode_clean = sub_mode.strip().lower()
    if "tanpa" in mode_clean or "none" in mode_clean or mode_clean == "no":
        return []

    base_no_ext = os.path.splitext(base_video_path)[0]

    filtered_subs = []
    for s in subtitles:
        lang = s.get("lang", "")
        lang_code = _get_lang_code(lang)

        if "indonesia" in mode_clean or mode_clean == "id":
            if lang_code == "id":
                filtered_subs.append((s, lang_code))
        elif "english" in mode_clean or mode_clean == "en":
            if lang_code == "en":
                filtered_subs.append((s, lang_code))
        else:
            filtered_subs.append((s, lang_code))

    saved_paths = []
    for s, lang_code in filtered_subs:
        url = s.get("url", "")
        if not url:
            continue
        target_srt_path = f"{base_no_ext}.{lang_code}.srt"
        unique_srt_path = get_unique_filepath(target_srt_path)
        success = download_subtitle(url, unique_srt_path)
        if success:
            saved_paths.append(unique_srt_path)

    return saved_paths

