import sys
import os
import re
import json
from datetime import datetime
import questionary
from rich.console import Console

from src.db_manager import init_db, add_to_cart, get_cart_items, remove_from_cart, clear_cart, format_cart_table
from src.ffmpeg_manager import ensure_ffmpeg, verify_media_file, get_ffmpeg_paths
import src.telegram_manager as tm
from src.config_manager import (
    load_config, save_config, add_target_url, set_active_url, delete_target_url,
    get_download_dir, set_download_dir, set_organize_mode, save_config_key,
)
from src.scraper import fetch_featured_content, search_content
from src.ui import (
    print_header, format_featured_table, print_error, print_success,
    print_download_summary, print_startup_dependency_notice,
    format_backup_table, format_local_delete_table, format_entry_label,
    apply_source_preference,
    format_hybrid_results, format_hybrid_table,
)
from src.telegram_manager import (
    ensure_telethon, create_client, login_flow, is_configured, is_logged_in,
    get_destinations, scan_backups, upload_backup, restore_backup,
    collect_local_entries, mark_backed_entries, matches_query,
    tg_connect, tg_disconnect, parse_destination_input,
    merge_local_entries, collect_folder_entries, test_destinations,
)
from src.video_extractor import extract_video_sources
from src.downloader import (
    download_media_stream,
    download_subtitle,
    get_unique_filepath,
    format_tv_paths,
    download_subtitles_batch,
    _get_lang_code
)
from src.series_extractor import fetch_series_details, extract_episode_sources
from src.download_log import add_entry, get_failed_entries, update_entry, format_log_table, is_already_downloaded, delete_log_entry, clear_all_logs
from src.n_m3u8dl_manager import download_with_re, ensure_binary, get_binary_path
from src.playwright_manager import ensure_playwright, is_chromium_installed

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

def precheck_existing_files_prompt(items: list[dict], batch_state: dict | None = None) -> tuple[str, dict]:
    """Pre-checks if any items in the batch already exist locally.

    Prompts user ONCE at the start if 1 or more items exist.
    Returns ('skip' or 'overwrite', batch_state).
    """
    if batch_state is None:
        batch_state = {}

    prechecked = batch_state.setdefault("prechecked_status", {})
    existing_items = []

    for item in items:
        path = item.get("expected_path")
        sub_choice = item.get("sub_choice")
        if not path:
            continue
        if path not in prechecked:
            if is_already_downloaded(path):
                verify_res = verify_media_file(path, required_sub_mode=sub_choice)
                is_healthy = verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]
                prechecked[path] = {"downloaded": True, "healthy": is_healthy, "verify_res": verify_res}
            else:
                prechecked[path] = {"downloaded": False, "healthy": False, "verify_res": None}

        if prechecked[path]["downloaded"] and prechecked[path]["healthy"]:
            existing_items.append(path)

    if not existing_items:
        batch_state.setdefault("mode", "skip_all")
        return "skip", batch_state

    if batch_state.get("mode"):
        return ("overwrite" if batch_state["mode"] == "overwrite_all" else "skip"), batch_state

    console.print(
        f"\n[bold yellow]⚠️ Terdeteksi {len(existing_items)} dari {len(items)} item sudah ada di disk secara lokal.[/bold yellow]"
    )
    choice = questionary.select(
        "Pilih tindakan untuk item yang sudah ada di disk:",
        choices=[
            "⏭ Skip semua item yang sudah ada (Default)",
            "🔄 Re-download & Timpa semua file lama",
        ],
    ).ask()

    if choice and choice.startswith("🔄 Re-download"):
        batch_state["mode"] = "overwrite_all"
        return "overwrite", batch_state

    batch_state["mode"] = "skip_all"
    return "skip", batch_state


def get_cached_media_status(expected_path: str, required_sub_mode: str = None, batch_state: dict | None = None) -> tuple[bool, dict | None]:
    if batch_state is None:
        batch_state = {}
    prechecked = batch_state.setdefault("prechecked_status", {})
    if expected_path not in prechecked:
        if is_already_downloaded(expected_path):
            verify_res = verify_media_file(expected_path, required_sub_mode=required_sub_mode)
            is_healthy = verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]
            prechecked[expected_path] = {"downloaded": True, "healthy": is_healthy, "verify_res": verify_res}
        else:
            prechecked[expected_path] = {"downloaded": False, "healthy": False, "verify_res": None}
    info = prechecked[expected_path]
    return info["downloaded"], info["verify_res"]


def handle_existing_file_decision(
    title: str,
    expected_path: str,
    batch_state: dict | None = None,
) -> tuple[str, dict]:
    if batch_state is None:
        batch_state = {}

    mode = batch_state.get("mode")
    if mode == "skip_all":
        return "skip", batch_state
    if mode == "overwrite_all":
        return "overwrite", batch_state

    console.print(f"\n[bold yellow]⚠️ File '{title}' sudah ada secara lokal dan sehat.[/bold yellow]")
    choice = questionary.select(
        "Pilih tindakan untuk file ini:",
        choices=[
            "⏭ Skip (Lewati file ini)",
            "🔄 Re-download / Timpa (Download ulang & timpa file ini)",
            "⏭ Skip Semua (Lewati semua file yang sudah ada)",
            "🔄 Re-download / Timpa Semua (Download ulang & timpa semua file yang sudah ada)",
        ],
    ).ask()

    if not choice or choice.startswith("⏭ Skip (Lewati"):
        return "skip", batch_state
    elif choice.startswith("🔄 Re-download / Timpa (Download"):
        return "overwrite", batch_state
    elif choice.startswith("⏭ Skip Semua"):
        batch_state["mode"] = "skip_all"
        return "skip", batch_state
    elif choice.startswith("🔄 Re-download / Timpa Semua"):
        batch_state["mode"] = "overwrite_all"
        return "overwrite", batch_state

    return "skip", batch_state


