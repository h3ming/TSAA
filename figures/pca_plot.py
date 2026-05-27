# figures/pca_plot.py

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pc
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

PCA_CSV = BASE_DIR / "figures" / "csv_data" / "chapters_pca.csv"
PCA_META = BASE_DIR / "figures" / "csv_data" / "pca_meta.json"

# ── Load data ────────────────────────────────────────────────────────────
df = pd.read_csv(PCA_CSV)

with open(PCA_META) as f:
    meta = json.load(f)

top_povs = meta["top_povs"]
overlays = meta["overlays"]

qual = pc.qualitative.D3

color_map = {
    pov: qual[i % len(qual)]
    for i, pov in enumerate(top_povs)
}
color_map["Other"] = "#bfbfbf"

book_marker = {
    "The Way of Kings": "circle",
    "Words of Radiance": "square",
}


# ── Figure builder ───────────────────────────────────────────────────────
def make_pca_figure(selected_pov=None):

    fig = go.Figure()

    # ── Filter dataframe ────────────────────────────────────────────────
    if selected_pov:
        plot_df = df[df["pov"] == selected_pov]
    else:
        plot_df = df

    # ── Hull ────────────────────────────────────────────────────────────
    if selected_pov and selected_pov in overlays:

        overlay = overlays[selected_pov]

        if "hull" in overlay:

            hull = overlay["hull"]

            hull_x = [p[0] for p in hull] + [hull[0][0]]
            hull_y = [p[1] for p in hull] + [hull[0][1]]

            fig.add_trace(
                go.Scatter(
                    x=hull_x,
                    y=hull_y,
                    fill="toself",
                    fillcolor=color_map[selected_pov],
                    opacity=0.12,
                    line=dict(
                        color=color_map[selected_pov],
                        width=1.2
                    ),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    # ── Scatter points ─────────────────────────────────────────────────
    for book, marker in book_marker.items():

        sub_book = plot_df[plot_df["book"] == book]

        for pov in sub_book["pov"].unique():

            sub = sub_book[sub_book["pov"] == pov]

            pov_group = pov if pov in top_povs else "Other"

            fig.add_trace(
                go.Scatter(
                    x=sub["pc1"],
                    y=sub["pc2"],
                    mode="markers",
                    marker=dict(
                        size=10,
                        symbol=marker,
                        color=color_map[pov_group],
                        line=dict(color="white", width=0.8),
                    ),
                    name=pov,
                    customdata=sub[
                        ["heading_text", "pov", "book", "word_count"]
                    ].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "POV: %{customdata[1]}<br>"
                        "Book: %{customdata[2]}<br>"
                        "Words: %{customdata[3]}<br>"
                        "PC1: %{x:.4f}<br>"
                        "PC2: %{y:.4f}<extra></extra>"
                    ),
                )
            )

    # ── Centroid ───────────────────────────────────────────────────────
    if selected_pov and selected_pov in overlays:

        centroid = overlays[selected_pov]["centroid"]

        fig.add_trace(
            go.Scatter(
                x=[centroid[0]],
                y=[centroid[1]],
                mode="markers+text",
                text=[selected_pov],
                textposition="top center",
                marker=dict(
                    size=20,
                    symbol="x",
                    color=color_map[selected_pov],
                    line=dict(color="black", width=2),
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # ── Layout ──────────────────────────────────────────────────────────
    fig.update_layout(
        title="Stormlight Chapters — PCA Stylometry",
        plot_bgcolor="white",
        hovermode="closest",
        height=750,
        xaxis=dict(
            title=f"PC1 ({meta['pc1_variance']:.1%} variance)",
            zeroline=True,
            zerolinecolor="lightgrey",
            gridcolor="whitesmoke",
        ),
        yaxis=dict(
            title=f"PC2 ({meta['pc2_variance']:.1%} variance)",
            zeroline=True,
            zerolinecolor="lightgrey",
            gridcolor="whitesmoke",
        ),
    )

    return fig