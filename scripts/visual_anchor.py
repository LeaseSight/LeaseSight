import json
from pathlib import Path

# Use the absolute path for reliability
BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"

def find_coordinates(file_name, snippet):
    """
    Finds the bounding box for a specific text snippet within a contract's digital twin.
    """
    # Ensure we look for the .json version of the PDF mapping
    json_path = JSON_MAP_DIR / f"{file_name}.json"
    
    if not json_path.exists():
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # We take a 'fingerprint' of the AI's answer to match against the JSON
    fingerprint = snippet[:30].strip().lower()

    for page in data['pages']:
        for line in page['lines']:
            if fingerprint in line['content'].lower():
                return {
                    "page": page['page_number'],
                    "text": line['content'],
                    "bounding_box": line['bounding_box']
                }
    
    return None