"""Plotly figure builder for the Stormlight sentiment trajectory.

Designed for drop-in Dash integration. Reads one CSV once (lru-cached) and
rebuilds a `plotly.graph_objects.Figure` on demand, filtered to a chapter
range and optionally focused on a single POV character.

------------------------------------------------------------------------------
INPUT FILE (expected in `csv_dir`, default `../csv_data`):

    chapters_sentiment.csv         one row per chapter
        narr_pos, book, book_short, chapter_order, heading_id,
        section_type, part_number, pov, heading_text, n_paras,
        compound_mean, compound_std, pos_mean, neg_mean

------------------------------------------------------------------------------
PUBLIC API:

    build_sentiment_figure(start_pos, end_pos, highlight, ...) -> go.Figure
    get_chapter_range(csv_dir)         -> (min_pos, max_pos)
    get_chapter_marks(csv_dir, step)   -> dict for dcc.RangeSlider marks
    get_pov_options(csv_dir)           -> list[dict] for dcc.Dropdown
    get_summary(csv_dir)               -> dict of counts (for header text)

------------------------------------------------------------------------------
DASH USAGE EXAMPLE:

    from dash import Dash, html, dcc, Input, Output
    from sentiment_figure import (
        build_sentiment_figure, get_chapter_range,
        get_chapter_marks, get_pov_options,
    )

    min_pos, max_pos = get_chapter_range()

    app.layout = html.Div([
        dcc.Dropdown(id="pov-highlight", options=get_pov_options(),
                     value="__all__", clearable=False),
        dcc.RangeSlider(id="chapter-range", min=min_pos, max=max_pos,
                        value=[min_pos, max_pos],
                        marks=get_chapter_marks(step=25),
                        step=1, allowCross=False),
        dcc.Graph(id="sentiment-graph", style={"height": "800px"}),
    ])

    @app.callback(
        Output("sentiment-graph", "figure"),
        Input("chapter-range", "value"),
        Input("pov-highlight", "value"),
    )
    def update(rng, highlight):
        return build_sentiment_figure(
            start_pos=rng[0], end_pos=rng[1], highlight=highlight,
        )

Behavior:
    - "All POVs" view: all top-6 character lines drawn at full color, plus the
      grey raw-chapter markers and the micro + macro smoothing lines.
    - Highlight a POV: that character's line goes bold + saturated, all other
      character lines fade to light grey for context.
    - Range slider filters EACH per-book subplot to chapters within the range.
      Smoothing is recomputed on the filtered data so the lines reflect what's
      visible.
"""
from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pcol
from plotly.subplots import make_subplots

DEFAULT_CSV_DIR = Path(__file__).resolve().parent.parent / "figures" /"csv_data"
ALL_VALUE = "__all__"

# Pastel band colors for the 5 Parts (matches the notebook + character graph palette)
PART_COLORS = ["#fde9e9", "#fef3d6", "#e6f4dc", "#e1ecf8", "#f1e8f6"]

BOOK_ORDER = ["The Way of Kings", "Words of Radiance"]


# ── Data loading (cached) ─────────────────────────────────────────────────────
@functools.lru_cache(maxsize=4)
def _load_data(csv_dir_str: str):
    csv_dir = Path(csv_dir_str)
    ch = pd.read_csv(csv_dir / "chapters_sentiment.csv")
    # Top POVs by chapter count (for line drawing + dropdown)
    top_povs = ch["pov"].value_counts().head(6).index.tolist()
    return ch, top_povs


def _resolve_dir(csv_dir) -> str:
    return str(Path(csv_dir).resolve())


# ── Helper accessors ──────────────────────────────────────────────────────────
def get_chapter_range(csv_dir=DEFAULT_CSV_DIR) -> tuple[int, int]:
    """Return (min_narr_pos, max_narr_pos) — for dcc.RangeSlider min/max."""
    ch, _ = _load_data(_resolve_dir(csv_dir))
    return int(ch["narr_pos"].min()), int(ch["narr_pos"].max())


def get_chapter_marks(csv_dir=DEFAULT_CSV_DIR, step: int = 25) -> dict[int, str]:
    """Marks dict for dcc.RangeSlider: positions every `step` chapters + endpoints."""
    ch, _ = _load_data(_resolve_dir(csv_dir))
    min_p = int(ch["narr_pos"].min())
    max_p = int(ch["narr_pos"].max())
    label_at = {
        int(r["narr_pos"]): f"{r['book_short']} #{int(r['chapter_order'])}"
        for _, r in ch.iterrows()
    }
    marks = {p: label_at[p] for p in label_at if (p - min_p) % step == 0}
    marks[min_p] = label_at[min_p]
    marks[max_p] = label_at[max_p]
    return marks


