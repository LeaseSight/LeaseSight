# api/main.py
# FastAPI backend — bridges the Next.js frontend to the existing Python scripts

import os
import sys
import json
import numpy as np
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# --- Path Setup ---
BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

load_dotenv(BASE_DIR / ".env")

# Import existing scripts
from scripts.full_audit import run_full_audit
from scripts.visual_anchor import find_coordinates
from scripts.query_engine import ask_document
from scripts.database_manager import commit_to_knowledge_base
from scripts.processor import process_new_pdf
from scripts.analytics import generate_3d_network_graph

from openai import OpenAI
from pinecone import Pinecone

# --- App ---
app = FastAPI(title="LeaseSight API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
JSON_MAP_DIR.mkdir(parents=True, exist_ok=True)

# --- Clients ---
oai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
pc_index = pc.Index("leasesight-index")

DPI = 72


# ========================================================================
# REQUEST MODELS
# ========================================================================
class AuditRequest(BaseModel):
    file_name: str

class ChatRequest(BaseModel):
    query: str
    file_name: str

class LocateRequest(BaseModel):
    file_name: str
    snippet: str

class CommitRequest(BaseModel):
    file_name: str
    vector_ids: Optional[list[str]] = None

class GraphRequest(BaseModel):
    file_name: str


# ========================================================================
# ENDPOINTS
# ========================================================================

@app.get("/api/health")
async def health_check():
    """System health check — Pinecone + OpenAI connectivity."""
    status = {"status": "ok", "pinecone": "unknown", "openai": "unknown"}
    try:
        pc_index.describe_index_stats()
        status["pinecone"] = "connected"
    except Exception:
        status["pinecone"] = "error"
    try:
        oai_client.models.list()
        status["openai"] = "connected"
    except Exception:
        status["openai"] = "error"
    return status


@app.get("/api/documents")
async def list_documents():
    """List all PDFs in the raw_pdfs directory."""
    pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    return {"documents": pdfs, "count": len(pdfs)}


@app.get("/api/pdf/{filename:path}")
async def serve_pdf(filename: str):
    """Serve a PDF file for the viewer."""
    pdf_path = RAW_PDF_DIR / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(str(pdf_path), media_type="application/pdf")


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a new PDF."""
    target_path = RAW_PDF_DIR / file.filename
    try:
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
        # Process with existing pipeline
        process_new_pdf(str(target_path), file.filename)
        return {"file_name": file.filename, "status": "indexed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audit")
async def run_audit(request: AuditRequest):
    """Run the multi-agent audit pipeline (Miner → Judge → Clerk)."""
    try:
        results = run_full_audit(request.file_name)
        if not results:
            return {"findings": [], "summary_paragraph": "No data found.", "risk_score": 1, "warnings": []}

        # Generate annotations for all findings
        annotations = []
        if results.get('findings'):
            for finding in results['findings']:
                evidence = finding.get('evidence_quote', '')
                if evidence and str(evidence).lower() != "not found":
                    coord_data = find_coordinates(request.file_name, str(evidence))
                    if coord_data:
                        bbox = coord_data['bounding_box']
                        xs = [p['x'] * DPI for p in bbox]
                        ys = [p['y'] * DPI for p in bbox]
                        annotations.append({
                            "page": int(coord_data['page']),
                            "x": min(xs), "y": min(ys),
                            "width": max(xs) - min(xs),
                            "height": max(ys) - min(ys),
                            "color": "red",
                        })

        results["annotations"] = annotations
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_with_document(request: ChatRequest):
    """Scoped document chat — queries only the specified document."""
    try:
        result = ask_document(request.query, request.file_name)
        # Try to locate the source text
        annotation = None
        if result.get('source_text'):
            coord_data = find_coordinates(request.file_name, result['source_text'][:80])
            if coord_data:
                bbox = coord_data['bounding_box']
                xs = [p['x'] * DPI for p in bbox]
                ys = [p['y'] * DPI for p in bbox]
                annotation = {
                    "page": int(coord_data['page']),
                    "x": min(xs), "y": min(ys),
                    "width": max(xs) - min(xs),
                    "height": max(ys) - min(ys),
                    "color": "orange",
                }
        result["annotation"] = annotation
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/locate")
async def locate_snippet(request: LocateRequest):
    """Find coordinates for a text snippet in the document's JSON map."""
    coord_data = find_coordinates(request.file_name, request.snippet)
    if not coord_data:
        return {"found": False, "page": None, "annotation": None}
    bbox = coord_data['bounding_box']
    xs = [p['x'] * DPI for p in bbox]
    ys = [p['y'] * DPI for p in bbox]
    return {
        "found": True,
        "page": int(coord_data['page']),
        "annotation": {
            "page": int(coord_data['page']),
            "x": min(xs), "y": min(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
            "color": "red",
        }
    }


@app.post("/api/commit")
async def commit_document(request: CommitRequest):
    """Commit a verified document to the knowledge base."""
    try:
        result = commit_to_knowledge_base(
            file_name=request.file_name,
            vector_ids=request.vector_ids
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph-data")
async def get_graph_data(request: GraphRequest):
    """Get PCA-reduced 3D coordinates for the similarity network graph."""
    try:
        # Generate embedding for the current document
        emb_res = oai_client.embeddings.create(
            input=["Parties involved, rent details, address, and legal obligations"],
            model="text-embedding-3-small"
        )
        current_vec = emb_res.data[0].embedding

        # Fetch archive vectors
        results = pc_index.query(
            vector=current_vec, top_k=100,
            include_values=True, include_metadata=True,
        )

        vectors, names, seen = [], [], set()
        for match in results.get('matches', []):
            fn = match.get('metadata', {}).get('file_name', 'Unknown')
            if fn == request.file_name or fn in seen:
                continue
            seen.add(fn)
            vectors.append(match['values'])
            names.append(fn)

        if len(vectors) < 3:
            return {"archive_coords": [], "new_coords": [], "names": [], "sufficient": False}

        # PCA reduction
        from sklearn.decomposition import PCA
        all_vectors = np.array(vectors + [current_vec])
        pca = PCA(n_components=3)
        coords_3d = pca.fit_transform(all_vectors)

        archive_coords = coords_3d[:-1].tolist()
        new_coords = coords_3d[-1].tolist()

        return {
            "archive_coords": archive_coords,
            "new_coords": new_coords,
            "names": names,
            "sufficient": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
