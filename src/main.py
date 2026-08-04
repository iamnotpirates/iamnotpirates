import sys
import os
import re
import questionary
from rich.console import Console

from src.db_manager import init_db
from src.ffmpeg_manager import ensure_ffmpeg, verify_media_file
from src.config_manager import (
    load_config, save_config, add_target_url, set_active_url, delete_target_url,
    get_download_dir, set_download_dir, set_organize_mode
)
from src.scraper import fetch_featured_content, search_content
from src.ui import print_header, format_featured_table, print_error, print_success
from src.video_extractor import extract_video_sources
from src.downloader import (
    download_media_stream,
    download_subtitle,
    get_unique_filepath,
    format_tv_paths,
    download_subtitles_batch
)
from src.series_extractor import fetch_series_details, extract_episode_sources
from src.download_log import add_entry, get_failed_entries, update_entry, format_log_table, is_already_downloaded
from src.n_m3u8dl_manager import download_with_re, ensure_binary

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

def handle_item_download(items: list[dict], active_url: str, config: dict) -> None:
    if not items:
        console.print("[yellow]Tidak ada item untuk di-download.[/yellow]")
        return

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
        sub_choices = ["Semua Subtitle Tersedia", "Indonesia saja", "English saja", "Tanpa Subtitle", "⬅ Kembali"]
        while True:
            selected_sub_choice = questionary.select(
                "Pilih Subtitle:",
                choices=sub_choices
            ).ask()

            if selected_sub_choice is None or selected_sub_choice == "⬅ Kembali":
                return
            break

        for ep in selected_episodes:
            console.print(f"\n[bold cyan]Memproses Episode {ep['episode_num']}: {ep['title']}...[/bold cyan]")
            season_dir, base_filename = format_tv_paths(clean_title, year, season_num, ep["episode_num"], target_dir)
            expected_path = os.path.join(season_dir, f"{base_filename}.mp4")

            try:
                sources = extract_episode_sources(ep["media_id"], item_url)
                m3u8_urls = sources.get("m3u8_urls", [])
                subtitles = sources.get("subtitles", [])

                if not m3u8_urls:
                    print_error(f"Gagal menemukan link video m3u8 untuk Episode {ep['episode_num']}")
                    add_entry(
                        title=f"{clean_title} S{season_num:02d}E{ep['episode_num']:02d}",
                        media_type="episode",
                        season=season_num,
                        episode=ep["episode_num"],
                        status="failed",
                        m3u8_url="",
                        output_path=expected_path,
                        error="No m3u8 url found"
                    )
                    continue

                m3u8_url = m3u8_urls[0]

                if is_already_downloaded(expected_path):
                    verify_res = verify_media_file(expected_path, required_sub_mode=selected_sub_choice)
                    if verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]:
                        console.print(f"[yellow]⏭ Episode {ep['episode_num']} sudah ada dan sehat, di-skip.[/yellow]")
                        add_entry(
                            title=f"{clean_title} S{season_num:02d}E{ep['episode_num']:02d}",
                            media_type="episode",
                            season=season_num,
                            episode=ep["episode_num"],
                            status="skipped",
                            m3u8_url=m3u8_url,
                            output_path=expected_path
                        )
                        continue
                    else:
                        console.print(f"[bold yellow]⚠️ Episode {ep['episode_num']} terdeteksi rusak/kurang subtitle (Status: {verify_res['video_status']}). Re-downloading...[/bold yellow]")

                console.print(f"[bold green]Memulai download Episode {ep['episode_num']} ke {season_dir}...[/bold green]")
                video_path = download_media_stream(m3u8_url, season_dir, base_filename, "N/A", "Best Available", create_subfolder=False)

                if video_path and os.path.exists(video_path):
                    print_success(f"Berhasil mendownload Episode {ep['episode_num']}: {video_path}")
                    add_entry(
                        title=f"{clean_title} S{season_num:02d}E{ep['episode_num']:02d}",
                        media_type="episode",
                        season=season_num,
                        episode=ep["episode_num"],
                        status="success",
                        m3u8_url=m3u8_url,
                        output_path=video_path
                    )
                    if selected_sub_choice != "Tanpa Subtitle":
                        sub_paths = download_subtitles_batch(subtitles, video_path, selected_sub_choice)
                        for sp in sub_paths:
                            print_success(f"Berhasil menyimpan Subtitle: {sp}")
                else:
                    print_error(f"Gagal mendownload video untuk Episode {ep['episode_num']}")
                    add_entry(
                        title=f"{clean_title} S{season_num:02d}E{ep['episode_num']:02d}",
                        media_type="episode",
                        season=season_num,
                        episode=ep["episode_num"],
                        status="failed",
                        m3u8_url=m3u8_url,
                        output_path=expected_path,
                        error="Download failed"
                    )
            except Exception as e:
                print_error(f"Error saat memproses Episode {ep['episode_num']}: {e}")
                add_entry(
                    title=f"{clean_title} S{season_num:02d}E{ep['episode_num']:02d}",
                    media_type="episode",
                    season=season_num,
                    episode=ep["episode_num"],
                    status="failed",
                    m3u8_url="",
                    output_path=expected_path,
                    error=str(e)
                )
        return

    console.print(f"\n[bold cyan]Memproses: {clean_title} ({year})...[/bold cyan]")

    # --- Download Path ---
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
            error="No m3u8 url found"
        )
        return

    m3u8_url = m3u8_urls[0]

    # --- Pilih Subtitle ---
    sub_choices = ["Tanpa Subtitle"] + [f"{s['lang']} - {s['url']}" for s in subtitles] + ["⬅ Kembali"]
    while True:
        selected_sub_choice = questionary.select(
            "Pilih Subtitle:",
            choices=sub_choices
        ).ask()

        if selected_sub_choice is None or selected_sub_choice == "⬅ Kembali":
            return
        break

    if is_already_downloaded(expected_path):
        verify_res = verify_media_file(expected_path, required_sub_mode=selected_sub_choice)
        if verify_res["video_status"] == "HEALTHY" and not verify_res["missing_subtitles"]:
            console.print(f"[yellow]⏭ {clean_title} sudah ada dan sehat, di-skip.[/yellow]")
            add_entry(
                title=clean_title,
                media_type="movie",
                season=None,
                episode=None,
                status="skipped",
                m3u8_url=m3u8_url,
                output_path=expected_path
            )
            return
        else:
            console.print(f"[bold yellow]⚠️ {clean_title} terdeteksi rusak/kurang subtitle (Status: {verify_res['video_status']}). Re-downloading...[/bold yellow]")

    # --- Trigger Download ---
    console.print(f"[bold green]Memulai download {clean_title} ke {target_dir}...[/bold green]")
    video_path = download_media_stream(m3u8_url, target_dir, clean_title, year, "Best Available")

    if video_path and os.path.exists(video_path):
        print_success(f"Berhasil mendownload Video: {video_path}")
        add_entry(
            title=clean_title,
            media_type="movie",
            season=None,
            episode=None,
            status="success",
            m3u8_url=m3u8_url,
            output_path=video_path
        )

        # Download Subtitle if selected
        if selected_sub_choice and selected_sub_choice != "Tanpa Subtitle":
            matched_sub = next((s for s in subtitles if f"{s['lang']} - {s['url']}" == selected_sub_choice), None)
            if matched_sub:
                sub_lang = "id" if "ind" in matched_sub["lang"].lower() or "id" in matched_sub["lang"].lower() else "en"
                base_name = os.path.splitext(video_path)[0]
                target_srt_path = f"{base_name}.{sub_lang}.srt"

                console.print(f"[bold yellow]Mengunduh dan mengonversi subtitle (.vtt -> .srt)...[/bold yellow]")
                sub_success = download_subtitle(matched_sub["url"], target_srt_path)
                if sub_success:
                    print_success(f"Berhasil menyimpan Subtitle SRT: {target_srt_path}")
                else:
                    print_error("Gagal mengunduh subtitle SRT.")
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
            error="Download failed"
        )

