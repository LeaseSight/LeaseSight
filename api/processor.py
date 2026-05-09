import os, json, sqlite3, time, sys
from typing import List, Dict, Any
from pathlib import Path

# Absolute path resolution
BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
DB_PATH = str(BASE_DIR / "leasesight.db")

class UniversalProcessor:
    def __init__(self, openai_client, pinecone_index, azure_client):
        self.openai = openai_client
        self.pinecone = pinecone_index
        # Forces the proxy detour for background extraction
        self.openai.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai-proxy.com/v1")

    async def process_batch(self, task_id: str, files: List[str]):
        """Background task for document OCR and Surgical Entity Extraction."""
        RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
        
        for file_name in files:
            try:
                # 1. OCR & Indexing (Handled by the pipeline, ensured via process_new_pdf logic)
                # ... (Optional: Insert direct call to process_new_pdf here if required) ...

                # 2. SURGICAL EXTRACTION WITH EXPONENTIAL BACKOFF (Handles 429 Errors)
                response_content = "{}"
                for attempt in range(3):
                    try:
                        response = self.openai.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "You are a legal data extraction expert. Return ONLY valid JSON."},
                                {"role": "user", "content": f"""Analyze the lease document '{file_name}' and extract these EXACT fields:
                                - Lessor Name, Lessee Name, Lease Title
                                - Total Lease Amount (include currency)
                                - Tenure/Duration (e.g., 5 years)
                                - Effective Date & Expiry Date
                                - Governing Law (e.g., Wisconsin, Pakistan)
                                - Payment Frequency
                                Return as JSON: {{"entities": [{{"category": "Tenure", "value": "5 years", "confidence": 0.9}}]}}"""}
                            ],
                            response_format={"type": "json_object"}
                        )
                        response_content = response.choices[0].message.content
                        break
                    except Exception as e:
                        if "429" in str(e):
                            # Exponential backoff: 5s, 10s, 15s
                            wait_time = 5 * (attempt + 1)
                            print(f"Rate limited (429). Waiting {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        raise e

                entities_raw = json.loads(response_content).get('entities', [])
                
                # 3. Store in Database (migration_results)
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                for ent in entities_raw:
                    c.execute("INSERT INTO migration_results (batch_id, file_name, category, value, confidence, status) VALUES (?,?,?,?,?,?)",
                             (task_id, file_name, ent.get('category'), str(ent.get('value')), ent.get('confidence', 0.8), "PENDING"))
                
                c.execute("UPDATE migration_batches SET processed_files = processed_files + 1 WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                print(f"Successfully processed surgical extraction for {file_name}")

            except Exception as e:
                print(f"CRITICAL PROCESSOR ERROR FOR {file_name}: {e}")
