import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Path resolution
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

load_dotenv()

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from pinecone import Pinecone
from scripts.processor import process_new_pdf

pdf_path = os.path.join(BASE_DIR, "data", "raw_pdfs", "Land_Lease_Agreement_Milwaukee (1).pdf")
file_name = "Land_Lease_Agreement_Milwaukee (1).pdf"
user_id = "academic_baseline"

print("--- STARTING E2E INDEXING PIPELINE TEST ---")
print(f"PDF Path: {pdf_path}")
print(f"File exists: {os.path.exists(pdf_path)}")

try:
    print("Initializing Pinecone...")
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index("leasesight-index")
    print("Pinecone index initialized.")
except Exception as e:
    print(f"Pinecone init failed: {e}")
    index = None

try:
    print("Initializing Azure client...")
    azure_client = DocumentAnalysisClient(
        endpoint=os.getenv("AZURE_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_KEY")),
    )
    print("Azure client initialized.")
except Exception as e:
    print(f"Azure client init failed: {e}")
    azure_client = None

try:
    print("Running process_new_pdf...")
    json_path = process_new_pdf(
        pdf_path=pdf_path,
        file_name=file_name,
        pinecone_index=index,
        azure_client=azure_client,
        user_id=user_id
    )
    print(f"SUCCESS! process_new_pdf completed. JSON map written to: {json_path}")
except Exception as e:
    import traceback
    print(f"FAILURE! process_new_pdf failed: {e}")
    traceback.print_exc()
