import os, sys, json, sqlite3, uuid, hashlib
# 1. HARDENED PATH RESOLUTION
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

# 2. MASTER GEOBLOCK BYPASS (HARDCODED FAIL-SAFE)
os.environ["OPENAI_BASE_URL"] = "https://api.openai-proxy.com/v1"

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from openai import OpenAI
from pinecone import Pinecone

# Local Imports (Using absolute-style paths for Docker stability)
from api.schemas import EntityStatus, MigrationEntity, AuthKeys
from api.processor import UniversalProcessor
from scripts.full_audit import run_full_audit

# Directories
DB_PATH = os.path.join(BASE_DIR, "leasesight.db")
RAW_PDF_DIR = os.path.join(BASE_DIR, "data", "raw_pdfs")
os.makedirs(RAW_PDF_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS migration_batches
                 (id TEXT PRIMARY KEY, timestamp TEXT, user_hash TEXT, total_files INTEGER, processed_files INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS migration_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id TEXT, file_name TEXT, category TEXT, value TEXT, confidence REAL, status TEXT DEFAULT 'PENDING', raw_json TEXT)''')
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="LeaseSight Production API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def start_migration(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(None, alias="file"),
    x_user_id: Optional[str] = Header(None)
):
    if not files:
        # Fallback if both 'file' and 'files' are missing
        raise HTTPException(status_code=422, detail="No files provided. Use field name 'file' or 'files'.")
    task_id = str(uuid.uuid4())[:8]
    file_names = []
    
    for file in files:
        target_path = os.path.join(RAW_PDF_DIR, file.filename)
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
        file_names.append(file.filename)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO migration_batches (id, timestamp, user_hash, total_files, processed_files, status) VALUES (?,?,?,?,?,?)",
              (task_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), x_user_id, len(file_names), 0, 'PENDING'))
    conn.commit()
    conn.close()

    # Client Init with Proxy
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.environ["OPENAI_BASE_URL"])
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index("leasesight-index")

    processor = UniversalProcessor(openai_client, index, None)
    background_tasks.add_task(processor.process_batch, task_id, file_names)
    
    return {"status": "success", "task_id": task_id, "files": file_names}

@app.post("/api/audit")
async def start_audit(request: dict):
    try:
        file_name = request.get("file_name")
        if not file_name: return {"error": "file_name required"}
        
        # Hardcoded proxy initialization
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.openai-proxy.com/v1")
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("leasesight-index")
        
        return run_full_audit(file_name, openai_client=openai_client, pinecone_index=index)
    except Exception as e:
        return {"error": f"Internal Server Error: {str(e)}"}

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.5",
        "last_sync": "2026-05-09 20:25:00",
        "proxy": os.environ.get("OPENAI_BASE_URL")
    }

@app.get("/api/documents")
async def list_documents():
    pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    return {"documents": pdfs}

@app.get("/pdfs/{filename:path}")
async def serve_pdf(filename: str):
    target_path = os.path.join(RAW_PDF_DIR, filename)
    if not os.path.exists(target_path): raise HTTPException(status_code=404)
    return FileResponse(target_path, media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
