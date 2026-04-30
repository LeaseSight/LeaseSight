# scripts/analytics.py
# The Math Engine — Dual Similarity Maps (Tactical + Strategic)

import numpy as np
import plotly.graph_objects as go
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA

def generate_query_heatmap(query_vector, chunk_vectors):
    """Map 1: Query vs. Current Document Chunks"""
    if not chunk_vectors or len(chunk_vectors) == 0:
        return None
    # Calculate similarity for each chunk
    similarities = cosine_similarity([query_vector], chunk_vectors)[0]
    
    fig = go.Figure(data=go.Heatmap(
        z=[similarities],
        x=[f"Chunk {i+1}" for i in range(len(similarities))],
        colorscale='GnBu' # Mint Green to Blue
    ))
    fig.update_layout(title="Internal Document Relevance", height=200, margin=dict(l=10, r=10, t=30, b=10))
    return fig

def generate_database_relationship_graph(current_doc_vector, archive_vectors, doc_names, is_committed=False):
    """Map 2: Current Document vs. Global Database"""
    if not archive_vectors or len(archive_vectors) < 3:
        return None
    all_vectors = np.vstack([archive_vectors, current_doc_vector])
    pca = PCA(n_components=3)
    coords = pca.fit_transform(all_vectors)

    fig = go.Figure()
    # Archive Nodes
    fig.add_trace(go.Scatter3d(
        x=coords[:-1, 0], y=coords[:-1, 1], z=coords[:-1, 2],
        mode='markers', marker=dict(size=4, color='#cbd5e1', opacity=0.6),
        text=doc_names, name="Verified Archive"
    ))
    
    # Current Doc Node
    node_name = "Current Lease (Verified Archive)" if is_committed else "Current Lease (New)"
    fig.add_trace(go.Scatter3d(
        x=[coords[-1, 0]], y=[coords[-1, 1]], z=[coords[-1, 2]],
        mode='markers', marker=dict(size=8, color='#9333ea', symbol='diamond'),
        name=node_name
    ))
    fig.update_layout(title="Global Similarity Context", scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False))
    return fig
