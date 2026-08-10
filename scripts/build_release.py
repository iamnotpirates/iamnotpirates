import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def clean_build_artifacts(base_dir: Path | str | None = None) -> None:
    """Removes build/ and dist/ directories if they exist."""
    if base_dir is None:
        base_dir = PROJECT_ROOT
    else:
        base_dir = Path(base_dir)

    for folder in ["build", "dist"]:
        folder_path = base_dir / folder
        if folder_path.exists():
            shutil.rmtree(folder_path, ignore_errors=True)


def build_executable() -> Path:
    """Cleans artifacts, executes PyInstaller build, checks executable, and prints file info."""
    clean_build_artifacts()

    spec_file = PROJECT_ROOT / "IAmNotPirates.spec"
    if not spec_file.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_file}")

    print("Building executable with PyInstaller...")
    cmd = ["pyinstaller", str(spec_file), "--noconfirm"]
    subprocess.run(cmd, check=True, cwd=str(PROJECT_ROOT))

    exe_path = PROJECT_ROOT / "dist" / "IAmNotPirates.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"Executable not found at {exe_path}")

    size_bytes = exe_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    print(f"Executable file path: {exe_path.resolve()}")
    print(f"Executable size: {size_mb:.2f} MB")
    return exe_path


if __name__ == "__main__":
    build_executable()
