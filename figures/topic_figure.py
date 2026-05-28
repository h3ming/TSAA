"""Plotly figure builder for the Stormlight topic stream graph.

Designed for drop-in Dash integration. Reads two CSVs once (lru-cached) and
rebuilds a `plotly.graph_objects.Figure` on demand, filtered to a chapter
range and optionally focused on a single topic.

------------------------------------------------------------------------------
INPUT FILES (expected in `csv_dir`, default `../csv_data`):

    topic_chapter_counts.csv     sparse long-format counts
        narr_pos, topic_id, count

    topic_meta.csv               one row per topic
        topic_id, label, top_words, total_count, is_catchall, is_outlier

    character_chapter_index.csv  (already used by character_graph_figure +
                                  sentiment_figure) for narr_pos labels.

------------------------------------------------------------------------------
PUBLIC API:

    build_topic_stream_figure(start_pos, end_pos, highlight_topic, ...) -> go.Figure
    get_chapter_range(csv_dir)         -> (min_pos, max_pos)
    get_chapter_marks(csv_dir, step)   -> dict for dcc.RangeSlider marks
    get_topic_options(csv_dir, top_n)  -> list[dict] for dcc.Dropdown
    get_summary(csv_dir)               -> dict of counts (for header text)

------------------------------------------------------------------------------
DASH USAGE EXAMPLE:

    from dash import Dash, html, dcc, Input, Output
    from topic_figure import (
        build_topic_stream_figure, get_chapter_range,
        get_chapter_marks, get_topic_options,
    )

    min_pos, max_pos = get_chapter_range()

    app.layout = html.Div([
        dcc.Dropdown(id="topic-highlight", options=get_topic_options(),
                     value="__all__", clearable=False),
        dcc.RangeSlider(id="chapter-range", min=min_pos, max=max_pos,
                        value=[min_pos, max_pos], marks=get_chapter_marks(step=25),
                        step=1, allowCross=False),
        dcc.Graph(id="topic-stream", style={"height": "640px"}),
    ])

    @app.callback(
        Output("topic-stream", "figure"),
        Input("chapter-range", "value"),
        Input("topic-highlight", "value"),
    )
    def update(rng, highlight):
        return build_topic_stream_figure(
            start_pos=rng[0], end_pos=rng[1], highlight_topic=highlight,
        )

Behavior:
    - "All topics" view: top-N named topics stacked + an "Other topics" grey
      ribbon for the long tail.
    - Highlight a topic: that ribbon stays full color; all others fade to
      light grey for context.
    - Topic 0 (BERTopic catch-all) is excluded by default — set
      `exclude_catchall=False` to include it.
"""
from __future__ import annotations

import functools
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.colors as pcol

DEFAULT_CSV_DIR = Path(__file__).resolve().parent.parent / "figures" / "csv_data"
ALL_VALUE = "__all__"


# ── Data loading (cached) ─────────────────────────────────────────────────────
@functools.lru_cache(maxsize=4)
def _load_data(csv_dir_str: str):
    csv_dir = Path(csv_dir_str)
    counts = pd.read_csv(csv_dir / "topic_chapter_counts.csv")
    meta   = pd.read_csv(csv_dir / "topic_meta.csv")
    chs    = pd.read_csv(csv_dir / "character_chapter_index.csv")

    # Build helpers
    label_at = {
        int(r["narr_pos"]): f"{r['book_short']} #{int(r['chapter_order'])}"
        for _, r in chs.iterrows()
    }
    book_at = {int(r["narr_pos"]): r["book"] for _, r in chs.iterrows()}
    wok_max = int(chs[chs["book"] == "The Way of Kings"]["narr_pos"].max())

    return counts, meta, label_at, book_at, wok_max


def _resolve_dir(csv_dir) -> str:
    return str(Path(csv_dir).resolve())


# ── Helper accessors ──────────────────────────────────────────────────────────
def get_chapter_range(csv_dir=DEFAULT_CSV_DIR) -> tuple[int, int]:
    """(min_narr_pos, max_narr_pos) for dcc.RangeSlider."""
    counts, _, label_at, _, _ = _load_data(_resolve_dir(csv_dir))
    positions = sorted(label_at.keys())
    return positions[0], positions[-1]


def get_chapter_marks(csv_dir=DEFAULT_CSV_DIR, step: int = 25) -> dict[int, str]:
    _, _, label_at, _, _ = _load_data(_resolve_dir(csv_dir))
    min_p = min(label_at)
    max_p = max(label_at)
    marks = {p: label_at[p] for p in label_at if (p - min_p) % step == 0}
    marks[min_p] = label_at[min_p]
    marks[max_p] = label_at[max_p]
    return marks


