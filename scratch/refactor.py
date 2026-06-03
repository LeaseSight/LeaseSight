import os
import shutil
import re

BASE_DIR = r"C:\Users\zain\OneDrive\Desktop\LeaseSight"

# Define directories
dirs_to_create = [
    os.path.join(BASE_DIR, "api", "core"),
    os.path.join(BASE_DIR, "api", "services"),
    os.path.join(BASE_DIR, "api", "database"),
]

for d in dirs_to_create:
    os.makedirs(d, exist_ok=True)

def safe_move(src, dst):
    if os.path.exists(src):
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
        print(f"Moved {src} -> {dst}")
    else:
        print(f"Warning: {src} does not exist.")

# 1. Move app/core/* to api/core/
safe_move(os.path.join(BASE_DIR, "app", "core", "evaluator.py"), os.path.join(BASE_DIR, "api", "core", "evaluator.py"))
safe_move(os.path.join(BASE_DIR, "app", "core", "rag_engine.py"), os.path.join(BASE_DIR, "api", "core", "rag_engine.py"))
safe_move(os.path.join(BASE_DIR, "app", "core", "__init__.py"), os.path.join(BASE_DIR, "api", "core", "__init__.py"))

# 2. Move database scripts to api/database/
db_scripts = ["database_manager.py", "index_to_pinecone.py", "recreate_pinecone_index.py", "reindex_pinecone.py"]
for f in db_scripts:
    safe_move(os.path.join(BASE_DIR, "scripts", f), os.path.join(BASE_DIR, "api", "database", f))

# 3. Move services scripts to api/services/
svc_scripts = ["full_audit.py", "query_engine.py", "groq_client.py", "gemini_client.py", "analytics.py", "report_generator.py", "visual_anchor.py", "extract_spatial_data.py", "audit_files.py"]
for f in svc_scripts:
    safe_move(os.path.join(BASE_DIR, "scripts", f), os.path.join(BASE_DIR, "api", "services", f))

# 4. Rename processor files
safe_move(os.path.join(BASE_DIR, "scripts", "processor.py"), os.path.join(BASE_DIR, "api", "services", "document_processor.py"))
safe_move(os.path.join(BASE_DIR, "api", "processor.py"), os.path.join(BASE_DIR, "api", "services", "universal_processor.py"))

# 5. Move app.py
safe_move(os.path.join(BASE_DIR, "app.py"), os.path.join(BASE_DIR, "api", "legacy_streamlit_app.py"))

# Refactor logic
def replace_in_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Replace absolute imports
    content = content.replace("from app.core.", "from api.core.")
    content = content.replace("import app.core.", "import api.core.")
    
    for db_f in db_scripts:
        mod_name = db_f.replace(".py", "")
        content = content.replace(f"from scripts.{mod_name}", f"from api.database.{mod_name}")
        content = content.replace(f"import scripts.{mod_name}", f"import api.database.{mod_name}")

    for svc_f in svc_scripts:
        mod_name = svc_f.replace(".py", "")
        content = content.replace(f"from scripts.{mod_name}", f"from api.services.{mod_name}")
        content = content.replace(f"import scripts.{mod_name}", f"import api.services.{mod_name}")

    # Processors
    content = content.replace("from scripts.processor ", "from api.services.document_processor ")
    content = content.replace("import scripts.processor", "import api.services.document_processor")
    content = content.replace("from api.processor ", "from api.services.universal_processor ")
    content = content.replace("import api.processor", "import api.services.universal_processor")

    # Catch-all for any remaining scripts
    content = content.replace("from scripts ", "from api.services ")
    content = content.replace("import scripts", "import api.services")

    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Refactored imports in {filepath}")

# Walk through all python files in the repo (except venv and UI)
for root, dirs, files in os.walk(BASE_DIR):
    if "venv" in root or "leasesight-ui" in root or ".git" in root or "__pycache__" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            replace_in_file(os.path.join(root, file))

print("Refactoring complete.")
