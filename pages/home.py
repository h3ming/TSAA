import dash
from dash import Dash, html, dcc, Input, Output, State, ctx
import plotly.graph_objects as go
import plotly.express as px

from figures.pca_plot import make_pca_figure, top_povs
from figures.character_graph_figure import (
    build_character_graph_figure,
    selection_from_click,
    get_chapter_range,
    get_chapter_marks,
    get_character_options,
)
from figures.sentiment_figure import (
    build_sentiment_figure,
    get_pov_options,
)
from figures.sentiment_figure import _load_data as _load_sentiment_data, DEFAULT_CSV_DIR as SENTIMENT_CSV_DIR
from figures.topic_figure import build_topic_stream_figure, get_topic_options
from pathlib import Path

# Build part marks from sentiment CSV
_ch, _ = _load_sentiment_data(str(Path(SENTIMENT_CSV_DIR).resolve()))
part_marks = {}
for book_short in ['WoK', 'WoR']:
    book_chs = _ch[_ch['book_short'] == book_short]
    for part in range(1, 6):
        part_chs = book_chs[book_chs['part_number'] == part]
        if not part_chs.empty:
            pos = int(part_chs['narr_pos'].min())
            part_marks[pos] = f"{book_short} P{part}"


# for character graph
min_pos, max_pos = get_chapter_range()
chapter_marks = get_chapter_marks(step=50) #set step=50 to fix overcrowding on the timeline
character_options = get_character_options()

# for sentiment graph
# Smin_pos, Smax_pos = get_sentiment_chapter_range()
# Schapter_marks = get_sentiment_chapter_marks()
Scharacter_options = get_pov_options()

topic_options = get_topic_options()


dash.register_page(__name__, path='/')



layout = html.Div(
    className="app-shell",
    children=[
        # store
        dcc.Store(id="selection-store", data=None),
        # BODY
        html.Div(
            className="body",
            children=[
                # SIDEBAR
                html.Div(
                    className="sidebar",
                    id="sidebar",
                    children=[]
                ),
                # MAIN CONTENT 
                html.Main(
                    className="main-content",
                    children=[
                        # graph stuff here
                        dcc.Tabs(id='tabs', value='tab1', children=[
                            dcc.Tab(label="PCA Stylometry", value='tab1', children=[
                                dcc.Graph(id='pca_graph',
                                          figure=make_pca_figure()),
                                          #TODO matt if there isn't enough space on the side bar 
                                          # you can also write the main description down here and maybe put interesting things to look at
                                          # on the side bar instead. 
                                          html.P("", style={"lineHeight": "1.5"}),
                            ]),
                            dcc.Tab(label="Character Interactions", value='tab2', children=[
                                dcc.Graph(id='character_graph',
                                          figure=build_character_graph_figure()),
                                html.H5("Chapter Range", style={"text-align": "center"}),
                                dcc.RangeSlider(
                                    id="chapter-range",
                                    min=min_pos,
                                    max=max_pos,
                                    value=[min_pos, max_pos],
                                    marks=part_marks,
                                    step=1,
                                    allowCross=False,
                                ),
                                #TODO similar case here
                                html.Hr(),
                                html.P("")
                            ]),
                            dcc.Tab(label="Sentiment Analysis", value='tab3', children=[
                                dcc.Graph( id='sentiment_graph',
                                        figure=build_sentiment_figure()),
                                #TODO here
                                html.P('')
                            ]),
                            dcc.Tab(label="Topics over Time", value='tab4', children=[
                                dcc.Graph(id='topics_graph',
                                          figure=build_topic_stream_figure()),
                                #TODO here
                                html.P('')
                            ]),
                        ]),
                    ]
                ),
            ]
        ),
    ]
)

