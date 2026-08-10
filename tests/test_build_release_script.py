import importlib
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_build_release_script_exists():
    script_path = ROOT_DIR / "scripts" / "build_release.py"
    assert script_path.exists(), "scripts/build_release.py does not exist"


def test_build_release_script_imports_cleanly():
    import scripts.build_release as build_release

    assert hasattr(build_release, "clean_build_artifacts")
    assert hasattr(build_release, "build_executable")


def test_clean_build_artifacts_removes_mock_folders(tmp_path):
    import scripts.build_release as build_release

    build_dir = tmp_path / "build"
    dist_dir = tmp_path / "dist"

    build_dir.mkdir()
    dist_dir.mkdir()

    (build_dir / "dummy_build.txt").write_text("test build artifact", encoding="utf-8")
    (dist_dir / "dummy_exe.exe").write_text("test dist artifact", encoding="utf-8")

    assert build_dir.exists()
    assert dist_dir.exists()

    build_release.clean_build_artifacts(tmp_path)

    assert not build_dir.exists(), "build folder was not removed"
    assert not dist_dir.exists(), "dist folder was not removed"


def test_clean_build_artifacts_handles_nonexistent_folders(tmp_path):
    import scripts.build_release as build_release

    non_existent_build = tmp_path / "build"
    non_existent_dist = tmp_path / "dist"

    assert not non_existent_build.exists()
    assert not non_existent_dist.exists()

    # Should run without error when directories do not exist
    build_release.clean_build_artifacts(tmp_path)

    assert not non_existent_build.exists()
    assert not non_existent_dist.exists()
