# scripts/full_audit.py
# Multi-Agent Orchestration: Miner → Judge → Clerk

import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

# --- IMPORT FALLBACK ---
sys.path.append(os.path.join(os.getcwd(), "scripts"))

# Load environment variables (API Keys)
load_dotenv()

# --- CONTEXT LIMIT SAFETY ---
# Maximum characters sent to Agent 1 to prevent API timeouts on massive documents
CONTEXT_CHAR_LIMIT = 15000

# ============================================================================
# AGENT PROMPTS
# ============================================================================

# --- AGENT 1: THE MINER ---
# High-fidelity extraction with mandatory evidence_quote for Feature 2 handshake
MINER_PROMPT = """
You are "The Miner," a Senior Legal Data Extractor with forensic precision.
Your SOLE job is to extract every critical data point from the contract text below.

Rules:
1. Extract up to 12 critical data points.
2. Return ONLY a JSON object with one key: 'findings'.
3. Each finding MUST have exactly three keys:
   - 'label': The field name (e.g., "Monthly Rent", "Lessor", "Start Date").
   - 'value': The extracted value (e.g., "$2,500", "June 1, 2023").
   - 'evidence_quote': THE EXACT short phrase from the source text where you found this.
     This is CRITICAL — downstream systems use this for visual grounding.
4. If a value cannot be found, set BOTH 'value' and 'evidence_quote' to "Not Found".
5. Include 'Document Type' as the FIRST finding.
6. Prioritize extraction order: Parties (Lessor/Lessee), Financials (Rent/Fees),
   Property/Asset Address, Timeline (Start Date, End Date, Term), Governing Law.

Example:
{
  "findings": [
    {"label": "Document Type", "value": "Lease Agreement", "evidence_quote": "This Lease Agreement is entered into"},
    {"label": "Start Date", "value": "January 1, 2024", "evidence_quote": "commencing on January 1, 2024"}
  ]
}
"""

# --- AGENT 2: THE JUDGE ---
# Critical review for Red Flags: date conflicts, missing parties, logical errors
JUDGE_PROMPT = """
You are "The Judge," a Legal Risk Analyst. You receive extracted findings from a contract
and must evaluate them for Red Flags and logical errors.

Your tasks:
1. Review ALL findings for logical consistency.
2. Specifically check for these Red Flags:
   - DATE CONFLICTS: Does the End Date occur BEFORE the Start Date?
   - MISSING PARTIES: Are Lessor/Lessee (or equivalent party names) missing or "Not Found"?
   - MISSING SIGNATURES: Is there no mention of signing parties or execution?
   - FINANCIAL ANOMALIES: Are rent/fee amounts suspiciously absent or zero?
   - TERM INCONSISTENCIES: Does the stated term length conflict with start/end dates?
3. Assign a 'risk_score' from 1 (very low risk) to 10 (critical issues found).
4. Provide a list of 'warnings' — each a clear, actionable sentence.

Return ONLY a JSON object:
{
  "risk_score": 3,
  "warnings": [
    "End Date (Dec 2022) occurs before Start Date (Jan 2023) — possible data entry error.",
    "Lessee name was not found in the extracted data."
  ]
}

If no issues are found, return: {"risk_score": 1, "warnings": []}
"""

# --- AGENT 3: THE CLERK ---
# Final synthesizer — merges Miner + Judge output into the canonical format
CLERK_PROMPT = """
You are "The Clerk," a Legal Document Synthesizer. You receive:
1. Extracted findings from the Miner (with evidence_quote for each field).
2. A risk assessment from the Judge (risk_score + warnings).

Your job is to produce the FINAL audit report as a single JSON object with these keys:
- 'findings': The Miner's findings list — PRESERVE ALL evidence_quote values exactly as-is.
  Do NOT modify, summarize, or remove any evidence_quote. They are used for visual grounding.
- 'summary_paragraph': A concise 3-sentence executive summary of the document.
- 'risk_score': The Judge's risk score (integer, 1-10).
- 'warnings': The Judge's warnings list (array of strings).

CRITICAL RULES:
- Do NOT alter the evidence_quote fields. Copy them verbatim from the Miner's output.
- Do NOT add or remove findings. Pass them through unchanged.
- The summary_paragraph should mention the document type, key parties, and any notable risks.

Return ONLY the JSON object.
"""

