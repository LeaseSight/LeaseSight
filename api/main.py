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
# Analytics logic is now handled directly or via frontend components

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

DPI = 1.0 # Emit raw Azure inches for Next.js formula


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


@app.get("/api/index-status/{filename:path}")
async def check_index_status(filename: str):
    """Check if document has a JSON map, index it if not."""
    json_path = JSON_MAP_DIR / f"{filename}.json"
    if not json_path.exists():
        target_path = RAW_PDF_DIR / filename
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="PDF not found")
        process_new_pdf(str(target_path), filename)
        return {"status": "indexed", "was_missing": True}
    return {"status": "indexed", "was_missing": False}


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

        # Log to Excel
        try:
            import pandas as pd
            import datetime
            excel_path = BASE_DIR / "audit_log.xlsx"
            if excel_path.exists():
                df = pd.read_excel(excel_path)
            else:
                df = pd.DataFrame()
                
            findings_dict = {f.get('label'): f.get('value') for f in results.get('findings', [])}
            log_data = {
                'Timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'File_Name': request.file_name,
                'Lessor/Lessee': findings_dict.get('Parties', findings_dict.get('Tenant/Landlord', 'Unknown')),
                'Rent': findings_dict.get('Monthly Rent', 'Unknown'),
                'Risk_Score': results.get('risk_score', 'N/A'),
                'Key_Terms': ', '.join([f"{k}: {v}" for k, v in findings_dict.items()][:5])
            }
            df = pd.concat([df, pd.DataFrame([log_data])], ignore_index=True)
            df.to_excel(excel_path, index=False)
        except Exception as e:
            print(f"Excel Logging Error: {e}")

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


class DiffRequest(BaseModel):
    baseline_file: str
    target_file: str

@app.post("/api/diff")
async def get_diff(request: DiffRequest):
    """Compare two documents and return spatial diffs."""
    import difflib
    
    # In some environments the json extension might be omitted
    baseline_name = request.baseline_file if request.baseline_file.endswith('.json') else f"{request.baseline_file}.json"
    target_name = request.target_file if request.target_file.endswith('.json') else f"{request.target_file}.json"
    
    baseline_path = JSON_MAP_DIR / baseline_name
    target_path = JSON_MAP_DIR / target_name
    
    if not baseline_path.exists() or not target_path.exists():
        # Fallback to creating an empty response instead of failing entirely
        return {"additions": [], "deletions": []}
    
    with open(baseline_path, "r") as f:
        base_data = json.load(f)
    with open(target_path, "r") as f:
        target_data = json.load(f)
        
    def extract_lines(data):
        lines = []
        for p in data.get('pages', []):
            page_num = p.get('page_number', 1)
            for l in p.get('lines', []):
                lines.append({
                    "text": l.get('content', ''),
                    "bbox": l.get('bounding_box', []),
                    "page": page_num
                })
        return lines
        
    base_lines = extract_lines(base_data)
    target_lines = extract_lines(target_data)
    
    base_text = [l['text'] for l in base_lines]
    target_text = [l['text'] for l in target_lines]
    
    sm = difflib.SequenceMatcher(None, base_text, target_text)
    
    additions = []
    deletions = []
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'insert' or tag == 'replace':
            for j in range(j1, j2):
                l = target_lines[j]
                if not l['bbox']: continue
                xs = [p['x'] * DPI for p in l['bbox']]
                ys = [p['y'] * DPI for p in l['bbox']]
                additions.append({
                    "page": l['page'],
                    "x": min(xs), "y": min(ys),
                    "width": max(xs) - min(xs),
                    "height": max(ys) - min(ys),
                    "color": "#10b981", # Mint
                    "text": l['text']
                })
        if tag == 'delete' or tag == 'replace':
            for i in range(i1, i2):
                l = base_lines[i]
                if not l['bbox']: continue
                xs = [p['x'] * DPI for p in l['bbox']]
                ys = [p['y'] * DPI for p in l['bbox']]
                deletions.append({
                    "page": l['page'],
                    "x": min(xs), "y": min(ys),
                    "width": max(xs) - min(xs),
                    "height": max(ys) - min(ys),
                    "color": "#ef4444", # Red
                    "text": l['text']
                })
                
    return {"additions": additions, "deletions": deletions}


