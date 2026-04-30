# scripts/analytics.py
# The Math Engine — Dual Similarity Maps (Tactical + Strategic)

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA


def generate_query_heatmap(query_vector, chunk_vectors, chunk_labels=None):
    """
    Map 1 (Tactical): Query vs. Current Document Chunks.
    Measures cosine similarity between a search query and individual chunks
    to show WHERE in the document the answer lives.

    Args:
        query_vector: The embedding vector of the search query.
        chunk_vectors: List of embedding vectors for each document chunk.
        chunk_labels: Optional labels for each chunk (e.g., "Page 1").

    Returns:
        dict with similarities list and labels for frontend rendering.
    """
    if not chunk_vectors or len(chunk_vectors) == 0:
        return {"similarities": [], "labels": [], "max_idx": 0}

    sims = cosine_similarity([query_vector], chunk_vectors)[0]
    labels = chunk_labels or [f"Chunk {i+1}" for i in range(len(sims))]

    return {
        "similarities": sims.tolist(),
        "labels": labels,
        "max_idx": int(np.argmax(sims)),
        "max_score": float(np.max(sims)),
    }


def generate_database_relationship_graph(current_doc_vector, archive_vectors, doc_names):
    """
    Map 2 (Strategic): Current Document vs. Global Database.
    Uses PCA to project the current document and all archived documents
    into 3D space to visualize structural similarity.

    Args:
        current_doc_vector: Embedding for the current document.
        archive_vectors: List of archive document embeddings.
        doc_names: Display names for archive documents.

    Returns:
        dict with PCA coordinates for frontend 3D rendering,
        or None if insufficient data.
    """
    if len(archive_vectors) < 3:
        return None

    all_vectors = np.array(archive_vectors + [current_doc_vector])
    pca = PCA(n_components=3)
    coords_3d = pca.fit_transform(all_vectors)

    archive_coords = coords_3d[:-1]
    new_coords = coords_3d[-1]

    # Compute cosine similarities to current doc for coloring
    sims = cosine_similarity([current_doc_vector], archive_vectors)[0]

    short_names = [(n[:45] + "...") if len(n) > 48 else n for n in doc_names]

    return {
        "archive_coords": archive_coords.tolist(),
        "new_coords": new_coords.tolist(),
        "names": short_names,
        "similarities": sims.tolist(),
        "sufficient": True,
        "explained_variance": pca.explained_variance_ratio_.tolist(),
    }


# --- LEGACY: Keep the old function for backward compatibility ---
def generate_3d_network_graph(new_vector, database_vectors, doc_names):
    """Legacy wrapper — returns coordinate data for the frontend."""
    result = generate_database_relationship_graph(new_vector, database_vectors, doc_names)
    return result
