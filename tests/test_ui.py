from io import StringIO
from rich.console import Console
from rich.table import Table

from src.ui import (
    format_featured_table,
    print_error,
    print_header,
    print_success,
)


def test_format_featured_table_columns_and_rows():
    sample_items = [
        {
            "title": "Inception 2010",
            "type": "Movie",
            "rating": "8.8",
            "quality": "WEB-DL",
            "url": "https://z2.idlixku.com/movie/inception-2010/",
        },
        {
            "title": "Breaking Bad",
            "type": "TV Series",
            "rating": "9.5",
            "quality": "HDTV",
            "url": "https://z2.idlixku.com/tvshows/breaking-bad/",
        },
    ]

    table = format_featured_table(sample_items)

    assert isinstance(table, Table)
    column_headers = [col.header for col in table.columns]
    assert column_headers == ["No", "Title", "Year", "Type", "Quality", "Rating", "URL"]
    assert table.row_count == 2


def test_format_featured_table_empty():
    table = format_featured_table([])
    assert isinstance(table, Table)
    assert table.row_count == 0
    column_headers = [col.header for col in table.columns]
    assert column_headers == ["No", "Title", "Year", "Type", "Quality", "Rating", "URL"]


def test_format_featured_table_missing_keys():
    incomplete_items = [{"title": "Unknown Stream"}]
    table = format_featured_table(incomplete_items)
    assert isinstance(table, Table)
    assert table.row_count == 1


def test_format_featured_table_year_extraction():
    sample_items = [
        {"title": "Supergirl 2026", "type": "Movie", "rating": "6.2", "url": "https://z2.idlixku.com/movie/supergirl-2026"},
        {"title": "A Shop for Killers", "type": "TV Series", "rating": "8.2", "url": "https://z2.idlixku.com/series/a-shop-for-killers-2024"},
    ]
    table = format_featured_table(sample_items)
    column_headers = [col.header for col in table.columns]
    assert column_headers == ["No", "Title", "Year", "Type", "Quality", "Rating", "URL"]
    assert "Year" in column_headers
    assert "Quality" in column_headers


def test_print_header():
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    print_header("https://z2.idlixku.com/", console=console)
    output = buf.getvalue()

    assert "I AM NOT PIRATES" in output
    assert "https://z2.idlixku.com/" in output


def test_print_error():
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    print_error("Failed to fetch page", console=console)
    output = buf.getvalue()

    assert "ERROR" in output
    assert "Failed to fetch page" in output


def test_print_success():
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    print_success("Operation completed", console=console)
    output = buf.getvalue()

    assert "SUCCESS" in output
    assert "Operation completed" in output
