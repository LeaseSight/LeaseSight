import time
import requests
import os

url = "http://localhost:8080/api/upload"
pdf_path = "scratch/pipeline_upload_test.pdf"

# Create a small dummy PDF if it doesn't exist
if not os.path.exists(pdf_path):
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n%Dummy PDF for testing the async BackgroundTasks upload route\n")

print(f"--- Initiating Upload Test to {url} ---")
start_time = time.time()

with open(pdf_path, "rb") as f:
    files = {"file": ("test_upload.pdf", f, "application/pdf")}
    headers = {"X-User-Id": "test_agent_123"}
    resp = requests.post(url, files=files, headers=headers)

end_time = time.time()

print(f"\n[HTTP {resp.status_code}]")
try:
    import json
    print(json.dumps(resp.json(), indent=2))
except:
    print(resp.text)

print(f"\nTotal Upload Latency: {end_time - start_time:.4f} seconds")

if (end_time - start_time) < 1.0:
    print("VERDICT: SUCCESS! The route is instantly asynchronous.")
else:
    print("VERDICT: FAIL! The route took too long and is likely still blocking.")
