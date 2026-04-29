import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
import os
import shutil
from pathlib import Path
from scripts.processor import process_new_pdf
from scripts.full_audit import run_full_audit
from scripts.visual_anchor import find_coordinates

st.set_page_config(layout="wide", page_title="LeaseSight AI")

# Absolute Paths
BASE_DIR = Path(r"C:\Users\zain\OneDrive\Desktop\LeaseSight")
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
JSON_MAP_DIR = BASE_DIR / "data" / "json_maps"

st.title("LeaseSight: Dynamic Visual Auditor")

# --- SIDEBAR: UPLOAD ---
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
    all_pdfs = [f for f in os.listdir(RAW_PDF_DIR) if f.lower().endswith('.pdf')]
    selected_doc = st.sidebar.selectbox("Or select existing:", all_pdfs)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 Inferred Data Points")
    
    if st.button("Run Extraction"):
        with st.spinner("Processing Lease Details..."):
            st.session_state['audit_results'] = run_full_audit(selected_doc)

    if 'audit_results' in st.session_state:
        data = st.session_state['audit_results']
        
        # 1. Basic Info Section
        st.markdown("### General")
        st.text_input("Lease Name", value=data.get("Lease_Info", {}).get("Lease_Name", ""))
        st.caption("Inferred from document")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("Asset Type", value=data.get("Lease_Info", {}).get("Asset_Type", ""))
        with col_b:
            st.text_input("Local Currency", value=data.get("Lease_Info", {}).get("Currency", ""))

        # 2. Dates Section
        st.markdown("### Timeline")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("Start Date", value=data.get("Dates_and_Terms", {}).get("Start_Date", ""))
        with c2:
            st.text_input("End Date", value=data.get("Dates_and_Terms", {}).get("End_Date", ""))
        with c3:
            st.text_input("Term (Months)", value=data.get("Dates_and_Terms", {}).get("Term_Months", ""))

        # 3. Specific Asset Details (The 'Toyota' example from your image)
        st.info("💡 Look what else we found")
        st.checkbox(f"Manufacturer: {data.get('Asset_Details', {}).get('Manufacturer', 'N/A')}", value=True)
        st.text_input("Registration No", value=data.get('Asset_Details', {}).get('Registration_No', ""))
        
        # Logic to add annotations for marking (Day 4 logic)
        # We flatten the JSON to look for coordinates
        all_values = []
        for section in data.values():
            if isinstance(section, dict):
                all_values.extend(section.values())
        
        for val in all_values:
            if val and val != "Not found":
                coord_data = find_coordinates(selected_doc, str(val))
                if coord_data:
                    bbox = coord_data['bounding_box']
                    xs = [p['x'] * 72 for p in bbox]
                    ys = [p['y'] * 72 for p in bbox]
                    annotations.append({
                        "page": coord_data['page'],
                        "x": min(xs), "y": min(ys),
                        "width": max(xs) - min(xs), "height": max(ys) - min(ys),
                        "color": "rgba(255, 0, 0, 0.3)"
                    })