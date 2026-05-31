# scripts/processor.py
# PDF ingestion: Azure Layout Analysis -> local sentence-transformer embeddings (768-dim) -> Pinecone upsert -> JSON spatial map.
# Embedding engine: sentence-transformers/all-mpnet-base-v2 (100% offline, no API keys, no rate limits).

import os
import json
from pathlib import Path
from typing import List

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Local Embedding Engine (singleton — model is loaded once at import time)
# ---------------------------------------------------------------------------

_LOCAL_MODEL = None
_LOCAL_MODEL_NAME = "all-mpnet-base-v2"  # 768-dim, state-of-the-art SBERT model


def _get_model():
    """Lazy-load the sentence-transformer model (cached after first call)."""
    global _LOCAL_MODEL
    if _LOCAL_MODEL is None:
        from sentence_transformers import SentenceTransformer
        print(f"[EMBED] Loading local model '{_LOCAL_MODEL_NAME}' (first use — downloading if needed)...")
        _LOCAL_MODEL = SentenceTransformer(_LOCAL_MODEL_NAME)
        print(f"[EMBED] Model loaded. Dimension: {_LOCAL_MODEL.get_sentence_embedding_dimension()}")
    return _LOCAL_MODEL


def get_local_embedding(text: str) -> List[float]:
    """
    Embed a single string using the local all-mpnet-base-v2 model.

    Returns a 768-dimensional float list, matching the existing Pinecone index.
    No API key, no network call, no rate limits.

    Parameters
    ----------
    text : str
        The text to embed. Long texts are automatically truncated by the model
        to its max token length (384 tokens for all-mpnet-base-v2).

    Returns
    -------
    List[float]
        768-dimensional embedding vector.
    """
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


# ---------------------------------------------------------------------------
# Main ingestion entry point
# ---------------------------------------------------------------------------

def process_new_pdf(
    pdf_path,
    file_name,
    pinecone_index=None,
    azure_client=None,
    # Legacy kwargs accepted but ignored (openai_client / embed_client removed)
    openai_client=None,
    embed_client=None,
):
    """
    Process a PDF:
      Azure layout analysis -> local sentence-transformer embedding -> Pinecone upsert -> JSON spatial map.

    No external embedding API required. Falls back to .env for Pinecone/Azure if clients not injected.
    """
    # --- Client Resolution ---
    if azure_client is None:
        azure_client = DocumentAnalysisClient(
            endpoint=os.getenv("AZURE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_KEY")),
        )

    if pinecone_index is None:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        pinecone_index = pc.Index("leasesight-index")

    # 1. Azure Layout Analysis
    with open(pdf_path, "rb") as f:
        poller = azure_client.begin_analyze_document("prebuilt-layout", f)
        result = poller.result()

    spatial_data = {"file_name": file_name, "pages": []}
    for page in result.pages:
        lines = []
        for line in page.lines:
            lines.append({
                "content": line.content,
                "bounding_box": [{"x": p.x, "y": p.y} for p in line.polygon],
            })

        spatial_data["pages"].append({
            "page_number": page.page_number,
            "width":       getattr(page, "width",  8.5),
            "height":      getattr(page, "height", 11.0),
            "unit":        getattr(page, "unit",   "inch"),
            "lines":       lines,
        })

    # Save JSON spatial map before embeddings so the audit pipeline can use the
    # extracted text even if vector indexing fails.
    BASE_DIR  = Path(__file__).resolve().parents[1]
    json_path = BASE_DIR / "data" / "json_maps" / f"{file_name}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(spatial_data, f, indent=4)

    # 2. Local Embedding + Pinecone Upsert (per-page)
    for page in spatial_data["pages"]:
        page_text   = " ".join(line.get("content", "") for line in page.get("lines", []))
        page_number = page.get("page_number", 1)

        if not page_text.strip():
            continue

        try:
            vector = get_local_embedding(page_text)
            metadata = {
                "file_name":   file_name,
                "page_number": page_number,
                "text":        page_text[:2000],     # Pinecone metadata size safety
                "coords":      json.dumps(
                    page["lines"][0]["bounding_box"] if page.get("lines") else []
                ),
            }
            pinecone_index.upsert(vectors=[(f"{file_name}_p{page_number}", vector, metadata)])
        except Exception as e:
            print(f"[INGEST] Skipping vector upsert for {file_name} page {page_number}: {e}")

    return json_path
