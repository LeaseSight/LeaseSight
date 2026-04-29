# app.py
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import os
import sys
from pathlib import Path

# --- IMPORT FALLBACK ---
# Use sys.path.append fallback to solve ImportError when running outside project root
sys.path.append(os.path.join(os.getcwd(), "scripts"))
try:
    from scripts.visual_anchor import find_coordinates
    from scripts.analytics import generate_3d_network_graph
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from scripts.visual_anchor import find_coordinates
    from scripts.analytics import generate_3d_network_graph

# Custom Script Imports
from scripts.processor import process_new_pdf
from scripts.full_audit import run_full_audit

# Pinecone + OpenAI (needed for archive vector fetching)
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

# --- DPI CONSTANT ---
DPI = 72

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="LeaseSight AI Auditor")

# --- PATH SETUP ---
BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
JSON_MAP_DIR.mkdir(parents=True, exist_ok=True)

# --- API CLIENTS (cached for performance) ---
@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@st.cache_resource
def get_pinecone_index():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return pc.Index("leasesight-index")

st.title("LeaseSight: Dynamic Visual Auditor")

# Initialize Session States
if 'audit_results' not in st.session_state:
    st.session_state['audit_results'] = None
if 'annotations' not in st.session_state:
    st.session_state['annotations'] = []
if 'current_vector' not in st.session_state:
    st.session_state['current_vector'] = None


# --- HELPER: FETCH ARCHIVE VECTORS FOR 3D GRAPH ---
def fetch_archive_vectors(current_doc_name, sample_size=100):
    """Fetches a representative sample of archive vectors from Pinecone."""
    try:
        idx = get_pinecone_index()
        current_vec = st.session_state.get('current_vector')
        if not current_vec:
            return [], []

        results = idx.query(
            vector=current_vec, top_k=sample_size,
            include_values=True, include_metadata=True,
        )

        vectors, names, seen_files = [], [], set()
        for match in results.get('matches', []):
            file_name = match.get('metadata', {}).get('file_name', 'Unknown')
            if file_name == current_doc_name:
                continue
            if file_name not in seen_files:
                seen_files.add(file_name)
                vectors.append(match['values'])
                names.append(file_name)
        return vectors, names
    except Exception as e:
        print(f"Error fetching archive vectors: {e}")
        return [], []


# --- DYNAMIC UI RENDERER (Updated for Multi-Agent output) ---
def render_dynamic_audit(summary_data, selected_doc):
    """
    Renders findings, Judge warnings, Executive Brief, and Locate buttons.
    Handles the new risk_score and warnings keys gracefully.
    """
    if not summary_data:
        st.warning("No data extracted yet.")
        return

    # --- JUDGE WARNINGS (Alert System) ---
    warnings = summary_data.get('warnings', [])
    if warnings:
        for w in warnings:
            st.warning(f"⚠️ {w}")
    
    risk = summary_data.get('risk_score')
    if risk and int(risk) >= 7:
        st.error(f"🚨 HIGH RISK DOCUMENT — Risk Score: {risk}/10")

    # 1. Dynamic Findings Loop
    st.markdown("### 📋 Key Findings")
    findings = summary_data.get('findings', [])

    found_any = False
    for i, finding in enumerate(findings):
        label = finding.get('label', 'Unknown Field')
        value = finding.get('value', 'Not Found')
        evidence = finding.get('evidence_quote', 'Not Found')

        if value and str(value).lower() != "not found":
            found_any = True
            col_label, col_input, col_btn = st.columns([1, 2, 0.5])
            with col_label:
                st.markdown(f"**{label}**")
            with col_input:
                st.text_input(
                    label=label, value=value,
                    label_visibility="collapsed", key=f"input_{i}"
                )
            with col_btn:
                if evidence and str(evidence).lower() != "not found":
                    if st.button("🔍", key=f"locate_{i}", help=f"Locate: {label}"):
                        coord_data = find_coordinates(selected_doc, str(evidence))
                        if coord_data:
                            bbox = coord_data['bounding_box']
                            xs = [p['x'] * DPI for p in bbox]
                            ys = [p['y'] * DPI for p in bbox]
                            st.session_state['annotations'] = [{
                                "page": int(coord_data['page']),
                                "x": min(xs), "y": min(ys),
                                "width": max(xs) - min(xs),
                                "height": max(ys) - min(ys),
                                "color": "red", "thickness": 2
                            }]
                            st.rerun()
                        else:
                            st.toast(f"⚠️ Could not locate '{label}' in the document map.")

    if not found_any:
        st.info("No core findings discovered in the provided context.")

    # 2. Executive Brief
    st.divider()
    st.subheader("💡 Executive Brief")
    brief = summary_data.get('summary_paragraph', "No brief available.")
    st.info(brief)


