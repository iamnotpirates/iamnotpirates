import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def print_header(active_url: str, console: Console | None = None) -> None:
    """Clears console and prints header panel with active target URL."""
    if console is None:
        console = Console()
    console.clear()
    panel = Panel(
        f"[bold cyan]I AM NOT PIRATES CLI v1.3.1[/bold cyan]\nTarget URL: [yellow]{active_url}[/yellow]",
        title="[bold green]I AM NOT PIRATES[/bold green]",
        subtitle="Streaming & Media Explorer / Penjelajah Media v1.3.1",
        border_style="magenta",
    )
    console.print(panel)


def format_featured_table(items: list[dict]) -> Table:
    """Returns a styled rich.table.Table with columns: No, Title, Year, Type, Quality, Rating, URL."""
    table = Table(
        title="[bold cyan]Featured Content[/bold cyan]",
        header_style="bold magenta",
        show_header=True,
        expand=True,
    )
    table.add_column("No", justify="right", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold white", min_width=30, max_width=45, no_wrap=False)
    table.add_column("Year", justify="center", style="yellow", no_wrap=True)
    table.add_column("Type", style="green", justify="center", no_wrap=True)
    table.add_column("Quality", justify="center", style="bold green", no_wrap=True)
    table.add_column("Rating", justify="center", style="yellow", no_wrap=True)
    table.add_column("URL", style="blue underline", no_wrap=True)

    for idx, item in enumerate(items, start=1):
        raw_title = item.get("title", "N/A")
        item_url = item.get("url", "")
        year = str(item.get("year", "")).strip()

        if year and year != "N/A":
            clean_title = re.sub(r"\s*\(" + re.escape(year) + r"\)$", "", raw_title).strip()
        else:
            year_match = re.search(r"\((19\d\d|20\d\d)\)$", raw_title)
            if year_match:
                year = year_match.group(1)
                clean_title = re.sub(r"\s*\(" + year + r"\)$", "", raw_title).strip()
            else:
                url_year_match = re.search(r"-?(19\d\d|20\d\d)\b", item_url)
                year = url_year_match.group(1) if url_year_match else "N/A"
                clean_title = raw_title

        quality = item.get("quality", "WEB-DL")
        if item_url:
            clean_url = re.sub(r"^https?://", "", item_url)
            short_url = clean_url[:22] + "..." if len(clean_url) > 25 else clean_url
            clickable_url = f"[link={item_url}]🔗 {short_url}[/link]"
        else:
            clickable_url = "N/A"

        table.add_row(
            str(idx),
            clean_title,
            year,
            item.get("type", "N/A"),
            quality,
            str(item.get("rating", "N/A")),
            clickable_url,
        )

    return table


def print_error(msg: str, console: Console | None = None) -> None:
    """Prints error message panel/alert."""
    if console is None:
        console = Console()
    panel = Panel(
        f"[bold red]Error:[/bold red] {msg}",
        title="[bold red]ERROR[/bold red]",
        border_style="red",
    )
    console.print(panel)


def print_success(msg: str, console: Console | None = None) -> None:
    """Prints success message panel/alert."""
    if console is None:
        console = Console()
    panel = Panel(
        f"[bold green]Success:[/bold green] {msg}",
        title="[bold green]SUCCESS[/bold green]",
        border_style="green",
    )
    console.print(panel)


def format_download_summary_table(summary_items: list[dict]) -> Table:
    """Formats a rich.table.Table summarizing video and subtitle download results."""
    table = Table(
        title="[bold cyan]Download Detail Result[/bold cyan]",
        header_style="bold magenta",
        show_header=True,
        expand=True,
    )
    table.add_column("No", justify="right", style="cyan", no_wrap=True)
    table.add_column("Item Title", style="bold white")
    table.add_column("Video", justify="center")
    table.add_column("Subtitles", justify="center")
    table.add_column("Details / Error", style="dim white")

    for idx, item in enumerate(summary_items, start=1):
        title = item.get("title", "N/A")
        v_status = item.get("video_status", "UNKNOWN")
        v_err = item.get("video_error")

        if v_status == "SUCCESS":
            v_text = "[bold green]✓ SUCCESS[/bold green]"
        elif v_status == "SKIPPED":
            v_text = "[bold yellow]⏭ SKIPPED[/bold yellow]"
        else:
            v_text = "[bold red]✗ FAILED[/bold red]"

        subs = item.get("subtitles", [])
        if not subs:
            sub_text = "[dim]N/A[/dim]"
        else:
            ok_count = sum(1 for s in subs if s.get("status") == "SUCCESS")
            total_count = len(subs)
            if ok_count == total_count:
                sub_text = f"[bold green]✓ {ok_count}/{total_count}[/bold green]"
            elif ok_count > 0:
                sub_text = f"[bold yellow]⚠️ {ok_count}/{total_count}[/bold yellow]"
            else:
                sub_text = f"[bold red]✗ 0/{total_count}[/bold red]"

        details = str(v_err) if v_err else "-"
        table.add_row(str(idx), title, v_text, sub_text, details)

    return table


def print_download_summary(summary_data: dict, console: Console | None = None) -> None:
    """Prints aggregate download summary panel and detailed results table."""
    if console is None:
        console = Console()

    tot = summary_data.get("total_items", 0)
    v_ok = summary_data.get("video_success", 0)
    v_fail = summary_data.get("video_failed", 0)
    v_skip = summary_data.get("video_skipped", 0)
    s_ok = summary_data.get("sub_success", 0)
    s_fail = summary_data.get("sub_failed", 0)

    stats_str = (
        f"[bold white]Total Items Processed:[/bold white] [cyan]{tot}[/cyan]\n"
        f"[bold white]Video Downloads:[/bold white] [green]✓ {v_ok} Success[/green]  |  "
        f"[yellow]⏭ {v_skip} Skipped[/yellow]  |  "
        f"[red]✗ {v_fail} Failed[/red]\n"
        f"[bold white]Subtitle Downloads:[/bold white] [green]✓ {s_ok} Success[/green]  |  "
        f"[red]✗ {s_fail} Failed[/red]"
    )

    panel = Panel(
        stats_str,
        title="[bold green]DOWNLOAD SUMMARY REPORT[/bold green]",
        border_style="cyan",
        expand=True,
    )

    console.print()
    console.print(panel)
    if summary_data.get("items"):
        table = format_download_summary_table(summary_data["items"])
        console.print(table)


def print_startup_dependency_notice(console: Console | None = None) -> None:
    """Prints a prominent Rich panel explaining system dependency checks & auto-downloads."""
    if console is None:
        console = Console()

    content = (
        "[bold cyan]Memeriksa komponen pendukung sistem (N_m3u8DL-RE, FFmpeg, Playwright Chromium)...[/bold cyan]\n"
        "[dim white]💡 Catatan: Komponen yang belum ada akan diunduh secara otomatis.\n"
        "   Pengunduhan ini [bold yellow]HANYA DILAKUKAN SEKALI[/bold yellow] saat pertama kali aplikasi dijalankan.[/dim white]"
    )

    panel = Panel(
        content,
        title="[bold green]🔍 System Dependency Check / Pemeriksaan Komponen Sistem[/bold green]",
        border_style="cyan",
        expand=True,
    )
    console.print(panel)


def human_size(num_bytes: float) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_backup_table(items: list) -> Table:
    table = Table(title="[bold cyan]📚 Daftar Backup Telegram[/bold cyan]",
                  header_style="bold magenta", show_header=True, expand=True)
    table.add_column("No", justify="right", style="cyan")
    table.add_column("Judul", style="bold white")
    table.add_column("Tahun", justify="center", style="yellow")
    table.add_column("Tipe", justify="center", style="green")
    table.add_column("S/E", justify="center")
    table.add_column("Ukuran", justify="right", style="cyan")
    table.add_column("Part", justify="center")
    table.add_column("Sub", justify="center")
    for idx, item in enumerate(items, start=1):
        se = "-"
        if item.get("season") is not None and item.get("episode") is not None:
            se = f"S{item['season']:02d}E{item['episode']:02d}"
        table.add_row(
            str(idx), item.get("title", ""), str(item.get("year", "") or "-"),
            item.get("media_type", ""), se,
            human_size(item.get("file_size", 0)),
            str(item.get("part_count", 1)), str(len(item.get("subtitles", []))),
        )
    return table


def format_entry_label(entry: dict) -> str:
    label = entry.get("title", "")
    year = str(entry.get("year") or "").strip()
    if year and year.upper() != "N/A":
        label += f" ({year})"
    if entry.get("media_type") == "episode":
        season = entry.get("season")
        episode = entry.get("episode")
        se = "S" + (f"{int(season):02d}" if season is not None else "??")
        se += "E" + (f"{int(episode):02d}" if episode is not None else "??")
        label += f" {se}"
    return label


def format_local_delete_table(entries: list) -> Table:
    table = Table(title="[bold cyan]🗑️ File Lokal[/bold cyan]",
                  header_style="bold magenta", show_header=True, expand=True)
    table.add_column("No", justify="right", style="cyan")
    table.add_column("Judul", style="bold white")
    table.add_column("Tipe", justify="center")
    table.add_column("Ukuran", justify="right", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Path", style="dim")
    for idx, entry in enumerate(entries, start=1):
        if entry.get("backed"):
            status = "[green]✅ Aman di Telegram[/green]"
        else:
            status = "[red]⚠️ BELUM DIBACKUP[/red]"
        table.add_row(
            str(idx), format_entry_label(entry), entry.get("media_type", ""),
            human_size(entry.get("file_size", 0)), status,
            entry.get("output_path", ""),
        )
    return table


def format_hybrid_results(idlix_items: list, tg_items: list) -> list:
    rows = []
    for item in idlix_items or []:
        rows.append(dict(item, __source__="idlix"))
    for item in tg_items or []:
        rows.append(dict(item, __source__="telegram"))
    return rows


def apply_source_preference(rows: list, preference: str) -> list:
    """Drop duplicate media entries when both sources offer the same title.

    Keeps the preferred source's row ("telegram" or "idlix"); rows present in
    only one source always stay.
    """
    groups = {}
    for row in rows:
        key = (
            str(row.get("title", "")).strip().lower(),
            str(row.get("year", "")),
            row.get("media_type", ""),
            row.get("season"), row.get("episode"),
        )
        groups.setdefault(key, []).append(row)
    kept = []
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue
        preferred = [r for r in group
                     if r.get("__source__") == preference] or group
        kept.append(preferred[0])
    return kept


def format_hybrid_table(rows: list) -> Table:
    table = Table(title="[bold cyan]🔍 Hasil Pencarian[/bold cyan]",
                  header_style="bold magenta", show_header=True, expand=True)
    table.add_column("No", justify="right", style="cyan")
    table.add_column("Sumber", justify="center")
    table.add_column("Judul", style="bold white")
    table.add_column("Tahun", justify="center", style="yellow")
    table.add_column("Tipe", justify="center")
    table.add_column("Info", style="dim")
    for idx, row in enumerate(rows, start=1):
        if row.get("__source__") == "telegram":
            source = "[magenta]📡 TELEGRAM[/magenta]"
            info = human_size(row.get("file_size", 0))
            media_type = row.get("media_type", "")
        else:
            source = "[blue]🌐 IDLIX[/blue]"
            info = row.get("url", "")
            media_type = row.get("type", "")
        table.add_row(
            str(idx), source, row.get("title", ""),
            str(row.get("year", "") or "-"), media_type, info,
        )
    return table


