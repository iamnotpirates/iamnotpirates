# SVG Logo & Icon Generation Design Specification

## Overview
Design specification for introducing a master SVG logo (`assets/logo.svg`) and automated icon generation pipeline (`scripts/generate_icons.py`) for the `iamnotpirates` repository. The new SVG logo uses a Modern Minimalist Jolly Roger + Media Play concept, structured specifically for easy AI-assisted editing and clean multi-resolution rendering (`icon.png` and `icon.ico`).

## Target Files & Output Artifacts

### 1. Master Vector Logo
- **Path**: `assets/logo.svg`
- **Format**: SVG 1.1 compliant vector graphics.
- **Canvas Size**: `viewBox="0 0 512 512"`.

### 2. Icon Generation Script
- **Path**: `scripts/generate_icons.py`
- **Purpose**: Reads `assets/logo.svg`, replaces existing legacy raster assets (`assets/icon.png`, `assets/icon.ico`), and produces high-quality PNG and ICO files.

### 3. Generated Assets
- **Path**: `assets/icon.png` (512x512 PNG, regenerated).
- **Path**: `assets/icon.ico` (Multi-resolution Windows Icon file: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256, regenerated).

---

## Visual Concept & Styling Specs

### Concept: Modern Minimalist Jolly Roger + Media Play
- **Main Emblem**: Stylized skull structure with the right eye socket integrated into a **Crimson Media Play Button** (`#FF2E4C`).
- **Background Elements**: Crossed pirate swords/bones at a symmetrical 45-degree angle behind the skull.
- **Header Accent**: Pirate bandana with gold/amber accent highlight (`#FFD700`).

### Color Palette & CSS Variables Structure
The SVG embeds CSS variables within a `<style>` block to ensure AI tools or developers can instantly modify theme colors:

```xml
<style>
  :root {
    --primary-red: #FF2E4C;    /* Crimson Media Play Accent */
    --gold-accent: #FFD700;    /* Amber/Gold Accent Highlight */
    --bone-white: #F8FAFC;     /* Structure White */
    --slate-dark: #0F172A;     /* Dark Slate Contrast */
    --shadow-dark: #020617;    /* Deep Shadow Layer */
  }
</style>
```

### Semantic Layer Grouping (AI-Editable Friendly)
All SVG elements are cleanly grouped with distinct XML IDs:
- `<g id="background-layer">`: Canvas background (supports toggleable transparency).
- `<g id="crossbones-layer">`: Crossed bones/swords silhouette.
- `<g id="skull-structure-layer">`: Main skull outline, jaw, and teeth geometry.
- `<g id="media-play-eye-layer">`: Triangle play icon with crimson gradient accent.
- `<g id="bandana-accents-layer">`: Headband and gold accent trim.

---

## Icon Pipeline & Conversion Strategy

1. **Clean Legacy Assets**: Remove old `assets/icon.png` and `assets/icon.ico`.
2. **Master Vector Creation**: Create pure XML SVG code in `assets/logo.svg`.
3. **Automated Conversion**: Implement `scripts/generate_icons.py` using Python (`cairosvg`, `Pillow`, or standard SVG parsing/rendering) to export:
   - High-res PNG `assets/icon.png`
   - Multi-size Windows ICO `assets/icon.ico`
4. **PyInstaller Integration**: Verify `IAmNotPirates.spec` and `scripts/build_release.py` continue to build using the updated `assets/icon.ico`.

---

## Verification Plan

### Automated / Command Verification
- Run `python scripts/generate_icons.py` to test PNG/ICO generation.
- Run `pytest` to ensure no test regressions.
- Verify file sizes and resolution layers of `assets/icon.ico` and `assets/icon.png`.

### Manual Verification
- Visual inspection of `assets/logo.svg` scaling and rendering.
- Verify clear visibility at small (16x16) icon scale.
