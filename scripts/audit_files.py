import os
from pathlib import Path

# Use the exact path from your error log
BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"

def audit():
    print(f"--- PATH CHECK ---")
    print(f"PDF Folder: {RAW_PDF_DIR} (Exists: {RAW_PDF_DIR.exists()})")
    print(f"JSON Folder: {JSON_MAP_DIR} (Exists: {JSON_MAP_DIR.exists()})")

    # 1. Count actual files in the folders
    pdfs = [f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')]
    jsons = [f for f in os.listdir(JSON_MAP_DIR) if f.lower().endswith('.json')]

    print(f"\n--- COUNT CHECK ---")
    print(f"PDFs found by script: {len(pdfs)}")
    print(f"JSONs found by script: {len(jsons)}")

    # 2. Check for the "Missing" files
    # The logic looks for: filename.pdf.json
    missing = []
    for p in pdfs:
        expected = f"{p}.json"
        if expected not in jsons:
            missing.append(p)

    print(f"\n--- LOGIC CHECK ---")
    print(f"Files that need mapping: {len(missing)}")
    
    if len(missing) > 0:
        print(f"Example missing file: {missing[0]}")
    else:
        print("Script thinks everything is mapped. Checking naming...")
        if len(pdfs) > len(jsons):
            print("WARNING: You have more PDFs than JSONs, but the script can't see the difference.")
            print(f"First PDF name: {pdfs[0]}")
            print(f"First JSON name: {jsons[0] if jsons else 'NONE'}")

if __name__ == "__main__":
    audit()