def handle_retry_failed(active_url: str, config: dict) -> None:
    failed = get_failed_entries()
    if not failed:
        console.print("[green]Tidak ada download yang gagal.[/green]")
        return

    table = format_log_table(failed)
    console.print(table)

    action = questionary.select(
        "Pilih Aksi:",
        choices=["🔄 Retry Semua yang Gagal", "↩️ Kembali"]
    ).ask()

    if action != "🔄 Retry Semua yang Gagal":
        return

    for entry in failed:
        console.print(f"\n[bold cyan]Retry: {entry['title']}...[/bold cyan]")
        try:
            m3u8_url = entry["m3u8_url"]
            output_path = entry["output_path"]
            output_dir = os.path.dirname(output_path)
            base_name = os.path.splitext(os.path.basename(output_path))[0]

            success = download_with_re(m3u8_url, output_dir, base_name)
            if success:
                update_entry(entry["id"], {"status": "success", "error": None})
                print_success(f"Berhasil: {output_path}")
            else:
                print_error(f"Masih gagal: {entry['title']}")
        except Exception as e:
            print_error(f"Error retry {entry['title']}: {e}")

def handle_featured(active_url: str) -> None:
    config = load_config()
    console.print("\n[bold cyan]Fetching featured content...[/bold cyan]")
    try:
        items = fetch_featured_content(active_url)
        if not items:
            console.print("[yellow]No featured content found or website structure differed.[/yellow]")
        else:
            table = format_featured_table(items)
            console.print(table)

            action = questionary.select(
                "Pilih Aksi:",
                choices=[
                    "📥 Download Film/Series",
                    "↩️ Kembali ke Menu Utama"
                ]
            ).ask()

            if action == "📥 Download Film/Series":
                handle_item_download(items, active_url, config)
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

        console.print(f"\n[bold cyan]Mencari \"{query.strip()}\"...[/bold cyan]")
        items = search_content(active_url, query.strip())
        if not items:
            console.print(f"[yellow]Tidak ada hasil ditemukan untuk \"{query.strip()}\".[/yellow]")
        else:
            table = format_featured_table(items)
            console.print(table)

            action = questionary.select(
                "Pilih Aksi:",
                choices=[
                    "📥 Download Film/Series",
                    "🔍 Cari Judul Lain",
                    "↩️ Kembali ke Menu Utama"
                ]
            ).ask()

            if action == "📥 Download Film/Series":
                handle_item_download(items, active_url, config)
                break
            elif action == "🔍 Cari Judul Lain":
                continue
            else:
                break

