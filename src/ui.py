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
        f"[bold cyan]I AM NOT PIRATES CLI[/bold cyan]\nTarget URL: [yellow]{active_url}[/yellow]",
        title="[bold green]I AM NOT PIRATES[/bold green]",
        subtitle="Streaming & Media Explorer",
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
