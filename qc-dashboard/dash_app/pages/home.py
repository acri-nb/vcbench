from dash import dcc, html
from dash_app.config import FILE_TYPES

def build_layout():
    """
    UI principale : sidebar fixe à gauche, sidebar à droite, contenu au centre.
    """

    # Dropdown options
    opts = []
    for key, suffix in FILE_TYPES.items():
        if key == "ROH_metrics":
            hethom = FILE_TYPES.get("HeThom", "")
            opts.append({"label": f"{suffix} & {hethom}", "value": key})
        elif key == "HeThom":
            continue
        else:
            opts.append({"label": suffix, "value": key})

    # Boutons dans la sidebar gauche
    emoji_map = {
        "ROH_metrics": "🧬",
        "Ploidy": "🧪",
        "bed_coverage": "📊",
        "WGS_contig_mean_cov": "📈",
        "mapping_metrics": "📁",
    }

    nav_items = []
    for key in FILE_TYPES.keys():
        nav_items.append(
            html.Button(
                [
                    html.Span(emoji_map.get(key, "📁"), className="icon"),
                    html.Span(key, className="label")
                ],
                id={"type": "nav-item", "index": key},
                n_clicks=0,
                className="nav-item"
            )
        )

    return html.Div([
        # ─── Sidebar gauche ───
        html.Div(nav_items, id="sidebar"),

        # ─── Sidebar droite ───
        html.Div([
            html.H2("Statuts manuels", className="status-label", style={
                "marginTop": "32px",
                "textAlign": "center",
                "color": "#fff"
            }),
            html.Div(id="manual-status-container", style={
                "padding": "12px",
                "display": "flex",
                "flexDirection": "column",
                "rowGap": "12px"
            }),
            html.Button("💾 Save Report Status", id="save-report-btn", n_clicks=0, style={
                "marginTop": "20px",
                "backgroundColor": "#4a90e2",
                "color": "white",
                "border": "none",
                "padding": "10px 20px",
                "borderRadius": "5px",
                "cursor": "pointer",
                "width": "90%",
                "marginLeft": "5%"
            }),
            html.Div(id="save-status-msg", className="status-label", style={
                "marginTop": "10px",
                "fontWeight": "bold",
                "color": "white",
                "textAlign": "center"
            })
        ], id="sidebar-right"),

        # ─── Contenu principal ───
        html.Div([
            html.H1("Comparaison CSV multi-types", style={
                "textAlign": "center",
                "marginBottom": "24px",
                "color": "#222"
            }),

            html.Div([
                html.Div([
                    html.Label("Type de fichier :", htmlFor="type-dropdown",
                               style={"fontWeight": "600", "marginRight": "8px"}),
                    dcc.Dropdown(
                        id="type-dropdown",
                        options=opts,
                        value=list(FILE_TYPES.keys())[0],
                        clearable=False,
                        style={"width": "240px"}
                    )
                ], style={"display": "none"}),

                html.Div([
                    html.Label("Échantillon de référence :", htmlFor="ref-dropdown",
                               style={"fontWeight": "600", "marginLeft": "40px", "marginRight": "8px"}),
                    dcc.Dropdown(
                        id="ref-dropdown",
                        clearable=False,
                        style={"width": "240px"}
                    )
                ], style={"display": "flex", "alignItems": "center"})
            ], style={
                "display": "flex",
                "justifyContent": "center",
                "columnGap": "32px",
                "marginBottom": "20px"
            }),

            html.Div(id="table-container", style={
                "padding": "16px",
                "backgroundColor": "#fff",
                "borderRadius": "8px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.1)"
            })
        ], id="main-content", style={
            "marginLeft": "4rem",
            "marginRight": "4rem"  # réactif avec effet hover CSS
        })
    ])
