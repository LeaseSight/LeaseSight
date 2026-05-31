# scripts/reindex_pinecone.py
# Re-index all existing Pinecone vectors from OpenAI 1536-dim
# to Gemini text-embedding-004 768-dim.
#
# STRATEGY
# --------
# The dimension of an existing Pinecone index CANNOT be changed in-place.
# This script therefore:
#   1. Fetches metadata for every existing vector (in pages of 100).
#   2. Re-embeds the stored `text` with Gemini text-embedding-004.
#   3. Upserts into the NEW 768-dim index (leasesight-index, already recreated
#      at dim=768 via scripts/recreate_pinecone_index.py).
#
# The script is idempotent: running it twice is safe because vector IDs are
# deterministic (f"{file_name}_p{page_number}").
#
# Usage
# -----
#   python -m scripts.reindex_pinecone
#
# Environment variables required (.env / api/.env):
#   PINECONE_API_KEY
#   GEMINI_API_KEY   (or MANAGED_GEMINI_KEY)

import os
import json
import time
import sys
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

# Load from both .env locations (root wins; api/.env is also checked)
_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "api" / ".env")

from pinecone import Pinecone
from scripts.gemini_client import GeminiEmbeddingClient

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

INDEX_NAME      = "leasesight-index"   # Must already be 768-dim
FETCH_BATCH     = 100                  # IDs to fetch per round
UPSERT_BATCH    = 50                   # Vectors to upsert per call
EMBED_DELAY     = 0.06                 # Seconds between embedding calls (rate-limit)
JSON_MAP_DIR    = _ROOT / "data" / "json_maps"

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _chunks(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


def _collect_ids_from_json_maps() -> List[str]:
    """
    Build the full list of expected vector IDs from local JSON spatial maps.
    This is the primary source of truth for what should be in the index.
    """
    ids = []
    for json_file in sorted(JSON_MAP_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            file_name = data.get("file_name", json_file.stem)
            for page in data.get("pages", []):
                page_num = page.get("page_number", "?")
                ids.append(f"{file_name}_p{page_num}")
        except Exception as e:
            print(f"  [WARN] Could not parse {json_file.name}: {e}")
    return ids


def _build_text_lookup() -> Dict[str, str]:
    """
    Return a dict mapping vector_id → page_text for every page in every JSON map.
    Used as the text source for re-embedding (avoids needing Pinecone metadata fetch
    when the index was recreated empty).
    """
    lookup: Dict[str, str] = {}
    for json_file in sorted(JSON_MAP_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            file_name = data.get("file_name", json_file.stem)
            for page in data.get("pages", []):
                page_num  = page.get("page_number", "?")
                page_text = " ".join(
                    line.get("content", "") for line in page.get("lines", [])
                )
                if page_text.strip():
                    lookup[f"{file_name}_p{page_num}"] = page_text
        except Exception as e:
            print(f"  [WARN] Could not build lookup for {json_file.name}: {e}")
    return lookup


def _build_metadata_lookup() -> Dict[str, Dict[str, Any]]:
    """
    Build a dict mapping vector_id → Pinecone metadata dict.
    Metadata is re-used verbatim so we don't need to fetch from the old index.
    """
    lookup: Dict[str, Dict[str, Any]] = {}
    for json_file in sorted(JSON_MAP_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            file_name = data.get("file_name", json_file.stem)
            for page in data.get("pages", []):
                page_num  = page.get("page_number", "?")
                page_text = " ".join(
                    line.get("content", "") for line in page.get("lines", [])
                )
                coords = json.dumps(
                    page["lines"][0]["bounding_box"] if page.get("lines") else []
                )
                vid = f"{file_name}_p{page_num}"
                lookup[vid] = {
                    "file_name":   file_name,
                    "page_number": page_num,
                    "text":        page_text[:2000],
                    "coords":      coords,
                }
        except Exception as e:
            print(f"  [WARN] Could not build metadata for {json_file.name}: {e}")
    return lookup


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def reindex(dry_run: bool = False):
    """
    Re-embed every page from local JSON maps using Gemini text-embedding-004
    and upsert into the 768-dim Pinecone index.

    Parameters
    ----------
    dry_run : bool
        If True, print what would be done without calling Pinecone upsert.
    """
    print("=" * 60)
    print("  LeaseSight -- Pinecone Re-indexing (OpenAI -> Gemini)")
    print("=" * 60)

    # --- Clients ---
    pc          = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index       = pc.Index(INDEX_NAME)
    embed       = GeminiEmbeddingClient()

    # --- Verify dimension ---
    stats = index.describe_index_stats()
    dim   = stats.get("dimension")
    if dim is not None and dim != 768:
        print(
            f"\n[ERROR] Index '{INDEX_NAME}' has dimension {dim}, expected 768.\n"
            "Run scripts/recreate_pinecone_index.py first to create a 768-dim index."
        )
        sys.exit(1)
    print(f"\nIndex '{INDEX_NAME}' confirmed at dimension {dim or 'unknown (new/empty)'}.")

    # --- Build source data from JSON maps ---
    print("\nScanning local JSON spatial maps...")
    text_lookup     = _build_text_lookup()
    metadata_lookup = _build_metadata_lookup()

    if not text_lookup:
        print(
            "[ERROR] No JSON maps found in data/json_maps/. "
            "Run the upload pipeline first to generate them."
        )
        sys.exit(1)

    all_ids = list(text_lookup.keys())
    print(f"Found {len(all_ids)} page vectors to re-index across "
          f"{len(set(v.split('_p')[0] for v in all_ids))} documents.")

    if dry_run:
        print("\n[DRY RUN] No changes will be made to Pinecone.")
        for vid in all_ids[:5]:
            print(f"  Would upsert: {vid!r}")
        if len(all_ids) > 5:
            print(f"  ... and {len(all_ids) - 5} more.")
        return

    # --- Embed & Upsert ---
    print("\nStarting embedding + upsert...")
    success_count = 0
    fail_count    = 0
    upsert_buffer: List[tuple] = []

    def _flush_buffer():
        nonlocal success_count
        if not upsert_buffer:
            return
        try:
            index.upsert(vectors=upsert_buffer)
            success_count += len(upsert_buffer)
            print(f"  [Pinecone] Upserted batch of {len(upsert_buffer)} vectors "
                  f"(total: {success_count})")
        except Exception as e:
            print(f"  [ERROR] Pinecone upsert failed: {e}")
        upsert_buffer.clear()

    for i, vid in enumerate(all_ids, start=1):
        page_text = text_lookup[vid]
        metadata  = metadata_lookup.get(vid, {})

        try:
            vector = embed.embed(page_text, task_type="RETRIEVAL_DOCUMENT")
            upsert_buffer.append((vid, vector, metadata))
        except Exception as e:
            fail_count += 1
            print(f"  [ERROR] Embedding failed for {vid}: {e}")
            continue

        # Flush every UPSERT_BATCH vectors
        if len(upsert_buffer) >= UPSERT_BATCH:
            _flush_buffer()

        # Progress every 50 embeddings
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(all_ids)} embedded...")

        time.sleep(EMBED_DELAY)

    # Flush any remainder
    _flush_buffer()

    # --- Summary ---
    print("\n" + "=" * 60)
    print(f"  Re-indexing complete.")
    print(f"  [OK] Upserted : {success_count} vectors")
    if fail_count:
        print(f"  [FAIL] Failed   : {fail_count} vectors (see errors above)")
    print("=" * 60)

    final_stats = index.describe_index_stats()
    total_vecs  = final_stats.get("total_vector_count", "?")
    print(f"\nPinecone index now contains {total_vecs} total vectors.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Re-index Pinecone from JSON maps using Gemini embeddings.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing to Pinecone.")
    args = parser.parse_args()
    reindex(dry_run=args.dry_run)
