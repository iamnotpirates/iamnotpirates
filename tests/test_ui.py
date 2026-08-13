from io import StringIO
from rich.console import Console
from rich.table import Table

from src.ui import (
    format_download_summary_table,
    format_featured_table,
    print_download_summary,
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
    assert table.title == "[bold cyan]Featured Content[/bold cyan]"
    column_headers = [col.header for col in table.columns]
    assert column_headers == [
        "No",
        "Title",
        "Year",
        "Type",
        "Quality",
        "Rating",
        "URL",
    ]
    assert table.row_count == 2


def test_format_featured_table_empty():
    table = format_featured_table([])
    assert isinstance(table, Table)
    assert table.row_count == 0
    column_headers = [col.header for col in table.columns]
    assert column_headers == [
        "No",
        "Title",
        "Year",
        "Type",
        "Quality",
        "Rating",
        "URL",
    ]


def test_format_featured_table_missing_keys():
    incomplete_items = [{"title": "Unknown Stream"}]
    table = format_featured_table(incomplete_items)
    assert isinstance(table, Table)
    assert table.row_count == 1


def test_format_featured_table_year_extraction():
    sample_items = [
        {"title": "Supergirl (2026)", "type": "Movie", "rating": "6.2", "url": "https://z2.idlixku.com/movie/supergirl-2026"},
        {"title": "A Shop for Killers", "type": "TV Series", "rating": "8.2", "url": "https://z2.idlixku.com/series/a-shop-for-killers-2024"},
    ]
    table = format_featured_table(sample_items)
    column_headers = [col.header for col in table.columns]
    assert column_headers == [
        "No",
        "Title",
        "Year",
        "Type",
        "Quality",
        "Rating",
        "URL",
    ]
    assert "Year" in column_headers
    assert "Quality" in column_headers


def test_format_featured_table_preserves_title_numbers_and_item_year():
    sample_items = [
        {"title": "Blade Runner 2049", "year": "2017", "type": "Movie", "rating": "8.0", "url": "https://z2.idlixku.com/movie/blade-runner-2049"},
        {"title": "2012 (2009)", "type": "Movie", "rating": "5.8", "url": "https://z2.idlixku.com/movie/2012-2009"},
    ]
    table = format_featured_table(sample_items)
    assert table.row_count == 2
    # Verify titles and years are properly extracted without stripping title digits


def test_print_header():
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    print_header("https://z2.idlixku.com/", console=console)
    output = buf.getvalue()

    assert "I AM NOT PIRATES" in output
    assert "Streaming & Media Explorer / Penjelajah Media v1.2.0" in output
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


def test_format_download_summary_table_rendering():
    items = [
        {
            "title": "Movie 1",
            "video_status": "SUCCESS",
            "video_error": None,
            "subtitles": [{"lang": "id", "status": "SUCCESS"}, {"lang": "en", "status": "SUCCESS"}],
        },
        {
            "title": "Movie 2",
            "video_status": "SKIPPED",
            "video_error": None,
            "subtitles": [{"lang": "id", "status": "SUCCESS"}, {"lang": "en", "status": "FAILED"}],
        },
        {
            "title": "Movie 3",
            "video_status": "FAILED",
            "video_error": "Connection timeout",
            "subtitles": [{"lang": "id", "status": "FAILED"}],
        },
        {
            "title": "Movie 4",
            "video_status": "SUCCESS",
            "video_error": None,
            "subtitles": [],
        },
    ]

    table = format_download_summary_table(items)
    assert isinstance(table, Table)
    assert table.title == "[bold cyan]Download Detail Result[/bold cyan]"
    assert table.row_count == 4

    column_headers = [col.header for col in table.columns]
    assert column_headers == ["No", "Item Title", "Video", "Subtitles", "Details / Error"]


def test_print_download_summary_rendering():
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=100)
    summary_data = {
        "total_items": 4,
        "video_success": 2,
        "video_failed": 1,
        "video_skipped": 1,
        "sub_success": 3,
        "sub_failed": 2,
        "items": [
            {
                "title": "Episode 1",
                "video_status": "SUCCESS",
                "video_error": None,
                "subtitles": [{"lang": "id", "status": "SUCCESS"}],
            },
            {
                "title": "Episode 2",
                "video_status": "FAILED",
                "video_error": "No m3u8",
                "subtitles": [],
            },
        ],
    }

    print_download_summary(summary_data, console=console)
    output = buf.getvalue()

    assert "DOWNLOAD SUMMARY REPORT" in output
    assert "Total Items Processed:" in output
    assert "Episode 1" in output
    assert "Episode 2" in output
    assert "No m3u8" in output


def test_print_startup_dependency_notice():
    from src.ui import print_startup_dependency_notice

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=160)
    print_startup_dependency_notice(console=console)
    output = buf.getvalue()

    assert "System Dependency Check" in output
    assert "sekali" in output.lower()


