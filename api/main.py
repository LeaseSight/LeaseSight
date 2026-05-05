# api/main.py — LeaseSight FastAPI Backend v3.0
# Keys accepted via request headers; falls back to .env for local development.

import os, sys, json
import numpy as np
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))
load_dotenv(BASE_DIR / ".env")

from scripts.full_audit import run_full_audit
from scripts.visual_anchor import find_coordinates
from scripts.query_engine import ask_document
from scripts.database_manager import commit_to_knowledge_base
from scripts.processor import process_new_pdf

from openai import OpenAI, AuthenticationError as OAIAuthError
from pinecone import Pinecone
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# ---------------------------------------------------------------------------
app = FastAPI(title="LeaseSight API", version="3.0")

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

DPI = 1.0  # Emit raw Azure inches for frontend formula


# ===========================================================================
# CLIENT DEPENDENCY — reads from headers, falls back to .env
# ===========================================================================

class ClientBundle:
    def __init__(self, openai_client, pinecone_index, azure_client):
        self.openai = openai_client
        self.pinecone = pinecone_index
        self.azure = azure_client


def get_clients(request: Request) -> ClientBundle:
    """
    Build per-request API clients from headers.
    Falls back to .env values when a header is absent (local dev support).
    Raises HTTP 401 with a clear message if a key is present but invalid.
    """
    openai_key = request.headers.get("X-OpenAI-Key") or os.getenv("OPENAI_API_KEY", "")
    pinecone_key = request.headers.get("X-Pinecone-Key") or os.getenv("PINECONE_API_KEY", "")
    azure_key = request.headers.get("X-Azure-Key") or os.getenv("AZURE_KEY", "")
    azure_endpoint = request.headers.get("X-Azure-Endpoint") or os.getenv("AZURE_ENDPOINT", "")

    if not openai_key:
        raise HTTPException(status_code=401, detail="OpenAI API key is missing. Please configure it in Settings.")
    if not pinecone_key:
        raise HTTPException(status_code=401, detail="Pinecone API key is missing. Please configure it in Settings.")

    try:
        oai = OpenAI(api_key=openai_key)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key. Please check your Settings.")

    try:
        pc = Pinecone(api_key=pinecone_key)
        pc_index = pc.Index("leasesight-index")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Pinecone API key. Please check your Settings.")

    azure_client = None
    if azure_key and azure_endpoint:
        try:
            azure_client = DocumentAnalysisClient(
                endpoint=azure_endpoint,
                credential=AzureKeyCredential(azure_key)
            )
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid Azure credentials. Please check your Settings.")

    return ClientBundle(oai, pc_index, azure_client)


# ===========================================================================
# REQUEST MODELS
# ===========================================================================

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

class DiffRequest(BaseModel):
    baseline_file: str
    target_file: str

class CalendarRequest(BaseModel):
    obligations: list[dict]


# ===========================================================================
# ENDPOINTS
# ===========================================================================

@app.get("/api/health")
async def health_check(clients: ClientBundle = Depends(get_clients)):
    status = {"status": "ok", "pinecone": "unknown", "openai": "unknown"}
    try:
        clients.pinecone.describe_index_stats()
        status["pinecone"] = "connected"
    except Exception:
        status["pinecone"] = "error"
    try:
        clients.openai.models.list()
        status["openai"] = "connected"
    except Exception:
        status["openai"] = "error"
    return status


@app.get("/api/documents")
async def list_documents():
    pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    return {"documents": pdfs, "count": len(pdfs)}


@app.get("/api/pdf/{filename:path}")
async def serve_pdf(filename: str):
    pdf_path = RAW_PDF_DIR / filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(str(pdf_path), media_type="application/pdf")