def process_download_item(selected_item: dict, active_url: str, config: dict, summary: dict, preset_sub_choice: str = None, preset_download_dir: str = None, batch_state: dict = None) -> None:
    raw_title = selected_item.get("title", "Unknown")
    item_url = selected_item.get("url", "")

    # Extract clean title and year
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", raw_title)
    if year_match:
        year = year_match.group(1)
        clean_title = re.sub(r"\b(19\d\d|20\d\d)\b", "", raw_title).strip()
    else:
        url_year = re.search(r"-?(19\d\d|20\d\d)\b", item_url)
        year = url_year.group(1) if url_year else "N/A"
        clean_title = raw_title

    is_series = selected_item.get("type") == "TV Series" or "/series/" in item_url

    if is_series:
        console.print(f"\n[bold cyan]Mengambil detail TV Series dari {item_url}...[/bold cyan]")
        series_info = fetch_series_details(item_url)
        seasons = series_info.get("seasons", [])
        if not seasons:
            print_error(f"Gagal menemukan season/episode di {item_url}")
            return

        if series_info.get("title"):
            clean_title = series_info["title"]
        if series_info.get("year") and series_info["year"] != "N/A":
            year = series_info["year"]

        # --- Step 1: Pilih Season ---
        season_choices = [f"Season {s['season_num']}" for s in seasons] + ["⬅ Kembali"]
        while True:
            selected_season_str = questionary.select(
                "Pilih Season:",
                choices=season_choices
            ).ask()

            if selected_season_str is None or selected_season_str == "⬅ Kembali":
                return

            selected_season = next((s for s in seasons if f"Season {s['season_num']}" == selected_season_str), None)
            if selected_season and selected_season.get("episodes"):
                break
            print_error("Season tidak valid atau tidak memiliki episode. Silakan pilih lagi.")

        season_num = selected_season["season_num"]
        episodes = selected_season["episodes"]

        # --- Step 2: Pilih Episode ---
        ep_choices = [f"Episode {ep['episode_num']}: {ep['title']}" for ep in episodes]
        while True:
            selected_ep_labels = questionary.checkbox(
                "Pilih Episode yang ingin di-download (SPACE untuk pilih, ENTER untuk lanjut):",
                choices=ep_choices
            ).ask()

            if selected_ep_labels is None:
                return
            if len(selected_ep_labels) == 0:
                console.print("[yellow]Belum ada episode yang dipilih. Pilih minimal 1 episode.[/yellow]")
                continue
            break

        ep_map = {f"Episode {ep['episode_num']}: {ep['title']}": ep for ep in episodes}
        selected_episodes = [ep_map[label] for label in selected_ep_labels if label in ep_map]

        # --- Step 3: Lokasi simpan ---
        if preset_download_dir:
            target_dir = preset_download_dir
        else:
            default_dir = get_download_dir(config, media_type="series")
            while True:
                custom_dir = questionary.text(
                    f"Lokasi simpan (Tekan ENTER untuk default: {default_dir}):",
                    default=default_dir
                ).ask()
                if custom_dir is None:
                    return
                target_dir = custom_dir.strip() if custom_dir else default_dir
                set_download_dir(config, target_dir, media_type="series")
                break

        # --- Step 4: Pilih Subtitle ---
        if preset_sub_choice:
            selected_sub_choice = preset_sub_choice
        else:
            sub_choices = ["Semua Subtitle Tersedia", "Indonesia saja", "English saja", "Tanpa Subtitle", "⬅ Kembali"]
            while True:
                selected_sub_choice = questionary.select(
                    "Pilih Subtitle:",
                    choices=sub_choices
                ).ask()

                if selected_sub_choice is None or selected_sub_choice == "⬅ Kembali":
                    return
                break

        # --- Pre-check existing local files at the start ---
        if batch_state is None:
            batch_state = {}
        ep_items_check = []
        for ep in selected_episodes:
            s_dir, b_name = format_tv_paths(clean_title, year, season_num, ep["episode_num"], target_dir)
            ep_path = os.path.join(s_dir, f"{b_name}.mp4")
            ep_items_check.append({"expected_path": ep_path, "sub_choice": selected_sub_choice})
        precheck_existing_files_prompt(ep_items_check, batch_state=batch_state)

        for ep in selected_episodes:
            console.print(f"\n[bold cyan]Memproses Episode {ep['episode_num']}: {ep['title']}...[/bold cyan]")
            season_dir, base_filename = format_tv_paths(clean_title, year, season_num, ep["episode_num"], target_dir)
            expected_path = os.path.join(season_dir, f"{base_filename}.mp4")
            ep_title = f"{clean_title} S{season_num:02d}E{ep['episode_num']:02d}"

            summary["total_items"] += 1

            try:
                # Instant local check
                is_dl, verify_res = get_cached_media_status(expected_path, required_sub_mode=selected_sub_choice, batch_state=batch_state)
                if is_dl:
                    if verify_res and verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]:
                        action = "overwrite" if batch_state.get("mode") == "overwrite_all" else "skip"
                        if action == "skip":
                            console.print(f"[yellow]⏭ Episode {ep['episode_num']} sudah ada dan sehat secara lokal, di-skip.[/yellow]")
                            add_entry(
                                title=ep_title,
                                media_type="episode",
                                season=season_num,
                                episode=ep["episode_num"],
                                status="skipped",
                                m3u8_url="",
                                output_path=expected_path,
                                page_url=item_url
                            )
                            summary["video_skipped"] += 1
                            summary["items"].append({
                                "title": ep_title,
                                "video_status": "SKIPPED",
                                "video_error": None,
                                "subtitles": []
                            })
                            continue
                        else:
                            console.print(f"[bold cyan]🔄 Re-download / Overwrite dipilih untuk {ep_title}. Download ulang...[/bold cyan]")
                    else:
                        v_status = verify_res["video_status"] if verify_res else "CORRUPT"
                        console.print(f"[bold yellow]⚠️ Episode {ep['episode_num']} terdeteksi rusak/kurang subtitle (Status: {v_status}). Re-downloading...[/bold yellow]")

                sources = extract_episode_sources(ep["media_id"], item_url)
                m3u8_urls = sources.get("m3u8_urls", [])
                subtitles = sources.get("subtitles", [])

                if not m3u8_urls:
                    print_error(f"Gagal menemukan link video m3u8 untuk Episode {ep['episode_num']}")
                    add_entry(
                        title=ep_title,
                        media_type="episode",
                        season=season_num,
                        episode=ep["episode_num"],
                        status="failed",
                        m3u8_url="",
                        output_path=expected_path,
                        error="No m3u8 url found",
                        page_url=item_url
                    )
                    summary["video_failed"] += 1
                    summary["items"].append({
                        "title": ep_title,
                        "video_status": "FAILED",
                        "video_error": "No m3u8 url found",
                        "subtitles": []
                    })
                    continue

                m3u8_url = m3u8_urls[0]

                console.print(f"[bold green]Memulai download Episode {ep['episode_num']} ke {season_dir}...[/bold green]")
                video_path = download_media_stream(m3u8_url, season_dir, base_filename, "N/A", "Best Available", create_subfolder=False)

                if video_path and os.path.exists(video_path):
                    print_success(f"Berhasil mendownload Episode {ep['episode_num']}: {video_path}")
                    add_entry(
                        title=ep_title,
                        media_type="episode",
                        season=season_num,
                        episode=ep["episode_num"],
                        status="success",
                        m3u8_url=m3u8_url,
                        output_path=video_path,
                        page_url=item_url
                    )
                    summary["video_success"] += 1
                    sub_results = []
                    if selected_sub_choice != "Tanpa Subtitle":
                        sub_paths = download_subtitles_batch(subtitles, video_path, selected_sub_choice)
                        for sp in sub_paths:
                            print_success(f"Berhasil menyimpan Subtitle: {sp}")

                        mode_clean = selected_sub_choice.strip().lower()
                        target_subs = []
                        for s in subtitles:
                            lang = s.get("lang", "")
                            l_code = _get_lang_code(lang)
                            if "indonesia" in mode_clean or mode_clean == "id":
                                if l_code == "id":
                                    target_subs.append((s, l_code))
                            elif "english" in mode_clean or mode_clean == "en":
                                if l_code == "en":
                                    target_subs.append((s, l_code))
                            else:
                                target_subs.append((s, l_code))

                        for idx_sub, (s, l_code) in enumerate(target_subs):
                            if idx_sub < len(sub_paths):
                                summary["sub_success"] += 1
                                sub_results.append({"lang": l_code, "status": "SUCCESS", "error": None})
                            else:
                                summary["sub_failed"] += 1
                                sub_results.append({"lang": l_code, "status": "FAILED", "error": "Download failed"})

                    summary["items"].append({
                        "title": ep_title,
                        "video_status": "SUCCESS",
                        "video_error": None,
                        "subtitles": sub_results
                    })
                    maybe_auto_backup(video_path, config, ep_title, year, "episode", season=season_num, episode=ep["episode_num"])
                else:
                    print_error(f"Gagal mendownload video untuk Episode {ep['episode_num']}")
                    add_entry(
                        title=ep_title,
                        media_type="episode",
                        season=season_num,
                        episode=ep["episode_num"],
                        status="failed",
                        m3u8_url=m3u8_url,
                        output_path=expected_path,
                        error="Download failed",
                        page_url=item_url
                    )
                    summary["video_failed"] += 1
                    summary["items"].append({
                        "title": ep_title,
                        "video_status": "FAILED",
                        "video_error": "Download failed",
                        "subtitles": []
                    })
            except Exception as e:
                print_error(f"Error saat memproses Episode {ep['episode_num']}: {e}")
                add_entry(
                    title=ep_title,
                    media_type="episode",
                    season=season_num,
                    episode=ep["episode_num"],
                    status="failed",
                    m3u8_url="",
                    output_path=expected_path,
                    error=str(e),
                    page_url=item_url
                )
                summary["video_failed"] += 1
                summary["items"].append({
                    "title": ep_title,
                    "video_status": "FAILED",
                    "video_error": str(e),
                    "subtitles": []
                })
        return

    console.print(f"\n[bold cyan]Memproses: {clean_title} ({year})...[/bold cyan]")
    summary["total_items"] += 1

    # --- Pilih Subtitle ---
    if preset_sub_choice:
        selected_sub_choice = preset_sub_choice
    else:
        sub_choices = ["Indonesia saja", "English saja", "Semua Subtitle Tersedia", "Tanpa Subtitle", "⬅ Kembali"]
        while True:
            selected_sub_choice = questionary.select(
                "Pilih Subtitle:",
                choices=sub_choices
            ).ask()

            if selected_sub_choice is None or selected_sub_choice == "⬅ Kembali":
                return
            break

    # --- Download Path ---
    if preset_download_dir:
        target_dir = preset_download_dir
    else:
        default_dir = get_download_dir(config, media_type="movie")
        while True:
            custom_dir = questionary.text(
                f"Lokasi simpan (Tekan ENTER untuk default: {default_dir}):",
                default=default_dir
            ).ask()
            if custom_dir is None:
                return
            target_dir = custom_dir.strip() if custom_dir else default_dir
            set_download_dir(config, target_dir, media_type="movie")
            break

    folder_name = f"{clean_title} ({year})" if year and year != "N/A" else clean_title
    expected_path = os.path.join(target_dir, folder_name, f"{folder_name}.mp4")

    if batch_state is None:
        batch_state = {}
    precheck_existing_files_prompt([{"expected_path": expected_path, "sub_choice": selected_sub_choice}], batch_state=batch_state)

    # Instant local check
    is_dl, verify_res = get_cached_media_status(expected_path, required_sub_mode=selected_sub_choice, batch_state=batch_state)
    if is_dl:
        if verify_res and verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]:
            action = "overwrite" if batch_state.get("mode") == "overwrite_all" else "skip"
            if action == "skip":
                console.print(f"[yellow]⏭ {clean_title} sudah ada dan sehat secara lokal, di-skip.[/yellow]")
                add_entry(
                    title=clean_title,
                    media_type="movie",
                    season=None,
                    episode=None,
                    status="skipped",
                    m3u8_url="",
                    output_path=expected_path,
                    page_url=selected_item["url"]
                )
                summary["video_skipped"] += 1
                summary["items"].append({
                    "title": clean_title,
                    "video_status": "SKIPPED",
                    "video_error": None,
                    "subtitles": []
                })
                return
            else:
                console.print(f"[bold cyan]🔄 Re-download / Overwrite dipilih untuk {clean_title}. Download ulang...[/bold cyan]")
        else:
            v_status = verify_res["video_status"] if verify_res else "CORRUPT"
            console.print(f"[bold yellow]⚠️ {clean_title} terdeteksi rusak/kurang subtitle (Status: {v_status}). Re-downloading...[/bold yellow]")

    # --- Extract Video Sources ---
    console.print("[bold yellow]Mengambil sumber video & subtitle...[/bold yellow]")
    sources = extract_video_sources(selected_item["url"])
    m3u8_urls = sources.get("m3u8_urls", [])
    subtitles = sources.get("subtitles", [])

    if not m3u8_urls:
        print_error(f"Gagal menemukan link video m3u8 di {selected_item['url']}")
        add_entry(
            title=clean_title,
            media_type="movie",
            season=None,
            episode=None,
            status="failed",
            m3u8_url="",
            output_path=expected_path,
            error="No m3u8 url found",
            page_url=selected_item["url"]
        )
        summary["video_failed"] += 1
        summary["items"].append({
            "title": clean_title,
            "video_status": "FAILED",
            "video_error": "No m3u8 url found",
            "subtitles": []
        })
        return

    m3u8_url = m3u8_urls[0]

    # --- Trigger Download ---
    console.print(f"[bold green]Memulai download {clean_title} ke {target_dir}...[/bold green]")
    video_path = download_media_stream(m3u8_url, target_dir, clean_title, year, "Best Available")

    sub_results = []
    if video_path and os.path.exists(video_path):
        print_success(f"Berhasil mendownload Video: {video_path}")
        add_entry(
            title=clean_title,
            media_type="movie",
            season=None,
            episode=None,
            status="success",
            m3u8_url=m3u8_url,
            output_path=video_path,
            page_url=selected_item["url"]
        )
        summary["video_success"] += 1

        # Download Subtitle if selected
        if selected_sub_choice and selected_sub_choice != "Tanpa Subtitle":
            if " - http" in selected_sub_choice:
                # Specific subtitle mode
                matched_sub = next((s for s in subtitles if f"{s['lang']} - {s['url']}" == selected_sub_choice), None)
                if matched_sub:
                    sub_lang = _get_lang_code(matched_sub.get("lang", ""))
                    base_name = os.path.splitext(video_path)[0]
                    target_srt_path = f"{base_name}.{sub_lang}.srt"

                    console.print(f"[bold yellow]Mengunduh dan mengonversi subtitle (.vtt -> .srt)...[/bold yellow]")
                    sub_success = download_subtitle(matched_sub["url"], target_srt_path)
                    if sub_success:
                        print_success(f"Berhasil menyimpan Subtitle SRT: {target_srt_path}")
                        summary["sub_success"] += 1
                        sub_results.append({"lang": sub_lang, "status": "SUCCESS", "error": None})
                    else:
                        print_error("Gagal mengunduh subtitle SRT.")
                        summary["sub_failed"] += 1
                        sub_results.append({"lang": sub_lang, "status": "FAILED", "error": "Download failed"})
            else:
                # General preference mode
                sub_paths = download_subtitles_batch(subtitles, video_path, selected_sub_choice)
                for sp in sub_paths:
                    print_success(f"Berhasil menyimpan Subtitle: {sp}")

                mode_clean = selected_sub_choice.strip().lower()
                target_subs = []
                for s in subtitles:
                    lang = s.get("lang", "")
                    l_code = _get_lang_code(lang)
                    if "indonesia" in mode_clean or mode_clean == "id":
                        if l_code == "id":
                            target_subs.append((s, l_code))
                    elif "english" in mode_clean or mode_clean == "en":
                        if l_code == "en":
                            target_subs.append((s, l_code))
                    else:
                        target_subs.append((s, l_code))

                for idx_sub, (s, l_code) in enumerate(target_subs):
                    if idx_sub < len(sub_paths):
                        summary["sub_success"] += 1
                        sub_results.append({"lang": l_code, "status": "SUCCESS", "error": None})
                    else:
                        summary["sub_failed"] += 1
                        sub_results.append({"lang": l_code, "status": "FAILED", "error": "Download failed"})

        maybe_auto_backup(video_path, config, clean_title, year, "movie")
        summary["items"].append({
            "title": clean_title,
            "video_status": "SUCCESS",
            "video_error": None,
            "subtitles": sub_results
        })
    else:
        print_error(f"Gagal mendownload video {clean_title}")
        add_entry(
            title=clean_title,
            media_type="movie",
            season=None,
            episode=None,
            status="failed",
            m3u8_url=m3u8_url,
            output_path=expected_path,
            error="Download failed",
            page_url=selected_item["url"]
        )
        summary["video_failed"] += 1
        summary["items"].append({
            "title": clean_title,
            "video_status": "FAILED",
            "video_error": "Download failed",
            "subtitles": []
        })


