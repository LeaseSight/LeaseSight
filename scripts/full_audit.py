# scripts/full_audit.py
# Multi-Agent Orchestration: Miner → Judge → Clerk

import os
import json
import re
import time
from pathlib import Path
from openai import OpenAI
from pinecone import Pinecone

# --- CONTEXT LIMIT SAFETY ---
CONTEXT_CHAR_LIMIT = 15000

# ============================================================================
# AGENT PROMPTS
# ============================================================================

MINER_PROMPT = """
You are "The Miner," a Legal Data Extraction specialist. Your goal is to extract EVERY critical clause and data point from the provided contract text.

CRITICAL EXTRACTION LIST:
1. Parties (Lessor/Lessee)
2. Commencement & Expiration Dates
3. Base Rent and Escalations
4. Security Deposit
5. Maintenance & Repair Obligations
6. Termination & Renewal Clauses
7. Governing Law

CRITICAL RULES:
1. Extract ALL details into the 'findings' array. 
2. Each finding MUST have: 'label', 'value', and 'evidence_quote'.
3. 'evidence_quote' MUST be the EXACT phrase from the text (do not paraphrase).
4. If a value is missing, use "Not Found".
5. Also populate the 'obligations' array with specific 'action_item', 'due_date', and 'party_responsible'.
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

AUDIT_PROMPT = """
You are a Senior Legal Analyst and Data Architect specializing in commercial real estate auditing.
Convert the provided lease text into high-fidelity structured JSON for visual grounding.

Required data fields:
- Parties: full legal names of the lessor/landlord and lessee/tenant.
- Financials: monthly or annual rent, security deposit, currency, rent escalation percentages.
- Term and tenure: total lease duration, commencement date, expiry date.
- Operational clauses: termination notice periods, renewal options, force majeure applicability.
- Legal and compliance: governing law and dispute resolution path.

Visual marking rules:
- Every finding and obligation must include evidence_quote.
- evidence_quote must be an exact verbatim string from the provided text.
- Prefer quotes at least 20 characters long.
- If the document does not contain a value, use value "Not Found" and evidence_quote "Not Found".