def get_topic_options(
    csv_dir=DEFAULT_CSV_DIR,
    top_n: int = 20,
    exclude_catchall: bool = True,
) -> list[dict]:
    """Dropdown options sorted by total_count. First entry is 'All topics'."""
    _, meta, _, _, _ = _load_data(_resolve_dir(csv_dir))
    filt = meta[~meta["is_outlier"]]
    if exclude_catchall:
        filt = filt[~filt["is_catchall"]]
    filt = filt.head(top_n)
    options = [{"label": "All topics", "value": ALL_VALUE}]
    for _, r in filt.iterrows():
        options.append({
            "label": f"{r['label']}  ({int(r['total_count'])})",
            "value": int(r["topic_id"]),
        })
    return options


def get_summary(csv_dir=DEFAULT_CSV_DIR) -> dict:
    counts, meta, label_at, _, _ = _load_data(_resolve_dir(csv_dir))
    return {
        "n_topics_total":   int(len(meta)),
        "n_topics_named":   int(meta["label"].apply(lambda s: not s.startswith("#")).sum()),
        "n_topics_named_excl": int(meta[~meta["is_catchall"] & ~meta["is_outlier"]]["label"].apply(
            lambda s: not s.startswith("#")).sum()),
        "n_paragraphs":     int(counts["count"].sum()),
        "n_positions":      int(len(label_at)),
        "min_pos":          int(min(label_at)),
        "max_pos":          int(max(label_at)),
    }


