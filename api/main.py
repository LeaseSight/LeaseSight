import os, sys, json, sqlite3, uuid, hashlib
# MASTER KEY FIX: Force global proxy for all library calls
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_PROXY_URL") or "https://api.openai-proxy.com/v1"
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# Local Imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
from api.schemas import EntityStatus, MigrationEntity, MigrationTask, ResearchAuditRequest, ResearchScorecard, AuthKeys
from api.processor import UniversalProcessor, ResearchAuditor
from scripts.processor import process_new_pdf
from scripts.query_engine import ask_document
from scripts.visual_anchor import find_coordinates
from scripts.full_audit import run_full_audit

load_dotenv(BASE_DIR / ".env")
DB_PATH = BASE_DIR / "leasesight.db"
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS migration_batches
                 (id TEXT PRIMARY KEY, timestamp TEXT, user_hash TEXT, total_files INTEGER, processed_files INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS migration_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, file_name TEXT, category TEXT, value TEXT, confidence REAL, status TEXT DEFAULT 'PENDING', raw_json TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user_hash TEXT, file_name TEXT, lessor_lessee TEXT, rent TEXT, risk_score TEXT, key_terms TEXT)''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="LeaseSight Production API", version="4.0")

# 1. PERMANENT CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.leasesights.tech",
        "https://leasesights.tech",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# DEPENDENCY: HYBRID KEY SYSTEM (BYOK + Managed)
# ---------------------------------------------------------------------------

async def get_api_keys(request: Request) -> AuthKeys:
    universal_key = request.headers.get("X-API-Key")
    openai_key = request.headers.get("X-OpenAI-Key") or universal_key or os.getenv("MANAGED_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
    pinecone_key = request.headers.get("X-Pinecone-Key") or os.getenv("MANAGED_PINECONE_KEY") or os.getenv("PINECONE_API_KEY")
    azure_key = request.headers.get("X-Azure-Key") or os.getenv("MANAGED_AZURE_KEY") or os.getenv("AZURE_KEY")
    azure_endpoint = request.headers.get("X-Azure-Endpoint") or os.getenv("MANAGED_AZURE_ENDPOINT") or os.getenv("AZURE_ENDPOINT")

    if not openai_key:
        raise HTTPException(status_code=401, detail="No OpenAI API key provided.")

    return AuthKeys(openai_key=openai_key, pinecone_key=pinecone_key, azure_key=azure_key, azure_endpoint=azure_endpoint)

def get_clients(keys: AuthKeys = Depends(get_api_keys)):
    # 2. PERMANENT GEOBLOCK FIX (PROXY)
    openai_base_url = os.getenv("OPENAI_PROXY_URL") or "https://api.openai-proxy.com/v1"
    os.environ["OPENAI_BASE_URL"] = openai_base_url # Global safety net
    openai_client = OpenAI(api_key=keys.openai_key, base_url=openai_base_url)
    pc = Pinecone(api_key=keys.pinecone_key)
    pinecone_index = pc.Index("leasesight-index")
    
    azure_client = None
    if keys.azure_key and keys.azure_endpoint:
        azure_client = DocumentAnalysisClient(endpoint=keys.azure_endpoint, credential=AzureKeyCredential(keys.azure_key))
        
    return {"openai": openai_client, "pinecone": pinecone_index, "azure": azure_client}

# ---------------------------------------------------------------------------
# SERVICE 1: UNIVERSAL LEGACY MIGRATION
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def start_migration(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    clients: dict = Depends(get_clients),
    x_user_id: Optional[str] = Header(None)
):
    task_id = str(uuid.uuid4())[:8]
    target_path = RAW_PDF_DIR / file.filename
    content = await file.read()
    with open(target_path, "wb") as f:
        f.write(content)

    # Initialize batch in DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO migration_batches (id, timestamp, user_hash, total_files, processed_files, status) VALUES (?,?,?,?,?,?)",
              (task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), x_user_id, 1, 0, 'PENDING'))
    conn.commit()
    conn.close()

    # Trigger background task
    processor = UniversalProcessor(clients['openai'], clients['pinecone'], clients['azure'])
    background_tasks.add_task(processor.process_batch, task_id, [file.filename])

    return {"status": "success", "task_id": task_id, "filename": file.filename}

