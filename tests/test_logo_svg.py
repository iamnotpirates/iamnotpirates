import os
import xml.etree.ElementTree as ET
from pathlib import Path

LOGO_PATH = Path("assets/logo.svg")

def test_logo_file_exists():
    assert LOGO_PATH.exists(), f"File {LOGO_PATH} does not exist"

def test_logo_xml_structure_and_viewbox():
    assert LOGO_PATH.exists(), f"File {LOGO_PATH} does not exist"
    tree = ET.parse(LOGO_PATH)
    root = tree.getroot()
    
    # Strip namespace if present
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    assert tag == "svg", f"Root element must be 'svg', found '{tag}'"
    
    viewbox = root.attrib.get("viewBox")
    assert viewbox == "0 0 512 512", f"Expected viewBox='0 0 512 512', got '{viewbox}'"

def test_logo_css_variables():
    assert LOGO_PATH.exists(), f"File {LOGO_PATH} does not exist"
    tree = ET.parse(LOGO_PATH)
    root = tree.getroot()
    
    # Find style elements (namespace agnostic)
    style_elements = [elem for elem in root.iter() if elem.tag.endswith("style")]
    assert len(style_elements) > 0, "No <style> element found in logo.svg"
    
    style_text = "".join(elem.text or "" for elem in style_elements)
    
    required_variables = [
        "--primary-red: #FF2E4C",
        "--gold-accent: #FFD700",
        "--bone-white: #F8FAFC",
        "--slate-dark: #0F172A",
        "--shadow-dark: #020617",
    ]
    
    for var in required_variables:
        assert var in style_text, f"CSS variable '{var}' missing in logo.svg <style> block"

def test_logo_layer_ids():
    assert LOGO_PATH.exists(), f"File {LOGO_PATH} does not exist"
    tree = ET.parse(LOGO_PATH)
    root = tree.getroot()
    
    g_elements = [elem for elem in root.iter() if elem.tag.endswith("g")]
    found_ids = {elem.attrib.get("id") for elem in g_elements if "id" in elem.attrib}
    
    required_layer_ids = {
        "background-layer",
        "crossbones-layer",
        "skull-structure-layer",
        "media-play-eye-layer",
        "bandana-accents-layer",
    }
    
    missing_layers = required_layer_ids - found_ids
    assert not missing_layers, f"Missing required layer IDs in logo.svg: {missing_layers}"