# --- SIDEBAR: UPLOAD & SELECTION ---
uploaded_file = st.sidebar.file_uploader("Upload a new Contract (PDF)", type="pdf")

if uploaded_file:
    target_path = RAW_PDF_DIR / uploaded_file.name
    if not target_path.exists():
        with st.status("Processing new document..."):
            with open(target_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            process_new_pdf(str(target_path), uploaded_file.name)
            st.success("Document Indexed!")
    selected_doc = uploaded_file.name
else:
    all_pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    selected_doc = st.sidebar.selectbox("Or select existing document:", all_pdfs) if all_pdfs else None

# --- SIDEBAR: RISK SCORE METRIC ---
# Display the Judge's risk score prominently in the sidebar
st.sidebar.divider()
if st.session_state['audit_results']:
    risk_score = st.session_state['audit_results'].get('risk_score', None)
    warnings_list = st.session_state['audit_results'].get('warnings', [])
    if risk_score is not None:
        delta_color = "inverse"  # Higher = worse, so red for high values
        st.sidebar.metric(
            label="📊 Document Risk Score",
            value=f"{risk_score} / 10",
            delta=f"{len(warnings_list)} warning(s)",
            delta_color=delta_color
        )
    else:
        st.sidebar.metric(label="📊 Document Risk Score", value="N/A")
else:
    st.sidebar.metric(label="📊 Document Risk Score", value="—")

# --- MAIN INTERFACE ---
col1, col2 = st.columns([1, 1])

# LEFT COLUMN: Results & Interaction
with col1:
    st.subheader("📊 Extraction Results")

    if selected_doc and st.button("Run Intelligent Audit", key="run_audit"):
        with st.spinner("AI Multi-Agent pipeline running (Miner → Judge → Clerk)..."):
            # 1. Trigger Multi-Agent extraction
            results = run_full_audit(selected_doc)
            st.session_state['audit_results'] = results

            # 2. Generate current document's embedding for the 3D graph
            try:
                oai = get_openai_client()
                emb_res = oai.embeddings.create(
                    input=["Parties involved, rent details, address, and legal obligations"],
                    model="text-embedding-3-small"
                )
                st.session_state['current_vector'] = emb_res.data[0].embedding
            except Exception as e:
                print(f"Error generating current vector: {e}")
                st.session_state['current_vector'] = None

            # 3. Generate Visual Anchors
            temp_annotations = []
            if results and 'findings' in results:
                for finding in results['findings']:
                    evidence = finding.get('evidence_quote', '')
                    if evidence and str(evidence).lower() != "not found":
                        coord_data = find_coordinates(selected_doc, str(evidence))
                        if coord_data:
                            bbox = coord_data['bounding_box']
                            xs = [p['x'] * DPI for p in bbox]
                            ys = [p['y'] * DPI for p in bbox]
                            temp_annotations.append({
                                "page": int(coord_data['page']),
                                "x": min(xs), "y": min(ys),
                                "width": max(xs) - min(xs),
                                "height": max(ys) - min(ys),
                                "color": "red", "thickness": 2
                            })
            st.session_state['annotations'] = temp_annotations

    if st.session_state['audit_results']:
        render_dynamic_audit(st.session_state['audit_results'], selected_doc)

# RIGHT COLUMN: PDF Preview
with col2:
    st.subheader("📄 Document Preview")
    if selected_doc:
        pdf_path = str(RAW_PDF_DIR / selected_doc)
        pdf_viewer(
            pdf_path,
            annotations=st.session_state.get('annotations', [])
        )
    else:
        st.info("Upload or select a document to begin.")

# --- FEATURE 3: 3D SIMILARITY NETWORK GRAPH ---
with st.expander("📊 View Document Relationship Map", expanded=False):
    if st.session_state.get('current_vector') and selected_doc:
        with st.spinner("Building 3D similarity network..."):
            archive_vectors, archive_names = fetch_archive_vectors(selected_doc)
            if len(archive_vectors) >= 3:
                fig = generate_3d_network_graph(
                    new_vector=st.session_state['current_vector'],
                    database_vectors=archive_vectors,
                    doc_names=archive_names,
                )
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Not enough documents in archive to generate a map.")
            else:
                st.info("Not enough documents in archive to generate a map.")
    else:
        st.info("Run an audit first to generate the document similarity map.")