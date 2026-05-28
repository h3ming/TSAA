import dash
from dash import Dash, html, dcc
import plotly.graph_objects as go

app = Dash(__name__, suppress_callback_exceptions=True, use_pages=True)

server = app.server 

app.layout = html.Div(
    className="app-shell",
    children=[
        # HEADER
        html.Header(
            children=[
            html.H1("Stormlight Archive Archive"),
            html.Img(src=app.get_asset_url('Kaladin.png'), title="Kaladin"),
            html.Img(src=app.get_asset_url('Shallan.png'),title="Shallan"),
            html.Img(src=app.get_asset_url('Dalinar.png'),title="Dalinar"),
            html.Img(src=app.get_asset_url('Adolin.png'),title="Adolin"),
            html.Img(src=app.get_asset_url('Eshonai.png'),title="Eshonai"),
            html.Img(src=app.get_asset_url('Szeth.png'),title="Szeth"),
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