# scripts/visual_anchor.py
import json
import re
import glob
from pathlib import Path

# Absolute path for reliability
BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"


def clean_text(text):
    """Removes non-alphanumeric characters for robust OCR/AI fuzzy matching."""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()


def _resolve_json_path(file_name):
    """
    Resolves the correct JSON map file for a given PDF filename.
    Handles Windows filename suffixes like ' (1)' via glob matching.
    Returns the Path or None if no match is found.
    """
    # 1. Direct match: <filename>.json  (e.g., "doc.pdf" -> "doc.pdf.json")
    direct = JSON_MAP_DIR / f"{file_name}.json"
    if direct.exists():
        return direct

    # 2. Glob match to handle Windows duplicates like ' (1)', ' (2)', etc.
    #    Strip known suffixes like ' (1)' from the PDF name before globbing.
    stem = file_name
    # Remove .pdf extension (case-insensitive)
    stem = re.sub(r'\.pdf$', '', stem, flags=re.IGNORECASE)
    # Remove Windows copy suffixes like ' (1)', ' (2)'
    stem = re.sub(r'\s*\(\d+\)$', '', stem)

    # Glob for any JSON that starts with the cleaned stem
    pattern = str(JSON_MAP_DIR / f"{glob.escape(stem)}*")
    candidates = glob.glob(pattern)
    json_candidates = [c for c in candidates if c.lower().endswith('.json')]

    if json_candidates:
        return Path(json_candidates[0])

    # 3. Substring containment fallback (case-insensitive)
    clean_pdf_name = file_name.lower().replace(".pdf", "")
    for f in JSON_MAP_DIR.iterdir():
        if f.suffix.lower() == '.json':
            fname_lower = f.name.lower()
            if clean_pdf_name in fname_lower or fname_lower.replace('.json', '') in clean_pdf_name:
                return f

    return None


def find_coordinates(file_name, snippet):
    """
    Matches the AI's evidence_quote to the physical coordinates in the JSON map.
    
    Uses alphanumeric-only fuzzy matching to handle OCR/AI discrepancies.
    Handles Windows filename suffixes like ' (1)' using glob matching.
    
    Returns:
        dict with 'page' (int) and 'bounding_box' (list of {x, y} dicts),
        or None if no match is found or JSON map is missing.
    """
    # --- THE HANDSHAKE: Silently return None if the JSON map is missing ---
    json_path = _resolve_json_path(file_name)
    if not json_path:
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return None

    # Prepare the search target ("The Fingerprint")
    # Use the first 25 alphanumeric chars as the matching fingerprint
    search_target = clean_text(snippet)[:25]
    if not search_target:
        return None

    # Search through the Azure 'Digital Twin'
    for page in data.get('pages', []):
        for line in page.get('lines', []):
            content = line.get('content', "")
            if search_target in clean_text(content):
                bbox = line.get("bounding_box", [])
                # Validate: must have at least 4 coordinate points
                if bbox and len(bbox) >= 4:
                    # Return structured {x, y} dicts and integer page number
                    return {
                        "page": int(page.get('page_number', 1)),
                        "bounding_box": [
                            {"x": point["x"], "y": point["y"]}
                            for point in bbox[:4]
                        ]
                    }
    return None