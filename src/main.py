import sys
import os
import re
import questionary
from rich.console import Console

from src.config_manager import (
    load_config, add_target_url, set_active_url, delete_target_url,
    get_download_dir, set_download_dir
)
from src.scraper import fetch_featured_content
from src.ui import print_header, format_featured_table, print_error, print_success
from src.video_extractor import extract_video_sources
from src.downloader import (
    inspect_stream_qualities,
    download_media_stream,
    download_subtitle,
    get_unique_filepath,
    format_tv_paths,
    download_subtitles_batch
)
from src.series_extractor import fetch_series_details, extract_episode_sources

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

    choice_num = questionary.text(
        f"Masukkan nomor item yang ingin di-download (1-{len(items)}):",
        validate=lambda val: val.isdigit() and 1 <= int(val) <= len(items)
    ).ask()

    if not choice_num:
        return

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

        season_choices = [f"Season {s['season_num']}" for s in seasons]
        selected_season_str = questionary.select(
            "Pilih Season:",
            choices=season_choices
        ).ask()

        if not selected_season_str:
            return

        selected_season = next((s for s in seasons if f"Season {s['season_num']}" == selected_season_str), None)
        if not selected_season or not selected_season.get("episodes"):
            print_error("Season tidak valid atau tidak memiliki episode.")
            return

        season_num = selected_season["season_num"]
        episodes = selected_season["episodes"]

        ep_choices = [f"Episode {ep['episode_num']}: {ep['title']}" for ep in episodes]
        selected_ep_labels = questionary.checkbox(
            "Pilih Episode yang ingin di-download:",
            choices=ep_choices
        ).ask()

        if not selected_ep_labels:
            console.print("[yellow]Tidak ada episode yang dipilih.[/yellow]")
            return

        ep_map = {f"Episode {ep['episode_num']}: {ep['title']}": ep for ep in episodes}
        selected_episodes = [ep_map[label] for label in selected_ep_labels if label in ep_map]

        default_dir = get_download_dir(config)
        custom_dir = questionary.text(
            f"Lokasi simpan (Tekan ENTER untuk default: {default_dir}):",
            default=default_dir
        ).ask()
        target_dir = custom_dir.strip() if custom_dir else default_dir
        set_download_dir(config, target_dir)

        qualities = inspect_stream_qualities("")
        selected_quality = questionary.select(
            "Pilih Kualitas Video:",
            choices=qualities
        ).ask()

        if not selected_quality:
            return

        sub_choices = ["Semua Subtitle Tersedia", "Indonesia saja", "English saja", "Tanpa Subtitle"]
        selected_sub_choice = questionary.select(
            "Pilih Subtitle:",
            choices=sub_choices
        ).ask()

        if not selected_sub_choice:
            return

        for ep in selected_episodes:
            console.print(f"\n[bold cyan]Memproses Episode {ep['episode_num']}: {ep['title']}...[/bold cyan]")
            try:
                sources = extract_episode_sources(ep["media_id"], item_url)
                m3u8_urls = sources.get("m3u8_urls", [])
                subtitles = sources.get("subtitles", [])

                if not m3u8_urls:
                    print_error(f"Gagal menemukan link video m3u8 untuk Episode {ep['episode_num']}")
                    continue

                season_dir, base_filename = format_tv_paths(clean_title, year, season_num, ep["episode_num"], target_dir)
                console.print(f"[bold green]Memulai download Episode {ep['episode_num']} ({selected_quality}) ke {season_dir}...[/bold green]")

                video_path = download_media_stream(m3u8_urls[0], season_dir, base_filename, "N/A", selected_quality)

                if video_path and os.path.exists(video_path):
                    print_success(f"Berhasil mendownload Episode {ep['episode_num']}: {video_path}")
                    if selected_sub_choice != "Tanpa Subtitle":
                        sub_paths = download_subtitles_batch(subtitles, video_path, selected_sub_choice)
                        for sp in sub_paths:
                            print_success(f"Berhasil menyimpan Subtitle: {sp}")
                else:
                    print_error(f"Gagal mendownload video untuk Episode {ep['episode_num']}")
            except Exception as e:
                print_error(f"Error saat memproses Episode {ep['episode_num']}: {e}")
        return

    console.print(f"\n[bold cyan]Memproses: {clean_title} ({year})...[/bold cyan]")

    # Download Path Prompt
    default_dir = get_download_dir(config)
    custom_dir = questionary.text(
        f"Lokasi simpan (Tekan ENTER untuk default: {default_dir}):",
        default=default_dir
    ).ask()
    target_dir = custom_dir.strip() if custom_dir else default_dir
    set_download_dir(config, target_dir)

    # Extract Video Sources
    console.print("[bold yellow]Mengambil sumber video & subtitle...[/bold yellow]")
    sources = extract_video_sources(selected_item["url"])
    m3u8_urls = sources.get("m3u8_urls", [])
    subtitles = sources.get("subtitles", [])

    if not m3u8_urls:
        print_error(f"Gagal menemukan link video m3u8 di {selected_item['url']}")
        return

    # Select Quality
    qualities = inspect_stream_qualities(m3u8_urls[0])
    selected_quality = questionary.select(
        "Pilih Kualitas Video:",
        choices=qualities
    ).ask()

    if not selected_quality:
        return

    # Select Subtitle
    sub_choices = ["Tanpa Subtitle"] + [f"{s['lang']} - {s['url']}" for s in subtitles]
    selected_sub_choice = questionary.select(
        "Pilih Subtitle:",
        choices=sub_choices
    ).ask()

    # Trigger Video Stream Download
    console.print(f"[bold green]Memulai download {clean_title} ({selected_quality}) ke {target_dir}...[/bold green]")
    video_path = download_media_stream(m3u8_urls[0], target_dir, clean_title, year, selected_quality)

    if video_path and os.path.exists(video_path):
        print_success(f"Berhasil mendownload Video: {video_path}")

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

def main() -> None:
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
                "🚀 Scrape Featured Content",
                "🌐 Pilih / Ganti Active Target URL",
                "➕ Tambah URL Target Baru",
                "⚙️  Manage List URL (Edit/Delete)",
                "❌ Exit Program"
            ]
        ).ask()

        if choice == "🚀 Scrape Featured Content":
            handle_featured(active_url)
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
