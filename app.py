import dash
from dash import Dash, html, dcc
import plotly.graph_objects as go

app = Dash(__name__, suppress_callback_exceptions=True, use_pages=True)

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
                html.A("About", href="/about"), 
            ]
        ),
        dash.page_container
    ]
)

if __name__ == '__main__':
    app.run(debug=True)