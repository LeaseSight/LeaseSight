import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone


load_dotenv()

# Detailed Schema based on your screenshot
EXTRACTION_SCHEMA = {
    "Lease_Info": {
        "Lease_Name": "Title of the agreement",
        "Asset_Type": "e.g., Vehicle, Property, Equipment",
        "Currency": "Local currency used in the contract"
    },
    "Parties": {
        "Lessor_Name": "Name of the owner/lessor",
        "Lessee_Name": "Name of the user/lessee"
    },
    "Dates_and_Terms": {
        "Start_Date": "MM/DD/YYYY",
        "End_Date": "MM/DD/YYYY",
        "Term_Months": "Duration in months"
    },
    "Financials": {
        "Monthly_Payment": "Amount paid per month",
        "Security_Deposit": "Refundable deposit amount"
    },
    "Asset_Details": {
        "Manufacturer": "e.g., Toyota",
        "Model": "e.g., Corolla",
        "Registration_No": "License plate or ID"
    }
}

def run_full_audit(target_file):
    # ... (Keep retrieval logic from before) ...

    prompt = f"""
    Act as a precise data extraction engine. Extract the following information from the contract text.
    Format your response as a JSON object matching this structure:
    {json.dumps(EXTRACTION_SCHEMA, indent=2)}
    
    Rules:
    1. Dates MUST be in MM/DD/YYYY format.
    2. If a value is missing, return "Not found".
    3. Use the context below:
    Context: {context}
    """
    
    # ... (Keep the OpenAI call from before) ...

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("leasesight-index")

# The 'Big 5' categories from the CUAD research paper
LABELS = [
    "Governing Law",
    "Termination for Convenience",
    "Indemnification",
    "Limitation of Liability",
    "Renewal Term"
]

def run_full_audit(target_file):
    print(f"--- STARTING FULL AUDIT FOR: {target_file} ---")
    
    # 1. Broad Retrieval
    # We query the database with a general 'legal summary' request to get the best pages
    res = client.embeddings.create(input=["Important clauses and legal provisions"], model="text-embedding-3-small")
    query_vector = res.data[0].embedding

    results = index.query(
        vector=query_vector, 
        top_k=10, # Get more pages for a full audit
        filter={"file_name": {"$eq": target_file}},
        include_metadata=True
    )

    context = "\n".join([f"Page {m['metadata']['page_number']}: {m['metadata']['text']}" for m in results['matches']])

    # 2. Structured Extraction
    prompt = f"""
    Act as a senior legal auditor. Analyze the provided contract snippets and extract the following:
    {', '.join(LABELS)}
    
    Return the result in a clean JSON format. If a clause isn't found, return "Not found".
    Context: {context}
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" }, # Force JSON output
        messages=[{"role": "system", "content": "You output legal audits in JSON."},
                  {"role": "user", "content": prompt}]
    )
    
    audit_results = json.loads(response.choices[0].message.content)
    
    # 3. Print the Audit Report
    print(json.dumps(audit_results, indent=4))
    return audit_results

if __name__ == "__main__":
    target = "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF"
    run_full_audit(target)