def get_pov_options(csv_dir=DEFAULT_CSV_DIR) -> list[dict]:
    """Dropdown options: 'All POVs' first, then top POVs by chapter count."""
    ch, top_povs = _load_data(_resolve_dir(csv_dir))
    counts = ch["pov"].value_counts()
    options = [{"label": "All POVs", "value": ALL_VALUE}]
    for pov in top_povs:
        options.append({
            "label": f"{pov}  ({int(counts[pov])})",
            "value": pov,
        })
    return options


def get_summary(csv_dir=DEFAULT_CSV_DIR) -> dict:
    """Quick stats for header text."""
    ch, _ = _load_data(_resolve_dir(csv_dir))
    return {
        "n_chapters":    len(ch),
        "n_books":       int(ch["book"].nunique()),
        "min_pos":       int(ch["narr_pos"].min()),
        "max_pos":       int(ch["narr_pos"].max()),
        "min_compound":  float(ch["compound_mean"].min()),
        "max_compound":  float(ch["compound_mean"].max()),
    }


# ── Figure builder ────────────────────────────────────────────────────────────
def build_sentiment_figure(
    start_pos: int | None = None,
    end_pos: int | None = None,
    highlight: str | None = None,
    csv_dir=DEFAULT_CSV_DIR,
    smooth_micro: int = 3,
    smooth_macro: int = 10,
    top_pov_lines: int = 6,
) -> go.Figure:
    """Build the sentiment trajectory figure (2 stacked subplots, one per book).

    Args:
        start_pos:      inclusive minimum narrative position (1-indexed). None → min.
        end_pos:        inclusive maximum narrative position. None → max.
        highlight:      optional POV name. If set, that character's line is bold +
                        saturated; other POV lines fade to grey. Pass None or
                        "__all__" to skip.
        csv_dir:        directory containing chapters_sentiment.csv.
        smooth_micro:   rolling window for the local-arc smoothing line.
        smooth_macro:   rolling window for the broad-arc smoothing line.
        top_pov_lines:  how many POVs to draw individual lines for.

    Returns:
        plotly.graph_objects.Figure ready to plug into `dcc.Graph(figure=...)`.
    """
    ch, top_povs = _load_data(_resolve_dir(csv_dir))

    if highlight in (None, "", ALL_VALUE):
        highlight = None

    # Resolve range
    min_p_avail = int(ch["narr_pos"].min())
    max_p_avail = int(ch["narr_pos"].max())
    s = int(start_pos) if start_pos is not None else min_p_avail
    e = int(end_pos)   if end_pos   is not None else max_p_avail
    if s > e:
        s, e = e, s
    s = max(s, min_p_avail)
    e = min(e, max_p_avail)

    ch_range = ch[(ch["narr_pos"] >= s) & (ch["narr_pos"] <= e)].copy()

    # Palette — share with the rest of the app via plotly's D3 qualitative scheme
    qual = pcol.qualitative.D3

    color_map = {
      "Kaladin": "#43a2fa",
    "Shallan" :"#de5410",
    "Dalinar":"#444c57",
    "Adolin":"#1318a4",
    "Dalinar/Adolin":"#2A2A62",
    "Szeth":"#ebe1c3",
    "Eshonai":"#bd0000",
    "Rysn":"#bfbfbf"
}

    #color_map["Other"] = "#bfbfbf"
    pov_color = color_map

    fig = make_subplots(
        rows=2, cols=1,
        shared_yaxes=True,
        vertical_spacing=0.12,
        subplot_titles=BOOK_ORDER,
    )

    legend_shown: set[str] = set()  # show each legend entry only once across subplots

    for row, book in enumerate(BOOK_ORDER, start=1):
        sub = (ch_range[ch_range["book"] == book]
               .sort_values("chapter_order")
               .reset_index(drop=True))
        if sub.empty:
            continue

        x_axis_id = "x" if row == 1 else f"x{row}"
        y_axis_domain = "y domain" if row == 1 else f"y{row} domain"

        # ── Background: pastel bands per Part ────────────────────────────────
        for part in [1, 2, 3, 4, 5]:
            sp = sub[sub["part_number"] == part]
            if sp.empty:
                continue
            x0 = float(sp["chapter_order"].min() - 0.5)
            x1 = float(sp["chapter_order"].max() + 0.5)
            fig.add_shape(
                type="rect", x0=x0, x1=x1, y0=0, y1=1,
                fillcolor=PART_COLORS[part - 1], opacity=0.5,
                layer="below", line_width=0,
                xref=x_axis_id, yref=y_axis_domain,
            )
            fig.add_annotation(
                x=(x0 + x1) / 2, y=0.97,
                xref=x_axis_id, yref=y_axis_domain,
                text=f"Part {part}", showarrow=False,
                font=dict(size=10, color="#888"),
                xanchor="center", yanchor="top",
            )

        # ── Raw per-chapter markers ──────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=sub["chapter_order"], y=sub["compound_mean"],
            mode="markers", marker=dict(color="#bbb", size=5),
            name="Per-chapter (raw)",
            showlegend=("raw" not in legend_shown),
            legendgroup="raw",
            customdata=np.stack([
                sub["heading_text"].fillna("").astype(str),
                sub["pov"].astype(str),
                sub["n_paras"].astype(int),
            ], axis=-1),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "POV: %{customdata[1]}<br>"
                "compound: %{y:.3f}<br>"
                "paragraphs: %{customdata[2]}<extra></extra>"
            ),
        ), row=row, col=1)
        legend_shown.add("raw")

        # ── Micro + macro smoothing on filtered data ─────────────────────────
        micro = (sub["compound_mean"]
                 .rolling(smooth_micro, center=True, min_periods=1).mean())
        macro = (sub["compound_mean"]
                 .rolling(smooth_macro, center=True, min_periods=1).mean())

        fig.add_trace(go.Scatter(
            x=sub["chapter_order"], y=micro, mode="lines",
            line=dict(color="#555", width=1.4),
            name=f"Micro arc ({smooth_micro}-ch)",
            showlegend=("micro" not in legend_shown),
            legendgroup="micro",
            hoverinfo="skip",
        ), row=row, col=1)
        legend_shown.add("micro")

        fig.add_trace(go.Scatter(
            x=sub["chapter_order"], y=macro, mode="lines",
            line=dict(color="black", width=3),
            name=f"Macro arc ({smooth_macro}-ch)",
            showlegend=("macro" not in legend_shown),
            legendgroup="macro",
            hoverinfo="skip",
        ), row=row, col=1)
        legend_shown.add("macro")

        # ── Per-POV lines (with highlight fade) ──────────────────────────────
        for pov in top_povs[:top_pov_lines]:
            pov_ch = sub[sub["pov"] == pov]
            if len(pov_ch) < 2:
                continue
            is_focus = (highlight is None) or (pov == highlight)
            color = pov_color[pov] if is_focus else "#bfbfbf"
            width = 3.0 if (highlight and pov == highlight) else 1.7
            opacity = 1.0 if is_focus else 0.40

            fig.add_trace(go.Scatter(
                x=pov_ch["chapter_order"], y=pov_ch["compound_mean"],
                mode="lines+markers",
                line=dict(color=color, width=width),
                marker=dict(size=6),
                opacity=opacity,
                name=pov,
                showlegend=(pov not in legend_shown),
                legendgroup=pov,
                customdata=np.stack([
                    pov_ch["heading_text"].fillna("").astype(str),
                    pov_ch["n_paras"].astype(int),
                ], axis=-1),
                hovertemplate=(
                    f"<b>%{{customdata[0]}}</b><br>"
                    f"POV: {pov}<br>"
                    "compound: %{y:.3f}<br>"
                    "paragraphs: %{customdata[1]}<extra></extra>"
                ),
            ), row=row, col=1)
            legend_shown.add(pov)

    # ── Title with range summary ──────────────────────────────────────────────
    label_at = {
        int(r["narr_pos"]): f"{r['book_short']} #{int(r['chapter_order'])}"
        for _, r in ch.iterrows()
    }
    s_label = label_at.get(s, f"#{s}")
    e_label = label_at.get(e, f"#{e}")
    title = f"Sentiment Trajectory · {s_label} → {e_label}"
    if highlight:
        title += f" · highlighting {highlight}"

    fig.update_layout(
        title=dict(text=title, font=dict(size=35)),
        plot_bgcolor="#FCF8EC",
        paper_bgcolor ="#F8C63E",
        height=820, 
        hovermode="closest",
        legend=dict(font=dict(size=10), groupclick="toggleitem"),
        margin=dict(t=80, r=20, b=50, l=60),
        font_family="Times New Roman",
        font_color="#040435",
        title_x=0.5,
    )
    fig.update_yaxes(
        range=[-0.4, 0.4],
        title="VADER compound",
        zeroline=True, zerolinecolor="#999", zerolinewidth=1,
        gridcolor="#eee",
    )
    fig.update_xaxes(
        title="Chapter",
        gridcolor="#eee",
    )

    return fig
