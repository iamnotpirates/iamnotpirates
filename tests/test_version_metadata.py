from pathlib import Path
from io import StringIO
from rich.console import Console
import tomllib
from src.ui import print_header


ROOT_DIR = Path(__file__).parent.parent


def test_pyproject_toml_version():
    pyproject_path = ROOT_DIR / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml not found"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    version = data.get("project", {}).get("version")
    assert version == "1.1.0", f"Expected pyproject.toml version to be 1.1.0, got '{version}'"


def test_ui_version():
    ui_path = ROOT_DIR / "src" / "ui.py"
    assert ui_path.exists(), "src/ui.py not found"

    content = ui_path.read_text(encoding="utf-8")
    assert "1.1.0" in content, "Expected '1.1.0' to be in src/ui.py"

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80)
    print_header("https://z2.idlixku.com/", console=console)
    output = buf.getvalue()
    assert "1.1.0" in output, "Expected '1.1.0' to be printed by print_header"


def test_readme_version():
    readme_path = ROOT_DIR / "README.md"
    assert readme_path.exists(), "README.md not found"

    content = readme_path.read_text(encoding="utf-8")
    assert "1.1.0" in content, "Expected '1.1.0' to be in README.md"
