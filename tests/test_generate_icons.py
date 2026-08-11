import os
import io
import pytest
from pathlib import Path
from PIL import Image

# Import target script module
import scripts.generate_icons as generate_icons_module
from scripts.generate_icons import render_svg_to_image, generate_icons, main


def test_logo_svg_source_exists():
    logo_path = Path("assets/logo.svg")
    assert logo_path.exists(), "Source SVG assets/logo.svg must exist"


def test_render_svg_to_image():
    logo_path = Path("assets/logo.svg")
    img = render_svg_to_image(logo_path, size=512)
    assert isinstance(img, Image.Image)
    assert img.size == (512, 512)
    assert img.mode == "RGBA"


def test_generate_icons_creates_valid_png_and_ico(tmp_path):
    svg_path = Path("assets/logo.svg")
    out_png = tmp_path / "test_icon.png"
    out_ico = tmp_path / "test_icon.ico"

    generate_icons(svg_path, out_png, out_ico)

    assert out_png.exists()
    assert out_ico.exists()

    # Validate PNG specs
    with Image.open(out_png) as png_img:
        assert png_img.format == "PNG"
        assert png_img.size == (512, 512)
        assert png_img.mode == "RGBA"

    # Validate ICO specs
    with Image.open(out_ico) as ico_img:
        assert ico_img.format == "ICO"
        ico_sizes = ico_img.info.get("sizes")
        expected_sizes = {(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
        if ico_sizes:
            assert expected_sizes.issubset(set(ico_sizes)) or ico_sizes == expected_sizes


def test_render_svg_fallback_pillow(monkeypatch):
    """Test pure Pillow fallback when external rendering libraries fail or are unavailable."""
    logo_path = Path("assets/logo.svg")
    
    # Mock renderers to raise Exception
    monkeypatch.setattr(generate_icons_module, "_try_cairosvg", lambda svg, size: None)
    monkeypatch.setattr(generate_icons_module, "_try_pymupdf", lambda svg, size: None)
    monkeypatch.setattr(generate_icons_module, "_try_svglib", lambda svg, size: None)

    img = render_svg_to_image(logo_path, size=512)
    assert isinstance(img, Image.Image)
    assert img.size == (512, 512)
    assert img.mode == "RGBA"


def test_assets_icons_are_up_to_date():
    png_path = Path("assets/icon.png")
    ico_path = Path("assets/icon.ico")

    assert png_path.exists(), "assets/icon.png does not exist"
    assert ico_path.exists(), "assets/icon.ico does not exist"

    with Image.open(png_path) as img:
        assert img.size == (512, 512)
        assert img.mode == "RGBA"

    with Image.open(ico_path) as img:
        assert img.format == "ICO"
