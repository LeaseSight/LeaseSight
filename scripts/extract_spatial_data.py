import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
# FIX: Using HttpResponseError instead of ResponseError
from azure.core.exceptions import HttpResponseError 

# 1. SETUP - Hardcoded absolute paths for reliability
load_dotenv()
ENDPOINT = os.getenv("AZURE_ENDPOINT")
KEY = os.getenv("AZURE_KEY")

client = DocumentAnalysisClient(endpoint=ENDPOINT, credential=AzureKeyCredential(KEY))

BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"

def finish_mapping():
    # Ensure folder exists
    JSON_MAP_DIR.mkdir(parents=True, exist_ok=True)

    # 2. CASE-INSENSITIVE SCAN: Looks for .pdf and .PDF
    all_files = [f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')]
    
    # Check what is actually missing based on your audit naming logic
    to_process = [f for f in all_files if not (JSON_MAP_DIR / f"{f}.json").exists()]
    
    print(f"Total PDFs found: {len(all_files)}")
    print(f"Remaining to map: {len(to_process)}")

    for file_name in to_process:
        file_path = RAW_PDF_DIR / file_name
        output_file = JSON_MAP_DIR / f"{file_name}.json"

        print(f"Analyzing: {file_name}...")
        
        try:
            with open(file_path, "rb") as f:
                # 3. ANALYSIS: Extracting the 41 critical label categories via Layout
                poller = client.begin_analyze_document("prebuilt-layout", f)
                result = poller.result()

            # 4. SPATIAL MAPPING: Store text + coordinates for Day 5 Visuals
            spatial_data = {"file_name": file_name, "pages": []}
            for page in result.pages:
                lines = []
                for line in page.lines:
                    lines.append({
                        "content": line.content,
                        "bounding_box": [{"x": p.x, "y": p.y} for p in line.polygon]
                    })
                spatial_data["pages"].append({
                    "page_number": page.page_number,
                    "lines": lines
                })

            with open(output_file, "w") as out:
                json.dump(spatial_data, out, indent=4)
            
            print(f"SUCCESS: {file_name}")
            
            # API Throttle - Important for Student Credits/Rate Limits
            time.sleep(2) 

        except HttpResponseError as e:
            if "429" in str(e):
                print("Rate limit hit! Sleeping for 20 seconds...")
                time.sleep(20)
            else:
                print(f"API Error on {file_name}: {e}")
        except Exception as e:
            print(f"Fatal error on {file_name}: {e}")

if __name__ == "__main__":
    finish_mapping()