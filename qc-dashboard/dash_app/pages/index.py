from dash import dcc, html, callback, Input, Output
import requests

from ..config import API_BASE_URL


NAV_ACTIONS = [
    {
        "label": "Pipeline",
        "title": "Run Management",
        "desc": "Upload DRAGEN runs and launch hap.py / Truvari benchmarking.",
        "href": "/runs",
        "external": False,
    },
    {
        "label": "Analysis",
        "title": "QC Dashboard",
        "desc": "Compare metrics across samples: SNV, SV, coverage, ploidy.",
        "href": "/home",
        "external": False,
    },
    {
        "label": "Reference",
        "title": "API Documentation",
        "desc": "Inspect REST endpoints, schemas, and OpenAPI definitions.",
        "href": "/api/docs",
        "external": True,
    },
]


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
                            html.Span("VCBench", className="product"),
                        ],
                        className="brand-text",
                    ),
                ],
                className="brand",
            ),
            html.Nav(
                [
                    dcc.Link("Overview", href="/", className="active"),
                    dcc.Link("Pipeline", href="/runs"),
                    dcc.Link("Dashboard", href="/home"),
                    dcc.Link("Truvari", href="/truvari"),
                    html.A("API", href="/api/docs", target="_blank"),
                ],
                className="site-nav",
            ),
        ],
        className="site-header",
    )


def _hero():
    return html.Section(
        html.Div(
            [
                html.Div("Whole Genome Sequencing QC", className="eyebrow"),
                html.H2("Benchmark, visualize, and approve DRAGEN runs in one place."),
                html.P(
                    "VCBench unifies hap.py and Truvari benchmarking with interactive "
                    "QC dashboards so the lab can sign off on each run with confidence.",
                    className="lede",
                ),
            ],
            className="index-hero-inner",
        ),
        className="index-hero",
    )


def _action_card(item):
    inner = html.Div(
        [
            html.Div(item["label"], className="label"),
            html.Div(item["title"], className="title"),
            html.Div(item["desc"], className="desc"),
        ]
    )
    if item["external"]:
        return html.A(inner, href=item["href"], target="_blank", className="action-card")
    return dcc.Link(inner, href=item["href"], className="action-card")


def create_index_layout():
    """Landing page: header, hero, action cards, recent runs panel."""
    return html.Div(
        [
            _site_header(),
            _hero(),
            html.Main(
                [
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.H2("Recent runs"),
                                    dcc.Link(
                                        "Manage all runs →",
                                        href="/runs",
                                        style={
                                            "fontSize": "0.875rem",
                                            "fontWeight": "500",
                                        },
                                    ),
                                ],
                                className="runs-panel-head",
                            ),
                            html.Div(id="runs-table"),
                        ],
                        className="runs-panel",
                    ),
                    html.H2("Jump in", style={"marginBottom": "0.5rem"}),
                    html.P(
                        "Choose a workspace based on what you need to do next.",
                        style={"color": "var(--vc-ink-500)", "fontSize": "0.95rem"},
                    ),
                    html.Div(
                        [_action_card(item) for item in NAV_ACTIONS],
                        className="action-grid",
                    ),
                ],
                className="index-main",
            ),
        ],
        className="index-page",
    )


def _format_run_row(run):
    approved = bool(run.get("approved_at"))
    pill_cls = "pill is-success" if approved else "pill is-warn"
    pill_text = "Approved" if approved else "Pending"
    return html.Div(
        [
            html.Span(run.get("run_name", "—"), className="run-name"),
            html.Span(pill_text, className=pill_cls),
        ],
        className="run-row",
    )


@callback(
    Output("runs-table", "children"),
    Input("runs-table", "id"),
)
def load_runs_table(_):
    """Load runs list. Errors render as inline state, never as raw exception text."""
    try:
        response = requests.get(f"{API_BASE_URL}/runs", timeout=4)
        response.raise_for_status()
        runs = response.json()
    except requests.exceptions.RequestException:
        return html.Div(
            "Couldn't reach the API. Check that the FastAPI server is running.",
            className="error-state",
        )
    except ValueError:
        return html.Div(
            "Invalid response from API.",
            className="error-state",
        )

    if not runs:
        return html.Div(
            "No runs yet. Upload your first DRAGEN run from the Pipeline page.",
            className="empty-state",
        )

    return [_format_run_row(run) for run in runs]
