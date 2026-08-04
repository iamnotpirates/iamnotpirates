"""Tests for src/ffmpeg_manager.py."""
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.ffmpeg_manager import (
    ensure_ffmpeg,
    get_ffmpeg_paths,
    verify_media_file,
)


def test_get_ffmpeg_paths():
    ffmpeg_path, ffprobe_path = get_ffmpeg_paths()
    expected_bin_dir = os.path.join(os.path.expanduser("~"), ".iamnotpirates", "bin")
    assert ffmpeg_path == os.path.join(expected_bin_dir, "ffmpeg.exe")
    assert ffprobe_path == os.path.join(expected_bin_dir, "ffprobe.exe")


@patch("os.path.exists")
def test_ensure_ffmpeg_existing(mock_exists):
    mock_exists.return_value = True
    ffmpeg_path, ffprobe_path = get_ffmpeg_paths()

    result_ffmpeg, result_ffprobe = ensure_ffmpeg()

    assert result_ffmpeg == ffmpeg_path
    assert result_ffprobe == ffprobe_path


@patch("src.ffmpeg_manager.zipfile.ZipFile")
@patch("src.ffmpeg_manager.requests.get")
@patch("os.makedirs")
@patch("os.path.exists")
def test_ensure_ffmpeg_download(mock_exists, mock_makedirs, mock_requests_get, mock_zipfile):
    # Mocking os.path.exists: return True only when open context is executed / after download loop
    created_files = set()

    def fake_exists(path):
        return path in created_files

    mock_exists.side_effect = fake_exists

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"zipbytes"
    mock_requests_get.return_value = mock_resp

    mock_zf = MagicMock()
    mock_zf.namelist.return_value = [
        "ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe",
        "ffmpeg-master-latest-win64-gpl/bin/ffprobe.exe",
    ]
    mock_source = MagicMock()
    mock_source.read.return_value = b"execontent"
    mock_zf.open.return_value.__enter__.return_value = mock_source
    mock_zipfile.return_value.__enter__.return_value = mock_zf

    ffmpeg_path, ffprobe_path = get_ffmpeg_paths()

    def fake_open(path, mode="r", *args, **kwargs):
        if "wb" in mode:
            created_files.add(path)
        return MagicMock()

    with patch("builtins.open", side_effect=fake_open):
        result_ffmpeg, result_ffprobe = ensure_ffmpeg()

    assert result_ffmpeg == ffmpeg_path
    assert result_ffprobe == ffprobe_path




def test_verify_media_file_missing(tmp_path):
    non_existent = str(tmp_path / "missing.mp4")
    result = verify_media_file(non_existent)
    assert result["video_status"] == "MISSING"
    assert result["missing_subtitles"] is False
    assert result["error_message"] is not None


def test_verify_media_file_small_size(tmp_path):
    small_file = tmp_path / "small.mp4"
    small_file.write_bytes(b"12345")  # Less than 1MB
    result = verify_media_file(str(small_file))
    assert result["video_status"] == "MISSING"
    assert result["error_message"] is not None


@patch("os.path.getsize")
@patch("os.path.exists")
@patch("subprocess.run")
def test_verify_media_file_corrupted(mock_run, mock_exists, mock_getsize):
    mock_exists.return_value = True
    mock_getsize.return_value = 2 * 1024 * 1024  # 2MB
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Invalid media")

    result = verify_media_file("dummy.mp4")
    assert result["video_status"] == "CORRUPTED"
    assert result["error_message"] is not None


@patch("os.path.getsize")
@patch("os.path.exists")
@patch("subprocess.run")
def test_verify_media_file_healthy_with_subs(mock_run, mock_exists, mock_getsize):
    def exists_side_effect(path):
        if path == "video.mp4":
            return True
        if path in ("video.id.srt", "video.en.srt", "video.srt"):
            return True
        return False

    mock_exists.side_effect = exists_side_effect
    mock_getsize.return_value = 5 * 1024 * 1024
    mock_run.return_value = MagicMock(returncode=0, stdout="120.5\n", stderr="")

    result = verify_media_file("video.mp4", required_sub_mode="Indonesian")
    assert result["video_status"] == "HEALTHY"
    assert result["missing_subtitles"] is False
    assert result["error_message"] is None


@patch("os.path.getsize")
@patch("os.path.exists")
@patch("subprocess.run")
def test_verify_media_file_healthy_missing_subs(mock_run, mock_exists, mock_getsize):
    def exists_side_effect(path):
        if path == "video.mp4":
            return True
        return False

    mock_exists.side_effect = exists_side_effect
    mock_getsize.return_value = 5 * 1024 * 1024
    mock_run.return_value = MagicMock(returncode=0, stdout="120.5\n", stderr="")

    result = verify_media_file("video.mp4", required_sub_mode="Indonesian")
    assert result["video_status"] == "HEALTHY"
    assert result["missing_subtitles"] is True
    assert result["error_message"] is None
