import dash
from dash import html

dash.register_page(__name__, path='/about')

layout = html.Div(className="about-container", children=[ 
    #TODO write the about section
    html.H2("About"),
    html.P("FILLER TEXT the stormlight archives by branderson sanderson each book has 5 parts and there are many narratives character and otherwise " \
    "it seems if i press enter it doesn't actually do it on the page" \
    "but we can still have paragraph breaks if we do this (create a new html.P)"),
    html.P("it is about these things and our data is centred around exploring this and our data is structured like so i'm not sure how much information we want "),
])