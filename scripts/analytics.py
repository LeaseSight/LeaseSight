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
    similarities = cosine_similarity([query_vector], chunk_vectors)[0]

    fig = go.Figure(data=go.Heatmap(
        z=[similarities],
        x=[f"Chunk {i+1}" for i in range(len(similarities))],
        colorscale='GnBu'
    ))
    fig.update_layout(
        title="Internal Document Relevance",
        height=200,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    return fig


def generate_database_relationship_graph(current_doc_vector, archive_vectors, doc_names, is_committed=False):
    """Map 2: Current Document vs. Global Database"""
    if not archive_vectors or len(archive_vectors) < 3:
        return None
    all_vectors = np.vstack([archive_vectors, current_doc_vector])
    pca = PCA(n_components=3)
    coords = pca.fit_transform(all_vectors)

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=coords[:-1, 0], y=coords[:-1, 1], z=coords[:-1, 2],
        mode='markers', marker=dict(size=4, color='#cbd5e1', opacity=0.6),
        text=doc_names, name="Verified Archive"
    ))
    node_name = "Current Lease (Verified Archive)" if is_committed else "Current Lease (New)"
    fig.add_trace(go.Scatter3d(
        x=[coords[-1, 0]], y=[coords[-1, 1]], z=[coords[-1, 2]],
        mode='markers', marker=dict(size=8, color='#9333ea', symbol='diamond'),
        name=node_name
    ))
    fig.update_layout(
        title="Global Similarity Context",
        scene=dict(xaxis_visible=False, yaxis_visible=False, zaxis_visible=False)
    )
    return fig


def generate_query_similarity_3d(query_vector, chunk_vectors):
    """
    Map 3 (Feature 8): Query Vector vs. Document Chunk Vectors in 3D space.
    
    - Blue nodes  = document chunk segments (sized by cosine similarity to query)
    - Yellow star = the live chat query
    
    Only triggered on-demand via the 'Map Query Similarity' button.
    """
    if not chunk_vectors or len(chunk_vectors) < 2:
        return None

    q = np.array(query_vector)
    chunks = np.array(chunk_vectors)

    # Cosine similarities: query vs each chunk
    sims = cosine_similarity([q], chunks)[0]

    # PCA on all vectors (chunks + query appended last)
    all_vecs = np.vstack([chunks, q])
    n_components = min(3, all_vecs.shape[0], all_vecs.shape[1])
    if n_components < 3:
        return None

    pca = PCA(n_components=3)
    coords = pca.fit_transform(all_vecs)

    chunk_coords = coords[:-1]   # all but last
    query_coord  = coords[-1]    # last row

    # Scale node sizes by similarity (range 4-14)
    min_s, max_s = 4.0, 14.0
    norm_sims = (sims - sims.min()) / (sims.max() - sims.min() + 1e-9)
    node_sizes = (norm_sims * (max_s - min_s) + min_s).tolist()

    hover_texts = [f"Chunk {i+1}<br>Similarity: {sims[i]:.3f}" for i in range(len(sims))]

    fig = go.Figure()

    # Document chunk nodes (blue, sized by similarity)
    fig.add_trace(go.Scatter3d(
        x=chunk_coords[:, 0], y=chunk_coords[:, 1], z=chunk_coords[:, 2],
        mode='markers',
        marker=dict(
            size=node_sizes,
            color=sims.tolist(),
            colorscale='Blues',
            showscale=True,
            colorbar=dict(title="Cosine<br>Similarity", thickness=12, len=0.6),
            opacity=0.85,
            line=dict(width=0.5, color='#1e40af'),
        ),
        text=hover_texts,
        hoverinfo='text',
        name='Document Segments',
    ))

    # Query node (yellow star)
    fig.add_trace(go.Scatter3d(
        x=[query_coord[0]], y=[query_coord[1]], z=[query_coord[2]],
        mode='markers+text',
        marker=dict(size=16, color='#facc15', symbol='diamond', opacity=1.0,
                    line=dict(width=2, color='#78350f')),
        text=['Your Query'],
        textposition='top center',
        textfont=dict(color='#facc15', size=12),
        name='Chat Query',
    ))

    fig.update_layout(
        title=dict(
            text="🔭 Query Similarity Space — 3D Visual Correlation",
            font=dict(size=14, color='#1e293b')
        ),
        scene=dict(
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
            zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=''),
            bgcolor='#f8fafc',
        ),
        paper_bgcolor='#f8fafc',
        height=520,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            font=dict(size=11),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e2e8f0',
            borderwidth=1,
        ),
    )
    return fig