def handle_item_download(items: list[dict], active_url: str, config: dict) -> None:
    if not items:
        console.print("[yellow]Tidak ada item untuk di-download.[/yellow]")
        return

    summary = {
        "total_items": 0,
        "video_success": 0,
        "video_failed": 0,
        "video_skipped": 0,
        "sub_success": 0,
        "sub_failed": 0,
        "items": []
    }

    while True:
        choice_num = questionary.text(
            f"Masukkan nomor item yang ingin di-download (1-{len(items)}):",
            validate=lambda val: val.isdigit() and 1 <= int(val) <= len(items)
        ).ask()

        if choice_num is None:
            return
        if not choice_num:
            console.print("[yellow]Masukkan nomor yang valid.[/yellow]")
            continue
        break

    selected_item = items[int(choice_num) - 1]
    process_download_item(selected_item, active_url, config, summary)
    print_download_summary(summary)
    questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali...").ask()


def handle_add_to_cart(items: list[dict]) -> None:
    if not items:
        console.print("[yellow]Tidak ada item untuk dimasukkan ke keranjang.[/yellow]")
        return

    choices = []
    for idx, item in enumerate(items):
        title = item.get("title", "Unknown")
        year = item.get("year")
        media_type = item.get("type", "Movie")
        year_str = f" ({year})" if year and year != "N/A" else ""
        choices.append(f"{idx+1}. [{media_type}] {title}{year_str}")

    selected_labels = questionary.checkbox(
        "Pilih item yang ingin ditambahkan ke Keranjang (SPACE untuk pilih, ENTER untuk lanjut):",
        choices=choices
    ).ask()

    if not selected_labels:
        console.print("[yellow]Tidak ada item yang dipilih.[/yellow]")
        return

    success_count = 0
    duplicate_count = 0

    for label in selected_labels:
        idx = int(label.split(".")[0]) - 1
        item = items[idx]
        url = item.get("url", "")
        title = item.get("title", "Unknown")
        media_type = item.get("type", "Movie")

        if add_to_cart(url, title, media_type):
            success_count += 1
            console.print(f"[green]✓ Berhasil menambahkan: {title}[/green]")
        else:
            duplicate_count += 1
            console.print(f"[yellow]⚠ Sudah ada di keranjang: {title}[/yellow]")

    console.print(f"\nHasil: {success_count} item berhasil ditambahkan, {duplicate_count} duplikat di-skip.\n")
    questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali...").ask()


