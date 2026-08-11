"""
Script to generate high-resolution PNG and multi-resolution ICO assets from SVG logo.
Supports PyMuPDF (pymupdf), CairoSVG, svglib, and a pure Pillow vector fallback.
"""

import sys
import io
import re
from pathlib import Path
from PIL import Image, ImageDraw

ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _preprocess_svg(svg_path: Path) -> str:
    """Read SVG and resolve CSS variables to hex colors for renderers with limited CSS variable support."""
    content = svg_path.read_text(encoding="utf-8")
    
    # CSS variable dictionary matching logo.svg
    css_vars = {
        "var(--primary-red)": "#FF2E4C",
        "var(--gold-accent)": "#FFD700",
        "var(--bone-white)": "#F8FAFC",
        "var(--slate-dark)": "#0F172A",
        "var(--shadow-dark)": "#020617",
    }
    for var_name, hex_val in css_vars.items():
        content = content.replace(var_name, hex_val)
        
    # Replace percent-based width/height with explicit target view dimensions if needed
    content = re.sub(r'width="100%"', 'width="512"', content)
    content = re.sub(r'height="100%"', 'height="512"', content)
    return content


def _try_pymupdf(svg_path: Path, size: int = 512) -> Image.Image | None:
    try:
        import pymupdf
        svg_content = _preprocess_svg(svg_path)
        doc = pymupdf.open("svg", svg_content.encode("utf-8"))
        page = doc[0]
        rect = page.rect
        scale_x = float(size) / rect.width if rect.width > 0 else 1.0
        scale_y = float(size) / rect.height if rect.height > 0 else 1.0
        mat = pymupdf.Matrix(scale_x, scale_y)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
        if img.size != (size, size):
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return img
    except Exception:
        pass
    return None


def _try_cairosvg(svg_path: Path, size: int = 512) -> Image.Image | None:
    try:
        import cairosvg
        svg_content = _preprocess_svg(svg_path)
        png_bytes = cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            output_width=size,
            output_height=size,
        )
        if png_bytes:
            img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            if img.size != (size, size):
                img = img.resize((size, size), Image.Resampling.LANCZOS)
            return img
    except Exception:
        pass
    return None


def _try_svglib(svg_path: Path, size: int = 512) -> Image.Image | None:
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        
        svg_content = _preprocess_svg(svg_path)
        temp_file = svg_path.parent / ".temp_logo_resolved.svg"
        temp_file.write_text(svg_content, encoding="utf-8")
        try:
            drawing = svg2rlg(str(temp_file))
        finally:
            if temp_file.exists():
                temp_file.unlink()
                
        if drawing:
            scale_x = float(size) / drawing.width if drawing.width > 0 else 1.0
            scale_y = float(size) / drawing.height if drawing.height > 0 else 1.0
            drawing.width = size
            drawing.height = size
            drawing.scale(scale_x, scale_y)
            png_data = renderPM.drawToString(drawing, fmt="PNG")
            img = Image.open(io.BytesIO(png_data)).convert("RGBA")
            if img.size != (size, size):
                img = img.resize((size, size), Image.Resampling.LANCZOS)
            return img
    except Exception:
        pass
    return None


