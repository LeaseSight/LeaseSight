import os, sys, json, sqlite3, uuid, hashlib
# 1. PATH FIX: Ensure Docker can see the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 2. MASTER KEY FIX: Force global proxy for all library calls
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

# Local Imports
from api.schemas import EntityStatus, MigrationEntity, MigrationTask, ResearchAuditRequest, ResearchScorecard, AuthKeys
from api.processor import UniversalProcessor, ResearchAuditor
from scripts.processor import process_new_pdf
from scripts.query_engine import ask_document
from scripts.visual_anchor import find_coordinates
from scripts.full_audit import run_full_audit

BASE_DIR = Path(__file__).resolve().parents[1]
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

app = FastAPI(title="LeaseSight Production API", version="5.0")

# PERMANENT CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# DEPENDENCIES
# ---------------------------------------------------------------------------

async def get_api_keys(request: Request) -> AuthKeys:
    openai_key = request.headers.get("X-OpenAI-Key") or os.getenv("OPENAI_API_KEY")
    pinecone_key = request.headers.get("X-Pinecone-Key") or os.getenv("PINECONE_API_KEY")
    if not openai_key: raise HTTPException(status_code=401, detail="No OpenAI API key.")
    return AuthKeys(openai_key=openai_key, pinecone_key=pinecone_key, azure_key=os.getenv("AZURE_KEY"), azure_endpoint=os.getenv("AZURE_ENDPOINT"))

def get_clients(keys: AuthKeys = Depends(get_api_keys)):
    proxy = os.environ["OPENAI_BASE_URL"]
    openai_client = OpenAI(api_key=keys.openai_key, base_url=proxy)
    pc = Pinecone(api_key=keys.pinecone_key)
    index = pc.Index("leasesight-index")
    return {"openai": openai_client, "pinecone": index}

# ---------------------------------------------------------------------------
# ENDPOINTS
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

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO migration_batches (id, timestamp, user_hash, total_files, processed_files, status) VALUES (?,?,?,?,?,?)",
              (task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), x_user_id, 1, 0, 'PENDING'))
    conn.commit()
    conn.close()

    processor = UniversalProcessor(clients['openai'], clients['pinecone'], None)
    background_tasks.add_task(processor.process_batch, task_id, [file.filename])
    return {"status": "success", "task_id": task_id, "filename": file.filename}

@app.post("/api/audit")
async def start_audit(request: dict, clients: dict = Depends(get_clients)):
    try:
        file_name = request.get("file_name")
        if not file_name: return {"error": "file_name required"}
        
        report = run_full_audit(file_name, openai_client=clients['openai'], pinecone_index=clients['pinecone'])
        if not report: return {"error": "Audit failed"}
        if "error" in report: return report

        annotations = []
        for finding in report.get("findings", []):
            quote = finding.get("evidence_quote")
            if quote and quote != "Not Found":
                coords = find_coordinates(file_name, quote)
                if coords and "bounding_box" in coords and len(coords["bounding_box"]) >= 4:
                    bbox = coords["bounding_box"]
                    annotations.append({"page": int(coords['page']), "x": bbox[0]['x'], "y": bbox[0]['y'], "width": bbox[2]['x'] - bbox[0]['x'], "height": bbox[2]['y'] - bbox[0]['y'], "color": "#3b82f6"})
        report["annotations"] = annotations
        return report
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/documents")
async def list_documents():
    pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    return {"documents": pdfs, "count": len(pdfs)}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "proxy": os.environ["OPENAI_BASE_URL"]}

@app.get("/pdfs/{filename:path}")
async def serve_pdf(filename: str):
    target_path = RAW_PDF_DIR / filename
    if not target_path.exists(): raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(target_path), media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