def handle_cart(active_url: str, config: dict) -> None:
    while True:
        cart_items = get_cart_items()
        if not cart_items:
            console.print("\n[bold yellow]🛒 Keranjang Download Anda kosong.[/bold yellow]\n")
            questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali ke menu...").ask()
            return

        console.print("\n[bold cyan]🛒 Daftar Item di Keranjang Download:[/bold cyan]")
        table = format_cart_table(cart_items)
        console.print(table)

        action = questionary.select(
            "Pilih Aksi:",
            choices=[
                "📥 Download Semua di Keranjang",
                "❌ Hapus Item dari Keranjang",
                "🗑️ Kosongkan Keranjang",
                "↩️ Kembali ke Menu Utama"
            ]
        ).ask()

        if action is None or action == "↩️ Kembali ke Menu Utama":
            return
        elif action == "📥 Download Semua di Keranjang":
            # 1. Ask Subtitle preference once for the entire batch
            sub_choices = ["Indonesia saja", "English saja", "Semua Subtitle Tersedia", "Tanpa Subtitle", "⬅ Kembali"]
            preset_sub_choice = questionary.select(
                "Pilih Subtitle untuk Semua Item di Keranjang:",
                choices=sub_choices
            ).ask()
            if preset_sub_choice is None or preset_sub_choice == "⬅ Kembali":
                continue

            # 2. Ask Download path once for the entire batch
            default_movie_dir = get_download_dir(config, media_type="movie")
            default_series_dir = get_download_dir(config, media_type="series")
            console.print(f"\n[bold cyan]Folder default saat ini:[/bold cyan]")
            console.print(f"  - Movies: {default_movie_dir}")
            console.print(f"  - TV Series: {default_series_dir}")
            preset_dir_input = questionary.text(
                "Lokasi simpan untuk semua item di keranjang (Tekan ENTER untuk menggunakan folder default):"
            ).ask()

            if preset_dir_input is None:
                continue

            preset_dir = preset_dir_input.strip() if preset_dir_input.strip() else None

            summary = {
                "total_items": 0,
                "video_success": 0,
                "video_failed": 0,
                "video_skipped": 0,
                "sub_success": 0,
                "sub_failed": 0,
                "items": []
            }
            batch_state = {}
            # Download item one by one and remove on success
            for idx, item in enumerate(cart_items):
                console.print(f"\n[bold cyan]=== Mengunduh Item Keranjang {idx+1}/{len(cart_items)}: {item['title']} ===[/bold cyan]")

                # Check media type to resolve the target default dir if no preset_dir was entered
                item_preset_dir = preset_dir
                if not item_preset_dir:
                    is_series = item.get("type") == "TV Series" or "/series/" in item.get("url", "")
                    if is_series:
                        item_preset_dir = default_series_dir
                    else:
                        item_preset_dir = default_movie_dir

                process_download_item(item, active_url, config, summary, preset_sub_choice=preset_sub_choice, preset_download_dir=item_preset_dir, batch_state=batch_state)

                # Check if this item had any failures in this step
                failures = [i for i in summary["items"] if i["video_status"] == "FAILED" and item["title"] in i["title"]]
                if not failures:
                    remove_from_cart(item["url"])
                    console.print(f"[green]✓ {item['title']} dihapus dari keranjang karena berhasil/skipped.[/green]")
                else:
                    console.print(f"[yellow]⚠ {item['title']} tetap di keranjang karena ada download yang gagal.[/yellow]")

            print_download_summary(summary)
            questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali...").ask()

        elif action == "❌ Hapus Item dari Keranjang":
            choices = [f"{idx+1}. {item['title']}" for idx, item in enumerate(cart_items)] + ["⬅ Kembali"]
            to_remove = questionary.select(
                "Pilih item yang ingin dihapus:",
                choices=choices
            ).ask()
            if to_remove and to_remove != "⬅ Kembali":
                idx = int(to_remove.split(".")[0]) - 1
                item = cart_items[idx]
                remove_from_cart(item["url"])
                print_success(f"Berhasil menghapus {item['title']} dari keranjang.")

        elif action == "🗑️ Kosongkan Keranjang":
            confirm = questionary.confirm("Apakah Anda yakin ingin mengosongkan seluruh keranjang?").ask()
            if confirm:
                clear_cart()
                print_success("Keranjang berhasil dikosongkan.")


def handle_retry_failed(active_url: str, config: dict) -> None:
    while True:
        failed = get_failed_entries()
        if not failed:
            console.print("[yellow]Tidak ada download yang gagal untuk di-retry.[/yellow]")
            questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali ke menu...").ask()
            return

        table = format_log_table(failed)
        console.print(table)

        action = questionary.select(
            "Pilih Aksi:",
            choices=[
                "🔄 Retry Semua yang Gagal",
                "❌ Hapus Log Tertentu",
                "🗑️ Kosongkan Seluruh Log",
                "↩️ Kembali"
            ]
        ).ask()

        if action is None or action == "↩️ Kembali":
            return
        elif action == "❌ Hapus Log Tertentu":
            choices = [f"{idx+1}. {item['title']}" for idx, item in enumerate(failed)] + ["⬅ Kembali"]
            to_remove = questionary.select(
                "Pilih log yang ingin dihapus:",
                choices=choices
            ).ask()
            if to_remove and to_remove != "⬅ Kembali":
                idx = int(to_remove.split(".")[0]) - 1
                item = failed[idx]
                delete_log_entry(item["id"])
                print_success(f"Berhasil menghapus log {item['title']}.")
        elif action == "🗑️ Kosongkan Seluruh Log":
            confirm = questionary.confirm("Apakah Anda yakin ingin mengosongkan seluruh log gagal?").ask()
            if confirm:
                clear_all_logs()
                print_success("Seluruh log gagal berhasil dikosongkan.")
        elif action == "🔄 Retry Semua yang Gagal":
            summary = {
                "total_items": len(failed),
                "video_success": 0,
                "video_failed": 0,
                "video_skipped": 0,
                "sub_success": 0,
                "sub_failed": 0,
                "items": []
            }

            for entry in failed:
                console.print(f"\n[bold cyan]Retry: {entry['title']}...[/bold cyan]")
                try:
                    m3u8_url = entry["m3u8_url"]
                    output_path = entry["output_path"]
                    output_dir = os.path.dirname(output_path)
                    base_name = os.path.splitext(os.path.basename(output_path))[0]

                    # Re-scrape if page_url exists
                    page_url = entry.get("page_url")
                    if page_url:
                        console.print(f"[bold yellow]Mengambil token m3u8 segar dari {page_url}...[/bold yellow]")
                        try:
                            if entry.get("media_type") == "movie":
                                sources = extract_video_sources(page_url)
                                fresh_urls = sources.get("m3u8_urls", [])
                                if fresh_urls:
                                    m3u8_url = fresh_urls[0]
                                    console.print("[green]Token m3u8 berhasil diperbarui.[/green]")
                                    update_entry(entry["id"], {"m3u8_url": m3u8_url})
                                else:
                                    console.print("[yellow]Gagal mengambil token segar, mencoba URL lama...[/yellow]")
                            elif entry.get("media_type") == "episode":
                                series_info = fetch_series_details(page_url)
                                seasons = series_info.get("seasons", [])
                                matched_ep = None
                                for s in seasons:
                                    if s.get("season_num") == entry.get("season"):
                                        for ep in s.get("episodes", []):
                                            if ep.get("episode_num") == entry.get("episode"):
                                                matched_ep = ep
                                                break
                                        if matched_ep:
                                            break
                                if matched_ep:
                                    sources = extract_episode_sources(matched_ep["media_id"], page_url)
                                    fresh_urls = sources.get("m3u8_urls", [])
                                    if fresh_urls:
                                        m3u8_url = fresh_urls[0]
                                        console.print("[green]Token m3u8 berhasil diperbarui.[/green]")
                                        update_entry(entry["id"], {"m3u8_url": m3u8_url})
                                    else:
                                        console.print("[yellow]Gagal mengambil token segar, mencoba URL lama...[/yellow]")
                                else:
                                    console.print("[yellow]Episode tidak ditemukan di detail halaman, mencoba URL lama...[/yellow]")
                        except Exception as e:
                            console.print(f"[yellow]Gagal mengambil token segar ({e}), mencoba URL lama...[/yellow]")

                    success = download_with_re(m3u8_url, output_dir, base_name)
                    if success:
                        update_entry(entry["id"], {"status": "success", "error": None})
                        print_success(f"Berhasil: {output_path}")
                        summary["video_success"] += 1
                        summary["items"].append({
                            "title": entry["title"],
                            "video_status": "SUCCESS",
                            "video_error": None,
                            "subtitles": []
                        })
                    else:
                        print_error(f"Masih gagal: {entry['title']}")
                        summary["video_failed"] += 1
                        summary["items"].append({
                            "title": entry["title"],
                            "video_status": "FAILED",
                            "video_error": "Download failed",
                            "subtitles": []
                        })
                except Exception as e:
                    print_error(f"Error retry {entry['title']}: {e}")
                    summary["video_failed"] += 1
                    summary["items"].append({
                        "title": entry["title"],
                        "video_status": "FAILED",
                        "video_error": str(e),
                        "subtitles": []
                    })

            print_download_summary(summary)
            questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali...").ask()
            break


