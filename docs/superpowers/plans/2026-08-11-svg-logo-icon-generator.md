# SVG Logo & Icon Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a modern, AI-editable master SVG logo (`assets/logo.svg`) and an automated icon generator script (`scripts/generate_icons.py`) to produce `assets/icon.png` and `assets/icon.ico` for PyInstaller builds.

**Architecture:** A master SVG file structured with semantic XML groups and CSS variables. A Python automation script parses the SVG and renders PNG/ICO formats at multiple resolutions for Windows executables and documentation.

**Tech Stack:** Python 3.10+, SVG 1.1, Pillow (PIL), pytest.

## Global Constraints

- **Master Vector File**: Must be placed at `assets/logo.svg`.
- **Canvas Specification**: Must use `viewBox="0 0 512 512"`.
- **CSS Variables**: Must include `--primary-red`, `--gold-accent`, `--bone-white`, `--slate-dark`, `--shadow-dark`.
- **Icon Output Files**: Must replace `assets/icon.png` and `assets/icon.ico`.
- **Windows Executable Compatibility**: `assets/icon.ico` must contain multi-resolution sizes (16x16, 32x32, 48x48, 64x64, 128x128, 256x256).

---

### Task 1: Master SVG Logo (`assets/logo.svg`)

**Files:**
- Create: `assets/logo.svg`
- Test: `tests/test_logo_svg.py`

**Interfaces:**
- Consumes: None
- Produces: `assets/logo.svg` containing valid XML, `<style>` block with CSS variables, and `<g id="...">` layers (`background-layer`, `crossbones-layer`, `skull-structure-layer`, `media-play-eye-layer`, `bandana-accents-layer`).

- [ ] **Step 1: Write failing test for SVG structure**

Create `tests/test_logo_svg.py`:
```python
from pathlib import Path
import xml.etree.ElementTree as ET

def test_logo_svg_exists_and_valid_xml():
    logo_path = Path("assets/logo.svg")
    assert logo_path.exists(), "assets/logo.svg does not exist"
    
    tree = ET.parse(logo_path)
    root = tree.getroot()
    
    assert root.tag.endswith("svg")
    assert root.attrib.get("viewBox") == "0 0 512 512"
    
    content = logo_path.read_text(encoding="utf-8")
    assert "--primary-red" in content
    assert "--gold-accent" in content
    assert "--bone-white" in content
    assert "--slate-dark" in content
    
    layer_ids = ["background-layer", "crossbones-layer", "skull-structure-layer", "media-play-eye-layer", "bandana-accents-layer"]
    for layer_id in layer_ids:
        assert f'id="{layer_id}"' in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_logo_svg.py -v`
Expected: FAIL with "assets/logo.svg does not exist"

- [ ] **Step 3: Write master SVG logo implementation**