# ============================================================================
# INITIALIZATION
# ============================================================================

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("leasesight-index")


# ============================================================================
# AGENT FUNCTIONS
# ============================================================================

def _call_agent(system_prompt, user_content, agent_name="Agent"):
    """Shared helper to call an LLM agent with JSON output."""
    try:
        response = client.chat.completions.create(
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


def agent_miner(context_text):
    """Agent 1: Extract all findings with evidence_quotes."""
    print("[MINER] Extracting data points...")
    # Apply context limit safety
    truncated = context_text[:CONTEXT_CHAR_LIMIT]
    result = _call_agent(
        MINER_PROMPT,
        f"Extract all critical data from this contract:\n\n{truncated}",
        "MINER"
    )
    if result:
        findings_count = len(result.get('findings', []))
        print(f"[MINER] Extracted {findings_count} data points.")
    return result or {"findings": []}


def agent_judge(miner_output):
    """Agent 2: Evaluate findings for red flags and assign risk score."""
    print("[JUDGE] Reviewing for red flags...")
    result = _call_agent(
        JUDGE_PROMPT,
        f"Review these extracted contract findings for issues:\n\n{json.dumps(miner_output, indent=2)}",
        "JUDGE"
    )
    if result:
        print(f"[JUDGE] Risk Score: {result.get('risk_score', '?')}, Warnings: {len(result.get('warnings', []))}")
    return result or {"risk_score": 1, "warnings": []}


def agent_clerk(miner_output, judge_output):
    """Agent 3: Synthesize the final report — preserving evidence_quotes."""
    print("[CLERK] Synthesizing final report...")
    combined_input = json.dumps({
        "miner_findings": miner_output,
        "judge_assessment": judge_output
    }, indent=2)
    result = _call_agent(
        CLERK_PROMPT,
        f"Produce the final audit report from these agent outputs:\n\n{combined_input}",
        "CLERK"
    )
    if result:
        print(f"[CLERK] Final report ready. Findings: {len(result.get('findings', []))}")
    # Fallback: assemble manually if the Clerk fails
    if not result:
        result = {
            "findings": miner_output.get("findings", []),
            "summary_paragraph": "Error during synthesis. Raw findings preserved.",
            "risk_score": judge_output.get("risk_score", 1),
            "warnings": judge_output.get("warnings", [])
        }
    return result


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def run_full_audit(target_file):
    """
    Multi-Agent Audit Pipeline:
    1. Retrieve top 15 segments from Pinecone (sorted by page).
    2. Agent 1 (Miner): Extract findings + evidence_quotes.
    3. Agent 2 (Judge): Review for red flags, assign risk_score.
    4. Agent 3 (Clerk): Synthesize final JSON with all fields preserved.
    """
    print(f"--- STARTING MULTI-AGENT AUDIT FOR: {target_file} ---")

    # 1. Broad Retrieval from Pinecone
    try:
        res = client.embeddings.create(
            input=["Parties involved, rent details, address, and legal obligations"],
            model="text-embedding-3-small"
        )
        query_vector = res.data[0].embedding

        results = index.query(
            vector=query_vector,
            top_k=15,
            filter={"file_name": {"$eq": target_file}},
            include_metadata=True
        )

        if not results['matches']:
            print("No matching segments found in database.")
            return None

        # Sequential Context Sorting
        sorted_matches = sorted(
            results['matches'],
            key=lambda x: x['metadata'].get('page_number', 0)
        )

        context = "\n".join([
            f"Page {m['metadata']['page_number']}: {m['metadata']['text']}"
            for m in sorted_matches
        ])

    except Exception as e:
        print(f"Pinecone Retrieval Error: {e}")
        return None

    # 2. PIPELINE: Miner → Judge → Clerk
    miner_output = agent_miner(context)
    judge_output = agent_judge(miner_output)
    final_report = agent_clerk(miner_output, judge_output)

    print(f"--- AUDIT COMPLETE: {len(final_report.get('findings', []))} findings, "
          f"Risk: {final_report.get('risk_score', '?')}/10 ---")

    return final_report


if __name__ == "__main__":
    # Test execution
    test_target = "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF"
    report = run_full_audit(test_target)
    if report:
        print(json.dumps(report, indent=4))