def handle_featured(active_url: str) -> None:
    config = load_config()
    try:
        with console.status("[bold cyan]🔥 Fetching featured content... / Mengambil konten populer...[/bold cyan]", spinner="dots"):
            items = fetch_featured_content(active_url)
        if not items:
            console.print("[yellow]No featured content found or website structure differed.[/yellow]")
        else:
            table = format_featured_table(items)
            console.print(table)

            action = questionary.select(
                "Pilih Aksi:",
                choices=[
                    "📥 Download Film/Series (Single-select)",
                    "🛒 Tambahkan ke Keranjang Download (Multi-select)",
                    "↩️ Kembali ke Menu Utama"
                ]
            ).ask()

            if action == "📥 Download Film/Series (Single-select)":
                handle_item_download(items, active_url, config)
            elif action == "🛒 Tambahkan ke Keranjang Download (Multi-select)":
                handle_add_to_cart(items)
    except Exception as e:
        print_error(str(e))

    questionary.press_any_key_to_continue(message="Tekan sebarang tombol untuk kembali ke menu...").ask()

def handle_select_active() -> None:
    config = load_config()
    urls = [item["url"] for item in config.get("target_urls", [])]
    if not urls:
        print_error("Belum ada URL tersimpan.")
        return

    chosen = questionary.select(
        "Pilih Active Target URL:",
        choices=urls
    ).ask()

    if chosen:
        set_active_url(chosen)
        print_success(f"Active URL diubah ke: {chosen}")

def handle_add_url() -> None:
    url = questionary.text("Masukkan Target URL baru (misal: https://z2.idlixku.com/):").ask()
    if url:
        name = questionary.text("Label/Nama untuk URL ini (opsional):").ask()
        add_target_url(url, name)
        print_success("URL berhasil ditambahkan!")

def handle_manage_urls() -> None:
    config = load_config()
    target_urls = config.get("target_urls", [])
    choices = [f"{item['name']} ({item['url']})" for item in target_urls] + ["⬅ Kembali"]

    selected = questionary.select("Pilih URL untuk di-manage:", choices=choices).ask()
    if selected and selected != "⬅ Kembali":
        target_item = next(
            (item for item in target_urls if f"{item['name']} ({item['url']})" == selected),
            None
        )
        if target_item:
            action = questionary.select(
                f"Aksi untuk {target_item['name']}:",
                choices=["Set as Active", "Hapus URL", "Batal"]
            ).ask()

            if action == "Set as Active":
                set_active_url(target_item["url"])
                print_success(f"Active URL diubah ke: {target_item['url']}")
            elif action == "Hapus URL":
                delete_target_url(target_item["url"])
                print_success(f"URL {target_item['url']} berhasil dihapus!")

def handle_settings() -> None:
    while True:
        config = load_config()
        mode = config.get("organize_mode", "separate")
        movies_dir = get_download_dir(config, "movie")
        series_dir = get_download_dir(config, "series")
        combined_dir = config.get("combined_dir", get_download_dir(config, "movie"))

        mode_str = "Dipisah (Separate - Movies & TV Series)" if mode == "separate" else "Digabung (Combined)"
        console.print(f"\n[bold cyan]⚙️  PENGATURAN PENYIMPANAN[/bold cyan]")
        console.print(f"Mode Organisasi   : [yellow]{mode_str}[/yellow]")
        if mode == "separate":
            console.print(f"Folder Movies     : [green]{movies_dir}[/green]")
            console.print(f"Folder TV Series  : [green]{series_dir}[/green]")
        else:
            console.print(f"Folder Combined   : [green]{combined_dir}[/green]")

        choices = [
            "🔀 Ubah Mode Organisasi (Dipisah / Digabung)",
            "🎬 Ubah Default Folder Movies",
            "📺 Ubah Default Folder TV Series",
            "📦 Ubah Default Folder Combined",
            "⬅ Kembali ke Menu Utama"
        ]

        action = questionary.select("Pilih Pengaturan:", choices=choices).ask()
        if not action or action == "⬅ Kembali ke Menu Utama":
            break

        if action == "🔀 Ubah Mode Organisasi (Dipisah / Digabung)":
            new_mode = questionary.select(
                "Pilih Mode Organisasi Folder:",
                choices=[
                    "separate - Dipisah per jenis (Movies/ & TV Series/)",
                    "combined - Digabung dalam 1 folder root"
                ]
            ).ask()
            if new_mode:
                mode_key = "separate" if "separate" in new_mode else "combined"
                set_organize_mode(config, mode_key)
                print_success(f"Mode organisasi diubah ke: {mode_key}")
        elif action == "🎬 Ubah Default Folder Movies":
            new_dir = questionary.text("Masukkan Path Folder Movies:", default=movies_dir).ask()
            if new_dir:
                config["movies_dir"] = new_dir.strip()
                save_config(config)
                print_success(f"Default Folder Movies diubah ke: {new_dir.strip()}")
        elif action == "📺 Ubah Default Folder TV Series":
            new_dir = questionary.text("Masukkan Path Folder TV Series:", default=series_dir).ask()
            if new_dir:
                config["series_dir"] = new_dir.strip()
                save_config(config)
                print_success(f"Default Folder TV Series diubah ke: {new_dir.strip()}")
        elif action == "📦 Ubah Default Folder Combined":
            new_dir = questionary.text("Masukkan Path Folder Combined:", default=combined_dir).ask()
            if new_dir:
                config["combined_dir"] = new_dir.strip()
                config["download_dir"] = new_dir.strip()
                save_config(config)
                print_success(f"Default Folder Combined diubah ke: {new_dir.strip()}")

