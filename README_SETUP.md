# LeaseSight – Local Setup Guide

## Prerequisites
- **Python 3.11.x** (recommended) – download from https://www.python.org/downloads/
- **Node.js 18+** – only needed if you want to run the Next.js frontend
- Git (optional)

---

## Step 1 – Create & Activate a Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

---

## Step 2 – Install Python Dependencies

```bash
pip install -r requirements.txt
```

> **GPU users (NVIDIA):** After the above command, install the matching CUDA torch:
> ```bash
> pip install torch==2.3.1+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
> ```
> CPU-only users don't need to do anything extra.

---

## Step 3 – Configure Environment Variables

Copy the example file and fill in your API keys:

```bash
cp .env.production.example .env
```

Open `.env` and set:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | From https://console.groq.com |
| `PINECONE_API_KEY` | From https://app.pinecone.io |
| `AZURE_KEY` | Azure Document Intelligence key |
| `AZURE_ENDPOINT` | Azure Document Intelligence endpoint |
| `GEMINI_API_KEY` | (Optional) Google Gemini key |

---

## Step 4 – Run the Backend API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at: http://localhost:8080

---

## Step 5 – (Optional) Run the Streamlit UI

```bash
streamlit run app.py
```

---

## Step 6 – (Optional) Run the Next.js Frontend

```bash
cd leasesight-ui
npm install
npm run dev
```

Frontend will be at: http://localhost:3000

---

## Troubleshooting

- **`sentence-transformers` model download**: The first run will automatically download the `all-mpnet-base-v2` model (~420 MB). Ensure you have an internet connection.
- **ChromaDB errors on Windows**: Run `pip install chromadb --upgrade` if you see import errors.
- **Port already in use**: Change `--port 8080` to another port like `--port 8000`.
