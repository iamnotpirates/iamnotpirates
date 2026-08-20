"""Tests for src/n_m3u8dl_manager.py — N_m3u8DL-RE binary manager."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import n_m3u8dl_manager


class TestGetBinaryPath(unittest.TestCase):
    def test_get_binary_path_returns_expected_location(self):
        path = n_m3u8dl_manager.get_binary_path()
        self.assertIn(".iamnotpirates", path)
        self.assertIn("bin", path)
        self.assertTrue(path.endswith("N_m3u8DL-RE.exe"))


class TestEnsureBinary(unittest.TestCase):
    @patch("n_m3u8dl_manager.os.path.exists", return_value=True)
    def test_ensure_binary_returns_path_if_exists(self, mock_exists):
        """If binary already cached, return path immediately without downloading."""
        result = n_m3u8dl_manager.ensure_binary()
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith("N_m3u8DL-RE.exe"))
        # requests.get should NOT have been called
        mock_exists.assert_called()

    @patch("n_m3u8dl_manager.zipfile.ZipFile")
    @patch("n_m3u8dl_manager.requests.get")
    @patch("n_m3u8dl_manager.os.makedirs")
    @patch("n_m3u8dl_manager.os.path.exists", return_value=False)
    def test_ensure_binary_downloads_if_missing(
        self, mock_exists, mock_makedirs, mock_get, mock_zipfile
    ):
        """If binary missing, download from GitHub and extract exe."""
        # Mock GitHub API response
        api_response = MagicMock()
        api_response.status_code = 200
        api_response.json.return_value = {
            "assets": [
                {
                    "name": "N_m3u8DL-RE_v0.3.0_win-x64_20240101.zip",
                    "browser_download_url": "https://example.com/fake.zip",
                }
            ]
        }

        # Mock zip download response
        zip_response = MagicMock()
        zip_response.status_code = 200
        zip_response.content = b"PK\x03\x04fakezipdata"

        mock_get.side_effect = [api_response, zip_response]

        # Mock zipfile extraction
        mock_zip_instance = MagicMock()
        mock_zipfile.return_value.__enter__ = MagicMock(return_value=mock_zip_instance)
        mock_zipfile.return_value.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", unittest.mock.mock_open()):
            result = n_m3u8dl_manager.ensure_binary()

        self.assertIsNotNone(result)
        self.assertTrue(result.endswith("N_m3u8DL-RE.exe"))
        mock_get.assert_called()




class TestDownloadWithRe(unittest.TestCase):
    @patch("n_m3u8dl_manager.subprocess.run")
    @patch("n_m3u8dl_manager.ensure_binary")
    def test_download_with_re_success(self, mock_ensure, mock_run):
        """subprocess.run returncode=0 → True."""
        mock_ensure.return_value = r"C:\fake\.iamnotpirates\bin\N_m3u8DL-RE.exe"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        result = n_m3u8dl_manager.download_with_re(
            "http://example.com/index.m3u8",
            r"C:\output",
            "TestMovie",
        )
        self.assertTrue(result)

    @patch("n_m3u8dl_manager.subprocess.run")
    @patch("n_m3u8dl_manager.ensure_binary")
    def test_download_with_re_failure(self, mock_ensure, mock_run):
        """subprocess.run returncode=1 → False."""
        mock_ensure.return_value = r"C:\fake\.iamnotpirates\bin\N_m3u8DL-RE.exe"
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        result = n_m3u8dl_manager.download_with_re(
            "http://example.com/index.m3u8",
            r"C:\output",
            "TestMovie",
        )
        self.assertFalse(result)

    @patch("n_m3u8dl_manager.subprocess.run")
    @patch("n_m3u8dl_manager.ensure_binary")
    def test_download_with_re_no_binary_returns_false(self, mock_ensure, mock_run):
        """If ensure_binary returns None (download failed) → False."""
        mock_ensure.return_value = None
        result = n_m3u8dl_manager.download_with_re(
            "http://example.com/index.m3u8",
            r"C:\output",
            "TestMovie",
        )
        self.assertFalse(result)
    @patch("n_m3u8dl_manager.shutil.move")
    @patch("n_m3u8dl_manager.os.remove")
    @patch("n_m3u8dl_manager.os.path.exists")
    @patch("n_m3u8dl_manager.subprocess.run")
    @patch("n_m3u8dl_manager.ensure_binary")
    def test_download_with_re_auto_heal(self, mock_ensure, mock_run, mock_exists, mock_remove, mock_move):
        """If expected .mp4 is missing but .MUX.mp4 exists, auto-heal renames it and cleans up .ts."""
        mock_ensure.return_value = r"C:\fake\.iamnotpirates\bin\N_m3u8DL-RE.exe"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        # Mock path existence for auto-heal scenario
        mock_exists.side_effect = lambda path: ".MUX.mp4" in path or ".ts" in path

        result = n_m3u8dl_manager.download_with_re(
            "http://example.com/index.m3u8",
            r"C:\output",
            "TestMovie",
        )
        self.assertTrue(result)
        mock_move.assert_called_once_with(r"C:\output\TestMovie.MUX.mp4", r"C:\output\TestMovie.mp4")
        mock_remove.assert_called_once_with(r"C:\output\TestMovie.ts")

    @patch("n_m3u8dl_manager.shutil.move")
    @patch("n_m3u8dl_manager.os.remove")
    @patch("n_m3u8dl_manager.os.path.exists")
    @patch("n_m3u8dl_manager.subprocess.run")
    @patch("n_m3u8dl_manager.ensure_binary")
    def test_download_with_re_auto_heal_remove_fails(self, mock_ensure, mock_run, mock_exists, mock_remove, mock_move):
        """Even if cleanup of .ts file fails, auto-heal should succeed."""
        mock_ensure.return_value = r"C:\fake\.iamnotpirates\bin\N_m3u8DL-RE.exe"
        mock_proc = MagicMock()
        mock_proc.returncode = 1  # Subprocess failed/crashed
        mock_run.return_value = mock_proc

        mock_exists.side_effect = lambda path: ".MUX.mp4" in path or ".ts" in path
        mock_remove.side_effect = OSError("Locked file")

        result = n_m3u8dl_manager.download_with_re(
            "http://example.com/index.m3u8",
            r"C:\output",
            "TestMovie",
        )
        self.assertTrue(result)
        mock_move.assert_called_once_with(r"C:\output\TestMovie.MUX.mp4", r"C:\output\TestMovie.mp4")
        mock_remove.assert_called_once_with(r"C:\output\TestMovie.ts")


if __name__ == "__main__":
    unittest.main()