@app.get("/api/index-status/{filename:path}")
async def check_index_status(filename: str, clients: ClientBundle = Depends(get_clients)):
    json_path = JSON_MAP_DIR / f"{filename}.json"
    if not json_path.exists():
        target_path = RAW_PDF_DIR / filename
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="PDF not found")
        process_new_pdf(str(target_path), filename,
                        openai_client=clients.openai,
                        pinecone_index=clients.pinecone,
                        azure_client=clients.azure)
        return {"status": "indexed", "was_missing": True}
    return {"status": "indexed", "was_missing": False}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), clients: ClientBundle = Depends(get_clients)):
    target_path = RAW_PDF_DIR / file.filename
    try:
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
        process_new_pdf(str(target_path), file.filename,
                        openai_client=clients.openai,
                        pinecone_index=clients.pinecone,
                        azure_client=clients.azure)
        return {"file_name": file.filename, "status": "indexed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audit")
async def run_audit(request: AuditRequest, clients: ClientBundle = Depends(get_clients)):
    try:
        results = run_full_audit(request.file_name,
                                 openai_client=clients.openai,
                                 pinecone_index=clients.pinecone)
        if not results:
            return {"findings": [], "summary_paragraph": "No data found.", "risk_score": 1, "warnings": []}

        annotations = []
        for finding in results.get('findings', []):
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

        try:
            import pandas as pd, datetime
            excel_path = BASE_DIR / "audit_log.xlsx"
            df = pd.read_excel(excel_path) if excel_path.exists() else pd.DataFrame()
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_with_document(request: ChatRequest, clients: ClientBundle = Depends(get_clients)):
    try:
        result = ask_document(request.query, request.file_name,
                              openai_client=clients.openai,
                              pinecone_index=clients.pinecone)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/locate")
async def locate_snippet(request: LocateRequest):
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
    try:
        result = commit_to_knowledge_base(file_name=request.file_name, vector_ids=request.vector_ids)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diff")
async def get_diff(request: DiffRequest):
    import difflib
    baseline_name = request.baseline_file if request.baseline_file.endswith('.json') else f"{request.baseline_file}.json"
    target_name = request.target_file if request.target_file.endswith('.json') else f"{request.target_file}.json"
    baseline_path, target_path = JSON_MAP_DIR / baseline_name, JSON_MAP_DIR / target_name
    if not baseline_path.exists() or not target_path.exists():
        return {"additions": [], "deletions": []}
    with open(baseline_path) as f: base_data = json.load(f)
    with open(target_path) as f: target_data = json.load(f)

    def extract_lines(data):
        lines = []
        for p in data.get('pages', []):
            pn = p.get('page_number', 1)
            for l in p.get('lines', []):
                lines.append({"text": l.get('content', ''), "bbox": l.get('bounding_box', []), "page": pn})
        return lines

    base_lines, target_lines = extract_lines(base_data), extract_lines(target_data)
    sm = difflib.SequenceMatcher(None, [l['text'] for l in base_lines], [l['text'] for l in target_lines])
    additions, deletions = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('insert', 'replace'):
            for j in range(j1, j2):
                l = target_lines[j]
                if not l['bbox']: continue
                xs = [p['x'] for p in l['bbox']]; ys = [p['y'] for p in l['bbox']]
                additions.append({"page": l['page'], "x": min(xs), "y": min(ys), "width": max(xs)-min(xs), "height": max(ys)-min(ys), "color": "#10b981", "text": l['text']})
        if tag in ('delete', 'replace'):
            for i in range(i1, i2):
                l = base_lines[i]
                if not l['bbox']: continue
                xs = [p['x'] for p in l['bbox']]; ys = [p['y'] for p in l['bbox']]
                deletions.append({"page": l['page'], "x": min(xs), "y": min(ys), "width": max(xs)-min(xs), "height": max(ys)-min(ys), "color": "#ef4444", "text": l['text']})
    return {"additions": additions, "deletions": deletions}


