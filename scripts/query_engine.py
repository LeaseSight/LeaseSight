# scripts/query_engine.py
import os, sys
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

sys.path.append(os.path.join(os.getcwd(), "scripts"))
load_dotenv()


def get_expert_answer(question, contexts, openai_client):
    prompt = f"You are a legal expert analyzing contracts.\nBased ONLY on the following snippets, answer the question.\nContext:\n{contexts}\nQuestion: {question}\nAnswer:"
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a professional legal auditor."}, {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def ask_document(query, file_name, openai_client=None, pinecone_index=None):
    """
    Scoped document chat. Clients injected by API layer; falls back to .env for local dev.
    """
    if openai_client is None:
        openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_PROXY_URL") or "https://api.openai.com/v1"
        )
    if pinecone_index is None:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        pinecone_index = pc.Index("leasesight-index")
    try:
        res = openai_client.embeddings.create(input=[query], model="text-embedding-3-small")
        query_vector = res.data[0].embedding
        results = pinecone_index.query(vector=query_vector, top_k=5, filter={"file_name": {"$eq": file_name}}, include_metadata=True)
        if not results['matches']:
            return {"answer": "I couldn't find relevant information in this document for your question.", "source_text": None, "page": None}
        context_text, best_source, best_page = "", None, None
        for match in results['matches']:
            meta = match.get('metadata', {})
            snippet, page = meta.get('text', ''), meta.get('page_number', 1)
            context_text += f"\n---\nPage {page}: {snippet}"
            if best_source is None:
                best_source, best_page = snippet, page
        answer = get_expert_answer(query, context_text, openai_client)
        return {"answer": answer, "source_text": best_source, "page": int(best_page) if best_page else None}
    except Exception as e:
        return {"answer": f"An error occurred: {e}", "source_text": None, "page": None}


if __name__ == "__main__":
    ask_document("What is the governing law?", "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF")