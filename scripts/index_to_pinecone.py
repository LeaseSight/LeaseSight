# scripts/index_to_pinecone.py
# Batch-index all JSON spatial maps into Pinecone using Gemini text-embedding-004 (768-dim).
# Migrated from OpenAI text-embedding-3-small (1536-dim).
#
# Usage:
#   python -m scripts.index_to_pinecone

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone

from scripts.processor import get_local_embedding

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------
load_dotenv()

# Pinecone client
pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("leasesight-index")     # Must be at dim=768

BASE_DIR     = Path(__file__).resolve().parents[1]
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"

# ---------------------------------------------------------------------------
# 2. UPLOAD LOOP
# ---------------------------------------------------------------------------

def upload_to_brain(user_id: str = None):
    json_files = list(JSON_MAP_DIR.glob("*.json"))
    print(f"Loading {len(json_files)} contract maps into the vector database...")

    total_pages  = 0
    failed_pages = 0
    ns = f"user_{user_id}" if user_id else "academic_baseline"

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        file_name = data["file_name"]
        print(f"Indexing: {file_name}")

        for page in data["pages"]:
            # Group all text on the page into one searchable chunk
            page_text = " ".join([line["content"] for line in page["lines"]])

            if not page_text.strip():
                continue

            total_pages += 1
            try:
                # --- Local embedding (768-dim, offline, no rate limits) ---
                vector = get_local_embedding(page_text)

                metadata = {
                    "file_name":   file_name,
                    "page_number": page["page_number"],
                    "text":        page_text[:2000],  # Pinecone metadata size safety
                    "coords":      json.dumps(page["lines"][0]["bounding_box"])
                                   if page.get("lines") else "[]",
                }

                unique_id = f"{file_name}_p{page['page_number']}"
                index.upsert(
                    vectors=[(unique_id, vector, metadata)],
                    namespace=ns
                )

                # Small delay to stay within Gemini free-tier rate limits
                time.sleep(0.05)

            except Exception as e:
                failed_pages += 1
                print(f"  [ERROR] {file_name} page {page['page_number']}: {e}")

    print(f"\n--- INDEXING COMPLETE ---")
    print(f"  Pages indexed : {total_pages - failed_pages}/{total_pages}")
    if failed_pages:
        print(f"  Pages failed  : {failed_pages} (check logs above)")


if __name__ == "__main__":
    upload_to_brain()