@app.post("/api/analytics")
async def get_analytics_data(request: GraphRequest, clients: ClientBundle = Depends(get_clients)):
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        from sklearn.decomposition import PCA
        emb_res = clients.openai.embeddings.create(
            input=["Parties involved, rent details, address, and legal obligations"],
            model="text-embedding-3-small"
        )
        current_vec = emb_res.data[0].embedding
        internal_results = clients.pinecone.query(vector=current_vec, top_k=50,
            filter={"file_name": {"$eq": request.file_name}}, include_values=True, include_metadata=False)
        chunk_vectors = [m['values'] for m in internal_results.get('matches', []) if 'values' in m]
        similarities = cosine_similarity([current_vec], chunk_vectors)[0].tolist() if chunk_vectors else []
        results = clients.pinecone.query(vector=current_vec, top_k=100, include_values=True, include_metadata=True)
        vectors, names, seen = [], [], set()
        for match in results.get('matches', []):
            fn = match.get('metadata', {}).get('file_name', 'Unknown')
            if fn == request.file_name or fn in seen: continue
            seen.add(fn); vectors.append(match['values']); names.append(fn)
        if len(vectors) < 3:
            return {"archive_coords": [], "new_coords": [], "names": [], "sufficient": False,
                    "internal_similarities": similarities, "benchmark_score": 0}
        all_vectors = np.array(vectors + [current_vec])
        coords_3d = PCA(n_components=3).fit_transform(all_vectors)
        top_sims = sorted(cosine_similarity([current_vec], vectors)[0], reverse=True)[:10]
        return {"archive_coords": coords_3d[:-1].tolist(), "new_coords": coords_3d[-1].tolist(),
                "names": names, "sufficient": True, "internal_similarities": similarities,
                "benchmark_score": int(np.mean(top_sims) * 100)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calendar")
async def generate_calendar(request: CalendarRequest):
    from datetime import datetime, timedelta
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//LeaseSight//Obligations//EN"]
    for obs in request.obligations:
        dt = datetime.now() + timedelta(days=30)
        dt_str = dt.strftime("%Y%m%dT%H%M%S")
        lines.extend(["BEGIN:VEVENT", f"DTSTART:{dt_str}", f"DTEND:{dt_str}",
                       f"SUMMARY:{obs.get('label', 'Obligation')}",
                       f"DESCRIPTION:{obs.get('description', '')}\\nDate mentioned: {obs.get('date', '')}",
                       "END:VEVENT"])
    lines.append("END:VCALENDAR")
    return Response(content="\\r\\n".join(lines), media_type="text/calendar")


@app.get("/api/audit-log")
async def download_audit_log():
    excel_path = BASE_DIR / "audit_log.xlsx"
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="Audit log not found")
    return FileResponse(str(excel_path),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        filename="audit_log.xlsx")


@app.post("/api/export/{file_name:path}")
async def export_audit(file_name: str, request: Request):
    try:
        audit_results = await request.json()
        from scripts.report_generator import generate_audit_pdf
        pdf_bytes = generate_audit_pdf(audit_results, file_name)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query-analytics")
async def get_query_analytics(request: ChatRequest, clients: ClientBundle = Depends(get_clients)):
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        from sklearn.decomposition import PCA
        emb_res = clients.openai.embeddings.create(input=[request.query], model="text-embedding-3-small")
        query_vec = emb_res.data[0].embedding
        internal_results = clients.pinecone.query(vector=query_vec, top_k=50,
            filter={"file_name": {"$eq": request.file_name}}, include_values=True, include_metadata=False)
        chunk_vectors = [m['values'] for m in internal_results.get('matches', []) if 'values' in m]
        if len(chunk_vectors) < 2:
            return {"sufficient": False}
        similarities = cosine_similarity([query_vec], chunk_vectors)[0].tolist()
        coords_3d = PCA(n_components=3).fit_transform(np.array(chunk_vectors + [query_vec]))
        return {"sufficient": True, "archive_coords": coords_3d[:-1].tolist(),
                "new_coords": coords_3d[-1].tolist(), "similarities": similarities,
                "names": [f"Chunk {i+1}" for i in range(len(chunk_vectors))]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
