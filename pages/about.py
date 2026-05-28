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
    html.P("Working Together"),
    html.P("This project was a highly collaborative effort from Matt Caputo, Heming Chen, and Violet Hall. The collaboration started in the planning phase where each member was tasked with coming up with the visualizations they thought would give an interesting analysis of the story. Then throughout the workflow all members played parts in each role. During the data finding and cleaning phase Matt was able to make full text documents for each work, cleaning out any unnecessary text. Then all members set to working together to manually break down the text into chapters and some sub chapters by POV character, Title, whether it was a backstory, and the text of the chapter. Matt then took the lead on the data generation, breaking the CSV into more specific elements related to each graphs needs. The next step was the platform. Heming set up the base of the website and designed many of the interactive and structural features for the site. The visualization was a group effort from conception to end with all members helping to write and rewrite the visualization tools. Matt mainly focused on background structure, as he had the knowledge of the analysis tools being presented. Heming took to making these visualizations come alive with interactive features. Violet focused on stylistic elements, ensuring a consistent color palette to push the comprehension of analysis, and make it pretty and accessible. Most of the work for this project was done while sitting in the same room, with each member getting to hold council at their home. So much of what each member created was intricately inspired by and tied to the group as a whole, with constant consultation leading the way to success. ")
])