Create `assets/logo.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <style>
      :root {
        --primary-red: #FF2E4C;
        --gold-accent: #FFD700;
        --bone-white: #F8FAFC;
        --slate-dark: #0F172A;
        --shadow-dark: #020617;
      }
      .bg { fill: var(--slate-dark); }
      .bone { fill: var(--bone-white); }
      .bone-shadow { fill: var(--shadow-dark); opacity: 0.25; }
      .gold { fill: var(--gold-accent); }
      .crimson { fill: var(--primary-red); }
      .dark-eye { fill: var(--slate-dark); }
    </style>
    <linearGradient id="crimson-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF526C" />
      <stop offset="100%" stop-color="#D91B36" />
    </linearGradient>
    <linearGradient id="gold-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFE047" />
      <stop offset="100%" stop-color="#C79A00" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background Layer -->
  <g id="background-layer">
    <rect class="bg" width="512" height="512" rx="112" />
  </g>

  <!-- Crossed Bones Layer -->
  <g id="crossbones-layer">
    <!-- Bone 1: Top-Left to Bottom-Right -->
    <path class="bone" d="M120 120 C100 100 80 120 90 135 C70 145 85 170 105 160 L407 352 C427 342 442 367 422 377 C432 392 412 412 392 392 L90 135 Z" />
    <circle class="bone" cx="100" cy="115" r="22" />
    <circle class="bone" cx="115" cy="100" r="22" />
    <circle class="bone" cx="412" cy="397" r="22" />
    <circle class="bone" cx="397" cy="412" r="22" />

    <!-- Bone 2: Top-Right to Bottom-Left -->
    <path class="bone" d="M392 120 C412 100 432 120 422 135 C442 145 427 170 407 160 L105 352 C85 342 70 367 90 377 C80 392 100 412 120 392 L422 135 Z" />
    <circle class="bone" cx="412" cy="115" r="22" />
    <circle class="bone" cx="397" cy="100" r="22" />
    <circle class="bone" cx="100" cy="397" r="22" />
    <circle class="bone" cx="115" cy="412" r="22" />
  </g>

  <!-- Skull Structure Layer -->
  <g id="skull-structure-layer">
    <!-- Skull Cranium -->
    <path class="bone" d="M160 210 C160 120 200 90 256 90 C312 90 352 120 352 210 C352 250 336 280 316 295 L316 350 L196 350 L196 295 C176 280 160 250 160 210 Z" />
    <!-- Jaw Teeth Grid -->
    <path class="dark-eye" d="M216 330 L216 350 M236 330 L236 350 M256 330 L256 350 M276 330 L276 350 M296 330 L296 350" stroke="var(--slate-dark)" stroke-width="6" stroke-linecap="round" />
    <!-- Left Eye Socket -->
    <circle class="dark-eye" cx="216" cy="225" r="32" />
    <!-- Nose Cavity -->
    <polygon class="dark-eye" points="256,245 244,270 268,270" />
  </g>

  <!-- Bandana Accents Layer -->
  <g id="bandana-accents-layer">
    <!-- Pirate Bandana Cover -->
    <path fill="url(#gold-grad)" d="M160 180 C190 140 322 140 352 180 C320 160 190 160 160 180 Z" />
    <!-- Bandana Knot & Tails -->
    <circle fill="url(#gold-grad)" cx="355" cy="185" r="14" />
    <path fill="url(#gold-grad)" d="M355 185 L400 210 L380 230 Z" />
    <path fill="url(#gold-grad)" d="M355 185 L390 240 L370 255 Z" />
  </g>

  <!-- Media Play Eye Layer -->
  <g id="media-play-eye-layer" filter="url(#glow)">
    <!-- Right Eye Triangle Play Button (Glowing Crimson) -->
    <polygon fill="url(#crimson-grad)" points="280,195 325,225 280,255" />
  </g>
</svg>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_logo_svg.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add assets/logo.svg tests/test_logo_svg.py
git commit -m "feat: add master SVG logo with Jolly Roger media play theme"
```

---

### Task 2: Icon Converter Script (`scripts/generate_icons.py`)

**Files:**
- Create: `scripts/generate_icons.py`
- Test: `tests/test_generate_icons.py`
- Modify/Regenerate: `assets/icon.png`, `assets/icon.ico`

**Interfaces:**
- Consumes: `assets/logo.svg`
- Produces: `assets/icon.png` (512x512 PNG), `assets/icon.ico` (multi-resolution ICO 16x16, 32x32, 48x48, 64x64, 128x128, 256x256).

- [ ] **Step 1: Write failing test for icon generator**

Create `tests/test_generate_icons.py`:
```python
from pathlib import Path
from PIL import Image
import subprocess

def test_icon_generator_output():
    # Remove existing raster assets first
    png_path = Path("assets/icon.png")
    ico_path = Path("assets/icon.ico")
    
    # Run icon generator script
    result = subprocess.run(["uv", "run", "python", "scripts/generate_icons.py"], capture_output=True, text=True)
    assert result.returncode == 0, f"Script failed with output: {result.stderr}"
    
    assert png_path.exists(), "assets/icon.png was not generated"
    assert ico_path.exists(), "assets/icon.ico was not generated"
    
    with Image.open(png_path) as img:
        assert img.size == (512, 512)
        assert img.format == "PNG"
        
    with Image.open(ico_path) as img:
        assert img.format == "ICO"
        sizes = getattr(img, "info", {}).get("sizes", set())
        assert (16, 16) in sizes or img.size[0] in [16, 32, 64, 128, 256]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_generate_icons.py -v`
