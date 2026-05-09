import os
import json
import time
from pathlib import Path
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

def _is_rate_limited(error):
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text or "openresty" in text

def _create_embedding_with_retry(openai_client, text, attempts=4):
    last_error = None
    for attempt in range(attempts):
        try:
            emb_res = openai_client.embeddings.create(input=text, model="text-embedding-3-small")
            return emb_res.data[0].embedding
        except Exception as e:
            last_error = e
            if attempt < attempts - 1 and _is_rate_limited(e):
                wait = 8 * (attempt + 1)
                print(f"[INGEST] Embedding rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise last_error


def process_new_pdf(pdf_path, file_name, openai_client=None, pinecone_index=None, azure_client=None):
    """
    Process a PDF: Azure layout analysis → OpenAI embeddings → Pinecone upsert → JSON spatial map.

    Clients are injected by the API layer (from request headers).
    Falls back to .env values if not provided, for local/dev use.
    """
    # --- Client Resolution (Dependency Injection with .env fallback) ---
    if azure_client is None:
        azure_client = DocumentAnalysisClient(
            endpoint=os.getenv("AZURE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_KEY"))
        )
    if openai_client is None:
        openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_PROXY_URL") or "https://api.openai.com/v1"
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
        page_text = ""
        for line in page.lines:
            lines.append({
                "content": line.content,
                "bounding_box": [{"x": p.x, "y": p.y} for p in line.polygon]
            })
            page_text += line.content + " "

        spatial_data["pages"].append({
            "page_number": page.page_number,
            "width": getattr(page, "width", 8.5),
            "height": getattr(page, "height", 11.0),
            "unit": getattr(page, "unit", "inch"),
            "lines": lines,
        })

    # Save JSON spatial map before embeddings so the audit pipeline can use the
    # extracted text even if vector indexing is throttled.
    BASE_DIR = Path(__file__).resolve().parents[1]
    json_path = BASE_DIR / "data" / "json_maps" / f"{file_name}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(spatial_data, f, indent=4)

    for page in spatial_data["pages"]:
        page_text = " ".join(line.get("content", "") for line in page.get("lines", []))
        page_number = page.get("page_number", 1)

        # 2. OpenAI Embedding + Pinecone Upsert.
        try:
            vector = _create_embedding_with_retry(openai_client, page_text)
            metadata = {
                "file_name": file_name,
                "page_number": page_number,
                "text": page_text[:2000],
                "coords": json.dumps(page["lines"][0]['bounding_box'] if page.get("lines") else [])
            }
            pinecone_index.upsert(vectors=[(f"{file_name}_p{page_number}", vector, metadata)])
        except Exception as e:
            print(f"[INGEST] Skipping vector upsert for {file_name} page {page_number}: {e}")

    return json_path