@app.post("/api/analytics")
async def get_analytics_data(request: GraphRequest):
    """Get dual analytics data: PCA-reduced 3D coordinates AND internal chunk similarities."""
    try:
        # Generate embedding for the current document/query
        emb_res = oai_client.embeddings.create(
            input=["Parties involved, rent details, address, and legal obligations"],
            model="text-embedding-3-small"
        )
        current_vec = emb_res.data[0].embedding

        # 1. Fetch internal chunks for the current document (Heatmap)
        from sklearn.metrics.pairwise import cosine_similarity
        internal_results = pc_index.query(
            vector=current_vec, top_k=50,
            filter={"file_name": {"$eq": request.file_name}},
            include_values=True, include_metadata=False
        )
        chunk_vectors = [m['values'] for m in internal_results.get('matches', []) if 'values' in m]
        similarities = []
        if chunk_vectors:
            similarities = cosine_similarity([current_vec], chunk_vectors)[0].tolist()

        # 2. Fetch archive vectors (Global Context)
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
            return {
                "archive_coords": [], "new_coords": [], "names": [], "sufficient": False,
                "internal_similarities": similarities, "benchmark_score": 0
            }

        # PCA reduction
        from sklearn.decomposition import PCA
        all_vectors = np.array(vectors + [current_vec])
        pca = PCA(n_components=3)
        coords_3d = pca.fit_transform(all_vectors)

        archive_coords = coords_3d[:-1].tolist()
        new_coords = coords_3d[-1].tolist()

        # Comparative Benchmarking (Cosine similarity with top 10 precedents)
        benchmark_score = 0
        if len(vectors) > 0:
            top_similarities = cosine_similarity([current_vec], vectors)[0]
            top_10 = sorted(top_similarities, reverse=True)[:10]
            benchmark_score = int(np.mean(top_10) * 100)

        return {
            "archive_coords": archive_coords,
            "new_coords": new_coords,
            "names": names,
            "sufficient": True,
            "internal_similarities": similarities,
            "benchmark_score": benchmark_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CalendarRequest(BaseModel):
    obligations: list[dict]

from fastapi import Response
from datetime import datetime, timedelta

@app.post("/api/calendar")
async def generate_calendar(request: CalendarRequest):
    """Generate an ICS file from extracted obligations."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LeaseSight//Obligations//EN",
    ]
    for obs in request.obligations:
        dt = datetime.now() + timedelta(days=30) # Default to 30 days if no parsing
        dt_str = dt.strftime("%Y%m%dT%H%M%S")
        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART:{dt_str}",
            f"DTEND:{dt_str}",
            f"SUMMARY:{obs.get('label', 'Obligation')}",
            f"DESCRIPTION:{obs.get('description', '')}\\nDate mentioned: {obs.get('date', '')}",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    return Response(content="\\r\\n".join(lines), media_type="text/calendar")

@app.get("/api/audit-log")
async def download_audit_log():
    """Download the master audit ledger."""
    excel_path = BASE_DIR / "audit_log.xlsx"
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="Audit log not found")
    return FileResponse(
        str(excel_path), 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="audit_log.xlsx"
    )

from fastapi import Request

@app.post("/api/export/{file_name:path}")
async def export_audit(file_name: str, request: Request):
    """Generate a branded PDF report for the audit using ReportLab."""
    try:
        audit_results = await request.json()
        from scripts.report_generator import generate_audit_pdf
        pdf_bytes = generate_audit_pdf(audit_results, file_name)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query-analytics")
async def get_query_analytics(request: ChatRequest):
    """Generate 3D correlation map for a query against document chunks."""
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        from sklearn.decomposition import PCA
        
        # Embed the query
        emb_res = oai_client.embeddings.create(
            input=[request.query],
            model="text-embedding-3-small"
        )
        query_vec = emb_res.data[0].embedding
        
        # Fetch chunk vectors
        internal_results = pc_index.query(
            vector=query_vec, top_k=50,
            filter={"file_name": {"$eq": request.file_name}},
            include_values=True, include_metadata=False
        )
        chunk_vectors = [m['values'] for m in internal_results.get('matches', []) if 'values' in m]
        
        if len(chunk_vectors) < 2:
            return {"sufficient": False}
            
        similarities = cosine_similarity([query_vec], chunk_vectors)[0].tolist()
        
        all_vectors = np.array(chunk_vectors + [query_vec])
        pca = PCA(n_components=3)
        coords_3d = pca.fit_transform(all_vectors)
        
        chunk_coords = coords_3d[:-1].tolist()
        query_coord = coords_3d[-1].tolist()
        
        return {
            "sufficient": True,
            "archive_coords": chunk_coords,
            "new_coords": query_coord,
            "similarities": similarities,
            "names": [f"Chunk {i+1}" for i in range(len(chunk_coords))]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
