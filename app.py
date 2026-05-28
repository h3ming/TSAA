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

# for character graph
min_pos, max_pos = get_chapter_range()
chapter_marks = get_chapter_marks()
character_options = get_character_options()

app = Dash(__name__, suppress_callback_exceptions=True) # some components are created dynamically 



app.layout = html.Div(
    className="app-shell",
    children=[
        # HEADER
        html.Header(
            children=[
            html.H1("Stormlight Archive Archive"),
            html.Img(src=app.get_asset_url('Kaladin.png')),
            html.Img(src=app.get_asset_url('Shallan.png')),
            html.Img(src=app.get_asset_url('Dalinar.png')),
            html.Img(src=app.get_asset_url('Adolin.png')),
            html.Img(src=app.get_asset_url('Eshonai.png')),
            html.Img(src=app.get_asset_url('Szeth.png')),
            ]
        ),
        # NAV
        html.Nav(
            id="navigation-bar",
            children=[
                html.A("Home", href="/"),
                html.A("About", href="/"),  # TODO make+link about page; dash might do this oddly
            ]
        ),
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
                    children=[ 
                        # filter stuff here
                    ]
                ),
                # MAIN CONTENT 
                html.Main(
                    className="main-content",
                    children=[
                        # graph stuff here
                        dcc.Tabs(id='tabs', value='tab1', children=[
                            dcc.Tab(label="graph1", value='tab1', children=[
                                html.P('pca graph'),
                                dcc.Graph(id='pca_graph',
                                          figure=make_pca_figure()),
                            ]),
                            dcc.Tab(label="graph2", value='tab2', children=[
                                html.P('info about graph'),
                                dcc.Graph(id='character_graph',
                                          figure=build_character_graph_figure()),
                                html.H5("Chapter Range"),
                                dcc.RangeSlider(
                                    id="chapter-range",
                                    min=min_pos,
                                    max=max_pos,
                                    value=[min_pos, max_pos],
                                    marks=chapter_marks,
                                    step=100,
                                    allowCross=False
                                )
                            ]),
                            dcc.Tab(label="graph3", value='tab3', children=[
                                html.P('info about graph'),
                                dcc.Graph(),
                            ]),
                        ]),
                    ]
                ),
            ]
        ),
    ]
)

#TODO: callbacks and figs, update_tab function once we have our figs

# ---- Sidebar ------ #
# dynamic depending on which tab is selected
# character dropdown for sentiment, pca, character graph
# also description beneath
@app.callback(
    Output('sidebar', 'children'),
    Input('tabs', 'value')
)
def update_sidebar(active_tab):
    if active_tab == 'tab1':
        return [
            html.H5("POV Character"),
            dcc.Dropdown(
                                id="character-dropdown",
                                options=[
                                    {"label": pov, "value": pov}
                                    for pov in top_povs
                                ],
                                placeholder="All POVs",
                                clearable=True,
                        ),
        ]
    elif active_tab == 'tab2':
        return [
            # html.H5("Highlight Character"),
            # dcc.Dropdown(id="char-highlight"),
            # html.H5("Chapter Range"),
            # dcc.RangeSlider(id="chapter-range")
            html.H5("Highlight Character"),
            dcc.Dropdown(
            id="char-highlight",
            options=character_options,
            value="__all__",
            clearable=False
            ),
        ]
    elif active_tab == 'tab3':
        return []  # fill in later



# ---- PCA GRAPH ---- #
@app.callback(
    Output("pca_graph", "figure"),
    Input("character-dropdown", "value")
)
def update_pca(selected_pov):
    return make_pca_figure(selected_pov)


# ---- CHARACTER GRAPH ---- #
@app.callback(
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


if __name__ == '__main__':
    app.run(debug=True)
