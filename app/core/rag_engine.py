# app/core/rag_engine.py
# Multi-namespace retrieval engine for strict tenant isolation.
# Queries both "academic_baseline" and the dynamic "user_{user_id}" namespace.

from typing import List, Dict, Any

def retrieve_dual_namespace(
    pinecone_index,
    query_vector: List[float],
    top_k: int = 5,
    file_name: str = None,
    user_id: str = None,
    include_metadata: bool = True,
    exclude_file_name: bool = False,
    include_values: bool = False
) -> Dict[str, Any]:
    """
    Queries Pinecone across both 'academic_baseline' and 'user_{user_id}' namespaces.
    Combines the results securely, keeping unique matches sorted by score.
    """
    matches = []
    
    # 1. Query 'academic_baseline' namespace
    try:
        filt = {}
        if file_name:
            key = "$ne" if exclude_file_name else "$eq"
            filt = {
                "$or": [
                    {"file_name": {key: file_name}},
                    {"filename": {key: file_name}}
                ]
            }
            
        res_baseline = pinecone_index.query(
            vector=query_vector,
            top_k=top_k,
            filter=filt if filt else None,
            namespace="academic_baseline",
            include_metadata=include_metadata,
            include_values=include_values
        )
        if res_baseline.get("matches"):
            for m in res_baseline["matches"]:
                # Normalize filename -> file_name for schema consistency
                if "metadata" in m and m["metadata"]:
                    if "filename" in m["metadata"] and "file_name" not in m["metadata"]:
                        m["metadata"]["file_name"] = m["metadata"]["filename"]
                matches.append(m)
    except Exception as e:
        print(f"[RAG_ENGINE] Error querying academic_baseline namespace: {e}")

    # 2. Query 'user_{user_id}' namespace if user_id is provided
    if user_id:
        user_ns = f"user_{user_id}"
        try:
            filt = {}
            if file_name:
                key = "$ne" if exclude_file_name else "$eq"
                filt = {
                    "$or": [
                        {"file_name": {key: file_name}},
                        {"filename": {key: file_name}}
                    ]
                }
                
            res_user = pinecone_index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filt if filt else None,
                namespace=user_ns,
                include_metadata=include_metadata,
                include_values=include_values
            )
            if res_user.get("matches"):
                for m in res_user["matches"]:
                    # Normalize filename -> file_name if present
                    if "metadata" in m and m["metadata"]:
                        if "filename" in m["metadata"] and "file_name" not in m["metadata"]:
                            m["metadata"]["file_name"] = m["metadata"]["filename"]
                    matches.append(m)
        except Exception as e:
            print(f"[RAG_ENGINE] Error querying {user_ns} namespace: {e}")

    # 3. Securely deduplicate and sort matches by score descending
    seen_ids = set()
    deduped_matches = []
    for m in matches:
        if m["id"] not in seen_ids:
            seen_ids.add(m["id"])
            deduped_matches.append(m)
            
    deduped_matches.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    
    # Return formatted results mimicking a standard Pinecone response
    return {"matches": deduped_matches[:top_k]}