# ── Figure builder ────────────────────────────────────────────────────────────
def build_topic_stream_figure(
    start_pos: int | None = None,
    end_pos: int | None = None,
    highlight_topic: int | str | None = None,
    csv_dir=DEFAULT_CSV_DIR,
    top_n_topics: int = 12,
    exclude_catchall: bool = True,
    smooth_window: int = 5,
    min_paras_per_pos: int = 5,
) -> go.Figure:
    """Build the stream graph of topic flow over the narrative.

    Args:
        start_pos:          inclusive minimum narr_pos. None → corpus min.
        end_pos:            inclusive maximum narr_pos. None → corpus max.
        highlight_topic:    topic_id (int) to emphasize. Pass None or "__all__"
                            to show all topics at full color. When set, all other
                            ribbons fade to grey.
        csv_dir:            directory containing the input CSVs.
        top_n_topics:       number of topics drawn as named ribbons. Rest collapse
                            into a grey "Other topics" ribbon.
        exclude_catchall:   drop Topic 0 (BERTopic\'s residual catch-all).
        smooth_window:      rolling-mean window applied per-book before normalizing.
        min_paras_per_pos:  positions below this many topic-tagged paragraphs
                            render as gaps in the stream.

    Returns:
        plotly.graph_objects.Figure ready for `dcc.Graph(figure=...)`.
    """
    counts, meta, label_at, book_at, wok_max = _load_data(_resolve_dir(csv_dir))

    # Normalize args
    if highlight_topic in (None, "", ALL_VALUE):
        highlight = None
    else:
        try:
            highlight = int(highlight_topic)
        except (TypeError, ValueError):
            highlight = None

    min_p_avail = min(label_at)
    max_p_avail = max(label_at)
    s = int(start_pos) if start_pos is not None else min_p_avail
    e = int(end_pos)   if end_pos   is not None else max_p_avail
    if s > e:
        s, e = e, s
    s = max(s, min_p_avail)
    e = min(e, max_p_avail)

    # Filter counts to range
    counts_in = counts[(counts["narr_pos"] >= s) & (counts["narr_pos"] <= e)].copy()
    # Drop outliers (-1) and optionally catchall (0)
    counts_in = counts_in[counts_in["topic_id"] != -1]
    if exclude_catchall:
        counts_in = counts_in[counts_in["topic_id"] != 0]

    # Pivot to chapter × topic matrix
    if counts_in.empty:
        return _empty_figure(s, e, label_at)
    ct = counts_in.pivot(index="narr_pos", columns="topic_id", values="count").fillna(0)

    # Reindex to every position in [s, e] so the smoothing doesn't skip gaps
    full_index = list(range(s, e + 1))
    ct = ct.reindex(full_index, fill_value=0)

    # Pick top-N topics by sum within the visible range
    topic_totals = ct.sum(axis=0).sort_values(ascending=False)
    top_topics = topic_totals.head(top_n_topics).index.tolist()
    ct_top = ct[top_topics].copy()
    ct_top["__other__"] = ct.drop(columns=top_topics).sum(axis=1)

    # Per-book smoothing
    book_series = pd.Series(book_at)
    ct_top["book"] = ct_top.index.map(book_series.to_dict())
    smooth_parts = []
    for book, group in ct_top.groupby("book", sort=False):
        g_data = group.drop(columns="book")
        smooth_parts.append(
            g_data.rolling(window=smooth_window, center=True, min_periods=1).mean()
        )
    ct_smooth = pd.concat(smooth_parts).sort_index()

    # Min-paragraph filter
    raw_totals = ct.sum(axis=1)
    low_mask = raw_totals < min_paras_per_pos
    ct_smooth.loc[low_mask] = np.nan

    # Normalize per chapter
    totals = ct_smooth.sum(axis=1).replace(0, np.nan)
    ct_norm = ct_smooth.div(totals, axis=0)

    # Sort topics by peak position
    peak_pos = {}
    for tid in top_topics:
        series = ct_norm[tid].dropna()
        peak_pos[tid] = int(series.idxmax()) if not series.empty else 0
    top_topics_sorted = sorted(top_topics, key=lambda t: peak_pos[t])

    # ── Build figure ──────────────────────────────────────────────────────────
    fig = go.Figure()
    palette = (
        pcol.qualitative.D3
        + ["#9467bd", "#c49c94"]
        + pcol.qualitative.Pastel
    )

    label_lookup = dict(zip(meta["topic_id"], meta["label"]))
    words_lookup = dict(zip(meta["topic_id"], meta["top_words"]))

    for i, tid in enumerate(top_topics_sorted):
        label = label_lookup.get(tid, f"Topic {tid}")
        top_words = (words_lookup.get(tid) or "").replace("|", ", ")
        # If highlighting, fade non-highlighted; otherwise full color
        if highlight is not None and tid != highlight:
            color = "rgba(190,190,195,0.55)"   # fade
        else:
            color = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=ct_norm.index, y=ct_norm[tid] * 100,
            mode="lines", stackgroup="one",
            line=dict(width=0.5, color="rgba(255,255,255,0.55)"),
            fillcolor=color,
            name=label,
            customdata=ct_smooth[tid].fillna(0).round(1).values.reshape(-1, 1),
            hovertemplate=(
                f"<b>{label}</b><br>"
                f"Top words: {top_words}<br>"
                "Position: %{x}<br>"
                "Share: %{y:.1f}%<br>"
                "Smoothed paragraph count: %{customdata[0]:.1f}"
                "<extra></extra>"
            ),
        ))

    # "Other topics"
    other_color = "rgba(220,220,225,0.7)" if highlight else "rgba(180,180,200,0.7)"
    fig.add_trace(go.Scatter(
        x=ct_norm.index, y=ct_norm["__other__"] * 100,
        mode="lines", stackgroup="one",
        line=dict(width=0.5, color="rgba(255,255,255,0.55)"),
        fillcolor=other_color,
        name=f"Other topics",
        hovertemplate=(
            "<b>Other topics</b><br>"
            "Position: %{x}<br>"
            "Share: %{y:.1f}%<extra></extra>"
        ),
    ))

    # WoK / WoR transition (only if range spans it)
    if s <= wok_max < e:
        fig.add_vline(x=wok_max + 0.5,
                      line=dict(color="#222", dash="dash", width=1.5))
        fig.add_annotation(
            x=wok_max + 0.5, y=1.02, yref="paper",
            text="WoR begins", showarrow=False,
            font=dict(size=11, color="#444"),
            xanchor="left", yanchor="bottom",
        )

    # Title
    s_label = label_at.get(s, f"#{s}")
    e_label = label_at.get(e, f"#{e}")
    title = f"Topic flow · {s_label} → {e_label}"
    if highlight is not None:
        hl_label = label_lookup.get(highlight, f"Topic {highlight}")
        title += f" · highlighting {hl_label}"

    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        width=None, height=620,
        plot_bgcolor="white",
        hovermode="closest",
        legend=dict(font=dict(size=10), traceorder="reversed"),
        margin=dict(t=60, r=20, b=50, l=60),
    )
    fig.update_xaxes(
        title="Narrative position",
        range=[s, e], gridcolor="#eee",
    )
    fig.update_yaxes(
        title="Share of chapter's topic-tagged paragraphs",
        range=[0, 100], ticksuffix="%", gridcolor="#eee",
    )
    return fig


def _empty_figure(s: int, e: int, label_at: dict) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=f"No topic-tagged paragraphs in range {label_at.get(s, s)} – {label_at.get(e, e)}",
        plot_bgcolor="white",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
