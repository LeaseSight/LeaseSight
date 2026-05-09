import os
import json
import sqlite3
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI
from scripts.processor import process_new_pdf
from scripts.query_engine import ask_document
from scripts.visual_anchor import find_coordinates
from api.schemas import EntityStatus, MigrationEntity, ResearchScorecard, Finding, Coordinate

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "leasesight.db"

class UniversalProcessor:
    def __init__(self, openai_client, pinecone_index, azure_client):
        self.openai = openai_client
        self.pinecone = pinecone_index
        self.azure = azure_client
        
        # PERMANENT GEOBLOCK FIX (Enforced in background tasks)
        proxy_url = os.getenv("OPENAI_PROXY_URL") or "https://api.openai-proxy.com/v1"
        self.openai.base_url = proxy_url

    async def process_batch(self, task_id: str, files: List[str]):
        """
        Processes a batch of files: OCR, Index, and Universal Entity Extraction.
        """
        RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
        
        for file_name in files:
            try:
                pdf_path = RAW_PDF_DIR / file_name
                
                # 1. OCR & Indexing
                process_new_pdf(str(pdf_path), file_name, 
                                openai_client=self.openai, 
                                pinecone_index=self.pinecone, 
                                azure_client=self.azure)
                
                # 2. Universal Extraction
                response = self.openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a surgical data extraction agent. Return ONLY raw JSON."},
                        {"role": "user", "content": f"Analyze this document and extract significant entities: {file_name}"}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                entities_raw = json.loads(response.choices[0].message.content).get('entities', [])
                
                # 3. Store in Database
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                for ent in entities_raw:
                    c.execute("""INSERT INTO migration_results 
                                (batch_id, file_name, category, value, confidence, status)
                                VALUES (?,?,?,?,?,?)""",
                             (task_id, file_name, ent.get('category', 'Unknown'), str(ent.get('value', 'Unknown')), ent.get('confidence', 0.5), EntityStatus.PENDING.value))
                
                # Update Progress
                c.execute("UPDATE migration_batches SET processed_files = processed_files + 1 WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

class ResearchAuditor:
    def __init__(self, openai_client: OpenAI, pinecone_index: Any):
        self.openai = openai_client
        self.pinecone = pinecone_index
        # Enforce proxy
        proxy_url = os.getenv("OPENAI_PROXY_URL") or "https://api.openai-proxy.com/v1"
        self.openai.base_url = proxy_url

    async def audit_paper(self, file_name: str) -> Dict[str, Any]:
        """
        Deep-dive Pre-Submission Audit.
        """
        doc_summary = ask_document("Identify core claims and methodology.", file_name, openai_client=self.openai, pinecone_index=self.pinecone)
        
        prompt = f"Audit this paper summary for novelty and rigor: {doc_summary['answer']}"
        
        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Critical Area Chair."}, {"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
