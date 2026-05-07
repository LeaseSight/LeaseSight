import os, sys, json, sqlite3, uuid, hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import pandas as pd
import io

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks
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

load_dotenv(BASE_DIR / ".env")
DB_PATH = BASE_DIR / "leasesight.db"
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Migration Batches
    c.execute('''CREATE TABLE IF NOT EXISTS migration_batches
                 (id TEXT PRIMARY KEY,
                  timestamp TEXT,
                  user_hash TEXT,
                  total_files INTEGER,
                  processed_files INTEGER,
                  status TEXT)''')
    
    # Migration Results with Status (PENDING, APPROVED, DISCARDED)
    c.execute('''CREATE TABLE IF NOT EXISTS migration_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  batch_id TEXT,
                  file_name TEXT,
                  category TEXT,
                  value TEXT,
                  confidence REAL,
                  status TEXT DEFAULT 'PENDING',
                  raw_json TEXT)''')
                  
    # Audit Logs for Interactive Auditor
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  user_hash TEXT,
                  file_name TEXT,
                  lessor_lessee TEXT,
                  rent TEXT,
                  risk_score TEXT,
                  key_terms TEXT)''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="LeaseSight Production API", version="4.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = BASE_DIR / "leasesight.db"
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# DEPENDENCY: HYBRID KEY SYSTEM (BYOK + Managed)
# ---------------------------------------------------------------------------

async def get_api_keys(request: Request) -> AuthKeys:
    """
    Dependency to resolve API keys.
    Priority: Request Headers (X-OpenAI-Key, etc.) -> .env (Managed)
    """
    openai_key = request.headers.get("X-OpenAI-Key") or os.getenv("MANAGED_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
    pinecone_key = request.headers.get("X-Pinecone-Key") or os.getenv("MANAGED_PINECONE_KEY") or os.getenv("PINECONE_API_KEY")
    azure_key = request.headers.get("X-Azure-Key") or os.getenv("MANAGED_AZURE_KEY") or os.getenv("AZURE_KEY")
    azure_endpoint = request.headers.get("X-Azure-Endpoint") or os.getenv("MANAGED_AZURE_ENDPOINT") or os.getenv("AZURE_ENDPOINT")
    
    if not openai_key:
        raise HTTPException(status_code=401, detail="No OpenAI API key provided or configured.")
        
    return AuthKeys(
        openai_key=openai_key,
        pinecone_key=pinecone_key,
        azure_key=azure_key,
        azure_endpoint=azure_endpoint
    )

def get_clients(keys: AuthKeys = Depends(get_api_keys)):
    openai_client = OpenAI(api_key=keys.openai_key)
    pc = Pinecone(api_key=keys.pinecone_key)
    pinecone_index = pc.Index("leasesight-index")
    
    azure_client = None
    if keys.azure_key and keys.azure_endpoint:
        azure_client = DocumentAnalysisClient(
            endpoint=keys.azure_endpoint,
            credential=AzureKeyCredential(keys.azure_key)
        )
        
    return {
        "openai": openai_client,
        "pinecone": pinecone_index,
        "azure": azure_client
    }

# ---------------------------------------------------------------------------
# AUTH: CLERK JWT VERIFICATION (Placeholder/Simulated for local dev)
# ---------------------------------------------------------------------------

async def verify_auth(request: Request):
    """
    Verifies the Clerk JWT token from the Authorization header.
    In production, use clerk_sdk.verify_token(token).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        # Fallback for local testing if needed, but in prod this should fail
        return "anonymous"
    
    # Token logic goes here...
    return "user_verified"

# ---------------------------------------------------------------------------
# SERVICE 1: UNIVERSAL LEGACY MIGRATION
# ---------------------------------------------------------------------------

@app.post("/api/migrate/upload")
async def start_migration(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...), 
    clients: dict = Depends(get_clients),
    user_id: str = Depends(verify_auth)
):
    task_id = str(uuid.uuid4())[:8]
    file_names = []
    
    for file in files:
        target_path = RAW_PDF_DIR / file.filename
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
        file_names.append(file.filename)
    
    # Initialize batch in DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO migration_batches (id, timestamp, user_hash, total_files, processed_files, status) VALUES (?,?,?,?,?,?)",
              (task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id, len(file_names), 0, 'PENDING'))
    conn.commit()
    conn.close()
    
    # Trigger background task
    processor = UniversalProcessor(clients['openai'], clients['pinecone'], clients['azure'])
    background_tasks.add_task(processor.process_batch, task_id, file_names)
    
    return {"task_id": task_id, "status": "QUEUED", "file_count": len(file_names)}

@app.get("/api/migrate/review/{task_id}")
async def get_migration_review(task_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, file_name, category, value, confidence, status FROM migration_results WHERE batch_id = ?", (task_id,))
    rows = c.fetchall()
    conn.close()
    
    results = [
        MigrationEntity(id=r[0], file_name=r[1], category=r[2], value=r[3], confidence=r[4], status=r[5])
        for r in rows
    ]
    return results

@app.post("/api/migrate/finalize")
async def finalize_migration(task_id: str):
    """
    Exports only 'APPROVED' items to a downloadable Excel file.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT file_name, category, value, confidence FROM migration_results WHERE batch_id = ? AND status = 'APPROVED'", conn, params=(task_id,))
    conn.close()
    
    if df.empty:
        raise HTTPException(status_code=400, detail="No approved items found to export.")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='MigrationResults')
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Migration_Export_{task_id}.xlsx"}
    )

# ---------------------------------------------------------------------------
# SERVICE 2: PEER-REVIEW ASSISTANT
# ---------------------------------------------------------------------------

@app.post("/api/audit/research")
async def run_research_audit(
    request: ResearchAuditRequest, 
    clients: dict = Depends(get_clients)
):
    auditor = ResearchAuditor(clients['openai'], clients['pinecone'])
    scorecard = await auditor.audit_paper(request.file_name)
    return scorecard

# ---------------------------------------------------------------------------
# CORE ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/api/documents")
async def list_documents():
    pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    return {"documents": pdfs, "count": len(pdfs)}

@app.get("/pdfs/{filename:path}")
async def serve_pdf(filename: str):
    target_path = RAW_PDF_DIR / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(str(target_path), media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
