import os
import json
from pathlib import Path
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# Clients
# CORRECT: Passing the names of the variables defined in your .env file
# Use the NAMES of the variables in your .env, not the actual values
client_azure = DocumentAnalysisClient(
    endpoint=os.getenv("AZURE_ENDPOINT"), 
    credential=AzureKeyCredential(os.getenv("AZURE_KEY"))
)
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("leasesight-index")

def process_new_pdf(pdf_path, file_name):
    # 1. Azure Mapping (Day 1)
    with open(pdf_path, "rb") as f:
        poller = client_azure.begin_analyze_document("prebuilt-layout", f)
        result = poller.result()

    spatial_data = {"file_name": file_name, "pages": []}
    for page in result.pages:
        lines = []
        page_text = ""
        for line in page.lines:
            lines.append({
                "content": line.content,
                "bounding_box": [{"x": p.x, "y": p.y} for p in line.polygon]
            })
            page_text += line.content + " "
        
        spatial_data["pages"].append({"page_number": page.page_number, "lines": lines})

        # 2. OpenAI & Pinecone Indexing (Day 2)
        emb_res = client_openai.embeddings.create(input=page_text, model="text-embedding-3-small")
        vector = emb_res.data[0].embedding
        
        metadata = {
            "file_name": file_name,
            "page_number": page.page_number,
            "text": page_text[:2000],
            "coords": json.dumps(lines[0]['bounding_box'] if lines else [])
        }
        index.upsert(vectors=[(f"{file_name}_p{page.page_number}", vector, metadata)])

    # Save JSON map for Day 4 Visuals
    json_path = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight\data\json_maps") / f"{file_name}.json"
    with open(json_path, "w") as f:
        json.dump(spatial_data, f, indent=4)
    
    return json_path