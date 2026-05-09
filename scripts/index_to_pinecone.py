import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

# 1. SETUP
load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_PROXY_URL") or "https://api.openai.com/v1"
)
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Connect to your newly created index
index = pc.Index("leasesight-index")

BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"

def upload_to_brain():
    json_files = list(JSON_MAP_DIR.glob("*.json"))
    print(f"Loading {len(json_files)} contract maps into the vector database...")

    for json_file in json_files:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        file_name = data['file_name']
        print(f"Indexing: {file_name}")

        for page in data['pages']:
            # Group all text on the page into one searchable chunk
            page_text = " ".join([line['content'] for line in page['lines']])
            
            if not page_text.strip():
                continue

            # 2. THE TRANSLATION (Embedding)
            # This converts legal sentences into a 1536-dimensional coordinate
            try:
                emb_res = client.embeddings.create(
                    input=page_text, 
                    model="text-embedding-3-small"
                )
                vector = emb_res.data[0].embedding

                # 3. THE BACKPACK (Metadata)
                # We save the coordinates so we can draw the red box later
                metadata = {
                    "file_name": file_name,
                    "page_number": page['page_number'],
                    "text": page_text[:2000], # Pinecone metadata limit safety
                    "coords": json.dumps(page['lines'][0]['bounding_box']) 
                }

                # 4. THE STORAGE (Upsert)
                unique_id = f"{file_name}_p{page['page_number']}"
                index.upsert(vectors=[(unique_id, vector, metadata)])
                
                # Small delay to respect OpenAI Tier 1 limits
                time.sleep(0.05) 

            except Exception as e:
                print(f"Error on {file_name} page {page['page_number']}: {e}")

    print("\n--- DAY 2 SUCCESS: 510 CONTRACTS ARE SEARCHABLE ---")

if __name__ == "__main__":
    upload_to_brain()