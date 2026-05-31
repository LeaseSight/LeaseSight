"""
recreate_pinecone_index.py
--------------------------
1. Deletes the old `leasesight-index` (1536-dim / OpenAI).
2. Recreates it at 768 dims for Gemini `models/text-embedding-004`.
3. Re-indexes every JSON map in data/json_maps/ via the updated
   index_to_pinecone.upload_to_brain() logic.

Run with:
    .\\venv\\Scripts\\python.exe scripts\\recreate_pinecone_index.py
"""

import os, sys, time, json
from pathlib import Path
from dotenv import load_dotenv

# --- Path setup ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Load .env from repo root
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME      = "leasesight-index"
DIMENSION       = 768          # Gemini text-embedding-004
METRIC          = "cosine"

# ── 1. VALIDATE KEYS ────────────────────────────────────────────────────────
if not GEMINI_API_KEY:
    sys.exit("[ERROR] GEMINI_API_KEY not found in .env")
if not PINECONE_API_KEY:
    sys.exit("[ERROR] PINECONE_API_KEY not found in .env")

print(f"[INFO] GEMINI_API_KEY  : {GEMINI_API_KEY[:12]}…")
print(f"[INFO] PINECONE_API_KEY: {PINECONE_API_KEY[:12]}…")

# ── 2. INIT CLIENTS ─────────────────────────────────────────────────────────
from google import genai
from google.genai import types as genai_types
from pinecone import Pinecone, ServerlessSpec

gemini  = genai.Client(api_key=GEMINI_API_KEY)
pc      = Pinecone(api_key=PINECONE_API_KEY)

# ── 3. DELETE OLD INDEX ─────────────────────────────────────────────────────
existing = [idx.name for idx in pc.list_indexes()]
if INDEX_NAME in existing:
    print(f"[STEP 1] Deleting existing index '{INDEX_NAME}' (old dim may be 1536)…")
    pc.delete_index(INDEX_NAME)
    # Wait for deletion to propagate
    for _ in range(30):
        if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
            break
        print("         Waiting for deletion…")
        time.sleep(3)
    print(f"[STEP 1] [OK] Deleted.")
else:
    print(f"[STEP 1] Index '{INDEX_NAME}' does not exist yet — skipping delete.")

# ── 4. RECREATE AT 768 DIMS ─────────────────────────────────────────────────
print(f"[STEP 2] Creating '{INDEX_NAME}' at {DIMENSION} dims (metric={METRIC})…")
pc.create_index(
    name=INDEX_NAME,
    dimension=DIMENSION,
    metric=METRIC,
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)

# Wait until ready
for _ in range(60):
    desc = pc.describe_index(INDEX_NAME)
    if desc.status and desc.status.get("ready"):
        break
    print("         Waiting for index to become ready…")
    time.sleep(4)

print(f"[STEP 2] [OK] Index ready at {DIMENSION} dims.")

# ── 5. RE-INDEX ALL JSON MAPS ───────────────────────────────────────────────
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"
index        = pc.Index(INDEX_NAME)
json_files   = sorted(JSON_MAP_DIR.glob("*.json"))

if not json_files:
    print("[STEP 3] No JSON maps found in data/json_maps/ — nothing to index.")
    sys.exit(0)

print(f"[STEP 3] Indexing {len(json_files)} contract map(s) into '{INDEX_NAME}'…")

total_vectors = 0
for json_file in json_files:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    file_name = data.get("file_name", json_file.stem)
    print(f"         → {file_name}")

    for page in data.get("pages", []):
        page_text = " ".join(
            line.get("content", "") for line in page.get("lines", [])
        ).strip()
        if not page_text:
            continue

        page_number = page.get("page_number", 1)
        unique_id   = f"{file_name}_p{page_number}"

        for attempt in range(4):
            try:
                result = gemini.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=page_text,
                    config=genai_types.EmbedContentConfig(output_dimensionality=768),
                )
                vector = result.embeddings[0].values

                metadata = {
                    "file_name":   file_name,
                    "page_number": page_number,
                    "text":        page_text[:2000],
                    "coords":      json.dumps(
                        page["lines"][0]["bounding_box"]
                        if page.get("lines") else []
                    ),
                }
                index.upsert(
                    vectors=[(unique_id, vector, metadata)],
                    namespace="academic_baseline"
                )
                total_vectors += 1
                time.sleep(0.05)   # respect Gemini free-tier rate limits
                break

            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err.lower():
                    wait = 10 * (attempt + 1)
                    print(f"           Rate-limited. Waiting {wait}s…")
                    time.sleep(wait)
                    continue
                print(f"           [WARN] Skipping {unique_id}: {e}")
                break

print(f"\n[DONE] [OK] Upserted {total_vectors} vectors into '{INDEX_NAME}' at {DIMENSION} dims.")
