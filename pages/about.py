import dash
from dash import html

dash.register_page(__name__, path='/about')

layout = html.Div(style={'padding': '2rem'}, children=[
    html.H2("About"),
    html.P("Write your description here...")
])