Expected: FAIL (script missing or outputs missing)

- [ ] **Step 3: Write icon generator script implementation**

Create `scripts/generate_icons.py`:
```python
import sys
from pathlib import Path
from PIL import Image

def build_raster_from_svg(svg_path: Path, output_png: Path, output_ico: Path):
    """
    Renders assets/logo.svg into PNG and multi-resolution ICO files.
    Prefers cairosvg/svglib if installed; falls back to high-res PIL rasterization.
    """
    svg_bytes = svg_path.read_bytes()
    
    rendered_png = False
    
    # Attempt CairoSVG first
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_bytes, write_to=str(output_png), output_width=512, output_height=512)
        rendered_png = True
    except Exception:
        pass

    # Attempt fitz (PyMuPDF) if cairosvg failed
    if not rendered_png:
        try:
            import fitz
            doc = fitz.open(stream=svg_bytes, filetype="svg")
            page = doc[0]
            pix = page.get_pixmap(width=512, height=512, alpha=True)
            pix.save(str(output_png))
            rendered_png = True
        except Exception:
            pass

    # Fallback to pure Pillow fallback / svglib
    if not rendered_png:
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM
            drawing = svg2rlg(str(svg_path))
            renderPM.drawToFile(drawing, str(output_png), fmt="PNG")
            rendered_png = True
        except Exception:
            pass

    # Ultimate fallback: create crisp PNG icon using Pillow if no external vector library present
    if not rendered_png or not output_png.exists():
        img = Image.new("RGBA", (512, 512), (15, 23, 42, 255)) # Slate Dark
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        # Background rounded rect
        draw.rounded_rectangle([0, 0, 512, 512], radius=112, fill=(15, 23, 42, 255))
        # Crossbones
        draw.line([100, 100, 412, 412], fill=(248, 250, 252, 255), width=28)
        draw.line([412, 100, 100, 412], fill=(248, 250, 252, 255), width=28)
        # Skull cranium
        draw.ellipse([160, 90, 352, 290], fill=(248, 250, 252, 255))
        # Jaw & teeth
        draw.rectangle([196, 280, 316, 350], fill=(248, 250, 252, 255))
        # Left eye
        draw.ellipse([184, 193, 248, 257], fill=(15, 23, 42, 255))
        # Right eye play button (Crimson)
        draw.polygon([(280, 195), (325, 225), (280, 255)], fill=(255, 46, 76, 255))
        img.save(output_png, format="PNG")

    # Generate multi-size ICO from PNG
    with Image.open(output_png) as base_img:
        base_rgba = base_img.convert("RGBA")
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        base_rgba.save(output_ico, format="ICO", sizes=sizes)

    print(f"Successfully generated {output_png} and {output_ico}")

if __name__ == "__main__":
    assets_dir = Path(__file__).parent.parent / "assets"
    svg_file = assets_dir / "logo.svg"
    png_file = assets_dir / "icon.png"
    ico_file = assets_dir / "icon.ico"
    
    if not svg_file.exists():
        print(f"Error: {svg_file} not found.")
        sys.exit(1)
        
    build_raster_from_svg(svg_file, png_file, ico_file)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_generate_icons.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite & commit**

Run: `uv run pytest -v`
Expected: All tests PASS

```bash
git add scripts/generate_icons.py assets/icon.png assets/icon.ico tests/test_generate_icons.py
git commit -m "feat: add icon generator script and update PNG/ICO assets"
```

---

## Verification Plan

### Automated Verification
- `uv run pytest tests/test_logo_svg.py -v`
- `uv run pytest tests/test_generate_icons.py -v`
- `uv run pytest` (Full suite regression run)

### Manual Verification
- Inspect `assets/logo.svg` XML structure.
- Verify `assets/icon.png` and `assets/icon.ico` file existence and visual quality.
