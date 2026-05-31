# api/processor.py
# Background batch processor: Gemini-powered entity extraction.
# Migrated from OpenAI (gpt-4o) → Gemini (gemini-2.5-pro-preview).

import os
import json
import sqlite3
import sys
from typing import List
from pathlib import Path

from scripts.gemini_client import GeminiChatClient

# Absolute path resolution
BASE_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
DB_PATH  = str(BASE_DIR / "leasesight.db")

_EXTRACTION_SYSTEM = (
    "You are a legal data extraction expert. "
    "Return ONLY valid JSON with no prose outside the JSON structure."
)

_EXTRACTION_USER_TMPL = """Analyze the lease document '{file_name}' and extract these EXACT fields:
- Lessor Name, Lessee Name, Lease Title
- Total Lease Amount (include currency)
- Tenure/Duration (e.g., 5 years)
- Effective Date & Expiry Date
- Governing Law (e.g., Wisconsin, Pakistan)
- Payment Frequency
Return as JSON: {{"entities": [{{"category": "Tenure", "value": "5 years", "confidence": 0.9}}]}}"""


class UniversalProcessor:
    def __init__(self, gemini_client: GeminiChatClient, pinecone_index, azure_client,
                 # Legacy keyword kept for backwards compatibility; ignored
                 openai_client=None):
        self.gemini   = gemini_client
        self.pinecone = pinecone_index

    async def process_batch(self, task_id: str, files: List[str], user_id: str = None):
        """Background task for Surgical Entity Extraction via Gemini."""
        for file_name in files:
            try:
                result = self.gemini.complete_json(
                    system_prompt=_EXTRACTION_SYSTEM,
                    user_content=_EXTRACTION_USER_TMPL.format(file_name=file_name),
                    agent_name="ENTITY_EXTRACTOR",
                )
                entities_raw = result.get("entities", [])

                conn = sqlite3.connect(DB_PATH)
                c    = conn.cursor()
                for ent in entities_raw:
                    c.execute(
                        "INSERT INTO migration_results "
                        "(batch_id, file_name, category, value, confidence, status) "
                        "VALUES (?,?,?,?,?,?)",
                        (
                            task_id,
                            file_name,
                            ent.get("category"),
                            str(ent.get("value")),
                            ent.get("confidence", 0.8),
                            "PENDING",
                        ),
                    )
                c.execute(
                    "UPDATE migration_batches SET processed_files = processed_files + 1 WHERE id = ?",
                    (task_id,),
                )
                conn.commit()
                conn.close()
                print(f"[PROCESSOR] Surgical extraction complete for {file_name}")

            except Exception as e:
                print(f"[PROCESSOR] CRITICAL ERROR for {file_name}: {e}")
