# app.py

import dash
from dash import html, dcc, callback, Input, Output

from dash_app.pages import home, runs, index
from .callbacks import (
    register_callbacks,
    register_nav_callbacks,
    register_nav_active_callback
)

# Création de l'application Dash
dash_app = dash.Dash(
    __name__,
    requests_pathname_prefix="/",  # Changed from "/dash/" to "/"
    suppress_callback_exceptions=True
)

# Titre de l'onglet
dash_app.title = "Dash QC Dashboard"

# Multi-page layout with URL routing
dash_app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content")
])

# URL routing callback
@callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    """Route to different pages based on URL"""
    if pathname == "/runs" or pathname == "/runs/":
        return runs.create_launch_layout()
    elif pathname == "/home" or pathname == "/home/":
        return home.build_layout()
    elif pathname == "/" or pathname is None:
        return index.create_index_layout()  # Index is now the main landing page
    else:
        # Default to index page for unknown routes
        return index.create_index_layout()

# Enregistrement des callbacks
register_callbacks(dash_app)
register_nav_callbacks(dash_app)
register_nav_active_callback(dash_app)

# Serveur WSGI exposé (FastAPI l'utilise)
server = dash_app.server

# Exécution en local (debug uniquement)
if __name__ == "__main__":
    dash_app.run(debug=True)