# ---- Sidebar ------ #
# dynamic depending on which tab is selected
# character dropdown for sentiment, pca, character graph
# also description beneath
@dash.callback(
    Output('sidebar', 'children'),
    Input('tabs', 'value')
)
def update_sidebar(active_tab):
    if active_tab == 'tab1':
        return [
            html.H3("POV Character"),
            dcc.Dropdown(
                id="character-dropdown",
                options=[
                    {"label": pov, "value": pov}
                    for pov in top_povs
                ],
                placeholder="All POVs",
                clearable=True,
            ), #TODO
            html.H3("PCA Graph"),
            html.P("This stylometric analysis tracks the ways that Sanderson’s prose shifts between chapters. Each chapter is represented by a dot in the graph, colored by the primary point of view character of that chapter. To see more information about a specific dot, mouse over it! For a detailed explanation of the analytical process, please refer to the “about” page."),
        ]
    elif active_tab == 'tab2':
        return [
            html.H3("Highlight Character"),
            dcc.Dropdown(
                id="char-highlight",
                options=character_options,
                value="__all__",
                clearable=False
            ), #TODO
            html.H3("Character graph"),
            html.P("This character interaction graph tracks which characters interact with who. Whenever two characters' names are used in the same chapter, it is logged as an interaction! To see a given character's most common interactions, click on their dot! Feel free to adjust the timeline to see how communities evolve across the two books. For a detailed explanation of the analytical process, please refer to the “about” page.")
        ]
    elif active_tab == 'tab3':
        return [
            html.H3("POV Character"),
            dcc.Dropdown(
                id="Scharacter-dropdown",
                options=Scharacter_options,
                value="__all__",
                clearable=False
            ), #TODO
            html.H3("Sentiment"),
            html.P("This sentiment analysis chart tracks the usage of words that carry positive or negative sentiment. If a chapter has positive sentiment, it is given a positive value. Negative sentiment gets a negative value. The black lines track the average sentiment regardless of PoV character. Take a look at how the sentiment arcs of the two books compare to each other! For a detailed explanation of the analytical process, please refer to the “about” page.")
        ]  # fill in later
    elif active_tab == 'tab4':
        return [ #TODO 
            html.H5("Display Options"),
            dcc.Checklist(
                id="topic-display-options",
                options=[{"label": " Show book parts", "value": "show_parts"}],
                value=["show_parts"]
            ),
            html.H3("Topics"),
            html.P("This topic ribon chart shows the listed topics prevelance at given points in the books. You can see how some topics commonly go together, how some are introduced later in the books, and how some fade away. For a detailed explanation of the analytical process, please refer to the “about” page.")
        ]



# ---- PCA GRAPH ---- #
@dash.callback(
    Output("pca_graph", "figure"),
    Input("character-dropdown", "value")
)
def update_pca(selected_pov):
    return make_pca_figure(selected_pov)


# ---- CHARACTER GRAPH ---- #
@dash.callback(
    Output("character_graph", "figure"),
    Output("selection-store", "data"),
    Input("chapter-range", "value"),
    Input("char-highlight", "value"),
    Input("character_graph", "clickData"),
    State("selection-store", "data"),
    prevent_initial_call=True
)
def update_character_graph(rng, highlight, click_data, prev_selection):
    selected = selection_from_click(
        click_data, prev_selection,
        triggered_by_click=(ctx.triggered_id == "character_graph"),
    )
    fig = build_character_graph_figure(
        start_pos=rng[0], end_pos=rng[1],
        highlight=highlight, selected_node=selected,
    )
    return fig, selected

# ------- SENTIMENT GRAPH -------- #
@dash.callback(
    Output("sentiment_graph", "figure"),
    Input("Scharacter-dropdown", "value"),
    prevent_initial_call=True
)
def update_sentiment_graph(highlight):
    return build_sentiment_figure(highlight=highlight)


# ---------- TOPICS GRAPH ---------- #
# checkbox that shows the part lines and doesn't redraw the entire graph each time it is clicked
@dash.callback(
    Output("topics_graph", "figure"),
    Input("topic-display-options", "value"),
    State("topics_graph", "figure"),
)
def update_topics_graph(display_options, current_figure):
    if current_figure is None:
        fig = build_topic_stream_figure()
    else:
        fig = go.Figure(current_figure)
        
        # remove only part line shapes, keep WoR line
        part_positions = set(part_marks.keys())
        fig.layout.shapes = [
            s for s in (fig.layout.shapes or [])
            if getattr(s, 'x0', None) not in part_positions
        ]
        
        # remove only part annotations, keep WoR annotation
        fig.layout.annotations = [
            a for a in (fig.layout.annotations or [])
            if not any(p in str(getattr(a, 'text', '')) for p in ['WoK P', 'WoR P'])
        ]

    if "show_parts" in (display_options or []):
        for pos, label in part_marks.items():
            fig.add_vline(
                x=pos,
                line=dict(color="#888", dash="dot", width=1),
                annotation_text=label,
                annotation_position="top",
                annotation_font=dict(size=10, color="#555")
            )
    
    return fig
