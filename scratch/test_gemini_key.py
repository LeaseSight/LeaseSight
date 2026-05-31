import os
import requests

api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

print("1. Testing API Key Validity & Models List...")
url_models = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
resp = requests.get(url_models)

if resp.status_code == 200:
    data = resp.json()
    models = [m.get('name') for m in data.get('models', [])]
    print(f"SUCCESS: Key is active. Found {len(models)} models.")
    print("\nAvailable Gemini Models include:")
    for m in models:
        if "gemini" in m.lower():
            print(f" - {m}")
else:
    print(f"FAILED: Status {resp.status_code}\nError: {resp.text}")

print("\n--------------------------------------------------\n")
print("2. Testing Text Generation (gemini-2.5-pro-preview)...")
url_gen = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview:generateContent?key={api_key}"
payload = {
    "contents": [{"parts":[{"text": "Hello, are you working?"}]}]
}

resp2 = requests.post(url_gen, headers={"Content-Type": "application/json"}, json=payload)
if resp2.status_code == 200:
    print("SUCCESS: Generation succeeded!")
    try:
        reply = resp2.json()['candidates'][0]['content']['parts'][0]['text']
        print(f"Model Reply: {reply}")
    except Exception as e:
        print(f"Could not parse reply: {resp2.text}")
else:
    print(f"FAILED: Status {resp2.status_code}\nError: {resp2.text}")
