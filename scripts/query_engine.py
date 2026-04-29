# scripts/query_engine.py
# Scoped Document Chat — retrieves answers from a single document only

import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

# --- IMPORT FALLBACK ---
sys.path.append(os.path.join(os.getcwd(), "scripts"))

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("leasesight-index")


def get_expert_answer(question, contexts):
    """Send question + retrieved context to GPT-4o for a grounded answer."""
    prompt = f"""
    You are a legal expert analyzing contracts. 
    Based ONLY on the following snippets, answer the question.
    Context:
    {contexts}
    Question: {question}
    Answer:"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a professional legal auditor."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def ask_document(query, file_name):
    """
    Scoped document chat — queries ONLY the specified document.

    Uses Pinecone metadata filter: {"file_name": {"$eq": file_name}}
    to act as a firewall against cross-contamination.

    Args:
        query (str): The user's natural language question.
        file_name (str): The PDF filename to scope the search to.

    Returns:
        dict: {"answer": str, "source_text": str, "page": int}
              or {"answer": str, "source_text": None, "page": None} on failure.
    """
    try:
        # 1. Embed the question
        res = client.embeddings.create(input=[query], model="text-embedding-3-small")
        query_vector = res.data[0].embedding

        # 2. Scoped Pinecone query — locked to current document
        results = index.query(
            vector=query_vector,
            top_k=5,
            filter={"file_name": {"$eq": file_name}},
            include_metadata=True
        )

        if not results['matches']:
            return {
                "answer": "I couldn't find relevant information in this document for your question.",
                "source_text": None,
                "page": None
            }

        # 3. Build context from matches
        context_text = ""
        best_source = None
        best_page = None

        for match in results['matches']:
            meta = match.get('metadata', {})
            snippet = meta.get('text', '')
            page = meta.get('page_number', 1)
            context_text += f"\n---\nPage {page}: {snippet}"

            # Keep the top match (highest score) as the source for highlighting
            if best_source is None:
                best_source = snippet
                best_page = page

        # 4. Get LLM answer
        answer = get_expert_answer(query, context_text)

        return {
            "answer": answer,
            "source_text": best_source,
            "page": int(best_page) if best_page else None
        }

    except Exception as e:
        print(f"[CHAT] Error: {e}")
        return {
            "answer": f"An error occurred while processing your question: {e}",
            "source_text": None,
            "page": None
        }


def ask_leasesight(question, target_file=None):
    """Legacy function — prints answer to console."""
    print(f"Searching for: {question}...")
    res = client.embeddings.create(input=[question], model="text-embedding-3-small")
    query_vector = res.data[0].embedding

    search_filter = {"file_name": {"$eq": target_file}} if target_file else None

    results = index.query(
        vector=query_vector,
        top_k=5,
        filter=search_filter,
        include_metadata=True
    )

    context_text = ""
    sources = []
    for match in results['matches']:
        context_text += f"\n---\nDoc: {match['metadata']['file_name']}\nText: {match['metadata']['text']}"
        sources.append({"file": match['metadata']['file_name'], "page": match['metadata']['page_number']})

    if not context_text:
        print("No matches found for that specific file.")
        return

    answer = get_expert_answer(question, context_text)
    print(f"\nAI ANSWER:\n{answer}\n")
    print("VERIFIED SOURCES:")
    for s in sources:
        print(f"- {s['file']} (Page {s['page']})")


if __name__ == "__main__":
    doc_to_check = "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF"
    user_q = "What is the governing law for this specific agreement?"
    ask_leasesight(user_q, target_file=doc_to_check)