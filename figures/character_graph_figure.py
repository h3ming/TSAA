"""Plotly figure builder for the Stormlight character interaction network.

Designed for drop-in Dash integration. Reads three CSVs once (lru-cached) and
rebuilds a `plotly.graph_objects.Figure` on demand, filtered to a chapter range
and optionally focused on a single character's ego network.

------------------------------------------------------------------------------
INPUT FILES (expected in `csv_dir`, default `../csv_data`):

    character_nodes.csv          one row per character
        character, mentions, community, color_hex, x, y,
        degree_combined, degree_wok, degree_wor,
        weighted_degree, betweenness, eigenvector

    character_edges.csv          one row per pair
        source, target,
        weight_total, weight_wok, weight_wor,
        chapters         ← ';'-delimited narrative positions
        n_chapters

    character_chapter_index.csv  one row per narrative position
        narr_pos, book, book_short, chapter_order, label, heading_text

------------------------------------------------------------------------------
PUBLIC API:

    build_character_graph_figure(start_pos, end_pos, highlight, selected_node, ...)
                                       -> go.Figure
    selection_from_click(click_data, prev, triggered_by_click)
                                       -> str | None  (click-toggle helper)
    get_chapter_range(csv_dir)         -> (min_pos, max_pos)
    get_chapter_marks(csv_dir, step)   -> dict for dcc.RangeSlider marks
    get_character_options(csv_dir)     -> list[dict] for dcc.Dropdown options
    get_summary(csv_dir)               -> dict of counts (for header text)

------------------------------------------------------------------------------
DASH USAGE EXAMPLE (with click-to-toggle deselection):

    from dash import Dash, html, dcc, Input, Output, State, ctx
    from character_graph_figure import (
        build_character_graph_figure, selection_from_click,
        get_chapter_range, get_chapter_marks, get_character_options,
    )

    min_pos, max_pos = get_chapter_range()

    app.layout = html.Div([
        dcc.Dropdown(
            id="char-highlight",
            options=get_character_options(),
            value="__all__", clearable=False,
        ),
        dcc.RangeSlider(
            id="chapter-range",
            min=min_pos, max=max_pos, value=[min_pos, max_pos],
            marks=get_chapter_marks(step=25),
            step=1, allowCross=False,
        ),
        dcc.Graph(id="char-graph", style={"height": "780px"}),
        # Holds the currently-selected character across renders.
        dcc.Store(id="selection-store", data=None),
    ])

    @app.callback(
        Output("char-graph", "figure"),
        Output("selection-store", "data"),
        Input("chapter-range", "value"),
        Input("char-highlight", "value"),
        Input("char-graph", "clickData"),
        State("selection-store", "data"),
    )
    def update(rng, highlight, click_data, prev_selection):
        selected = selection_from_click(
            click_data, prev_selection,
            triggered_by_click=(ctx.triggered_id == "char-graph"),
        )
        fig = build_character_graph_figure(
            start_pos=rng[0], end_pos=rng[1],
            highlight=highlight, selected_node=selected,
        )
        return fig, selected

Behavior:
    - Click a node       → that node becomes selected (red ring + top-5 box)
    - Click the same node again → deselects (box disappears)
    - Click a different node    → selects the new one
    - Move the slider / change highlight → selection persists
"""
from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

# csv_data lives at the repo root; this module lives one level down (code/).
DEFAULT_CSV_DIR = Path(__file__).resolve().parent.parent / "csv_data"

ALL_VALUE = "__all__"


# ── Data loading (cached) ─────────────────────────────────────────────────────
@functools.lru_cache(maxsize=4)
def _load_data(csv_dir_str: str):
    csv_dir = Path(csv_dir_str)
    nodes = pd.read_csv(csv_dir / "character_nodes.csv")
    edges = pd.read_csv(csv_dir / "character_edges.csv")
    chs   = pd.read_csv(csv_dir / "character_chapter_index.csv")

    # Pre-parse `chapters` strings into frozensets for O(1) intersection lookups.
    edges["chapter_set"] = edges["chapters"].apply(
        lambda s: frozenset(int(x) for x in str(s).split(";") if x)
    )
    return nodes, edges, chs


