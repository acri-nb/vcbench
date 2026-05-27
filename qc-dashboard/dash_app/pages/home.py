from dash import dcc, html

from dash_app.config import FILE_TYPES


def _site_header():
    return html.Header(
        [
            html.Div(
                [
                    html.Img(src="/assets/logo_institut.png", alt="IARC"),
                    html.Div(
                        [
                            html.Span("Institut Atlantique de Recherche sur le Cancer",
                                      className="eyebrow"),
                            html.Span("VCBench · Dashboard", className="product"),
                        ],
                        className="brand-text",
                    ),
                ],
                className="brand",
            ),
            html.Nav(
                [
                    dcc.Link("Overview", href="/"),
                    dcc.Link("Pipeline", href="/runs"),
                    dcc.Link("Monitoring", href="/monitoring"),
                    dcc.Link("Dashboard", href="/home", className="active"),
                    dcc.Link("Truvari", href="/truvari"),
                    html.A("API", href="/docs", target="_blank"),
                ],
                className="site-nav",
            ),
        ],
        className="site-header",
    )


# Two- to three-letter mark used in the collapsed sidebar (replaces emoji icons).
NAV_MARKS = {
    "Summary":             "Sum",
    "Metrics":             "SV",
    "VC_metrics":          "VC",
    "CNV_metrics":         "CNV",
    "ROH_metrics":         "ROH",
    "HeThom":              "HT",
    "Ploidy":              "Plo",
    "bed_coverage":        "Bed",
    "WGS_contig_mean_cov": "Cov",
    "mapping_metrics":     "Map",
}

# Human-readable label used when the sidebar is expanded.
NAV_LABELS = {
    "Summary":             "Summary",
    "Metrics":             "SV metrics",
    "VC_metrics":          "VC metrics",
    "CNV_metrics":         "CNV metrics",
    "ROH_metrics":         "ROH + HeThom",
    "HeThom":              "HeThom ratio",
    "Ploidy":              "Ploidy estimation",
    "bed_coverage":        "BED coverage",
    "WGS_contig_mean_cov": "Contig mean coverage",
    "mapping_metrics":     "Mapping metrics",
}


def _dropdown_options():
    opts = []
    for key, suffix in FILE_TYPES.items():
        if key == "ROH_metrics":
            hethom = FILE_TYPES.get("HeThom", "")
            opts.append({"label": f"{suffix} & {hethom}", "value": key})
        elif key == "HeThom":
            continue
        else:
            opts.append({"label": suffix, "value": key})
    return opts


def _nav_button(key):
    return html.Button(
        [
            html.Span(NAV_MARKS.get(key, "—"), className="icon"),
            html.Span(NAV_LABELS.get(key, key), className="label"),
        ],
        id={"type": "nav-item", "index": key},
        n_clicks=0,
        className="nav-item",
    )


def _left_sidebar():
    return html.Div(
        [_nav_button(key) for key in FILE_TYPES.keys()],
        id="sidebar",
    )


def _right_sidebar():
    return html.Div(
        [
            # Visible only when collapsed (vertical letter mark).
            html.Div("MANUAL STATUS", className="right-stub"),
            # Visible only when expanded (full controls).
            html.Div(
                [
                    html.H2("Manual status"),
                    html.P(
                        "Select a run, then mark each metric Pass / Warning / Fail. "
                        "Save when ready.",
                        className="panel-help",
                    ),
                    html.Div(id="manual-status-container"),
                    html.Button(
                        "Save report status",
                        id="save-report-btn",
                        n_clicks=0,
                        className="btn btn-primary save-btn",
                    ),
                    html.Div(id="save-status-msg", className="save-status-msg"),
                ],
                className="right-panel",
            ),
        ],
        id="sidebar-right",
    )


def _main_content():
    return html.Div(
        [
            html.H1("QC dashboard"),
            html.P(
                "Compare metrics across samples using a chosen reference. "
                "Use the rail on the left to switch metric category.",
                className="lede",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(
                                "File type",
                                htmlFor="type-dropdown",
                                style={"fontWeight": 600, "fontSize": "0.875rem",
                                       "marginBottom": "0.25rem", "display": "block",
                                       "color": "var(--vc-ink-700)"},
                            ),
                            dcc.Dropdown(
                                id="type-dropdown",
                                options=_dropdown_options(),
                                value=list(FILE_TYPES.keys())[0],
                                clearable=False,
                                style={"width": "260px"},
                            ),
                        ],
                        # Hidden control — kept so the existing callbacks still bind.
                        style={"display": "none"},
                    ),
                    html.Div(
                        [
                            html.Label(
                                "Reference sample",
                                htmlFor="ref-dropdown",
                                style={"fontWeight": 600, "fontSize": "0.875rem",
                                       "marginBottom": "0.25rem", "display": "block",
                                       "color": "var(--vc-ink-700)"},
                            ),
                            dcc.Dropdown(
                                id="ref-dropdown",
                                clearable=False,
                                placeholder="Choose a reference sample…",
                                style={"width": "320px"},
                            ),
                        ]
                    ),
                ],
                style={"display": "flex", "gap": "var(--vc-s-5)",
                       "marginBottom": "var(--vc-s-5)", "alignItems": "flex-end"},
            ),
            html.Div(
                id="table-container",
                className="section-card",
                style={"padding": "var(--vc-s-4)"},
            ),
        ],
        id="main-content",
    )


def build_layout():
    """Dashboard: header, left rail (file type), main (tables/plots), right rail (status)."""
    return html.Div(
        [
            _site_header(),
            html.Div(
                [_left_sidebar(), _right_sidebar(), _main_content()],
                className="dashboard-shell",
            ),
        ],
        style={"minHeight": "100vh", "background": "var(--vc-bg)"},
    )