def handle_search(active_url: str, config: dict) -> None:
    while True:
        query = questionary.text("Masukkan judul film/series yang dicari:").ask()
        if not query or not query.strip():
            return

        clean_query = query.strip()
        with console.status(f"[bold cyan]🔍 Mencari \"{clean_query}\" di IDLIX...[/bold cyan]", spinner="dots"):
            idlix_items = search_content(active_url, clean_query)

        tg_items = []
        telegram_skip_reason = None
        try:
            tg_items = [
                it for it in scan_with_spinner(config)
                if matches_query(it.get("title", ""), clean_query)
            ]
        except Exception as exc:
            telegram_skip_reason = type(exc).__name__

        for item in tg_items:
            item["__source__"] = "telegram"

        if telegram_skip_reason:
            console.print(f"[dim]ℹ️ Pencarian backup Telegram dilewati ({telegram_skip_reason}).[/dim]")

        rows = format_hybrid_results(idlix_items, tg_items)
        rows = apply_source_preference(rows, config.get("source_preference", "telegram"))
        if not rows:
            console.print(f"[yellow]Tidak ada hasil ditemukan untuk \"{clean_query}\".[/yellow]")
            continue

        console.print(format_hybrid_table(rows))

        if len(rows) == 1:
            chosen = rows[0]
            if chosen.get("__source__") == "telegram":
                if not _confirm_or_proceed(
                    f"Hanya 1 hasil: restore '{chosen['title']}' dari Telegram sekarang?"
                ):
                    continue
                try:
                    out_path = _restore_from_telegram(config, chosen)
                    print_success(f"Restore selesai: {out_path}")
                    restored_total = 1
                except Exception as exc:
                    print_error(f"Restore gagal: {type(exc).__name__}: {exc}")
                    _log_exception("Restore gagal", exc)
                    restored_total = 0
            else:
                summary_auto = {
                    "total_items": 0, "video_success": 0, "video_failed": 0,
                    "video_skipped": 0, "sub_success": 0, "sub_failed": 0, "items": [],
                }
                process_download_item(chosen, active_url, config, summary_auto)
                print_download_summary(summary_auto)
            _pause()
            return

        raw = questionary.text(
            f"Pilih nomor item (bisa lebih dari satu, contoh 1,3 — kosongkan untuk kembali):"
        ).ask()
        if not raw or not raw.strip():
            console.print("[yellow]Pilihan dibatalkan.[/yellow]")
            return
        indices = []
        for part in re.split(r"[,\s]+", raw.strip()):
            if not part.isdecimal() or not (1 <= int(part) <= len(rows)):
                console.print(f"[yellow]Nomor '{part}' tidak valid — dilewati.[/yellow]")
                continue
            idx = int(part) - 1
            if idx not in indices:
                indices.append(idx)
        if not indices:
            return
        summary = {
            "total_items": 0, "video_success": 0, "video_failed": 0,
            "video_skipped": 0, "sub_success": 0, "sub_failed": 0, "items": [],
        }
        restored = failed_count = 0
        for idx in indices:
            chosen = rows[idx]
            if chosen.get("__source__") == "telegram":
                if not _confirm_or_proceed(f"Restore '{chosen['title']}' dari Telegram ke lokal?"):
                    continue
                try:
                    out_path = _restore_from_telegram(config, chosen)
                    print_success(f"Restore selesai: {out_path}")
                    restored += 1
                except Exception as exc:
                    print_error(f"Restore gagal: {type(exc).__name__}: {exc}")
                    _log_exception("Restore gagal", exc)
                    failed_count += 1
            else:
                process_download_item(chosen, active_url, config, summary)
        if summary["total_items"]:
            print_download_summary(summary)
        if restored or failed_count:
            console.print(f"[bold]Telegram: {restored} berhasil, {failed_count} gagal.[/bold]")
        _pause()
        return

def require_telegram_ready(config: dict) -> bool:
    if not ensure_telethon(console):
        return False
    if not is_configured(config) or not is_logged_in():
        console.print("[yellow]Telegram belum terhubung. Setup diperlukan sekali saja.[/yellow]")
        return bool(login_flow(console, config))
    return True


def scan_with_spinner(config: dict) -> list:
    with console.status("[bold cyan]📡 Mencari di Telegram... / Searching in Telegram...[/bold cyan]", spinner="dots"):
        client = _connected_client(config)
        try:
            items = scan_backups(client, get_destinations(config))
        finally:
            tg_disconnect(client)
    return items


def _connected_client(config: dict):
    client = create_client(config)
    tg_connect(client)
    return client


def _backup_key_of(item: dict) -> str:
    return tm.backup_key(
        item.get("title", ""), item.get("year"),
        item.get("season"), item.get("episode"),
    )


def _restore_from_telegram(config: dict, chosen: dict) -> str:
    client = _connected_client(config)
    try:
        try:
            progress, cb = _rich_progress(
                chosen.get("file_size", 0), f"⬇️ {chosen.get('title', '')}"
            )
            with progress:
                return restore_backup(client, chosen, config, progress_callback=cb)
        except Exception as exc:
            if len(get_destinations(config)) > 1:
                items = scan_with_spinner(config)
                candidate = next(
                    (it for it in items
                     if _backup_key_of(it) == _backup_key_of(chosen)
                     and it.get("chat") != chosen.get("chat")),
                    None,
                )
                if candidate is not None:
                    retry_progress, retry_cb = _rich_progress(
                        candidate.get("file_size", 0), f"⬇️ {candidate.get('title', '')}"
                    )
                    try:
                        with retry_progress:
                            return restore_backup(client, candidate, config,
                                                  progress_callback=retry_cb)
                    except Exception:
                        pass
            raise exc
    finally:
            tg_disconnect(client)


def handle_telegram_settings(config: dict) -> None:
    while True:
        fresh = load_config()
        config.update(fresh)
        dests_raw = fresh.get("tg_destinations", '["saved"]')
        console.print(f"\n[bold cyan]⚙️ TELEGRAM SETTINGS[/bold cyan]")
        console.print(f"API ID  : [yellow]{fresh.get('tg_api_id') or '-'}[/yellow]")
        console.print(f"Channel : [yellow]{fresh.get('tg_channel_id') or '-'}[/yellow]")
        console.print(f"Auto-backup : [yellow]{'ON' if fresh.get('tg_auto_backup') == '1' else 'OFF'}[/yellow]")
        console.print(f"Tujuan  : [yellow]{dests_raw}[/yellow]")

        action = questionary.select(
            "Pilih Pengaturan:",
            choices=[
                "🔑 Isi Ulang API ID / Hash",
                "📢 Set Channel Tujuan / Set Target Channel",
                "🎯 Ubah Tujuan Backup (Saved/Channel/Group/Topik)",
                "🧪 Test Tujuan Backup",
                "🤖 Toggle Auto-Backup",
                "🚪 Logout (hapus session)",
                "⬅ Kembali / Back",
            ]
        ).ask()
        if not action or action == "⬅ Kembali / Back":
            return
        if action == "🔑 Isi Ulang API ID / Hash":
            api_id = questionary.text("API ID:", default=fresh.get("tg_api_id", "")).ask()
            api_hash = questionary.password("API Hash:").ask()
            if api_id and api_hash:
                if not api_id.strip().isdigit():
                    console.print("[red]API ID harus berupa angka.[/red]")
                else:
                    save_config_key("tg_api_id", api_id.strip())
                    save_config_key("tg_api_hash", api_hash.strip())
                    print_success("API credentials disimpan.")
        elif action == "📢 Set Channel Tujuan / Set Target Channel":
            channel = questionary.text("Username channel (@nama) atau ID (-100...):",
                                       default=fresh.get("tg_channel_id", "")).ask()
            if channel is not None:
                save_config_key("tg_channel_id", channel.strip())
                print_success("Channel disimpan. Pastikan Anda adalah admin/member channel tersebut.")
        elif action == "🎯 Ubah Tujuan Backup (Saved/Channel/Group/Topik)":
            console.print("[dim]Bisa paste langsung Copy Message Link dari Telegram:[/dim]")
            console.print("[dim]  https://t.me/c/2312123164/10777/10778 → group -1002312123164, topik 10777[/dim]")
            console.print("[dim]Atau format manual (pisahkan koma):[/dim]")
            console.print("[dim]  saved | channel:<id> | group:<id> | group:<id>:<topik>[/dim]")
            console.print("[dim]Contoh: saved, channel:@filmku, group:-100123456789:7[/dim]")
            raw = questionary.text(
                "Daftar tujuan backup (kosongkan untuk batal):"
            ).ask()
            if raw and raw.strip():
                tokens = tm.parse_destination_input(raw)
                save_config_key("tg_destinations", json.dumps(tokens))
                print_success(f"Tujuan backup: {tokens}")
                console.print("[yellow]Catatan: group dengan topik di-upload ulang "
                              "(forward Telegram tidak bisa menentukan topik).[/yellow]")
        elif action == "🧪 Test Tujuan Backup":
            dests = get_destinations(fresh)
            if not dests:
                print_error("Tujuan backup belum diatur. Pakai 'Ubah Tujuan Backup' dulu.")
            else:
                client = _connected_client(config)
                try:
                    results = test_destinations(client, dests)
                finally:
                    tg_disconnect(client)
                for res in results:
                    mark = "[green]✓[/green]" if res["ok"] else "[red]✗[/red]"
                    console.print(f" {mark} {res['destination']} — {res['detail']}")
                console.print(
                    "[dim]Verifikasi: klik kanan pesan tes → Copy Message Link. "
                    "Contoh https://t.me/c/2312123164/10777/10778 berarti "
                    "group -1002312123164 topik 10777 (segmen-2 = topik, segmen-3 = nomor pesan).[/dim]")
        elif action == "🤖 Toggle Auto-Backup":
            new_val = "0" if fresh.get("tg_auto_backup") == "1" else "1"
            save_config_key("tg_auto_backup", new_val)
            print_success(f"Auto-backup: {'ON' if new_val == '1' else 'OFF'}")
        elif action == "🚪 Logout (hapus session)":
            confirm = questionary.confirm("Hapus session Telegram di PC ini?").ask()
            if confirm:
                tm.logout_session()
                print_success("Session Telegram dihapus.")


