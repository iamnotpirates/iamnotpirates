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

def test_get_download_dir_default():
    empty_config = {}
    expected_default = os.path.join(os.path.expanduser("~"), "Downloads")
    assert get_download_dir(empty_config) == expected_default

def test_get_download_dir_custom():
    custom_config = {"download_dir": "/custom/downloads"}
    assert get_download_dir(custom_config) == "/custom/downloads"

def test_set_download_dir():
    config = load_config(TEST_CONFIG)
    new_path = "/path/to/my_downloads"
    updated_config = set_download_dir(config, new_path, config_path=TEST_CONFIG)
    assert updated_config["download_dir"] == new_path

    reloaded_config = load_config(TEST_CONFIG)
    assert get_download_dir(reloaded_config) == new_path

