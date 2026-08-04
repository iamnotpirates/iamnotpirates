import os
import pytest
from src.config_manager import (
    load_config,
    save_config,
    add_target_url,
    set_active_url,
    delete_target_url,
    get_download_dir,
    set_download_dir,
    set_organize_mode,
)

TEST_CONFIG = "test_config.json"

@pytest.fixture(autouse=True)
def cleanup():
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)
    yield
    if os.path.exists(TEST_CONFIG):
        os.remove(TEST_CONFIG)

def test_load_default_config():
    config = load_config(TEST_CONFIG)
    assert config["active_url"] == "https://z2.idlixku.com/"
    assert config["organize_mode"] == "separate"
    assert len(config["target_urls"]) == 1

def test_add_and_set_active_url():
    load_config(TEST_CONFIG)
    add_target_url("https://idlix.example.com", name="Backup", config_path=TEST_CONFIG)
    config = set_active_url("https://idlix.example.com/", config_path=TEST_CONFIG)
    assert config["active_url"] == "https://idlix.example.com/"
    assert len(config["target_urls"]) == 2

def test_delete_url():
    load_config(TEST_CONFIG)
    add_target_url("https://to-delete.com", config_path=TEST_CONFIG)
    config = delete_target_url("https://to-delete.com/", config_path=TEST_CONFIG)
    assert len(config["target_urls"]) == 1

def test_get_download_dir_separate_and_combined():
    config = {
        "organize_mode": "separate",
        "movies_dir": "/path/movies",
        "series_dir": "/path/series",
        "combined_dir": "/path/combined"
    }
    assert get_download_dir(config, "movie") == "/path/movies"
    assert get_download_dir(config, "series") == "/path/series"

    config["organize_mode"] = "combined"
    assert get_download_dir(config, "movie") == "/path/combined"
    assert get_download_dir(config, "series") == "/path/combined"

def test_set_download_dir():
    config = load_config(TEST_CONFIG)
    set_download_dir(config, "/path/movies_new", media_type="movie", config_path=TEST_CONFIG)
    set_download_dir(config, "/path/series_new", media_type="series", config_path=TEST_CONFIG)

    reloaded = load_config(TEST_CONFIG)
    assert get_download_dir(reloaded, "movie") == "/path/movies_new"
    assert get_download_dir(reloaded, "series") == "/path/series_new"

def test_set_organize_mode():
    config = load_config(TEST_CONFIG)
    set_organize_mode(config, "combined", config_path=TEST_CONFIG)
    reloaded = load_config(TEST_CONFIG)
    assert reloaded["organize_mode"] == "combined"