_BACKUP_ERROR_LOG = os.path.join(os.path.expanduser("~"), ".iamnotpirates", "last_backup_error.log")


def _log_exception(context: str, exc: Exception) -> None:
    """Append failure details to a persistent log so nothing fails silently."""
    import traceback
    try:
        with open(_BACKUP_ERROR_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"\n[{datetime.now().isoformat(timespec='seconds')}] {context}\n")
            fh.write(f"{type(exc).__name__}: {exc}\n")
            fh.write(traceback.format_exc())
            fh.write("-" * 60 + "\n")
    except OSError:
        pass


def _confirm_or_proceed(message: str) -> bool:
    try:
        return bool(questionary.confirm(message).ask())
    except Exception:
        return False


def _pause() -> None:
    try:
        questionary.press_any_key_to_continue(message="Tekan sebarang tombol...").ask()
    except Exception:
        pass


def handle_telegram_search_restore(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    query = questionary.text("Masukkan judul yang dicari di backup Telegram:").ask()
    if not query or not query.strip():
        return
    try:
        items = scan_with_spinner(config)
    except Exception as exc:
        print_error(f"Gagal membaca Telegram: {exc}")
        return
    filtered = [it for it in items if matches_query(it.get("title", ""), query.strip())]
    if not filtered:
        console.print(f"[yellow]Tidak ada backup cocok untuk \"{query.strip()}\".[/yellow]")
        _pause()
        return
    console.print(format_backup_table(filtered))
    raw = questionary.text(
        f"Pilih nomor untuk restore (bisa lebih dari satu, contoh 1,3 — kosongkan untuk batal):"
    ).ask()
    if not raw or not raw.strip():
        console.print("[yellow]Restore dibatalkan.[/yellow]")
        return
    indices = []
    for part in re.split(r"[,\s]+", raw.strip()):
        if not part.isdecimal() or not (1 <= int(part) <= len(filtered)):
            console.print(f"[yellow]Nomor '{part}' tidak valid — dilewati.[/yellow]")
            continue
        idx = int(part) - 1
        if idx not in indices:
            indices.append(idx)
    if not indices:
        console.print("[yellow]Restore dibatalkan.[/yellow]")
        return
    success = failed = skipped = 0
    last_path = None
    for idx in indices:
        chosen = filtered[idx]
        if not _confirm_or_proceed(f"Restore '{chosen['title']}' ke folder lokal sekarang?"):
            skipped += 1
            continue
        try:
            last_path = _restore_from_telegram(config, chosen)
            print_success(f"Restore selesai: {last_path}")
            success += 1
        except Exception as exc:
            print_error(f"Restore gagal: {type(exc).__name__}: {exc}")
            _log_exception("Restore gagal", exc)
            failed += 1
    console.print(f"[bold]Selesai: {success} berhasil, {failed} gagal, {skipped} dilewati.[/bold]")
    if success == 1 and last_path:
        try:
            import subprocess
            target = os.path.normpath(last_path)
            folder = os.path.dirname(target)
            if folder and os.path.isdir(folder):
                subprocess.Popen(["explorer", "/select,", target])
        except Exception:
            pass
    _pause()


def handle_telegram_list(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    try:
        items = scan_with_spinner(config)
    except Exception as exc:
        print_error(f"Gagal membaca Telegram: {exc}")
        return
    if not items:
        console.print("[yellow]Belum ada backup di tujuan Telegram yang dikonfigurasi.[/yellow]")
        _pause()
        return
    console.print(format_backup_table(items))
    _pause()


def _default_scan_dirs(config: dict) -> list:
    dirs = []
    for media_type in ("movie", "series"):
        try:
            d = get_download_dir(config, media_type=media_type)
        except Exception:
            d = None
        if d and d not in dirs:
            dirs.append(d)
    return dirs


def _local_listing_with_backup_status(config: dict) -> list:
    entries = merge_local_entries(
        collect_local_entries(),
        collect_folder_entries(_default_scan_dirs(config)),
    )
    try:
        scanned = scan_with_spinner(config)
    except Exception:
        scanned = []
        console.print("[yellow]⚠️ Tidak bisa menghubungi Telegram — status backup tidak diketahui.[/yellow]")
    return mark_backed_entries(entries, scanned)


def _rich_progress(total: int, description: str):
    from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn
    progress = Progress(
        TextColumn("[bold blue]" + description + "[/bold blue]"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        console=console,
    )
    task_id = progress.add_task(description, total=total)

    def callback(current: int, total_bytes: int):
        progress.update(task_id, completed=current)

    return progress, callback


def maybe_auto_backup(video_path: str, config: dict, title: str, year: str,
                      media_type: str, season=None, episode=None) -> None:
    if config.get("tg_auto_backup") != "1":
        return
    try:
        if not is_configured(config) or not is_logged_in():
            return
        destinations = get_destinations(config)
        if not destinations:
            return
        video_dir = os.path.dirname(video_path)
        stem = os.path.splitext(os.path.basename(video_path))[0]
        sub_paths = [
            os.path.join(video_dir, name)
            for name in sorted(os.listdir(video_dir))
            if name.lower().endswith(".srt") and os.path.splitext(name)[0].startswith(stem)
        ]
        meta = {
            "title": title, "year": year, "media_type": media_type,
            "season": season, "episode": episode, "subtitles": [],
        }
        size = os.path.getsize(video_path)
        progress, cb = _rich_progress(size, f"☁️ {title}")
        client = _connected_client(config)
        try:
            with progress:
                upload_backup(client, video_path, sub_paths, meta, destinations, progress_callback=cb)
        finally:
            tg_disconnect(client)
        print_success(f"Auto-backup Telegram selesai: {title}")
    except Exception as exc:
        console.print(f"[yellow]⚠️ Auto-backup gagal untuk {title}: {exc}[/yellow]")


def handle_telegram_manual_backup(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    entries = _local_listing_with_backup_status(config)
    if not entries:
        console.print("[yellow]Tidak ada file lokal yang tercatat sukses di log.[/yellow]")
        return

    console.print(format_local_delete_table(entries))
    labels = []
    for idx, entry in enumerate(entries, start=1):
        label_title = format_entry_label(entry)
        if entry.get("backed"):
            label_title += " [RE-BACKUP / OVERWRITE]"
        labels.append(f"{idx}. {label_title}")
    picked = questionary.checkbox(
        "Pilih item untuk di-backup ke Telegram (SPACE pilih, ENTER lanjut):",
        choices=labels
    ).ask()
    if not picked:
        console.print("[yellow]Tidak ada item dipilih.[/yellow]")
        return
    chosen_indices = [int(label.split(".")[0]) - 1 for label in picked]
    destinations = get_destinations(config)
    if not destinations:
        print_error("Tujuan backup belum valid. Atur di ⚙️ Pengaturan Telegram.")
        return
    success_count = 0
    fail_count = 0
    client = _connected_client(config)
    try:
        for pos, idx in enumerate(chosen_indices, start=1):
            entry = entries[idx]
            if not os.path.exists(entry["output_path"]):
                print_error(f"File tidak ditemukan, di-skip: {entry['output_path']}")
                fail_count += 1
                continue
            console.print(f"\n[bold cyan]=== Backup {pos}/{len(chosen_indices)}: {entry['title']} ===[/bold cyan]")
            sub_dir = os.path.dirname(entry["output_path"])
            sub_paths = [
                os.path.join(sub_dir, name)
                for name in sorted(os.listdir(sub_dir))
                if name.lower().endswith(".srt")
            ]
            meta = {
                "title": entry["title"], "year": entry["year"],
                "media_type": entry["media_type"], "season": entry["season"],
                "episode": entry["episode"], "subtitles": [],
            }
            try:
                progress, cb = _rich_progress(entry["file_size"], entry["title"])
                with progress:
                    upload_backup(client, entry["output_path"], sub_paths, meta, destinations, progress_callback=cb)
                print_success(f"Berhasil backup: {entry['title']}")
                success_count += 1
            except KeyboardInterrupt:
                console.print(f"\n[bold yellow]⚠️ Dibatalkan saat meng-upload {entry['title']} — "
                              f"sisa batch dilewati.[/bold yellow]")
                break
            except Exception as exc:
                _log_exception(f"Backup gagal: {entry['title']}", exc)
                print_error(f"Gagal backup {entry['title']}: {type(exc).__name__}: {exc}")
                fail_count += 1
    finally:
            tg_disconnect(client)
    console.print(f"\n[bold]Selesai: {success_count} berhasil, {fail_count} gagal.[/bold]")
    _pause()


def handle_telegram_delete_local(config: dict) -> None:
    if not require_telegram_ready(config):
        return
    entries = _local_listing_with_backup_status(config)
    if not entries:
        console.print("[yellow]Tidak ada file lokal yang tercatat sukses di log.[/yellow]")
        return
    console.print(format_local_delete_table(entries))
    labels = []
    for idx, entry in enumerate(entries, start=1):
        label_title = format_entry_label(entry)
        if entry["backed"]:
            labels.append(f"{idx}. ✅ {label_title} (aman)")
        else:
            labels.append(f"{idx}. ⚠️ {label_title} (BELUM DIBACKUP)")
    picked = questionary.checkbox(
        "Pilih file lokal yang ingin DIHAPUS (SPACE pilih, ENTER lanjut):",
        choices=labels
    ).ask()
    if not picked:
        console.print("[yellow]Tidak ada file dipilih.[/yellow]")
        return
    deleted = 0
    for label in picked:
        idx = int(label.split(".")[0]) - 1
        entry = entries[idx]
        path = entry["output_path"]
        if entry["backed"]:
            ok = _confirm_or_proceed(f"Hapus '{path}'? (sudah aman di Telegram)")
            if not ok:
                continue
            os.remove(path)
            deleted += 1
            print_success(f"Dihapus: {path}")
        else:
            console.print(f"\n[bold red]⛔ PERINGATAN: '{entry['title']}' TIDAK ditemukan di Telegram![/bold red]")
            console.print("[bold red]Jika dihapus, file hilang PERMANEN dan tidak bisa dipulihkan![/bold red]")
            ok = _confirm_or_proceed("Saya mengerti risikonya — lanjutkan penghapusan?")
            if not ok:
                console.print("[yellow]Penghapusan dibatalkan.[/yellow]")
                continue
            typed = questionary.text("Ketik HAPUS untuk mengonfirmasi permanen:").ask()
            if typed != "HAPUS":
                console.print("[yellow]Konfirmasi salah — penghapusan dibatalkan.[/yellow]")
                continue
            os.remove(path)
            deleted += 1
            print_success(f"Dihapus permanen: {path}")
        parent = os.path.dirname(path)
        try:
            if parent and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass
    console.print(f"\n[bold]Selesai: {deleted} file dihapus.[/bold]")
    _pause()


def handle_telegram_menu(active_url: str, config: dict) -> None:
    while True:
        action = questionary.select(
            "📡 Telegram Backup — Pilih Aksi:",
            choices=[
                "🔍 Cari & Restore dari Telegram / Search & Restore",
                "📚 Daftar Semua Backup / List All Backups",
                "📤 Backup Manual / Manual Backup",
                "🗑️ Hapus File Lokal / Delete Local Files",
                "⚙️ Pengaturan Telegram / Telegram Settings",
                "⬅ Kembali / Back",
            ]
        ).ask()
        if action is None or action == "⬅ Kembali / Back":
            return
        fresh = load_config()
        config.update(fresh)
        if action.startswith("⚙️"):
            handle_telegram_settings(config)
        elif action.startswith("🔍"):
            handle_telegram_search_restore(fresh)
        elif action.startswith("📚"):
            handle_telegram_list(fresh)
        elif action.startswith("📤"):
            handle_telegram_manual_backup(fresh)
        elif action.startswith("🗑️"):
            handle_telegram_delete_local(fresh)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-v", "version"):
        console.print("I Am Not Pirates v1.3.0")
        return

    init_db()

    has_n_m3u8 = os.path.exists(get_binary_path())
    ffmpeg_p, ffprobe_p = get_ffmpeg_paths()
    has_ffmpeg = os.path.exists(ffmpeg_p) and os.path.exists(ffprobe_p)
    has_playwright = is_chromium_installed()

    if not (has_n_m3u8 and has_ffmpeg and has_playwright):
        print_startup_dependency_notice(console)

    ensure_binary(console)
    ensure_ffmpeg(console)
    ensure_playwright(console)

    while True:
        config = load_config()
        active_url = config.get("active_url", "")

        if not active_url or not config.get("target_urls"):
            console.clear()
            console.print("[yellow]Belum ada target URL tersimpan. Silakan masukkan URL pertama:[/yellow]")
            url = questionary.text(
                "Target URL (default: https://z2.idlixku.com/):",
                default="https://z2.idlixku.com/"
            ).ask()
            if url:
                add_target_url(url, "Primary IDLIX")
                set_active_url(url)
            continue

        print_header(active_url)

        choice = questionary.select(
            "Select Menu / Pilih Menu:",
            choices=[
                "1. 🔍 Search Movie & TV Series / Cari Film & TV Series",
                "2. 🔥 Browse Featured Content / Lihat Content Populer",
                "3. 📋 Download Log & Retry / Log & Retry Download Gagal",
                "4. 🛒 Keranjang Download / Kelola Keranjang Download",
                "5. 🛠️  Settings / Pengaturan (Folder & Mode)",
                "6. 🌐 Switch Target URL / Pilih Active Target URL",
                "7. ➕ Add New Target URL / Tambah Target URL Baru",
                "8. ⚙️  Manage Target URLs / Kelola Daftar Target URL",
                "9. 📡 Telegram Backup / Kelola Backup Telegram",
                "10. ❌ Exit / Keluar",
            ]
        ).ask()

        if choice is None or choice.startswith("10."):
            console.print("[bold yellow]Terima kasih! Sampai jumpa.[/bold yellow]")
            sys.exit(0)
        elif choice.startswith("1."):
            handle_search(active_url, config)
        elif choice.startswith("2."):
            handle_featured(active_url)
        elif choice.startswith("3."):
            handle_retry_failed(active_url, config)
        elif choice.startswith("4."):
            handle_cart(active_url, config)
        elif choice.startswith("5."):
            handle_settings()
        elif choice.startswith("6."):
            handle_select_active()
        elif choice.startswith("7."):
            handle_add_url()
        elif choice.startswith("8."):
            handle_manage_urls()
        elif choice.startswith("9."):
            handle_telegram_menu(active_url, config)

if __name__ == "__main__":
    main()

