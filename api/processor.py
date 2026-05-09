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
        # Enforce proxy URL
        self.openai.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai-proxy.com/v1")

    async def process_batch(self, task_id: str, files: List[str]):
        """Background task for document OCR and Targeted Entity Extraction."""
        for file_name in files:
            try:
                # 1. OCR & Indexing Placeholder (Ensure scripts/process_new_pdf.py is called)
                # ... (Background indexing logic here) ...

                # 2. SURGICAL EXTRACTION WITH RETRY LOGIC
                response_content = "{}"
                for attempt in range(3):
                    try:
                        response = self.openai.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "You are a legal data extraction expert. Return ONLY valid JSON."},
                                {"role": "user", "content": f"""Analyze the document '{file_name}' and extract:
                                1. Lessor Name
                                2. Lessee Name
                                3. Total Amount (with Currency)
                                4. Tenure/Duration
                                5. Effective Date
                                6. Expiry Date
                                7. Governing Law
                                8. Payment Terms
                                Return as JSON: {{"entities": [{{"category": "CategoryName", "value": "ExtractedValue", "confidence": 0.9}}]}}"""}
                            ],
                            response_format={"type": "json_object"}
                        )
                        response_content = response.choices[0].message.content
                        break
                    except Exception as e:
                        if "429" in str(e):
                            time.sleep(5)
                            continue
                        raise e

                entities_raw = json.loads(response_content).get('entities', [])
                
                # 3. Store in Database
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                for ent in entities_raw:
                    c.execute("INSERT INTO migration_results (batch_id, file_name, category, value, confidence, status) VALUES (?,?,?,?,?,?)",
                             (task_id, file_name, ent.get('category'), str(ent.get('value')), ent.get('confidence', 0.8), "PENDING"))
                
                c.execute("UPDATE migration_batches SET processed_files = processed_files + 1 WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                print(f"Successfully processed {file_name} for batch {task_id}")

            except Exception as e:
                print(f"CRITICAL PROCESSOR ERROR FOR {file_name}: {e}")