Return JSON only with this shape:
{
  "lease_metadata": {"title": "...", "lessor": "...", "lessee": "...", "tenure": "..."},
  "findings": [{"label": "...", "value": "...", "evidence_quote": "...", "risk_level": "Low|Medium|High"}],
  "obligations": [{"label": "...", "date": "...", "description": "...", "evidence_quote": "..."}],
  "risk_score": 1,
  "warnings": [],
  "summary_paragraph": "..."
}
"""

# ============================================================================
# AGENT FUNCTIONS
# ============================================================================

def _is_rate_limit_error(error_text):
    text = str(error_text).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text or "openresty" in text

def _public_error_message(error_text):
    if _is_rate_limit_error(error_text):
        return "AI service is temporarily rate-limited. A conservative partial audit was generated from indexed document text."
    return "AI audit service was unavailable. A conservative partial audit was generated from indexed document text."

def _call_agent(system_prompt, user_content, agent_name="Agent", openai_client=None, attempts=3):
    """Shared helper to call an LLM agent with JSON output."""
    if not openai_client:
        raise RuntimeError(f"{agent_name}: OpenAI client missing")

    last_error = None
    for attempt in range(attempts):
        try:
            response = openai_client.chat.completions.create(
                model=os.getenv("AUDIT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError(f"{agent_name}: Empty response from AI")
            return json.loads(content)
        except Exception as e:
            last_error = e
            print(f"[{agent_name}] attempt {attempt + 1}/{attempts} failed: {str(e)[:300]}")
            if attempt < attempts - 1 and _is_rate_limit_error(e):
                time.sleep(8 * (attempt + 1))
                continue
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(_public_error_message(last_error))

def _first_match(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = " ".join(match.group(1).split())
            quote = " ".join(match.group(0).split())
            return value[:180], quote[:500]
    return "Not Found", "Not Found"

def _fallback_audit(context_text, target_file, warning=None):
    text = " ".join((context_text or "").split())
    patterns = {
        "Lessor": [
            r"(?:lessor|landlord)\s*[:\-]?\s*([A-Z][A-Za-z0-9&.,'() \-]{3,120})",
            r"between\s+([A-Z][A-Za-z0-9&.,'() \-]{3,120})\s+(?:\(|,)?\s*(?:as\s+)?(?:lessor|landlord)",
        ],
        "Lessee": [
            r"(?:lessee|tenant)\s*[:\-]?\s*([A-Z][A-Za-z0-9&.,'() \-]{3,120})",
            r"and\s+([A-Z][A-Za-z0-9&.,'() \-]{3,120})\s+(?:\(|,)?\s*(?:as\s+)?(?:lessee|tenant)",
        ],
        "Rent": [
            r"((?:monthly|annual|base)?\s*rent[^.]{0,180}(?:\$|USD|Rs\.?|PKR)[^.]{0,120})",
            r"((?:\$|USD|Rs\.?|PKR)\s?[0-9][0-9,]*(?:\.[0-9]{2})?[^.]{0,120}(?:rent|per month|per annum|annually|monthly))",
        ],
        "Security Deposit": [
            r"(security deposit[^.]{0,180}(?:\$|USD|Rs\.?|PKR)[^.]{0,120})",
        ],
        "Commencement Date": [
            r"(commencement date[^.]{0,160})",
            r"(effective date[^.]{0,160})",
        ],
        "Expiry Date": [
            r"(expir(?:y|ation) date[^.]{0,160})",
            r"(term[^.]{0,120}(?:expire|expires|expiration)[^.]{0,120})",
        ],
        "Termination Notice": [
            r"(termination[^.]{0,180}(?:notice|days)[^.]{0,120})",
            r"((?:[0-9]+|thirty|sixty|ninety)\s*\(?[0-9]*\)?\s*days[^.]{0,160}notice[^.]{0,80})",
        ],
        "Renewal Option": [
            r"(renew(?:al|)[^.]{0,220})",
        ],
        "Force Majeure": [
            r"(force majeure[^.]{0,220})",
        ],
        "Governing Law": [
            r"(governing law[^.]{0,180})",
            r"(laws of [A-Z][A-Za-z ]{2,80})",
        ],
        "Dispute Resolution": [
            r"(dispute[^.]{0,220}(?:arbitration|litigation|court)[^.]{0,120})",
            r"(arbitration[^.]{0,220})",
        ],
    }

def _context_from_json_map(target_file):
    json_path = Path(__file__).resolve().parents[1] / "data" / "json_maps" / f"{target_file}.json"
    if not json_path.exists():
        return ""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pages = []
        for page in data.get("pages", []):
            page_number = page.get("page_number", "?")
            text = " ".join(line.get("content", "") for line in page.get("lines", []))
            if text.strip():
                pages.append(f"Page {page_number}: {text}")
        return "\n".join(pages)
    except Exception as e:
        print(f"[AUDIT] Could not load JSON map context for {target_file}: {e}")
        return ""

    findings = []
    for label, label_patterns in patterns.items():
        value, quote = _first_match(label_patterns, text)
        if value != "Not Found":
            findings.append({
                "label": label,
                "value": value,
                "evidence_quote": quote,
                "risk_level": "Medium" if label in {"Termination Notice", "Governing Law", "Dispute Resolution"} else "Low",
            })

    obligations = []
    for label in ("Termination Notice", "Renewal Option"):
        value, quote = _first_match(patterns[label], text)
        if value != "Not Found":
            obligations.append({
                "label": label,
                "date": value[:80],
                "description": value,
                "evidence_quote": quote,
            })

    warning_text = warning or "AI audit service was unavailable. Showing conservative extraction from indexed document text."
    return {
        "lease_metadata": {"title": target_file, "lessor": "Not Found", "lessee": "Not Found", "tenure": "Not Found"},
        "findings": findings,
        "obligations": obligations,
        "summary_paragraph": "A conservative audit was generated from indexed lease text because the AI audit service was temporarily unavailable. Review the extracted fields against the source document before committing them to the knowledge base.",
        "risk_score": 5 if findings else 1,
        "warnings": [warning_text],
    }

def _normalize_report(report, target_file):
    if not isinstance(report, dict):
        report = {}
    findings = report.get("findings") or []
    obligations = report.get("obligations") or []
    warnings = report.get("warnings") or []

    clean_warnings = []
    for warning in warnings:
        text = str(warning)
        if "<html" in text.lower() or "openresty" in text.lower() or "crash:" in text.lower():
            clean_warnings.append(_public_error_message(text))
        elif text.strip():
            clean_warnings.append(text)

    for item in findings:
        item.setdefault("label", "Finding")
        item.setdefault("value", "Not Found")
        item.setdefault("evidence_quote", "Not Found")
        item.setdefault("risk_level", "Medium")
    for item in obligations:
        item.setdefault("label", "Obligation")
        item.setdefault("date", "Not Found")
        item.setdefault("description", item.get("value", ""))
        item.setdefault("evidence_quote", "Not Found")

    summary = report.get("summary_paragraph") or report.get("summary") or ""
    if not summary or "technical error" in summary.lower() or "crash" in summary.lower():
        summary = "Lease audit completed. Review the extracted fields and source evidence before committing this document to the knowledge base."

    return {
        "lease_metadata": report.get("lease_metadata") or {"title": target_file},
        "findings": findings,
        "obligations": obligations,
        "summary_paragraph": summary,
        "risk_score": int(report.get("risk_score") or 5),
        "warnings": clean_warnings,
    }

def agent_miner(context_text, openai_client):
    print("[MINER] Extracting data points...")
    truncated = (context_text or "")[:CONTEXT_CHAR_LIMIT]
    result = _call_agent(MINER_PROMPT, f"Extract from:\n\n{truncated}", "MINER", openai_client)
    return result

def agent_judge(miner_output, market_context, openai_client):
    print("[JUDGE] Reviewing for red flags...")
    input_data = json.dumps({"findings": miner_output, "market_context": market_context})
    result = _call_agent(JUDGE_PROMPT, f"Review:\n\n{input_data}", "JUDGE", openai_client)
    return result

def agent_clerk(miner_output, judge_output, openai_client):
    print("[CLERK] Synthesizing report...")
    combined = json.dumps({"miner": miner_output, "judge": judge_output})
    result = _call_agent(CLERK_PROMPT, f"Synthesize:\n\n{combined}", "CLERK", openai_client)
    return result

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def run_full_audit(target_file, openai_client=None, pinecone_index=None):
    try:
        if not openai_client or not pinecone_index:
            return {"error": "Clients not initialized correctly"}

        print(f"--- STARTING AUDIT: {target_file} ---")

        # 1. Retrieval: prefer the exact Azure JSON map for the selected PDF.
        # Pinecone remains a fallback for older documents without spatial maps.
        context = _context_from_json_map(target_file)
        vec = None
        if not context:
            try:
                res = openai_client.embeddings.create(input=["Lease terms, parties, rent"], model="text-embedding-3-small")
                vec = res.data[0].embedding
                results = pinecone_index.query(vector=vec, top_k=15, filter={"file_name": {"$eq": target_file}}, include_metadata=True)
                if results['matches']:
                    context = "\n".join([f"Page {m['metadata'].get('page_number', '?')}: {m['metadata'].get('text', '')}" for m in results['matches']])
            except Exception as e:
                print(f"[AUDIT] Pinecone retrieval skipped: {str(e)[:300]}")

        if not context:
            return _fallback_audit("", target_file, f"No indexed text found for {target_file}. Upload indexing may still be in progress.")

        # 2. Market Precedents
        market_context = "No market precedents found."
        try:
            if vec:
                m_res = pinecone_index.query(vector=vec, top_k=5, filter={"file_name": {"$ne": target_file}}, include_metadata=True)
            else:
                m_res = {"matches": []}
            if m_res.get('matches'):
                market_context = "\n".join([m['metadata'].get('text', '') for m in m_res['matches']])
        except: pass

        try:
            payload = json.dumps({
                "document_name": target_file,
                "lease_text": context[:CONTEXT_CHAR_LIMIT],
                "market_context": market_context[:5000],
            })
            final_report = _call_agent(AUDIT_PROMPT, payload, "AUDIT", openai_client, attempts=4)
            return _normalize_report(final_report, target_file)
        except Exception as e:
            print(f"[AUDIT] Falling back after error: {str(e)}")
            return _fallback_audit(context, target_file, str(e))
    except Exception as e:
        return _fallback_audit("", target_file, f"Audit pipeline could not complete: {str(e)}")
