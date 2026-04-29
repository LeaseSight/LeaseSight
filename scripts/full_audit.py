# scripts/full_audit.py

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

# Load environment variables (API Keys)
load_dotenv()

# --- THE BRAIN: UNIVERSAL EXTRACTION PROMPT ---
# Now updated to support Visual Grounding (Evidence Quotes)
UNIVERSAL_EXTRACTION_PROMPT = """
You are a Senior Legal Auditor. Provide an exhaustive 'Intelligent Summary'.
Extract up to 12 critical data points from the provided contract snippets.

Rules:
1. Return ONLY a JSON object with two keys:
   - 'findings': A list of objects containing 'label', 'value', and 'evidence_quote'.
   - 'summary_paragraph': A concise 3-sentence executive summary of the document.
2. Each 'findings' object MUST have:
   - 'label': The specific field name (e.g., "Monthly Rent", "Lessor").
   - 'value': The actual data point found (e.g., "$2,500").
   - 'evidence_quote': THE EXACT SHORT PHRASE/SENTENCE from the text where this data was found. This is critical for verification.
3. If a value is missing, return 'Not Found' for both value and evidence_quote.
4. Include 'Document Type' as the first finding.
5. Prioritize: Parties (Lessor/Lessee), Financials, Property Address, and Timeline.

Example Structure:
{
  "findings": [
    {
      "label": "Monthly Rent", 
      "value": "$1,200", 
      "evidence_quote": "The Tenant shall pay a monthly sum of $1,200"
    }
  ],
  "summary_paragraph": "Brief summary here..."
}
"""

# --- INITIALIZATION ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("leasesight-index")

def get_intelligent_summary(text_content):
    """
    Sends the compiled context to GPT-4o for structured extraction.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": UNIVERSAL_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Analyze this contract text and provide the audit:\n\n{text_content[:18000]}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error during LLM extraction: {e}")
        return {"findings": [], "summary_paragraph": "Error processing document."}

def run_full_audit(target_file):
    """
    Workflow:
    1. Embeds a general search query.
    2. Retrieves the top 15 most relevant segments from Pinecone.
    3. Sorts segments by page number (Sequential Context).
    4. Runs extraction via get_intelligent_summary.
    """
    print(f"--- STARTING AUDIT FOR: {target_file} ---")
    
    # 1. Broad Retrieval
    # We query for the most important legal and identifying sections
    try:
        res = client.embeddings.create(
            input=["Parties involved, rent details, address, and legal obligations"], 
            model="text-embedding-3-small"
        )
        query_vector = res.data[0].embedding

        # 2. Query Pinecone
        results = index.query(
            vector=query_vector, 
            top_k=15, 
            filter={"file_name": {"$eq": target_file}},
            include_metadata=True
        )

        if not results['matches']:
            print("No matching segments found in database.")
            return None

        # 3. Sequential Context Sorting
        # Azure/Pinecone results are often out of order; sorting ensures the AI reads 
        # the document naturally from start to finish.
        sorted_matches = sorted(
            results['matches'], 
            key=lambda x: x['metadata'].get('page_number', 0)
        )

        context = "\n".join([
            f"Page {m['metadata']['page_number']}: {m['metadata']['text']}" 
            for m in sorted_matches
        ])

        # 4. Extract Data
        audit_results = get_intelligent_summary(context)
        
        # Logging for debugging
        print(f"Extraction Complete. Found {len(audit_results.get('findings', []))} points.")
        return audit_results

    except Exception as e:
        print(f"Full Audit Workflow Error: {e}")
        return None

if __name__ == "__main__":
    # Test execution
    test_target = "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF"
    report = run_full_audit(test_target)
    if report:
        print(json.dumps(report, indent=4))