def _resolve_dir(csv_dir) -> str:
    return str(Path(csv_dir).resolve())


# ── Helper accessors ──────────────────────────────────────────────────────────
def get_chapter_range(csv_dir=DEFAULT_CSV_DIR) -> tuple[int, int]:
    """Return (min_narr_pos, max_narr_pos)."""
    _, _, chs = _load_data(_resolve_dir(csv_dir))
    return int(chs["narr_pos"].min()), int(chs["narr_pos"].max())


def get_chapter_marks(csv_dir=DEFAULT_CSV_DIR, step: int = 25) -> dict[int, str]:
    """Marks dict for dcc.RangeSlider: positions every `step` chapters + endpoints."""
    _, _, chs = _load_data(_resolve_dir(csv_dir))
    min_p, max_p = int(chs["narr_pos"].min()), int(chs["narr_pos"].max())
    label_at = dict(zip(chs["narr_pos"], chs["label"]))
    marks = {p: label_at[p] for p in label_at if (p - min_p) % step == 0}
    marks[min_p] = label_at[min_p]
    marks[max_p] = label_at[max_p]
    return marks


def get_character_options(csv_dir=DEFAULT_CSV_DIR) -> list[dict]:
    """Dropdown options sorted by weighted degree. First entry is 'All characters'."""
    nodes, _, _ = _load_data(_resolve_dir(csv_dir))
    options = [{"label": "All characters", "value": ALL_VALUE}]
    for _, r in nodes.iterrows():
        options.append({
            "label": f"{r['character']}  ({int(r['weighted_degree'])})",
            "value": r["character"],
        })
    return options


def selection_from_click(
    click_data,
    prev_selection: str | None,
    triggered_by_click: bool,
) -> str | None:
    """Resolve the new `selected_node` value for a Dash callback.

    Implements click-to-toggle: clicking a node selects it; clicking the same
    node again deselects (returns None). Slider/dropdown changes leave the
    selection untouched.

    Args:
        click_data:         The `clickData` Input value from `dcc.Graph`.
        prev_selection:     The previous selection (from a `dcc.Store` via State).
        triggered_by_click: True if this callback was triggered by the graph
                            click input (typically `ctx.triggered_id == "char-graph"`).
                            False for any other input — we then preserve the
                            existing selection.

    Returns:
        The new selection (a character name), or None if no selection.
    """
    if not triggered_by_click:
        return prev_selection
    if not click_data or not click_data.get("points"):
        return prev_selection
    cd = click_data["points"][0].get("customdata")
    if not cd:
        return prev_selection
    clicked = cd[0]
    # Toggle off if clicking the same node again
    return None if clicked == prev_selection else clicked


def get_summary(csv_dir=DEFAULT_CSV_DIR) -> dict:
    """Quick stats for header text."""
    nodes, edges, chs = _load_data(_resolve_dir(csv_dir))
    return {
        "n_characters":   len(nodes),
        "n_edges":        len(edges),
        "n_positions":    len(chs),
        "min_pos":        int(chs["narr_pos"].min()),
        "max_pos":        int(chs["narr_pos"].max()),
        "n_communities":  int(nodes["community"].nunique()),
    }