def main() -> None:
    init_db()
    ensure_binary(console)
    ensure_ffmpeg(console)
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
            "Pilih Menu:",
            choices=[
                "🔍 Cari Film / TV Series",
                "🔥 Lihat Featured Content",
                "📋 Lihat & Retry Download Gagal",
                "🛠️  Pengaturan (Folder & Mode)",
                "🌐 Pilih / Ganti Active Target URL",
                "➕ Tambah URL Target Baru",
                "⚙️  Manage List URL (Edit/Delete)",
                "❌ Exit Program"
            ]
        ).ask()

        if choice == "🔍 Cari Film / TV Series":
            handle_search(active_url, config)
        elif choice == "🔥 Lihat Featured Content" or choice == "🚀 Scrape Featured Content":
            handle_featured(active_url)
        elif choice == "📋 Lihat & Retry Download Gagal":
            handle_retry_failed(active_url, config)
        elif choice == "🛠️  Pengaturan (Folder & Mode)":
            handle_settings()
        elif choice == "🌐 Pilih / Ganti Active Target URL":
            handle_select_active()
        elif choice == "➕ Tambah URL Target Baru":
            handle_add_url()
        elif choice == "⚙️  Manage List URL (Edit/Delete)":
            handle_manage_urls()
        elif choice == "❌ Exit Program" or choice is None:
            console.print("[bold yellow]Terima kasih! Sampai jumpa.[/bold yellow]")
            sys.exit(0)

if __name__ == "__main__":
    main()

