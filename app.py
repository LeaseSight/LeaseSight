# app.py
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import os
import sys
from pathlib import Path
import pandas as pd
import datetime

# --- IMPORT FALLBACK ---
sys.path.append(os.path.join(os.getcwd(), "scripts"))
try:
    from scripts.visual_anchor import find_coordinates
    from scripts.analytics import generate_database_relationship_graph, generate_query_heatmap, generate_query_similarity_3d
    from scripts.database_manager import commit_to_knowledge_base
    from scripts.query_engine import ask_document
    from scripts.report_generator import generate_audit_pdf
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from scripts.visual_anchor import find_coordinates
    from scripts.analytics import generate_database_relationship_graph, generate_query_heatmap, generate_query_similarity_3d
    from scripts.database_manager import commit_to_knowledge_base
    from scripts.query_engine import ask_document
    from scripts.report_generator import generate_audit_pdf

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
TEMP_DIR = BASE_DIR / "data" / "temp"
RAW_PDF_DIR.mkdir(parents=True, exist_ok=True)
JSON_MAP_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# --- API CLIENTS (cached) ---
@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@st.cache_resource
def get_pinecone_index():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    return pc.Index("leasesight-index")

st.title("LeaseSight: Dynamic Visual Auditor")

# --- PROFESSIONAL LIGHT THEME CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    .stButton>button { background-color: #9333ea; color: white; border-radius: 6px; }
    .success-box { 
        background-color: #f0fdf4; 
        border: 1px solid #bbf7d0; 
        padding: 15px; 
        border-radius: 8px; 
        color: #166534;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
defaults = {
    'audit_results': None,
    'annotations': [],
    'current_vector': None,
    'chunk_vectors': [],
    'vector_ids': [],
    'committed': False,
    'source_path': None,
    'confirm_commit': False,
    'messages': [],       # Chat history
    'pdf_page': None,     # Auto-scroll target page
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- HELPER: EXCEL LOGGER ---
def log_audit_to_excel(data_dict):
    try:
        excel_path = BASE_DIR / "audit_log.xlsx"
        if excel_path.exists():
            df = pd.read_excel(excel_path)
        else:
            df = pd.DataFrame()
        
        data_dict['Timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df = pd.concat([df, pd.DataFrame([data_dict])], ignore_index=True)
        df.to_excel(excel_path, index=False)
    except Exception as e:
        print(f"Error logging to Excel: {e}")

# --- HELPER: FETCH ARCHIVE VECTORS ---
def fetch_archive_vectors(current_doc_name, sample_size=100):
    try:
        idx = get_pinecone_index()
        current_vec = st.session_state.get('current_vector')
        if not current_vec:
            return [], []
        results = idx.query(
            vector=current_vec, top_k=sample_size,
            include_values=True, include_metadata=True,
        )
        vectors, names, seen = [], [], set()
        for match in results.get('matches', []):
            fn = match.get('metadata', {}).get('file_name', 'Unknown')
            if fn == current_doc_name or fn in seen:
                continue
            seen.add(fn)
            vectors.append(match['values'])
            names.append(fn)
        return vectors, names
    except Exception as e:
        print(f"Error fetching archive vectors: {e}")
        return [], []


# --- DYNAMIC UI RENDERER ---
def render_dynamic_audit(summary_data, selected_doc):
    if not summary_data:
        st.warning("No data extracted yet.")
        return

    st.markdown("""
    <div class="success-box">
        ✨ <b>Look what we found</b><br>
        We processed the lease document and extracted key information. Please review for accuracy.
    </div>
    """, unsafe_allow_html=True)

    # Judge Warnings
    warnings = summary_data.get('warnings', [])
    if warnings:
        for w in warnings:
            st.warning(f"⚠️ {w}")
    risk = summary_data.get('risk_score')
    if risk and int(risk) >= 7:
        st.error(f"🚨 HIGH RISK DOCUMENT — Risk Score: {risk}/10")

    # Findings
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
                st.text_input(label=label, value=value,
                              label_visibility="collapsed", key=f"input_{i}")
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
                                "height": max(ys) - min(ys)
                            }]
                            st.session_state['pdf_page'] = int(coord_data['page'])
                            st.rerun()
                        else:
                            st.toast(f"⚠️ Could not locate '{label}' in the document map.")
    if not found_any:
        st.info("No core findings discovered in the provided context.")

    # Executive Brief
    st.divider()
    st.subheader("💡 Executive Brief")
    st.info(summary_data.get('summary_paragraph', "No brief available."))

    # Commit Button
    st.divider()
    if st.session_state.get('committed'):
        st.success("✅ This document has been committed as a legal precedent.")
    else:
        st.markdown("### 📥 Commit to Knowledge Base")
        st.caption("Verify the audit above, then commit this document as a permanent legal precedent.")
        if st.button("✅ Commit to Database", key="commit_btn", type="primary"):
            st.session_state['confirm_commit'] = True
        if st.session_state.get('confirm_commit'):
            st.warning("⚠️ Are you sure? This will mark the document as a verified legal precedent.")
            cy, cn = st.columns(2)
            with cy:
                if st.button("Yes, Commit", key="confirm_yes", type="primary"):
                    with st.spinner("Committing to knowledge base..."):
                        result = commit_to_knowledge_base(
                            file_name=selected_doc,
                            source_path=st.session_state.get('source_path'),
                            vector_ids=st.session_state.get('vector_ids') or None
                        )
                        if result['success']:
                            st.session_state['committed'] = True
                            st.session_state['confirm_commit'] = False
                            st.balloons()
                            st.sidebar.success("Document added to Gold Standard archive.")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
                            st.session_state['confirm_commit'] = False
            with cn:
                if st.button("Cancel", key="confirm_no"):
                    st.session_state['confirm_commit'] = False
                    st.rerun()


# ========================================================================
# SIDEBAR
# ========================================================================
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
    st.session_state['source_path'] = str(target_path)
    st.session_state['committed'] = False
else:
    all_pdfs = sorted([f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')])
    selected_doc = st.sidebar.selectbox("Or select existing document:", all_pdfs) if all_pdfs else None
    if selected_doc:
        target_path = RAW_PDF_DIR / selected_doc
        st.session_state['source_path'] = str(target_path)
        
        json_map_path = JSON_MAP_DIR / f"{selected_doc}.json"
        if not json_map_path.exists():
            with st.sidebar.status("Indexing existing document..."):
                process_new_pdf(str(target_path), selected_doc)
                st.sidebar.success("Document Indexed!")

# Risk Score Metric
st.sidebar.divider()
excel_path = BASE_DIR / "audit_log.xlsx"
if excel_path.exists():
    with open(excel_path, "rb") as f:
        st.sidebar.download_button(
            label="⬇ Download Audit History",
            data=f,
            file_name="audit_log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if st.session_state['audit_results']:
    rs = st.session_state['audit_results'].get('risk_score')
    wl = st.session_state['audit_results'].get('warnings', [])
    if rs is not None:
        st.sidebar.metric("📊 Document Risk Score", f"{rs} / 10",
                          delta=f"{len(wl)} warning(s)", delta_color="inverse")
    else:
        st.sidebar.metric("📊 Document Risk Score", "N/A")
else:
    st.sidebar.metric("📊 Document Risk Score", "—")


# ========================================================================
# MAIN INTERFACE
# ========================================================================
col1, col2 = st.columns([1, 1])

# LEFT COLUMN: Results & Interaction
with col1:
    st.subheader("📊 Extraction Results")

    if selected_doc and st.button("Run Intelligent Audit", key="run_audit"):
        st.session_state['committed'] = False
        st.session_state['confirm_commit'] = False
        st.session_state['messages'] = []
        st.session_state['pdf_page'] = None

        with st.spinner("AI Multi-Agent pipeline running (Miner → Judge → Clerk)..."):
            results = run_full_audit(selected_doc)
            st.session_state['audit_results'] = results

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

            try:
                idx = get_pinecone_index()
                vec = st.session_state.get('current_vector')
                if vec:
                    id_results = idx.query(
                        vector=vec, top_k=50,
                        filter={"file_name": {"$eq": selected_doc}},
                        include_metadata=False,
                        include_values=True
                    )
                    st.session_state['vector_ids'] = [m['id'] for m in id_results.get('matches', [])]
                    st.session_state['chunk_vectors'] = [m['values'] for m in id_results.get('matches', []) if 'values' in m]
            except Exception:
                st.session_state['vector_ids'] = []
                st.session_state['chunk_vectors'] = []

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
                                "height": max(ys) - min(ys)
                            })
            st.session_state['annotations'] = temp_annotations

            # Log audit to excel
            findings_dict = {f.get('label'): f.get('value') for f in results.get('findings', [])}
            log_data = {
                'File_Name': selected_doc,
                'Lease_Name': findings_dict.get('Document Type', 'Unknown'),
                'Total_Rent': findings_dict.get('Monthly Rent', 'Unknown'),
                'Risk_Score': results.get('risk_score', 'N/A'),
                'Key_Terms': ', '.join([f"{k}: {v}" for k, v in findings_dict.items()][:5])
            }
            log_audit_to_excel(log_data)

    if st.session_state['audit_results']:
        render_dynamic_audit(st.session_state['audit_results'], selected_doc)
        
        st.divider()
        pdf_bytes = generate_audit_pdf(st.session_state['audit_results'], selected_doc)
        st.download_button(
            label="📄 Export Audit Report (PDF)",
            data=pdf_bytes,
            file_name=f"Audit_Report_{selected_doc}.pdf",
            mime="application/pdf",
            type="primary"
        )

# RIGHT COLUMN: PDF Preview
with col2:
    st.subheader("📄 Document Preview")
    if selected_doc:
        pdf_path = str(RAW_PDF_DIR / selected_doc)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        st.markdown("""
        <style>
        iframe { border: none !important; }
        [data-testid="stVerticalBlock"] { overflow-y: auto; max-height: 820px; }
        </style>
        """, unsafe_allow_html=True)
        
        viewer_kwargs = {
            "input": pdf_bytes,
            "width": 700,
            "height": 800,
            "annotations": st.session_state.get('annotations', []),
        }
        target_page = st.session_state.get('pdf_page')
        if target_page:
            viewer_kwargs["pages_to_render"] = [target_page]
        pdf_viewer(**viewer_kwargs)
    else:
        st.info("Upload or select a document to begin.")

# ========================================================================
# FEATURE 3: SIMILARITY ANALYTICS (DUAL GRAPHS)
# ========================================================================
with st.expander("📊 Similarity Analytics", expanded=True):
    if st.session_state.get('current_vector') and selected_doc:
        tab_internal, tab_global = st.tabs(["🎯 Query Heatmap", "🌐 Database Context"])
        
        with tab_internal:
            chunk_vecs = st.session_state.get('chunk_vectors', [])
            if chunk_vecs:
                query_fig = generate_query_heatmap(st.session_state['current_vector'], chunk_vecs)
                if query_fig:
                    st.plotly_chart(query_fig, use_container_width=True)
                else:
                    st.info("Could not generate heatmap.")
            else:
                st.info("No chunk vectors available for heatmap.")
                
        with tab_global:
            with st.spinner("Building 3D similarity network..."):
                archive_vectors, archive_names = fetch_archive_vectors(selected_doc)
                global_fig = generate_database_relationship_graph(
                    current_doc_vector=st.session_state['current_vector'],
                    archive_vectors=archive_vectors,
                    doc_names=archive_names,
                    is_committed=st.session_state.get('committed', False)
                )
                if global_fig:
                    st.plotly_chart(global_fig, use_container_width=True)
                else:
                    st.info("Not enough documents in archive to generate a map.")
    else:
        st.info("Run an audit first to generate the similarity maps.")

# ========================================================================
# FEATURE 6: SCOPED DOCUMENT CHAT
# ========================================================================
st.divider()
st.subheader("💬 Chat with Document")

if not selected_doc:
    st.info("Upload or select a document to start chatting.")
else:
    # Render chat history (persistent in session_state)
    for idx, msg in enumerate(st.session_state['messages']):
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
            # Show Locate button for assistant messages that have source_text
            if msg['role'] == 'assistant' and msg.get('source_text'):
                if st.button("📍 Locate in Document", key=f"chat_locate_{idx}"):
                    coord_data = find_coordinates(selected_doc, msg['source_text'][:80])
                    if coord_data:
                        bbox = coord_data['bounding_box']
                        xs = [p['x'] * DPI for p in bbox]
                        ys = [p['y'] * DPI for p in bbox]
                        st.session_state['annotations'] = [{
                            "page": int(coord_data['page']),
                            "x": min(xs), "y": min(ys),
                            "width": max(xs) - min(xs),
                            "height": max(ys) - min(ys)
                        }]
                        st.session_state['pdf_page'] = int(coord_data['page'])
                        st.rerun()
                    elif msg.get('page'):
                        # Fallback: at least jump to the page
                        st.session_state['pdf_page'] = msg['page']
                        st.rerun()
                    else:
                        st.toast("⚠️ Could not locate the source in the document map.")

    # Chat input
    user_query = st.chat_input("Ask a question about this document...", key="chat_input")

    if user_query:
        # Add user message
        st.session_state['messages'].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Get scoped answer
        with st.chat_message("assistant"):
            with st.spinner("Searching document..."):
                result = ask_document(user_query, selected_doc)
                answer = result['answer']
                source_text = result.get('source_text')
                page = result.get('page')

                st.markdown(answer)

                # Store assistant message with source metadata for Locate button
                st.session_state['messages'].append({
                    "role": "assistant",
                    "content": answer,
                    "source_text": source_text,
                    "page": page
                })

                # Auto-scroll: if we have source text, highlight + jump
                if source_text:
                    coord_data = find_coordinates(selected_doc, source_text[:80])
                    if coord_data:
                        bbox = coord_data['bounding_box']
                        xs = [p['x'] * DPI for p in bbox]
                        ys = [p['y'] * DPI for p in bbox]
                        st.session_state['annotations'] = [{
                            "page": int(coord_data['page']),
                            "x": min(xs), "y": min(ys),
                            "width": max(xs) - min(xs),
                            "height": max(ys) - min(ys)
                        }]
                        st.session_state['pdf_page'] = int(coord_data['page'])
                    elif page:
                        st.session_state['pdf_page'] = page

                if source_text:
                    st.caption(f"📄 Source: Page {page or '?'}")

    # Feature 8: 3D Query Similarity Map
    if st.session_state['messages'] and st.session_state['messages'][-1]['role'] == 'assistant':
        if st.button("🔭 Map Query Similarity"):
            last_user_msg = next((m['content'] for m in reversed(st.session_state['messages']) if m['role'] == 'user'), None)
            if last_user_msg and st.session_state.get('chunk_vectors'):
                with st.spinner("Generating 3D Correlation Map..."):
                    try:
                        oai = get_openai_client()
                        emb_res = oai.embeddings.create(input=[last_user_msg], model="text-embedding-3-small")
                        query_vec = emb_res.data[0].embedding
                        fig = generate_query_similarity_3d(query_vec, st.session_state['chunk_vectors'])
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Not enough data to plot similarity map.")
                    except Exception as e:
                        st.error(f"Error generating similarity map: {e}")