# ── Figure builder ────────────────────────────────────────────────────────────
def build_character_graph_figure(
    start_pos: int | None = None,
    end_pos: int | None = None,
    highlight: str | None = None,
    selected_node: str | None = None,
    csv_dir=DEFAULT_CSV_DIR,
    label_top_k: int = 15,
    top_edges_k: int = 5,
) -> go.Figure:
    """Build the Stormlight character network figure.

    Args:
        start_pos:    inclusive minimum narrative position (1-indexed). None → min.
        end_pos:      inclusive maximum narrative position. None → max.
        highlight:    optional character name. If set, shows the ego network
                      (only edges touching this character). Pass None or "__all__"
                      to skip.
        selected_node: optional character name (typically from a `clickData`
                      callback). When set, that character's top-K strongest edges
                      in the current range are emphasized in red and listed in
                      an info box pinned to the top-right of the figure.
        csv_dir:      directory containing the three CSVs.
        label_top_k:  number of nodes to label, ranked by in-range weighted degree.
        top_edges_k:  number of edges to emphasize/list for `selected_node`.

    Returns:
        plotly.graph_objects.Figure ready to plug into `dcc.Graph(figure=...)`.
    """
    nodes, edges, chs = _load_data(_resolve_dir(csv_dir))

    # ── Normalize args ────────────────────────────────────────────────────────
    min_p_avail = int(chs["narr_pos"].min())
    max_p_avail = int(chs["narr_pos"].max())
    s = int(start_pos) if start_pos is not None else min_p_avail
    e = int(end_pos)   if end_pos   is not None else max_p_avail
    if s > e:
        s, e = e, s
    s = max(s, min_p_avail)
    e = min(e, max_p_avail)

    if highlight in (None, "", ALL_VALUE):
        highlight = None
    if selected_node in (None, "", ALL_VALUE):
        selected_node = None

    # ── Filter edges by chapter overlap ───────────────────────────────────────
    range_set = frozenset(range(s, e + 1))
    edges_in = edges[edges["chapter_set"].apply(
        lambda cs: not cs.isdisjoint(range_set)
    )].copy()
    edges_in["weight_in_range"] = edges_in["chapter_set"].apply(
        lambda cs: len(cs & range_set)
    )

    # ── Ego network if highlighting ──────────────────────────────────────────
    if highlight:
        is_inc = (edges_in["source"] == highlight) | (edges_in["target"] == highlight)
        edges_in = edges_in[is_inc]

    # ── Find visible nodes ────────────────────────────────────────────────────
    visible = set(edges_in["source"]) | set(edges_in["target"])
    if highlight:
        visible.add(highlight)
    nodes_in = nodes[nodes["character"].isin(visible)].copy()

    # Per-range weighted degree → drives label selection & node size
    deg_in_range: dict[str, int] = {}
    for _, r in edges_in.iterrows():
        deg_in_range[r["source"]] = deg_in_range.get(r["source"], 0) + int(r["weight_in_range"])
        deg_in_range[r["target"]] = deg_in_range.get(r["target"], 0) + int(r["weight_in_range"])
    nodes_in["weight_in_range"] = (
        nodes_in["character"].map(deg_in_range).fillna(0).astype(int)
    )

    fig = go.Figure()

    # ── Empty-state fallback ──────────────────────────────────────────────────
    if nodes_in.empty:
        fig.update_layout(
            title=f"No interactions in selected range ({s} – {e})",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor="white",
            margin=dict(t=60, r=20, b=20, l=20),
        )
        return fig

    pos = {row["character"]: (row["x"], row["y"]) for _, row in nodes_in.iterrows()}

    # ── Edges in three thickness tiers (so structure pops without overplotting)
    if len(edges_in):
        max_w = max(int(edges_in["weight_in_range"].max()), 1)
        tiers = [
            (0, max_w / 3,         0.6, "rgba(150,150,155,0.20)"),
            (max_w / 3, 2 * max_w / 3, 1.4, "rgba(110,110,120,0.40)"),
            (2 * max_w / 3, max_w + 1, 2.6, "rgba(60,60,75,0.60)"),
        ]
        for lo, hi, width, rgba in tiers:
            tier_edges = edges_in[
                (edges_in["weight_in_range"] > lo) &
                (edges_in["weight_in_range"] <= hi)
            ]
            ex, ey = [], []
            for _, r in tier_edges.iterrows():
                if r["source"] not in pos or r["target"] not in pos:
                    continue
                x0, y0 = pos[r["source"]]
                x1, y1 = pos[r["target"]]
                ex += [x0, x1, None]
                ey += [y0, y1, None]
            if ex:
                fig.add_trace(go.Scatter(
                    x=ex, y=ey, mode="lines",
                    line=dict(color=rgba, width=width),
                    hoverinfo="skip", showlegend=False,
                ))

    # ── Selected node: compute + emphasize its top-K strongest edges ─────────
    selected_top_edges: list[dict] = []
    if selected_node and selected_node in visible:
        node_rows = edges_in[
            (edges_in["source"] == selected_node) |
            (edges_in["target"] == selected_node)
        ].sort_values("weight_in_range", ascending=False).head(top_edges_k)

        ex, ey = [], []
        for _, r in node_rows.iterrows():
            other = r["target"] if r["source"] == selected_node else r["source"]
            if selected_node not in pos or other not in pos:
                continue
            x0, y0 = pos[selected_node]
            x1, y1 = pos[other]
            ex += [x0, x1, None]
            ey += [y0, y1, None]
            selected_top_edges.append({
                "other": other,
                "weight_in_range": int(r["weight_in_range"]),
                "weight_total": int(r["weight_total"]),
            })
        if ex:
            fig.add_trace(go.Scatter(
                x=ex, y=ey, mode="lines",
                line=dict(color="#d62728", width=3.5),
                hoverinfo="skip", showlegend=False,
            ))

    # ── Node labels: top K by in-range weight ────────────────────────────────
    ranked = nodes_in.sort_values("weight_in_range", ascending=False)
    label_set = set(ranked.head(label_top_k)["character"].tolist())
    if highlight:
        label_set.add(highlight)
    labels = [n if n in label_set else "" for n in nodes_in["character"]]

    # Node size from total combined degree (visual stability across ranges)
    sizes = [8 + 0.55 * int(d) for d in nodes_in["degree_combined"]]

    # Ring styling: selected_node wins (red), then highlight (black), else white
    line_widths = [
        3.5 if (selected_node and n == selected_node) else
        2.6 if (highlight and n == highlight) else 1.0
        for n in nodes_in["character"]
    ]
    line_colors = [
        "#d62728" if (selected_node and n == selected_node) else
        "black"   if (highlight and n == highlight) else "white"
        for n in nodes_in["character"]
    ]
    # Ensure the selected node also gets a labeled marker even if not in top-K
    if selected_node:
        label_set.add(selected_node)
        labels = [n if n in label_set else "" for n in nodes_in["character"]]

    fig.add_trace(go.Scatter(
        x=nodes_in["x"], y=nodes_in["y"], mode="markers+text",
        text=labels,
        textposition="top center",
        textfont=dict(size=10, color="#222"),
        marker=dict(
            size=sizes,
            color=nodes_in["color_hex"],
            line=dict(color=line_colors, width=line_widths),
        ),
        customdata=nodes_in[[
            "character", "mentions", "community",
            "weighted_degree", "weight_in_range", "degree_combined",
        ]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Mentions: %{customdata[1]}<br>"
            "Community: %{customdata[2]}<br>"
            "Connections: %{customdata[5]}<br>"
            "Total weight: %{customdata[3]}<br>"
            "Weight in range: %{customdata[4]}<extra></extra>"
        ),
        showlegend=False,
    ))

    # ── Title & layout ────────────────────────────────────────────────────────
    label_at = dict(zip(chs["narr_pos"], chs["label"]))
    s_label = label_at.get(s, f"#{s}")
    e_label = label_at.get(e, f"#{e}")
    title = f"Character interactions · {s_label} → {e_label}"
    if highlight:
        title += f" · ego network of {highlight}"
    title += f"  ·  n={len(nodes_in)} chars, m={len(edges_in)} edges"

    # ── Info-box annotation for the selected node's top edges ───────────────
    annotations = []
    if selected_top_edges:
        width = max(len(t["other"]) for t in selected_top_edges)
        lines = [f"<b>Top {len(selected_top_edges)} edges · {selected_node}</b>"]
        for t in selected_top_edges:
            name = t["other"].ljust(width)
            lines.append(
                f"{name}  · {t['weight_in_range']} ch in range"
                f" ({t['weight_total']} total)"
            )
        annotations.append(dict(
            text="<br>".join(lines),
            xref="paper", yref="paper",
            x=0.99, y=0.99, xanchor="right", yanchor="top",
            showarrow=False, align="left",
            font=dict(size=11, color="#222", family="monospace"),
            bgcolor="rgba(255,255,255,0.94)",
            bordercolor="#d62728", borderwidth=1.5, borderpad=10,
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        plot_bgcolor="white",
        margin=dict(t=60, r=20, b=20, l=20),
        hovermode="closest",
        showlegend=False,
        annotations=annotations,
        clickmode="event+select",
    )
    return fig
