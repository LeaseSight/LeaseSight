import os
import json
from pathlib import Path
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()


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

        spatial_data["pages"].append({"page_number": page.page_number, "lines": lines})

        # 2. OpenAI Embedding + Pinecone Upsert
        emb_res = openai_client.embeddings.create(input=page_text, model="text-embedding-3-small")
        vector = emb_res.data[0].embedding

        metadata = {
            "file_name": file_name,
            "page_number": page.page_number,
            "text": page_text[:2000],
            "coords": json.dumps(lines[0]['bounding_box'] if lines else [])
        }
        pinecone_index.upsert(vectors=[(f"{file_name}_p{page.page_number}", vector, metadata)])

    # 3. Save JSON spatial map for visual grounding
    BASE_DIR = Path(__file__).resolve().parents[1]
    json_path = BASE_DIR / "data" / "json_maps" / f"{file_name}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(spatial_data, f, indent=4)

    return json_path