@app.get("/api/migrate/review/{task_id}")
async def get_migration_review(task_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, file_name, category, value, confidence, status FROM migration_results WHERE batch_id = ?", (task_id,))
    rows = c.fetchall()
    conn.close()
    return [MigrationEntity(id=r[0], file_name=r[1], category=r[2], value=r[3], confidence=r[4], status=r[5]) for r in rows]

@app.post("/api/migrate/finalize")
async def finalize_migration(task_id: str):
    conn = sqlite3.connect(DB_PATH)
    import pandas as pd
    import io
    df = pd.read_sql_query("SELECT file_name, category, value, confidence FROM migration_results WHERE batch_id = ? AND status = 'APPROVED'", conn, params=(task_id,))
    conn.close()
    if df.empty: raise HTTPException(status_code=400, detail="No approved items found.")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='MigrationResults')
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=Export_{task_id}.xlsx"})

# ---------------------------------------------------------------------------
# SERVICE 2: PEER-REVIEW & AUDIT
# ---------------------------------------------------------------------------

@app.post("/api/audit/research")
async def run_research_audit(request: ResearchAuditRequest, clients: dict = Depends(get_clients)):
    auditor = ResearchAuditor(clients['openai'], clients['pinecone'])
    return await auditor.audit_paper(request.file_name)

@app.post("/api/audit")
async def start_audit(request: dict, clients: dict = Depends(get_clients)):
    file_name = request.get("file_name")
    if not file_name: raise HTTPException(status_code=400, detail="file_name required")
    report = run_full_audit(file_name, openai_client=clients['openai'], pinecone_index=clients['pinecone'])
    
    if not report:
        raise HTTPException(status_code=500, detail="Audit engine returned no data.")
    
    if "error" in report:
        # Return a 404 if the document is missing from the DB, otherwise 500
        status_code = 404 if "not found" in report["error"].lower() else 500
        raise HTTPException(status_code=status_code, detail=report["error"])
    annotations = []
    for finding in report.get("findings", []):
        quote = finding.get("evidence_quote")
        if quote and quote != "Not Found":
            coords = find_coordinates(file_name, quote)
            if coords and "bounding_box" in coords and len(coords["bounding_box"]) >= 4:
                annotations.append({
                    "page": int(coords['page']),
                    "x": coords['bounding_box'][0]['x'],
                    "y": coords['bounding_box'][0]['y'],
                    "width": coords['bounding_box'][2]['x'] - coords['bounding_box'][0]['x'],
                    "height": coords['bounding_box'][2]['y'] - coords['bounding_box'][0]['y'],
                    "color": "#3b82f6"
                })
    report["annotations"] = annotations
    return report

@app.post("/api/chat")
async def chat(request: dict, clients: dict = Depends(get_clients)):
    query, file_name = request.get("query"), request.get("file_name")
    if not query or not file_name: raise HTTPException(status_code=400, detail="query/file_name required")
    result = ask_document(query, file_name, openai_client=clients['openai'], pinecone_index=clients['pinecone'])
    if result.get("source_text"):
        coords = find_coordinates(file_name, result["source_text"])
        if coords:
            result["annotation"] = {"page": int(coords['page']), "x": coords['bounding_box'][0]['x'], "y": coords['bounding_box'][0]['y'], "width": coords['bounding_box'][2]['x'] - coords['bounding_box'][0]['x'], "height": coords['bounding_box'][2]['y'] - coords['bounding_box'][0]['y'], "color": "#10b981"}
    return result

# ---------------------------------------------------------------------------
# CORE ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/api/documents")
async def list_documents():
    pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    return {"documents": pdfs, "count": len(pdfs)}

@app.get("/api/health")
async def health(request: Request):
    openai_key = request.headers.get("X-OpenAI-Key") or request.headers.get("X-API-Key") or os.getenv("MANAGED_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
    return {"status": "healthy", "version": "4.0", "openai": "connected" if openai_key else "missing"}

@app.get("/api/test-connection")
async def test_connection(x_openai_key: Optional[str] = Header(None), x_api_key: Optional[str] = Header(None)):
    openai_key = x_openai_key or x_api_key
    success = openai_key and openai_key.startswith("sk-")
    return {"success": success, "openai": "connected" if success else "missing"}

@app.get("/pdfs/{filename:path}")
async def serve_pdf(filename: str):
    target_path = RAW_PDF_DIR / filename
    if not target_path.exists(): raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(target_path), media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