def _pillow_fallback(svg_path: Path, size: int = 512) -> Image.Image:
    """Pure Pillow rendering fallback when external SVG rendering libraries fail or are unavailable."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background circle
    cx, cy = size // 2, size // 2
    r_bg = int(size * 0.47)
    draw.ellipse([cx - r_bg, cy - r_bg, cx + r_bg, cy + r_bg], fill="#0F172A", outline="#FFD700", width=int(size * 0.015))
    
    r_inner = int(size * 0.44)
    draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=None, outline="#FF2E4C", width=int(size * 0.008))
    
    # Crossbones
    bone_w = int(size * 0.06)
    bone_len = int(size * 0.65)
    draw.line([(cx - bone_len // 2, cy - bone_len // 2), (cx + bone_len // 2, cy + bone_len // 2)], fill="#F8FAFC", width=bone_w)
    draw.line([(cx - bone_len // 2, cy + bone_len // 2), (cx + bone_len // 2, cy - bone_len // 2)], fill="#F8FAFC", width=bone_w)
    
    # Skull shape
    skull_w = int(size * 0.38)
    skull_h = int(size * 0.42)
    draw.ellipse([cx - skull_w // 2, cy - skull_h // 2 - int(size * 0.02), cx + skull_w // 2, cy + skull_h // 2 - int(size * 0.02)], fill="#F8FAFC", outline="#020617", width=int(size * 0.01))
    
    jaw_w = int(size * 0.22)
    jaw_h = int(size * 0.15)
    draw.rectangle([cx - jaw_w // 2, cy + int(size * 0.10), cx + jaw_w // 2, cy + int(size * 0.10) + jaw_h], fill="#F8FAFC", outline="#020617", width=int(size * 0.01))
    
    for x_off in [-int(size * 0.06), -int(size * 0.02), int(size * 0.02), int(size * 0.06)]:
        draw.line([(cx + x_off, cy + int(size * 0.14)), (cx + x_off, cy + int(size * 0.23))], fill="#020617", width=int(size * 0.008))
        
    # Eyepatch & Play eye
    eye_r = int(size * 0.07)
    draw.ellipse([cx - int(size * 0.08) - eye_r, cy - int(size * 0.05) - eye_r, cx - int(size * 0.08) + eye_r, cy - int(size * 0.05) + eye_r], fill="#020617", outline="#FFD700", width=int(size * 0.008))
    
    p1 = (cx + int(size * 0.05), cy - int(size * 0.10))
    p2 = (cx + int(size * 0.14), cy - int(size * 0.05))
    p3 = (cx + int(size * 0.05), cy + int(size * 0.00))
    draw.polygon([p1, p2, p3], fill="#FF2E4C", outline="#020617", width=int(size * 0.008))
    
    # Bandana
    draw.arc([cx - skull_w // 2 - int(size * 0.01), cy - skull_h // 2 - int(size * 0.04), cx + skull_w // 2 + int(size * 0.01), cy - skull_h // 2 + int(size * 0.12)], start=180, end=360, fill="#FF2E4C", width=int(size * 0.06))
    
    return img


def render_svg_to_image(svg_path: Path, size: int = 512) -> Image.Image:
    """Attempts SVG renderers in priority order: PyMuPDF -> CairoSVG -> svglib -> Pillow Fallback."""
    # 1. Try PyMuPDF
    img = _try_pymupdf(svg_path, size)
    if img:
        return img

    # 2. Try CairoSVG
    img = _try_cairosvg(svg_path, size)
    if img:
        return img

    # 3. Try svglib
    img = _try_svglib(svg_path, size)
    if img:
        return img

    # 4. Pure Pillow Fallback
    return _pillow_fallback(svg_path, size)


def generate_icons(svg_path: Path, output_png: Path, output_ico: Path) -> None:
    if not svg_path.exists():
        raise FileNotFoundError(f"Source SVG icon not found at {svg_path}")

    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_ico.parent.mkdir(parents=True, exist_ok=True)

    img_512 = render_svg_to_image(svg_path, size=512)
    img_512.save(output_png, format="PNG")
    print(f"Generated PNG icon: {output_png} ({img_512.size[0]}x{img_512.size[1]})")

    img_512.save(output_ico, format="ICO", sizes=ICO_SIZES)
    print(f"Generated ICO icon: {output_ico} (Sizes: {ICO_SIZES})")


def main() -> None:
    svg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets/logo.svg")
    out_png = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("assets/icon.png")
    out_ico = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("assets/icon.ico")

    generate_icons(svg_path, out_png, out_ico)


if __name__ == "__main__":
    main()
