# scripts/full_audit.py
# Multi-Agent Orchestration: Miner → Judge → Clerk

import os
import json
from pathlib import Path
from openai import OpenAI
from pinecone import Pinecone

# --- CONTEXT LIMIT SAFETY ---
CONTEXT_CHAR_LIMIT = 15000

# ============================================================================
# AGENT PROMPTS
# ============================================================================

MINER_PROMPT = """
You are "The Miner," a Legal Data Extraction specialist. Your goal is to extract every critical clause and data point from a contract.

CRITICAL RULES:
1. Extract ALL details into the 'findings' array. 
2. Each finding MUST have: 'label', 'value', and 'evidence_quote'.
3. 'evidence_quote' MUST be the EXACT phrase from the text.
4. If a value is missing, use "Not Found".
"""

JUDGE_PROMPT = """
You are "The Judge," a Legal Risk Analyst. Compare the findings against Market Context and identify outliers or red flags.
Assign a 'risk_score' (1-10) and a list of 'warnings'.
"""

CLERK_PROMPT = """
You are "The Clerk," a Legal Synthesizer. Produce a final JSON report with:
- findings (Miner's output)
- obligations (Miner's output)
- summary_paragraph (3 sentences)
- risk_score (Judge's score)
- warnings (Judge's warnings)
"""

# ============================================================================
# AGENT FUNCTIONS
# ============================================================================

def _call_agent(system_prompt, user_content, agent_name="Agent", openai_client=None):
    """Shared helper to call an LLM agent with JSON output."""
    try:
        if not openai_client:
            return {"error": f"{agent_name}: OpenAI client missing"}
            
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if not content:
            return {"error": f"{agent_name}: Empty response from AI"}
            
        return json.loads(content)
    except Exception as e:
        print(f"[{agent_name}] Error: {str(e)}")
        return {"error": f"{agent_name} crash: {str(e)}"}

def agent_miner(context_text, openai_client):
    print("[MINER] Extracting data points...")
    truncated = (context_text or "")[:CONTEXT_CHAR_LIMIT]
    result = _call_agent(MINER_PROMPT, f"Extract from:\n\n{truncated}", "MINER", openai_client)
    if "error" in result: return {"findings": [], "obligations": [], "error": result["error"]}
    return result

def agent_judge(miner_output, market_context, openai_client):
    print("[JUDGE] Reviewing for red flags...")
    input_data = json.dumps({"findings": miner_output, "market_context": market_context})
    result = _call_agent(JUDGE_PROMPT, f"Review:\n\n{input_data}", "JUDGE", openai_client)
    if "error" in result: return {"risk_score": 5, "warnings": [result["error"]]}
    return result

def agent_clerk(miner_output, judge_output, openai_client):
    print("[CLERK] Synthesizing report...")
    combined = json.dumps({"miner": miner_output, "judge": judge_output})
    result = _call_agent(CLERK_PROMPT, f"Synthesize:\n\n{combined}", "CLERK", openai_client)
    if "error" in result:
        return {
            "findings": miner_output.get("findings", []),
            "obligations": miner_output.get("obligations", []),
            "summary_paragraph": "Audit synthesized with errors.",
            "risk_score": judge_output.get("risk_score", 5),
            "warnings": judge_output.get("warnings", []) + [result["error"]]
        }
    return result

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def run_full_audit(target_file, openai_client=None, pinecone_index=None):
    try:
        if not openai_client or not pinecone_index:
            return {"error": "Clients not initialized correctly"}

        print(f"--- STARTING AUDIT: {target_file} ---")

        # 1. Retrieval
        res = openai_client.embeddings.create(input=["Lease terms, parties, rent"], model="text-embedding-3-small")
        vec = res.data[0].embedding
        results = pinecone_index.query(vector=vec, top_k=15, filter={"file_name": {"$eq": target_file}}, include_metadata=True)

        if not results['matches']:
            return {"error": f"No data found for {target_file}. Is it indexed?"}

        context = "\n".join([f"Page {m['metadata'].get('page_number', '?')}: {m['metadata'].get('text', '')}" for m in results['matches']])

        # 2. Market Precedents
        market_context = "No market precedents found."
        try:
            m_res = pinecone_index.query(vector=vec, top_k=5, filter={"file_name": {"$ne": target_file}}, include_metadata=True)
            if m_res['matches']:
                market_context = "\n".join([m['metadata'].get('text', '') for m in m_res['matches']])
        except: pass

        # 3. Pipeline
        miner_out = agent_miner(context, openai_client)
        judge_out = agent_judge(miner_out, market_context, openai_client)
        final_report = agent_clerk(miner_out, judge_out, openai_client)

        return final_report

    except Exception as e:
        return {"error": f"Audit Pipeline Error: {str(e)}"}