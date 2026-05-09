# scripts/full_audit.py
# Multi-Agent Orchestration: Miner → Judge → Clerk

import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

sys.path.append(os.path.join(os.getcwd(), "scripts"))

load_dotenv()

# --- CONTEXT LIMIT SAFETY ---
CONTEXT_CHAR_LIMIT = 15000

# ============================================================================
# AGENT PROMPTS
# ============================================================================

MINER_PROMPT = """
You are "The Miner," a Senior Legal Data Extractor with forensic precision.
Your SOLE job is to extract every critical data point from the contract text below.

Rules:
1. Extract up to 12 critical data points.
2. Return ONLY a JSON object with two keys: 'findings' and 'obligations'.
3. Each finding MUST have exactly three keys:
   - 'label': The field name (e.g., "Monthly Rent", "Lessor", "Start Date").
   - 'value': The extracted value (e.g., "$2,500", "June 1, 2023").
   - 'evidence_quote': THE EXACT short phrase from the source text where you found this.
     This is CRITICAL — downstream systems use this for visual grounding.
4. If a value cannot be found, set BOTH 'value' and 'evidence_quote' to "Not Found".
5. Include 'Document Type' as the FIRST finding.
6. Extract all time-sensitive dates (Renewals, Notice Periods, Rent Hikes) into the 'obligations' array.
   Each obligation MUST have: 'label' (short title), 'date' (exact date or relative time), and 'description'.

Example:
{
  "findings": [
    {"label": "Document Type", "value": "Lease Agreement", "evidence_quote": "This Lease Agreement is entered into"}
  ],
  "obligations": [
    {"label": "Renewal Notice Due", "date": "September 1, 2024", "description": "Tenant must provide 90 days written notice to renew."}
  ]
}
"""

JUDGE_PROMPT = """
You are "The Judge," a Legal Risk Analyst. You receive extracted findings from a contract and a "Market Context" sample of standard precedents from our verified archive.

Your tasks:
1. Compare the findings against the provided Market Context to determine if the clauses (e.g., rent, termination, deposit) are "Standard" or "Outliers".
2. Review ALL findings for logical consistency.
3. Specifically check for these Red Flags:
   - NON-STANDARD CLAUSES: Is the security deposit unusually high compared to the market? Are termination terms predatory?
   - DATE CONFLICTS: Does the End Date occur BEFORE the Start Date?
   - MISSING PARTIES: Are Lessor/Lessee missing?
4. Assign a 'risk_score' from 1 (very low risk, highly standard) to 10 (critical issues, extreme outlier).
5. Provide a list of 'warnings' (Red Flags) — each a clear, actionable sentence.

Return ONLY a JSON object:
{
  "risk_score": 3,
  "warnings": [
    "Security deposit is 3x monthly rent, whereas the market standard is 1x.",
    "End Date occurs before Start Date."
  ]
}

If no issues are found, return: {"risk_score": 1, "warnings": []}
"""

CLERK_PROMPT = """
You are "The Clerk," a Legal Document Synthesizer. You receive:
1. Extracted findings and obligations from the Miner (with evidence_quote for each field).
2. A risk assessment from the Judge (risk_score + warnings).

Your job is to produce the FINAL audit report as a single JSON object with these keys:
- 'findings': The Miner's findings list — PRESERVE ALL evidence_quote values exactly as-is.
- 'obligations': The Miner's obligations list — PRESERVE as-is.
- 'summary_paragraph': A concise 3-sentence executive summary of the document.
- 'risk_score': The Judge's risk score (integer, 1-10).
- 'warnings': The Judge's warnings list (array of strings).

CRITICAL RULES:
- Do NOT alter the evidence_quote fields. Copy them verbatim from the Miner's output.
- Do NOT add or remove findings or obligations. Pass them through unchanged.
- The summary_paragraph should mention the document type, key parties, and any notable risks.

Return ONLY the JSON object.
"""


# ============================================================================
# AGENT FUNCTIONS
# ============================================================================

