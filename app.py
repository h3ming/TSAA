from dash import Dash, html, dcc, Input, Output
import plotly.graph_objects as go
import plotly.express as px
from figures.pca_plot import make_pca_figure, top_povs

app = Dash(__name__)



app.layout = html.Div(
    className="app-shell",
    children=[
        # HEADER
        html.Header(
            html.H1("Stormlight Archive Archive")
        ),
        # NAV
        html.Nav(
            id="navigation-bar",
            children=[
                html.A("Home", href="/"),
                html.A("About", href="/"),  # TODO make+link about page; dash might do this oddly
            ]
        ),
        # BODY
        html.Div(
            className="body",
            children=[
                # SIDEBAR
                html.Div(
                    className="sidebar",
                    children=[
                        # filter stuff here
                        html.H5("Character"), 
                        dcc.Dropdown(
                                id="character-dropdown",
                                options=[
                                    {"label": pov, "value": pov}
                                    for pov in top_povs
                                ],
                                placeholder="All POVs",
                                clearable=True,
                        ),
                        html.H5("Book section"),
                        dcc.Dropdown(),
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
                                dcc.Graph(),
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
@app.callback(
    Output("pca_graph", "figure"),
    Input("character-dropdown", "value")
)
def update_pca(selected_pov):
    return make_pca_figure(selected_pov)

if __name__ == '__main__':
    app.run(debug=True)
