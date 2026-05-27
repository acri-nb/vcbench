from dash import dcc, html, callback, Input, Output
import requests

from ..config import API_BASE_URL


JOB_TYPES = [
    {"label": "All types", "value": ""},
    {"label": "ZIP uploads", "value": "upload_zip"},
    {"label": "AWS imports", "value": "aws_import"},
    {"label": "Pipeline", "value": "pipeline"},
]

JOB_STATUSES = [
    {"label": "All statuses", "value": ""},
    {"label": "Queued", "value": "queued"},
    {"label": "Running", "value": "running"},
    {"label": "Completed", "value": "completed"},
    {"label": "Failed", "value": "failed"},
    {"label": "Canceled", "value": "canceled"},
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
                            html.Span("VCBench - Monitoring", className="product"),
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
                    dcc.Link("Monitoring", href="/monitoring", className="active"),
                    dcc.Link("Dashboard", href="/home"),
                    dcc.Link("Truvari", href="/truvari"),
                    html.A("API", href="/docs", target="_blank"),
                ],
                className="site-nav",
            ),
        ],
        className="site-header",
    )


def create_monitoring_layout():
    return html.Div(
        [
            _site_header(),
            html.Main(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H2("Transfer monitoring"),
                                    html.P(
                                        "Follow ZIP uploads, AWS imports, and pipeline jobs from one operational view.",
                                        className="monitoring-subtitle",
                                    ),
                                ]
                            ),
                            dcc.Interval(id="monitoring-refresh", interval=3000, n_intervals=0),
                        ],
                        className="monitoring-head",
                    ),
                    html.Div(id="monitoring-summary", className="monitoring-summary"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Type", htmlFor="monitoring-type-filter"),
                                    dcc.Dropdown(
                                        id="monitoring-type-filter",
                                        options=JOB_TYPES,
                                        value="",
                                        clearable=False,
                                    ),
                                ],
                                className="monitoring-filter",
                            ),
                            html.Div(
                                [
                                    html.Label("Status", htmlFor="monitoring-status-filter"),
                                    dcc.Dropdown(
                                        id="monitoring-status-filter",
                                        options=JOB_STATUSES,
                                        value="",
                                        clearable=False,
                                    ),
                                ],
                                className="monitoring-filter",
                            ),
                            html.Div(
                                [
                                    html.Label("Job detail", htmlFor="monitoring-job-select"),
                                    dcc.Dropdown(
                                        id="monitoring-job-select",
                                        options=[],
                                        placeholder="Choose a job",
                                        clearable=True,
                                    ),
                                ],
                                className="monitoring-filter monitoring-filter-wide",
                            ),
                        ],
                        className="monitoring-filters",
                    ),
                    html.Div(id="monitoring-job-table", className="monitoring-panel"),
                    html.Div(id="monitoring-job-detail", className="monitoring-panel"),
                ],
                className="page-section monitoring-page",
            ),
        ],
        style={"minHeight": "100vh", "background": "var(--vc-bg)"},
    )


@callback(
    Output("monitoring-summary", "children"),
    Input("monitoring-refresh", "n_intervals"),
)
def load_monitoring_summary(_):
    try:
        response = requests.get(f"{API_BASE_URL}/jobs/summary", timeout=4)
        response.raise_for_status()
        summary = response.json()
    except requests.exceptions.RequestException:
        return html.Div("Monitoring API is unavailable.", className="error-state")

    return [
        _summary_card("Active", summary.get("active_jobs", 0), "running jobs", "running"),
        _summary_card("Queued", summary.get("queued_jobs", 0), "waiting jobs", "queued"),
        _summary_card("Throughput", _format_rate(summary.get("total_rate_bps", 0)), "current total", "neutral"),
        _summary_card("Failures", summary.get("failed_24h", 0), "last 24 hours", "failed"),
        _summary_card("Disk free", _format_bytes(summary.get("disk_free_bytes", 0)), "data volume", "neutral"),
    ]


@callback(
    [Output("monitoring-job-table", "children"),
     Output("monitoring-job-select", "options")],
    [Input("monitoring-refresh", "n_intervals"),
     Input("monitoring-type-filter", "value"),
     Input("monitoring-status-filter", "value")],
)
def load_monitoring_jobs(_, job_type, status):
    params = {}
    if job_type:
        params["type"] = job_type
    if status:
        params["status"] = status

    try:
        response = requests.get(f"{API_BASE_URL}/jobs", params=params, timeout=4)
        response.raise_for_status()
        jobs = response.json()
    except requests.exceptions.RequestException:
        return html.Div("Could not load transfer jobs.", className="error-state"), []

    if not jobs:
        return html.Div("No transfer jobs match these filters.", className="empty-state"), []

    options = [
        {"label": f"{job['subject_id']} ({job['status']})", "value": job["id"]}
        for job in jobs
    ]

    rows = [
        html.Thead(
            html.Tr(
                [
                    html.Th("Job"),
                    html.Th("Type"),
                    html.Th("Status"),
                    html.Th("Phase"),
                    html.Th("Progress"),
                    html.Th("ETA"),
                ]
            )
        ),
        html.Tbody([_job_row(job) for job in jobs]),
    ]
    return html.Table(rows, className="monitoring-table"), options


