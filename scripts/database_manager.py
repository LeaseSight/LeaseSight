# scripts/database_manager.py
# The Persistence Layer — Commit verified documents to the knowledge base

import os
import sys
import shutil
import time
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone

# --- IMPORT FALLBACK ---
sys.path.append(os.path.join(os.getcwd(), "scripts"))

load_dotenv()

BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
TEMP_DIR = BASE_DIR / "data" / "temp"
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
ARCHIVE_DIR = BASE_DIR / "data" / "archive"

# Ensure directories exist
TEMP_DIR.mkdir(parents=True, exist_ok=True)
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def _get_pinecone_index():
    """Initialize Pinecone index."""
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return pc.Index("leasesight-index")


def commit_to_knowledge_base(file_name, source_path=None, dest_folder=None, vector_ids=None):
    """
    Commits a verified document to the permanent knowledge base.

    Steps:
        1. Physically relocate the PDF from temp → raw_pdfs (if source provided).
        2. Update Pinecone vector metadata to status='verified', category='precedent'.

    Args:
        file_name (str): The document filename (e.g., "contract.pdf").
        source_path (str|Path|None): Source file path. If None, assumes already in raw_pdfs.
        dest_folder (str|Path|None): Destination folder. Defaults to raw_pdfs.
        vector_ids (list[str]|None): List of Pinecone vector IDs to update.
            If None, auto-generates IDs based on file_name pattern.

    Returns:
        dict: {"success": bool, "message": str, "moved": bool, "vectors_updated": int}
    """
    result = {"success": False, "message": "", "moved": False, "vectors_updated": 0}

    # --- STEP 1: PHYSICAL FILE MOVE ---
    if source_path:
        source = Path(source_path)
        dest = Path(dest_folder) if dest_folder else ARCHIVE_DIR
        dest.mkdir(parents=True, exist_ok=True)
        dest_path = dest / file_name

        if source.exists() and source != dest_path:
            try:
                # Close-safety: retry with small delay for Windows "File in Use" errors
                for attempt in range(3):
                    try:
                        shutil.move(str(source), str(dest_path))
                        result["moved"] = True
                        print(f"[COMMIT] Moved: {source} → {dest_path}")
                        break
                    except PermissionError:
                        if attempt < 2:
                            print(f"[COMMIT] File in use, retrying in 1s... (attempt {attempt + 1})")
                            time.sleep(1)
                        else:
                            raise
            except PermissionError:
                result["message"] = f"Permission denied: '{file_name}' is in use. Close the viewer and retry."
                print(f"[COMMIT] ERROR: {result['message']}")
                return result
            except FileNotFoundError:
                result["message"] = f"Source file not found: {source}"
                print(f"[COMMIT] ERROR: {result['message']}")
                return result
            except Exception as e:
                result["message"] = f"File move error: {e}"
                print(f"[COMMIT] ERROR: {result['message']}")
                return result

    # --- STEP 2: UPDATE PINECONE METADATA ---
    try:
        idx = _get_pinecone_index()

        # Auto-generate vector IDs if not provided
        # Vectors are stored as "{file_name}_p{page_number}"
        if not vector_ids:
            # Query Pinecone to discover all vectors for this file
            # We use a dummy vector query with metadata filter
            from openai import OpenAI
            oai = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_PROXY_URL") or "https://api.openai.com/v1"
            )
            emb = oai.embeddings.create(
                input=["contract document"],
                model="text-embedding-3-small"
            )
            query_results = idx.query(
                vector=emb.data[0].embedding,
                top_k=50,
                filter={"file_name": {"$eq": file_name}},
                include_metadata=False
            )
            vector_ids = [m['id'] for m in query_results.get('matches', [])]

        updated = 0
        for vid in vector_ids:
            try:
                idx.update(
                    id=vid,
                    set_metadata={
                        "status": "verified",
                        "category": "precedent"
                    }
                )
                updated += 1
            except Exception as e:
                print(f"[COMMIT] Vector update failed for '{vid}': {e}")

        result["vectors_updated"] = updated
        print(f"[COMMIT] Updated {updated}/{len(vector_ids)} vectors to 'verified'.")

    except Exception as e:
        result["message"] = f"Pinecone update error: {e}"
        print(f"[COMMIT] ERROR: {result['message']}")
        # Even if Pinecone fails, the file move may have succeeded
        if result["moved"]:
            result["success"] = True
            result["message"] += " (File was moved successfully.)"
        return result

    result["success"] = True
    result["message"] = f"✅ '{file_name}' committed as legal precedent. {result['vectors_updated']} vectors verified."
    return result
