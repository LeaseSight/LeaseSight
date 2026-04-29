# scripts/analytics.py
# The Math Engine — 3D PCA Similarity Network Graph

import numpy as np
import plotly.graph_objects as go
from sklearn.decomposition import PCA


def generate_3d_network_graph(new_vector, database_vectors, doc_names):
    """
    Generates a 3D interactive scatter plot showing the spatial relationship
    between a new document and the existing archive using PCA dimensionality reduction.

    Args:
        new_vector (list[float]): The embedding vector for the currently selected document.
        database_vectors (list[list[float]]): Embedding vectors from the archive.
        doc_names (list[str]): Display names corresponding to each archive vector.

    Returns:
        plotly.graph_objects.Figure or None if insufficient data.
    """

    # --- ROBUSTNESS CHECK ---
    # PCA(n_components=3) requires at least 3 samples to define a 3D space.
    # With fewer archive vectors, dimensionality reduction is mathematically invalid.
    if len(database_vectors) < 3:
        return None

    # --- PCA DIMENSIONALITY REDUCTION ---
    # Combine the new vector with the archive to project them into the same 3D space.
    all_vectors = np.array(database_vectors + [new_vector])
    all_names = doc_names + ["📄 CURRENT DOCUMENT"]

    pca = PCA(n_components=3)
    coords_3d = pca.fit_transform(all_vectors)

    # Split back: archive = all except last, current = last
    archive_coords = coords_3d[:-1]
    new_coords = coords_3d[-1]

    # --- PLOTLY 3D SCATTER ---
    # Truncate long filenames for cleaner hover labels
    short_names = [
        (n[:45] + "...") if len(n) > 48 else n for n in doc_names
    ]

    # Archive nodes: blue, low opacity, small markers
    archive_trace = go.Scatter3d(
        x=archive_coords[:, 0],
        y=archive_coords[:, 1],
        z=archive_coords[:, 2],
        mode="markers",
        name="Archive Contracts",
        text=short_names,
        hoverinfo="text",
        marker=dict(
            size=4,
            color="rgba(65, 105, 225, 0.35)",  # Royal blue, low opacity
            symbol="circle",
            line=dict(width=0.5, color="rgba(65, 105, 225, 0.6)"),
        ),
    )

    # New upload node: red diamond, high visibility
    new_trace = go.Scatter3d(
        x=[new_coords[0]],
        y=[new_coords[1]],
        z=[new_coords[2]],
        mode="markers+text",
        name="Current Document",
        text=["📄 CURRENT DOCUMENT"],
        textposition="top center",
        textfont=dict(size=11, color="#FF4444"),
        hoverinfo="text",
        marker=dict(
            size=10,
            color="#FF4444",          # Bright red
            symbol="diamond",
            line=dict(width=2, color="#FFFFFF"),
        ),
    )

    # --- LAYOUT ---
    fig = go.Figure(data=[archive_trace, new_trace])

    fig.update_layout(
        title=dict(
            text="🌐 Document Similarity Network (PCA 3D Projection)",
            font=dict(size=16, color="#E0E0E0"),
            x=0.5,
        ),
        scene=dict(
            xaxis=dict(
                title="PC1",
                backgroundcolor="rgba(20, 20, 35, 0.95)",
                gridcolor="rgba(80, 80, 120, 0.3)",
                showbackground=True,
                zerolinecolor="rgba(100, 100, 150, 0.4)",
            ),
            yaxis=dict(
                title="PC2",
                backgroundcolor="rgba(20, 20, 35, 0.95)",
                gridcolor="rgba(80, 80, 120, 0.3)",
                showbackground=True,
                zerolinecolor="rgba(100, 100, 150, 0.4)",
            ),
            zaxis=dict(
                title="PC3",
                backgroundcolor="rgba(20, 20, 35, 0.95)",
                gridcolor="rgba(80, 80, 120, 0.3)",
                showbackground=True,
                zerolinecolor="rgba(100, 100, 150, 0.4)",
            ),
        ),
        paper_bgcolor="rgba(15, 15, 25, 1)",
        plot_bgcolor="rgba(15, 15, 25, 1)",
        font=dict(color="#C0C0C0"),
        legend=dict(
            bgcolor="rgba(30, 30, 50, 0.8)",
            bordercolor="rgba(80, 80, 120, 0.5)",
            borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        height=600,
    )

    return fig
