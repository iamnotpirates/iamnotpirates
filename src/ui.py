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
        f"[bold cyan]I AM NOT PIRATES CLI v1.1.0[/bold cyan]\nTarget URL: [yellow]{active_url}[/yellow]",
        title="[bold green]I AM NOT PIRATES[/bold green]",
        subtitle="Streaming & Media Explorer v1.1.0",
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
    table.add_column("Title", style="bold white")
    table.add_column("Year", justify="center", style="yellow")
    table.add_column("Type", style="green")
    table.add_column("Quality", justify="center", style="bold green")
    table.add_column("Rating", justify="center", style="yellow")
    table.add_column("URL", style="blue underline", no_wrap=True)

    for idx, item in enumerate(items, start=1):
        raw_title = item.get("title", "N/A")
        item_url = item.get("url", "")
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", raw_title)
        if year_match:
            year = year_match.group(1)
            clean_title = re.sub(r"\b(19\d\d|20\d\d)\b", "", raw_title).strip()
        else:
            url_year_match = re.search(r"-?(19\d\d|20\d\d)\b", item_url)
            year = url_year_match.group(1) if url_year_match else "N/A"
            clean_title = raw_title

        quality = item.get("quality", "WEB-DL")
        clickable_url = f"[link={item_url}]{item_url}[/link]" if item_url else "N/A"

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

