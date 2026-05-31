import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_ENDPOINT")
key = os.getenv("AZURE_KEY")
pdf_path = r"c:\Users\zain\OneDrive\Desktop\LeaseSight\data\raw_pdfs\Land_Lease_Agreement_Milwaukee (1).pdf"

print(f"Testing Azure connection...")
print(f"Endpoint: {endpoint}")
print(f"Key length: {len(key) if key else 0}")
print(f"File exists: {os.path.exists(pdf_path)}")

try:
    client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", f)
        result = poller.result(timeout=30)
    print("SUCCESS! Azure layout extraction succeeded.")
    print(f"Number of pages: {len(result.pages)}")
except Exception as e:
    print(f"FAILURE! Azure test failed: {e}")
