from unittest.mock import MagicMock, patch
import pytest

from src.scraper import fetch_featured_content, parse_featured_html

MOCK_HTML = """
<html>
<body>
  <div id="featured-titles">
    <article class="item movies">
      <div class="poster">
        <img src="https://image.tmdb.org/t/p/w185/poster1.jpg" alt="Movie Title 1">
        <div class="rating">8.5</div>
      </div>
      <div class="data">
        <h3><a href="https://z2.idlixku.com/movie/test-movie-1/">Test Movie 1</a></h3>
        <span>2024</span>
      </div>
    </article>
    <article class="item tvshows">
      <div class="poster">
        <img src="https://image.tmdb.org/t/p/w185/poster2.jpg" alt="TV Show 1">
        <div class="rating">9.0</div>
      </div>
      <div class="data">
        <h3><a href="https://z2.idlixku.com/tvshows/test-series-1/">Test Series 1</a></h3>
        <span>2024</span>
      </div>
    </article>
  </div>
</body>
</html>
"""

MOCK_HTML_FALLBACK = """
<html>
<body>
  <div>
    <article class="item">
      <div class="title"><a href="https://z2.idlixku.com/movie/fallback-movie/">Fallback Movie</a></div>
    </article>
  </div>
</body>
</html>
"""


def test_parse_featured_html():
    items = parse_featured_html(MOCK_HTML)
    assert len(items) == 2

    assert items[0]["title"] == "Test Movie 1"
    assert items[0]["url"] == "https://z2.idlixku.com/movie/test-movie-1/"
    assert items[0]["rating"] == "8.5"
    assert items[0]["type"] == "Movie"
    assert items[0]["poster"] == "https://image.tmdb.org/t/p/w185/poster1.jpg"

    assert items[1]["title"] == "Test Series 1"
    assert items[1]["url"] == "https://z2.idlixku.com/tvshows/test-series-1/"
    assert items[1]["rating"] == "9.0"
    assert items[1]["type"] == "TV Series"
    assert items[1]["poster"] == "https://image.tmdb.org/t/p/w185/poster2.jpg"


def test_parse_featured_html_fallback_and_defaults():
    items = parse_featured_html(MOCK_HTML_FALLBACK)
    assert len(items) == 1
    assert items[0]["title"] == "Fallback Movie"
    assert items[0]["url"] == "https://z2.idlixku.com/movie/fallback-movie/"
    assert items[0]["rating"] == "N/A"
    assert items[0]["type"] == "Movie"
    assert items[0]["poster"] == ""


@patch("src.scraper.fetch_featured_with_playwright")
@patch("src.scraper.requests.get")
def test_fetch_featured_content_fallback_success(mock_get, mock_pw):
    mock_pw.return_value = []
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = MOCK_HTML
    mock_get.return_value = mock_response

    items = fetch_featured_content("https://z2.idlixku.com/")
    assert len(items) == 2
    mock_get.assert_called_once()


@patch("src.scraper.fetch_featured_with_playwright")
@patch("src.scraper.requests.get")
def test_fetch_featured_content_http_error(mock_get, mock_pw):
    mock_pw.return_value = []
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_get.return_value = mock_response

    with pytest.raises(Exception, match="HTTP Status 403"):
        fetch_featured_content("https://z2.idlixku.com/")


@patch("src.scraper.fetch_featured_with_playwright")
def test_fetch_featured_content_playwright_success(mock_pw):
    mock_pw.return_value = [
        {"title": "Supergirl", "url": "https://z2.idlixku.com/movie/supergirl-2026", "rating": "6.2", "type": "Movie", "poster": ""}
    ]
    items = fetch_featured_content("https://z2.idlixku.com/")
    assert len(items) == 1
    assert items[0]["title"] == "Supergirl"


@patch("src.scraper.requests.get")
def test_search_content_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Avatar",
                "contentType": "movie",
                "slug": "avatar-2009",
                "releaseDate": "2009-12-18",
                "voteAverage": 7.9
            },
            {
                "name": "Avatar: The Last Airbender",
                "contentType": "tv_series",
                "slug": "avatar-the-last-airbender-2024",
                "releaseDate": "2024-02-22",
                "voteAverage": 8.1
            }
        ]
    }
    mock_get.return_value = mock_response

    from src.scraper import search_content
    items = search_content("https://z2.idlixku.com/", "avatar")

    assert len(items) == 2
    assert items[0]["title"] == "Avatar"
    assert items[0]["url"] == "https://z2.idlixku.com/movie/avatar-2009"
    assert items[0]["type"] == "Movie"
    assert items[0]["year"] == "2009"
    assert items[0]["rating"] == "7.9"

    assert items[1]["title"] == "Avatar: The Last Airbender"
    assert items[1]["url"] == "https://z2.idlixku.com/series/avatar-the-last-airbender-2024"
    assert items[1]["type"] == "TV Series"
    assert items[1]["year"] == "2024"
    assert items[1]["rating"] == "8.1"

