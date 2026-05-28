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
    html.P("This project was a highly collaborative effort from Matt Caputo, Heming Chen, and Violet Hall. The collaboration started in the planning phase where each member was tasked with coming up with the visualizations they thought would give an interesting analysis of the story. Then throughout the workflow all members played parts in each role. During the data finding and cleaning phase Matt was able to make full text documents for each work, cleaning out any unnecessary text. Then all members set to working together to manually break down the text into chapters and some sub chapters by POV character, Title, whether it was a backstory, and the text of the chapter. Matt then took the lead on the data generation, breaking the CSV into more specific elements related to each graphs needs. The next step was the platform. Heming set up the base of the website and designed many of the interactive and structural features for the site. The visualization was a group effort from conception to end with all members helping to write and rewrite the visualization tools. Matt mainly focused on background structure, as he had the knowledge of the analysis tools being presented. Heming took to making these visualizations come alive with interactive features. Violet focused on stylistic elements, ensuring a consistent color palette to push the comprehension of analysis, and make it pretty and accessible. Most of the work for this project was done while sitting in the same room, with each member getting to hold council at their home. So much of what each member created was intricately inspired by and tied to the group as a whole, with constant consultation leading the way to success. "),
    html.H2("Characters (Images From Left to Right)"),
     html.H3("Kaladin Stormblessed"),
     html.P("Kaladin is the son of a surgeon hardened by the deaths of so many he has tried to protect. He is a great warrior who became a hero, learning to put others before himself and life before death."),
     html.P("Kaladin becomes enchanced with great power from a mystical Spren named Syl, who helps him fly high and destroy those who wish to harm those he loves."),
     html.H3("Shallan Davar"),
     html.P("Shallan is the artist daughter of a nobleman . She is haunted by the deaths of her parents and her part in them. She travels to work with the King's sister and along the way discovers her true power."),
     html.P("Aided by her Spren, Pattern, Shallan is able to take any disguise and use her art to create false reality."),
     html.H3("Dalinar Kholin"),
     html.P("Dalinar is the brother of the last king, uncle of the present, and a great warrior. He wants to do good by his nation and unite them into one. His dreams are pushed by nightmares that seem to be prophecy."),
     html.P("Dalinar longs to take the throne, but before he can he must take the mantle to recreate the ancient order of knights. He is empowered by the Spren of the great storm for this role."),
      html.H3("Adolin Knholin"),
     html.P("Adolin is the son of Dalinar and a great duelist. He has sorry luck with women running them all off, but he has a good heart underneath his spoiled frame."),
     html.P("Eventually he finds romance seeming to go right with Shallan. But when the ancient knights are rising and he is not among them where will his place be?"),
      html.H3("Eshonai"),
     html.P("Eshonai is the war leader of the Parshendi, a race of sentient creatures locked in bitter war with humans, after murdering the Alethi king."),
     html.P("Eshonai turns the tides of the war with an ancient power that may offer hope for her people, but could also be their damnation."),
      html.H3("Szeth"),
     html.P("Szeth is the assassin in white hired to kill the king by the Parshendi. He was cast from his far off home and forced to kill for whoever holds his stone."),
     html.P("He is tragic and cannot find peace until Kaladin defeats him in battle and takes his mighty fearful weapon."),
])
