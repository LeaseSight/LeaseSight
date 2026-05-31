# scripts/query_engine.py
# Scoped document chat: Gemini embeddings (768-dim) + Gemini chat.
# Migrated from OpenAI (gpt-4o / text-embedding-3-small).

import os
import sys
from dotenv import load_dotenv
from pinecone import Pinecone

from scripts.gemini_client import GeminiChatClient, GeminiEmbeddingClient

sys.path.append(os.path.join(os.getcwd(), "scripts"))
load_dotenv()

_LEGAL_SYSTEM = "You are a professional legal auditor. Answer questions strictly from the provided context."


def get_expert_answer(question: str, contexts: str, gemini_client: GeminiChatClient) -> str:
    prompt = (
        f"Based ONLY on the following contract snippets, answer the question.\n\n"
        f"Context:\n{contexts}\n\n"
        f"Question: {question}\n\nAnswer:"
    )
    result = gemini_client.complete_json(
        system_prompt=_LEGAL_SYSTEM,
        user_content=prompt,
        agent_name="QUERY",
    )
    # The model might return {"answer": "..."} or raw text wrapped in JSON
    return result.get("answer") or str(result)


def ask_document(
    query: str,
    file_name: str,
    gemini_client: GeminiChatClient = None,
    embed_client: GeminiEmbeddingClient = None,
    pinecone_index=None,
    # Legacy kwargs accepted but ignored
    openai_client=None,
) -> dict:
    """
    Scoped document chat. Clients injected by API layer; falls back to .env for local dev.
    """
    if gemini_client is None:
        gemini_client = GeminiChatClient()
    if embed_client is None:
        embed_client = GeminiEmbeddingClient()
    if pinecone_index is None:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        pinecone_index = pc.Index("leasesight-index")

    try:
        query_vector = embed_client.embed_query(query)
        results = pinecone_index.query(
            vector=query_vector,
            top_k=5,
            filter={"file_name": {"$eq": file_name}},
            include_metadata=True,
        )
        if not results["matches"]:
            return {
                "answer": "I couldn't find relevant information in this document for your question.",
                "source_text": None,
                "page": None,
            }

        context_text, best_source, best_page = "", None, None
        for match in results["matches"]:
            meta = match.get("metadata", {})
            snippet, page = meta.get("text", ""), meta.get("page_number", 1)
            context_text += f"\n---\nPage {page}: {snippet}"
            if best_source is None:
                best_source, best_page = snippet, page

        answer = get_expert_answer(query, context_text, gemini_client)
        return {
            "answer": answer,
            "source_text": best_source,
            "page": int(best_page) if best_page else None,
        }
    except Exception as e:
        return {"answer": f"An error occurred: {e}", "source_text": None, "page": None}


if __name__ == "__main__":
    print(ask_document("What is the governing law?", "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF"))