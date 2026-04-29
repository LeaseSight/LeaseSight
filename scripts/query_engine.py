import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("leasesight-index")

def get_expert_answer(question, contexts):
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

def ask_leasesight(question, target_file=None):
    print(f"Searching for: {question}...")
    res = client.embeddings.create(input=[question], model="text-embedding-3-small")
    query_vector = res.data[0].embedding

    # 1. APPLY FILTER: If a filename is provided, search ONLY that document
    search_filter = {"file_name": {"$eq": target_file}} if target_file else None

    results = index.query(
        vector=query_vector, 
        top_k=5, 
        filter=search_filter, # The Sniper Scope
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

    # 2. EXPERT EXTRACTION
    answer = get_expert_answer(question, context_text)
    print(f"\nAI ANSWER:\n{answer}\n")
    print("VERIFIED SOURCES:")
    for s in sources:
        print(f"- {s['file']} (Page {s['page']})")

if __name__ == "__main__":
    # TEST CASE: Specific document search
    doc_to_check = "ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT.PDF"
    user_q = "What is the governing law for this specific agreement?"
    ask_leasesight(user_q, target_file=doc_to_check)