import os, sys, json, sqlite3, uuid, hashlib, io, time
# 1. HARDENED PATH RESOLUTION
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

def clean_secret(value):
    if not value:
        return value
    return value.strip().strip('"').strip("'")

# 2. MASTER GEOBLOCK BYPASS
OPENAI_BASE_URL = clean_secret(os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_PROXY_URL")) or "https://api.openai-proxy.com/v1"
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks, Header
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from openai import OpenAI
from pinecone import Pinecone

# ReportLab for PDF Export
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from xml.sax.saxutils import escape

# Local Imports
from api.schemas import EntityStatus, MigrationEntity, AuthKeys
from api.processor import UniversalProcessor
from app.core.evaluator import evaluate_live_document, run_system_evaluation
from scripts.processor import process_new_pdf
from scripts.full_audit import run_full_audit
from scripts.visual_anchor import find_coordinates

# Directories
DB_PATH = os.path.join(BASE_DIR, "leasesight.db")
RAW_PDF_DIR = os.path.join(BASE_DIR, "data", "raw_pdfs")
JSON_MAP_DIR = os.path.join(BASE_DIR, "data", "json_maps")
os.makedirs(RAW_PDF_DIR, exist_ok=True)
os.makedirs(JSON_MAP_DIR, exist_ok=True)


class ContactPayload(BaseModel):
    email: str
    industry: str
    company_size: str | None = None
    message: str


def init_local_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            industry TEXT NOT NULL,
            company_size TEXT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS live_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            file_name TEXT NOT NULL,
            status TEXT NOT NULL,
            query TEXT,
            generated_output TEXT,
            retrieved_chunk_count INTEGER DEFAULT 0,
            faithfulness REAL DEFAULT 0,
            answer_relevance REAL DEFAULT 0,
            groundedness_index REAL DEFAULT 0,
            is_trusted INTEGER DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


init_local_tables()

async def get_api_keys(request: Request) -> AuthKeys:
    openai_key = (
        request.headers.get("X-OpenAI-Key")
        or request.headers.get("X-API-Key")
        or os.getenv("OPENAI_API_KEY")
    )
    pinecone_key = os.getenv("PINECONE_API_KEY")
    azure_key = os.getenv("AZURE_KEY")
    azure_endpoint = os.getenv("AZURE_ENDPOINT")
    return AuthKeys(
        openai_key=clean_secret(openai_key),
        pinecone_key=clean_secret(pinecone_key),
        azure_key=clean_secret(azure_key),
        azure_endpoint=clean_secret(azure_endpoint),
    )

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

@app.get("/api/v1/evaluation")
async def get_evaluation_summary():
    try:
        summary = await run_system_evaluation()
        return {
            "status": "success",
            "deepeval_metrics": summary["deepeval_metrics"],
            "academic_benchmark": summary["academic_benchmark"],
            "failed_cases": summary.get("failed_cases", []),
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evaluation failed: {e}")

@app.api_route("/api/test-connection", methods=["GET", "POST", "OPTIONS"])
async def test_connection(keys: AuthKeys = Depends(get_api_keys)):
    try:
        client = OpenAI(api_key=keys.openai_key, base_url="https://api.openai-proxy.com/v1")
        client.models.list()
        return {"success": True, "status": "success", "message": "OpenAI connection verified"}
    except Exception as e:
        return {"success": False, "status": "error", "message": str(e)}

@app.post("/api/contact")
async def contact(payload: ContactPayload):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO contact_inquiries (email, industry, company_size, message) VALUES (?, ?, ?, ?)",
        (payload.email, payload.industry, payload.company_size, payload.message),
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Contact request received"}

def _collect_live_evaluation_chunks(file_name: str, openai_client: OpenAI, pinecone_index) -> List[str]:
    chunks = []
    try:
        res = openai_client.embeddings.create(
            input=["Lease compliance audit summary, critical clauses, obligations, risk warnings"],
            model="text-embedding-3-small",
        )
        query_vector = res.data[0].embedding
        results = pinecone_index.query(
            vector=query_vector,
            top_k=8,
            filter={"file_name": {"$eq": file_name}},
            include_metadata=True,
        )
        for match in results.get("matches", []):
            text = (match.get("metadata") or {}).get("text")
            if text:
                chunks.append(str(text))
    except Exception as e:
        print(f"[LIVE_EVAL] Pinecone chunk collection skipped for {file_name}: {e}")

    if chunks:
        return chunks

    json_map_path = os.path.join(JSON_MAP_DIR, f"{file_name}.json")
    try:
        with open(json_map_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for page in data.get("pages", [])[:8]:
            page_text = " ".join(
                line.get("content", "")
                for line in page.get("lines", [])
                if line.get("content")
            )
            if page_text.strip():
                chunks.append(page_text)
    except Exception as e:
        print(f"[LIVE_EVAL] JSON map chunk collection skipped for {file_name}: {e}")

    return chunks

def _audit_report_to_text(report: dict) -> str:
    return json.dumps(
        {
            "lease_metadata": report.get("lease_metadata", {}),
            "findings": report.get("findings", []),
            "obligations": report.get("obligations", []),
            "summary_paragraph": report.get("summary_paragraph", ""),
            "risk_score": report.get("risk_score"),
            "warnings": report.get("warnings", []),
        },
        ensure_ascii=True,
    )

def _save_live_evaluation_status(
    task_id: str,
    file_name: str,
    status: str,
    scores: Optional[Dict[str, Any]] = None,
    query: Optional[str] = None,
    generated_output: Optional[str] = None,
    retrieved_chunk_count: int = 0,
    error: Optional[str] = None,
):
    scores = scores or {}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO live_evaluations (
            task_id, file_name, status, query, generated_output, retrieved_chunk_count,
            faithfulness, answer_relevance, groundedness_index, is_trusted, error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            file_name,
            status,
            query,
            generated_output,
            retrieved_chunk_count,
            float(scores.get("faithfulness", 0.0) or 0.0),
            float(scores.get("answer_relevance", 0.0) or 0.0),
            float(scores.get("groundedness_index", 0.0) or 0.0),
            1 if scores.get("is_trusted") else 0,
            error or scores.get("error"),
        ),
    )
    conn.commit()
    conn.close()

def _latest_live_evaluation(file_name: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        """
        SELECT *
        FROM live_evaluations
        WHERE file_name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (file_name,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["is_trusted"] = bool(data.get("is_trusted"))
    return data

def _run_background_live_verification(
    task_id: str,
    file_names: List[str],
    openai_key: str,
    pinecone_key: str,
):
    openai_client = OpenAI(api_key=openai_key, base_url=os.environ["OPENAI_BASE_URL"])
    pc = Pinecone(api_key=pinecone_key)
    index = pc.Index("leasesight-index")
    live_eval_query = (
        "Evaluate whether this generated lease clause analysis is grounded in the "
        "retrieved contract text and relevant to legal compliance review."
    )

    for file_name in file_names:
        _save_live_evaluation_status(
            task_id=task_id,
            file_name=file_name,
            status="PROCESSING",
            query=live_eval_query,
        )
        try:
            for _ in range(12):
                if os.path.exists(os.path.join(JSON_MAP_DIR, f"{file_name}.json")):
                    break
                time.sleep(5)

            report = run_full_audit(
                file_name,
                openai_client=openai_client,
                pinecone_index=index,
            )
            if not report or report.get("error"):
                raise RuntimeError(report.get("error") if isinstance(report, dict) else "Audit report was empty.")

            generated_output = _audit_report_to_text(report)
            retrieved_chunks = _collect_live_evaluation_chunks(file_name, openai_client, index)
            scores = evaluate_live_document(
                user_query=live_eval_query,
                generated_output=generated_output,
                retrieved_chunks=retrieved_chunks,
            )
            _save_live_evaluation_status(
                task_id=task_id,
                file_name=file_name,
                status="COMPLETED",
                scores=scores,
                query=live_eval_query,
                generated_output=generated_output,
                retrieved_chunk_count=len(retrieved_chunks),
            )
            print(f"[LIVE_EVAL] Completed {file_name}: {scores}")
        except Exception as e:
            _save_live_evaluation_status(
                task_id=task_id,
                file_name=file_name,
                status="FAILED",
                query=live_eval_query,
                error=str(e)[:500],
            )
            print(f"[LIVE_EVAL] Failed for {file_name}: {e}")

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
    summary_paragraph = request.get("summary_paragraph", "") or request.get("summary", "")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=48,
        bottomMargin=48,
        title=f"LeaseSight Audit Report: {filename}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "LeaseSightTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "LeaseSightMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=4,
    )
    section_style = ParagraphStyle(
        "LeaseSightSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "LeaseSightBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )
    cell_style = ParagraphStyle(
        "LeaseSightCell",
        parent=body_style,
        fontSize=8.5,
        leading=11,
    )

    story = [
        Paragraph(f"LeaseSight Audit Report: {escape(filename)}", title_style),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style),
        Paragraph(f"Risk Score: {escape(str(risk_score))}/10", meta_style),
        Spacer(1, 12),
        Paragraph("Executive Brief", section_style),
        Paragraph(escape(summary_paragraph or "No executive brief was provided."), body_style),
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d1d5db"), spaceBefore=4, spaceAfter=12),
        Paragraph("Key Findings", section_style),
    ]

    table_data = [[
        Paragraph("Finding", cell_style),
        Paragraph("Value", cell_style),
        Paragraph("Risk", cell_style),
    ]]
    for finding in findings:
        table_data.append([
            Paragraph(escape(str(finding.get("label", ""))), cell_style),
            Paragraph(escape(str(finding.get("value", ""))), cell_style),
            Paragraph(escape(str(finding.get("risk_level", ""))), cell_style),
        ])

    if len(table_data) == 1:
        story.append(Paragraph("No findings were included in this audit export.", body_style))
    else:
        findings_table = Table(table_data, colWidths=[160, 250, 70], repeatRows=1)
        findings_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(findings_table)

    doc.build(story)
    buffer.seek(0)
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
        live_eval_query = (
            "Evaluate whether this lease compliance audit is faithful to the retrieved "
            "contract text and relevant to identifying key lease terms, obligations, and risks."
        )
        live_eval_chunks = _collect_live_evaluation_chunks(file_name, openai_client, index)
        live_trust_scores = evaluate_live_document(
            user_query=live_eval_query,
            generated_output=_audit_report_to_text(report),
            retrieved_chunks=live_eval_chunks,
        )
        
        # --- FIX: EXHAUSTIVE MARKING LOGIC ---
        annotations = []
        all_findings = report.get("findings", []) + report.get("obligations", [])
        for item in all_findings:
            quote = item.get("evidence_quote")
            if quote and len(quote) > 15 and quote != "Not Found":
                try:
                    coords = find_coordinates(file_name, quote)
                except Exception as e:
                    print(f"[ANNOTATION] skipped coordinate lookup for {file_name}: {e}")
                    coords = None
                if coords and "bounding_box" in coords:
                    bbox = coords["bounding_box"]
                    xs = [point["x"] for point in bbox]
                    ys = [point["y"] for point in bbox]
                    x1, x2 = min(xs), max(xs)
                    y1, y2 = min(ys), max(ys)
                    annotations.append({
                        "page": int(coords.get('page', 1)), 
                        "x": x1, "y": y1, 
                        "width": max(0, x2 - x1), 
                        "height": max(0, y2 - y1), 
                        "color": "#3b82f6",
                        "label": item.get("label", "Key Term")
                    })
        
        report["annotations"] = annotations
        report["live_trust_scores"] = live_trust_scores
        report["analysis_results"] = {
            key: value
            for key, value in report.items()
            if key not in {"analysis_results", "live_trust_scores"}
        }
        return report
    except Exception as e:
        return {"error": str(e), "findings": [], "obligations": []}

@app.post("/api/upload")
async def start_migration(background_tasks: BackgroundTasks, files: List[UploadFile] = File(None, alias="file"), keys: AuthKeys = Depends(get_api_keys)):
    if not files: raise HTTPException(status_code=422, detail="No files")
    if not keys.openai_key:
        raise HTTPException(status_code=401, detail="OpenAI API key is missing. Add it in settings or configure OPENAI_API_KEY on the server.")
    if not keys.pinecone_key:
        raise HTTPException(status_code=401, detail="Pinecone API key is missing. Add it in settings or configure PINECONE_API_KEY on the server.")
    if not keys.azure_key or not keys.azure_endpoint:
        raise HTTPException(status_code=401, detail="Azure Document Intelligence credentials are missing. Add them in settings or configure AZURE_KEY and AZURE_ENDPOINT on the server.")

    try:
        task_id = str(uuid.uuid4())[:8]
        file_names = [os.path.basename(f.filename) for f in files]
        for file in files:
            target = os.path.join(RAW_PDF_DIR, os.path.basename(file.filename))
            with open(target, "wb") as f:
                f.write(await file.read())

        openai_client = OpenAI(api_key=keys.openai_key, base_url=os.environ["OPENAI_BASE_URL"])
        pc = Pinecone(api_key=keys.pinecone_key)
        index = pc.Index("leasesight-index")
        azure_client = DocumentAnalysisClient(
            endpoint=keys.azure_endpoint,
            credential=AzureKeyCredential(keys.azure_key),
        )

        def index_uploaded_files():
            for name in file_names:
                path = os.path.join(RAW_PDF_DIR, name)
                try:
                    process_new_pdf(path, name, openai_client=openai_client, pinecone_index=index, azure_client=azure_client)
                    print(f"[UPLOAD] Indexed {name}")
                except Exception as e:
                    print(f"[UPLOAD] Indexing failed for {name}: {e}")

        processor = UniversalProcessor(openai_client, index, None)
        background_tasks.add_task(index_uploaded_files)
        background_tasks.add_task(processor.process_batch, task_id, file_names)
        background_tasks.add_task(
            _run_background_live_verification,
            task_id,
            file_names,
            keys.openai_key,
            keys.pinecone_key,
        )
        return {
            "status": "success",
            "task_id": task_id,
            "file_name": file_names[0],
            "files": file_names,
            "live_evaluation": {
                "status": "QUEUED",
                "status_url": f"/api/live-evaluation/{file_names[0]}",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upload initialization failed: {e}")

@app.get("/api/index-status/{filename:path}")
async def get_index_status(filename: str):
    if os.path.exists(os.path.join(JSON_MAP_DIR, f"{filename}.json")):
        return {"status": "COMPLETED", "indexed": True}
    if os.path.exists(os.path.join(RAW_PDF_DIR, filename)):
        return {"status": "PROCESSING", "indexed": False}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM migration_results WHERE file_name = ? LIMIT 1", (filename,))
    result = c.fetchone()
    conn.close()
    return {"status": "COMPLETED", "indexed": True} if result else {"status": "PENDING", "indexed": False}

@app.get("/api/live-evaluation/{filename:path}")
async def get_live_evaluation_status(filename: str):
    latest = _latest_live_evaluation(filename)
    if not latest:
        return {
            "status": "QUEUED",
            "file_name": filename,
            "live_trust_scores": None,
        }

    return {
        "status": latest["status"],
        "file_name": latest["file_name"],
        "task_id": latest.get("task_id"),
        "retrieved_chunk_count": latest.get("retrieved_chunk_count", 0),
        "live_trust_scores": {
            "faithfulness": latest.get("faithfulness", 0.0),
            "answer_relevance": latest.get("answer_relevance", 0.0),
            "groundedness_index": latest.get("groundedness_index", 0.0),
            "is_trusted": latest.get("is_trusted", False),
        },
        "error": latest.get("error"),
        "updated_at": latest.get("updated_at"),
    }

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
