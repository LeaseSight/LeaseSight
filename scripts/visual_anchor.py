# scripts/visual_anchor.py
import json
import re
import glob
import statistics
from pathlib import Path

# Absolute path for reliability
BASE_DIR = Path(__file__).resolve().parents[1]
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"
VIEWER_PAGE_WIDTH = 8.5
VIEWER_PAGE_HEIGHT = 11.0
VERTICAL_PADDING = 2.0 / 72.0


def clean_text(text):
    """Removes non-alphanumeric characters for robust OCR/AI fuzzy matching."""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

def _page_dimensions(page):
    width = page.get("width") or page.get("page_width") or VIEWER_PAGE_WIDTH
    height = page.get("height") or page.get("page_height") or VIEWER_PAGE_HEIGHT
    try:
        return float(width), float(height)
    except (TypeError, ValueError):
        return VIEWER_PAGE_WIDTH, VIEWER_PAGE_HEIGHT

def _normalize_point(point, page_width, page_height):
    x = float(point.get("x", 0))
    y = float(point.get("y", 0))

    if page_width <= 1.5 and page_height <= 1.5:
        return {"x": x * VIEWER_PAGE_WIDTH, "y": y * VIEWER_PAGE_HEIGHT}
    if page_width <= 100 and page_height <= 100 and (x > VIEWER_PAGE_WIDTH or y > VIEWER_PAGE_HEIGHT):
        return {"x": (x / 100.0) * VIEWER_PAGE_WIDTH, "y": (y / 100.0) * VIEWER_PAGE_HEIGHT}

    return {
        "x": (x / page_width) * VIEWER_PAGE_WIDTH if page_width else x,
        "y": (y / page_height) * VIEWER_PAGE_HEIGHT if page_height else y,
    }

def _line_rect(line, page_width, page_height):
    bbox = line.get("bounding_box", [])
    if not bbox or len(bbox) < 4:
        return None
    points = [_normalize_point(point, page_width, page_height) for point in bbox[:4]]
    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    return {
        "x1": min(xs),
        "x2": max(xs),
        "y1": min(ys),
        "y2": max(ys),
        "height": max(ys) - min(ys),
    }

def _rect_to_bbox(rect):
    return [
        {"x": rect["x1"], "y": rect["y1"]},
        {"x": rect["x2"], "y": rect["y1"]},
        {"x": rect["x2"], "y": rect["y2"]},
        {"x": rect["x1"], "y": rect["y2"]},
    ]

def _normalized_quote_box(lines, page_width, page_height):
    rects = []
    for line in lines:
        rect = _line_rect(line, page_width, page_height)
        if rect:
            rects.append(rect)
    if not rects:
        return None

    median_y = statistics.median(rect["y1"] for rect in rects)
    median_height = statistics.median(rect["height"] for rect in rects)
    y1 = max(0, median_y - VERTICAL_PADDING)
    y2 = min(VIEWER_PAGE_HEIGHT, median_y + median_height + VERTICAL_PADDING)

    return _rect_to_bbox({
        "x1": max(0, min(rect["x1"] for rect in rects)),
        "x2": min(VIEWER_PAGE_WIDTH, max(rect["x2"] for rect in rects)),
        "y1": y1,
        "y2": y2,
    })

def _matching_lines(page, snippet):
    lines = page.get("lines", [])
    clean_snippet = clean_text(snippet)
    if not clean_snippet:
        return []

    for line in lines:
        if clean_snippet[:25] in clean_text(line.get("content", "")):
            return [line]

    max_window = min(6, len(lines))
    for size in range(2, max_window + 1):
        for start in range(0, len(lines) - size + 1):
            window = lines[start:start + size]
            merged = clean_text(" ".join(line.get("content", "") for line in window))
            if clean_snippet[: min(60, len(clean_snippet))] in merged:
                return window

    return []


def _resolve_json_path(file_name):
    """
    Resolves the correct JSON map file for a given PDF filename.
    Handles Windows filename suffixes like ' (1)' via glob matching.
    Returns the Path or None if no match is found.
    """
    if not JSON_MAP_DIR.exists():
        return None

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

    for page in data.get('pages', []):
        matched_lines = _matching_lines(page, snippet)
        if not matched_lines:
            continue

        page_width, page_height = _page_dimensions(page)
        bbox = _normalized_quote_box(matched_lines, page_width, page_height)
        if bbox:
            return {
                "page": int(page.get('page_number', 1)),
                "bounding_box": bbox
            }
    return None