def _call_agent(system_prompt, user_content, agent_name="Agent", openai_client=None):
    """Shared helper to call an LLM agent with JSON output."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[{agent_name}] Error: {e}")
        return None


def agent_miner(context_text, openai_client):
    """Agent 1: Extract all findings with evidence_quotes."""
    print("[MINER] Extracting data points...")
    truncated = context_text[:CONTEXT_CHAR_LIMIT]
    result = _call_agent(
        MINER_PROMPT,
        f"Extract all critical data from this contract:\n\n{truncated}",
        "MINER",
        openai_client=openai_client
    )
    if result:
        print(f"[MINER] Extracted {len(result.get('findings', []))} data points.")
    return result or {"findings": []}


def agent_judge(miner_output, market_context, openai_client):
    """Agent 2: Evaluate findings for red flags and assign risk score."""
    print("[JUDGE] Reviewing for red flags against market standard...")
    input_content = json.dumps({"findings": miner_output, "market_context": market_context}, indent=2)
    result = _call_agent(
        JUDGE_PROMPT,
        f"Review these extracted contract findings against the market precedents:\n\n{input_content}",
        "JUDGE",
        openai_client=openai_client
    )
    if result:
        print(f"[JUDGE] Risk Score: {result.get('risk_score', '?')}, Warnings: {len(result.get('warnings', []))}")
    return result or {"risk_score": 1, "warnings": []}


def agent_clerk(miner_output, judge_output, openai_client):
    """Agent 3: Synthesize the final report — preserving evidence_quotes."""
    print("[CLERK] Synthesizing final report...")
    combined_input = json.dumps({"miner_findings": miner_output, "judge_assessment": judge_output}, indent=2)
    result = _call_agent(
        CLERK_PROMPT,
        f"Produce the final audit report from these agent outputs:\n\n{combined_input}",
        "CLERK",
        openai_client=openai_client
    )
    if result:
        print(f"[CLERK] Final report ready. Findings: {len(result.get('findings', []))}")
    if not result:
        result = {
            "findings": miner_output.get("findings", []),
            "obligations": miner_output.get("obligations", []),
            "summary_paragraph": "Error during synthesis. Raw findings preserved.",
            "risk_score": judge_output.get("risk_score", 1),
            "warnings": judge_output.get("warnings", [])
        }
    return result


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def run_full_audit(target_file, openai_client=None, pinecone_index=None):
    """
    Multi-Agent Audit Pipeline: Miner → Judge → Clerk.
    """
    try:
        # --- Client Resolution ---
        if openai_client is None:
            openai_client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_PROXY_URL") or "https://api.openai-proxy.com/v1"
            )
        if pinecone_index is None:
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            pinecone_index = pc.Index("leasesight-index")

        print(f"--- STARTING MULTI-AGENT AUDIT FOR: {target_file} ---")

        # 1. Broad Retrieval from Pinecone
        try:
            res = openai_client.embeddings.create(
                input=["Parties involved, rent details, address, and legal obligations"],
                model="text-embedding-3-small"
            )
            query_vector = res.data[0].embedding

            results = pinecone_index.query(
                vector=query_vector,
                top_k=15,
                filter={"file_name": {"$eq": target_file}},
                include_metadata=True
            )

            if not results['matches']:
                print(f"No matching segments found for: {target_file}")
                return {"error": "Document not found in database. Please wait 10 seconds for indexing to complete."}

            sorted_matches = sorted(
                results['matches'],
                key=lambda x: x['metadata'].get('page_number', 0)
            )
            context = "\n".join([
                f"Page {m['metadata']['page_number']}: {m['metadata']['text']}"
                for m in sorted_matches
            ])
        except Exception as e:
            return {"error": f"Database retrieval failed: {str(e)}"}

        # 2. Market Context
        try:
            market_res = openai_client.embeddings.create(
                input=["Standard lease termination, security deposit, and renewal clauses"],
                model="text-embedding-3-small"
            )
            market_vec = market_res.data[0].embedding
            market_results = pinecone_index.query(
                vector=market_vec,
                top_k=5,
                filter={"file_name": {"$ne": target_file}},
                include_metadata=True
            )
            market_context = "\n".join([
                f"Precedent: {m['metadata'].get('text', '')}"
                for m in market_results.get('matches', [])
            ])
            if not market_context:
                market_context = "No precedents available."
        except Exception:
            market_context = "Market context unavailable."

        # 3. PIPELINE
        miner_output = agent_miner(context, openai_client)
        judge_output = agent_judge(miner_output, market_context, openai_client)
        final_report = agent_clerk(miner_output, judge_output, openai_client)

        return final_report

    except Exception as e:
        return {"error": f"Audit pipeline crash: {str(e)}"}


if __name__ == "__main__":
    test_target = "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF"
    report = run_full_audit(test_target)
    if report:
        print(json.dumps(report, indent=4))