@callback(
    Output("monitoring-job-detail", "children"),
    [Input("monitoring-job-select", "value"),
     Input("monitoring-refresh", "n_intervals")],
)
def load_job_detail(job_id, _):
    if not job_id:
        return html.Div("Choose a job to inspect events and diagnostics.", className="empty-state")

    try:
        job_response = requests.get(f"{API_BASE_URL}/jobs/{job_id}", timeout=4)
        job_response.raise_for_status()
        events_response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/events", timeout=4)
        events_response.raise_for_status()
        job = job_response.json()
        events = events_response.json().get("events", [])
    except requests.exceptions.RequestException:
        return html.Div("Could not load job detail.", className="error-state")

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(job.get("subject_id", "Unknown job"), className="monitoring-detail-title"),
                            html.Div(job.get("id", ""), className="monitoring-detail-id"),
                        ]
                    ),
                    _status_badge(job.get("status", "queued")),
                ],
                className="monitoring-detail-head",
            ),
            html.Div(
                [
                    _detail_item("Type", job.get("type")),
                    _detail_item("Phase", job.get("phase")),
                    _detail_item("Progress", _format_progress(job)),
                    _detail_item("Rate", _format_rate(job.get("rate_bps"))),
                    _detail_item("ETA", _format_eta(job.get("eta_seconds"))),
                    _detail_item("Destination", job.get("destination_path") or "-"),
                ],
                className="monitoring-detail-grid",
            ),
            html.Div([_event_line(event) for event in events[-80:]], className="monitoring-log"),
        ]
    )


def _summary_card(label, value, caption, state):
    return html.Div(
        [
            html.Div(label, className="summary-label"),
            html.Div(str(value), className="summary-value"),
            html.Div(caption, className="summary-caption"),
        ],
        className=f"summary-card summary-card-{state}",
    )


def _job_row(job):
    return html.Tr(
        [
            html.Td(
                [
                    html.Div(job.get("subject_id", "-"), className="job-subject"),
                    html.Div(job.get("id", ""), className="job-id"),
                ]
            ),
            html.Td(job.get("type", "-")),
            html.Td(_status_badge(job.get("status", "queued"))),
            html.Td(job.get("phase") or "-"),
            html.Td(_progress_bar(job)),
            html.Td(_format_eta(job.get("eta_seconds"))),
        ]
    )


def _status_badge(status):
    safe_status = status or "queued"
    return html.Span(safe_status, className=f"job-status job-status-{safe_status}")


def _progress_bar(job):
    total = job.get("bytes_total")
    done = job.get("bytes_done") or 0
    pct = 100 if job.get("status") == "completed" else 0
    if total:
        pct = min(max((done / total) * 100, 0), 100)
    return html.Div(
        [
            html.Div(
                html.Div(style={"width": f"{pct:.1f}%"}),
                className="progress-track",
            ),
            html.Div(_format_progress(job), className="progress-caption"),
        ],
        className="progress-cell",
    )


def _event_line(event):
    return html.Div(
        [
            html.Span(_short_time(event.get("timestamp")), className="log-time"),
            html.Span(event.get("level", "info"), className=f"log-level log-level-{event.get('level', 'info')}"),
            html.Span(event.get("message", ""), className="log-message"),
        ],
        className="log-line",
    )


def _detail_item(label, value):
    return html.Div(
        [html.Div(label, className="detail-label"), html.Div(str(value or "-"), className="detail-value")],
        className="detail-item",
    )


def _format_progress(job):
    total = job.get("bytes_total")
    done = job.get("bytes_done") or 0
    if total:
        pct = min(max((done / total) * 100, 0), 100)
        return f"{pct:.1f}% - {_format_bytes(done)} / {_format_bytes(total)}"
    if done:
        return _format_bytes(done)
    return "phase only"


def _format_bytes(value):
    value = int(value or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def _format_rate(value):
    if not value:
        return "0 B/s"
    return f"{_format_bytes(value)}/s"


def _format_eta(value):
    if value is None:
        return "-"
    seconds = int(value)
    minutes, sec = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minute:02d}m"
    if minute:
        return f"{minute}m {sec:02d}s"
    return f"{sec}s"


def _short_time(timestamp):
    if not timestamp:
        return "--:--:--"
    if "T" in timestamp:
        return timestamp.split("T", 1)[1][:8]
    return timestamp[:8]
