import os, sys, json, sqlite3, uuid, hashlib, io, time
# 1. HARDENED PATH RESOLUTION
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

# 2. MASTER GEOBLOCK BYPASS
os.environ["OPENAI_BASE_URL"] = "https://api.openai-proxy.com/v1"

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks, Header
from fastapi.responses import FileResponse, Response, StreamingResponse
from openai import OpenAI
from pinecone import Pinecone

# ReportLab for PDF Export
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Local Imports
from api.schemas import EntityStatus, MigrationEntity, AuthKeys
from api.processor import UniversalProcessor
from scripts.full_audit import run_full_audit
from scripts.visual_anchor import find_coordinates

# Directories
DB_PATH = os.path.join(BASE_DIR, "leasesight.db")
RAW_PDF_DIR = os.path.join(BASE_DIR, "data", "raw_pdfs")
os.makedirs(RAW_PDF_DIR, exist_ok=True)

async def get_api_keys(request: Request) -> AuthKeys:
    openai_key = request.headers.get("X-OpenAI-Key") or os.getenv("OPENAI_API_KEY")
    pinecone_key = request.headers.get("X-Pinecone-Key") or os.getenv("PINECONE_API_KEY")
    return AuthKeys(openai_key=openai_key, pinecone_key=pinecone_key)

app = FastAPI(title="LeaseSight Production API")

# CORS is handled ONLY by Caddy reverse proxy
# This middleware ensures FastAPI never sends CORS headers (strip them if they exist)
@app.middleware("http")
async def remove_cors_headers(request: Request, call_next):
    response = await call_next(request)
    # Strip all CORS headers from response - Caddy will add the correct ones
    headers_to_remove = [
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Credentials",
        "Access-Control-Expose-Headers",
        "Access-Control-Max-Age"
    ]
    for header in headers_to_remove:
        try:
            del response.headers[header]
        except KeyError:
            pass
    return response

@app.get("/api/health")
async def health():
    return {
        "status": "ULTRA_HEALTHY",
        "version": "1.3.1",
        "last_sync": "2026-05-10 01:21:00",
        "proxy": os.environ.get("OPENAI_BASE_URL")
    }

@app.api_route("/api/test-connection", methods=["GET", "POST", "OPTIONS"])
async def test_connection(keys: AuthKeys = Depends(get_api_keys)):
    try:
        client = OpenAI(api_key=keys.openai_key, base_url="https://api.openai-proxy.com/v1")
        client.models.list()
        return {"status": "success", "message": "BYOK Connection Verified"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/commit")
async def commit_audit(request: Request):
    try:
        data = await request.json()
        task_id = data.get("task_id")
        if not task_id: raise HTTPException(status_code=400, detail="task_id required")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE migration_results SET status = 'APPROVED' WHERE batch_id = ?", (task_id,))
        c.execute("UPDATE migration_batches SET status = 'COMPLETED' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Batch Approved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/export/{filename:path}")
async def export_audit(filename: str, request: dict):
    findings = request.get("findings", [])
    risk_score = request.get("risk_score", 0)
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, f"LeaseSight Audit Report: {filename}")
    p.setFont("Helvetica", 12)
    p.drawString(50, 730, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(50, 710, f"Risk Score: {risk_score}/10")
    y = 680
    for f in findings:
        if y < 100: p.showPage(); y = 750
        p.setFont("Helvetica-Bold", 10); p.drawString(50, y, f"Finding: {f.get('label')}")
        p.setFont("Helvetica", 10); p.drawString(70, y-15, f"Value: {f.get('value')}")
        y -= 40
    p.showPage(); p.save(); buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=audit_{filename}"})

@app.post("/api/audit")
async def start_audit(request: dict, keys: AuthKeys = Depends(get_api_keys)):
    try:
        file_name = request.get("file_name")
        if not file_name: return {"error": "file_name required", "findings": [], "obligations": []}
        
        openai_client = OpenAI(api_key=keys.openai_key, base_url="https://api.openai-proxy.com/v1")
        pc = Pinecone(api_key=keys.pinecone_key)
        index = pc.Index("leasesight-index")
        
        report = run_full_audit(file_name, openai_client=openai_client, pinecone_index=index)
        if not report: report = {"findings": [], "risk_score": 0}
        
        report.setdefault("findings", [])
        report.setdefault("obligations", [])
        
        # --- FIX: EXHAUSTIVE MARKING LOGIC ---
        annotations = []
        all_findings = report.get("findings", []) + report.get("obligations", [])
        for item in all_findings:
            quote = item.get("evidence_quote")
            if quote and len(quote) > 15 and quote != "Not Found":
                coords = find_coordinates(file_name, quote)
                if coords and "bounding_box" in coords:
                    bbox = coords["bounding_box"]
                    annotations.append({
                        "page": int(coords.get('page', 1)), 
                        "x": bbox[0]['x'], "y": bbox[0]['y'], 
                        "width": bbox[2]['x'] - bbox[0]['x'], 
                        "height": bbox[2]['y'] - bbox[0]['y'], 
                        "color": "#3b82f6",
                        "label": item.get("label", "Key Term")
                    })
        
        report["annotations"] = annotations
        return report
    except Exception as e:
        return {"error": str(e), "findings": [], "obligations": []}

@app.post("/api/upload")
async def start_migration(background_tasks: BackgroundTasks, files: List[UploadFile] = File(None, alias="file")):
    if not files: raise HTTPException(status_code=422, detail="No files")
    task_id = str(uuid.uuid4())[:8]
    file_names = [f.filename for f in files]
    for file in files:
        with open(os.path.join(RAW_PDF_DIR, file.filename), "wb") as f: f.write(await file.read())
    
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.environ["OPENAI_BASE_URL"])
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index("leasesight-index")
    processor = UniversalProcessor(openai_client, index, None)
    background_tasks.add_task(processor.process_batch, task_id, file_names)
    return {"status": "success", "task_id": task_id, "files": file_names}

@app.get("/api/index-status/{filename:path}")
async def get_index_status(filename: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM migration_results WHERE file_name = ? LIMIT 1", (filename,))
    result = c.fetchone()
    conn.close()
    return {"status": "COMPLETED", "indexed": True} if result else {"status": "PENDING", "indexed": False}

@app.get("/api/documents")
async def list_documents():
    pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    return {"documents": pdfs}

@app.get("/api/ping")
async def ping():
    return {"message": "PONG - NEW CODE IS LIVE"}

@app.get("/pdfs/{filename:path}")
async def serve_pdf(filename: str):
    target_path = os.path.join(RAW_PDF_DIR, filename)
    if not os.path.exists(target_path): raise HTTPException(status_code=404)
    return FileResponse(target_path, media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
