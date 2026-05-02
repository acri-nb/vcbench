from dash import dcc, html, callback, Input, Output, State
import requests

from ..config import API_BASE_URL


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
                            html.Span("VCBench · Pipeline", className="product"),
                        ],
                        className="brand-text",
                    ),
                ],
                className="brand",
            ),
            html.Nav(
                [
                    dcc.Link("Overview", href="/"),
                    dcc.Link("Pipeline", href="/runs", className="active"),
                    dcc.Link("Dashboard", href="/home"),
                    html.A("API", href="/api/docs", target="_blank"),
                ],
                className="site-nav",
            ),
        ],
        className="site-header",
    )


def _aws_section():
    """AWS S3 import block. Pulls a known sample from S3 and runs the pipeline."""
    return html.Div(
        [
            html.H3("Import from AWS S3"),
            html.P(
                "Pull a known GIAB sample directly from S3, fetch the matching "
                "reference truth set, and launch benchmarking in one shot.",
                style={"color": "var(--vc-ink-500)", "fontSize": "0.95rem",
                       "marginBottom": "1.25rem"},
            ),
            html.Div(
                [
                    html.Label(
                        "Sample ID",
                        htmlFor="aws-sample-id",
                        style={"fontWeight": 600, "fontSize": "0.875rem",
                               "marginBottom": "0.375rem", "display": "block",
                               "color": "var(--vc-ink-700)"},
                    ),
                    dcc.Input(
                        id="aws-sample-id",
                        type="text",
                        placeholder="e.g. NA24143_Lib3_Rep1",
                        style={
                            "width": "100%",
                            "maxWidth": "480px",
                            "padding": "0.5rem 0.75rem",
                            "border": "1px solid var(--vc-border)",
                            "borderRadius": "var(--vc-r-sm)",
                            "fontSize": "0.9375rem",
                            "fontFamily": "inherit",
                            "boxSizing": "border-box",
                        },
                    ),
                ],
                style={"marginBottom": "1.25rem"},
            ),
            html.Div(
                [
                    html.Label(
                        "Benchmarking options",
                        style={"fontWeight": 600, "fontSize": "0.875rem",
                               "marginBottom": "0.5rem", "display": "block",
                               "color": "var(--vc-ink-700)"},
                    ),
                    dcc.Checklist(
                        id="aws-benchmarking-checkboxes",
                        options=[
                            {'label': ' hap.py (small variants)', 'value': 'happy'},
                            {'label': ' stratified (requires hap.py)', 'value': 'stratified'},
                            {'label': ' truvari (structural variants)', 'value': 'truvari'},
                            {'label': ' csv (CSV export)', 'value': 'csv'},
                        ],
                        value=['csv', 'truvari'],
                        labelStyle={"display": "block", "margin": "0 0 0.375rem 0",
                                    "fontSize": "0.9375rem"},
                    ),
                ],
                style={"marginBottom": "1rem"},
            ),
            dcc.Checklist(
                id="aws-auto-process",
                options=[
                    {'label': ' Process automatically after download',
                     'value': 'auto'},
                ],
                value=['auto'],
                labelStyle={"display": "inline-block", "fontSize": "0.9375rem",
                            "color": "var(--vc-ink-700)"},
                style={"marginBottom": "1.25rem"},
            ),
            html.Button(
                "Import from AWS",
                id="aws-import-btn",
                n_clicks=0,
                disabled=True,
                className="btn btn-secondary",
            ),
            html.Div(id="aws-status-message", style={"marginTop": "1rem"}),
            html.Div(
                [
                    html.H4(
                        "Download progress",
                        style={"marginTop": "1.25rem", "marginBottom": "0.5rem",
                               "fontSize": "0.875rem", "fontWeight": 600,
                               "textTransform": "uppercase",
                               "letterSpacing": "0.04em",
                               "color": "var(--vc-ink-500)"},
                    ),
                    html.Div(
                        id="aws-logs-console",
                        style={
                            "height": "320px",
                            "overflowY": "auto",
                            "background": "#1e1e1e",
                            "color": "#d4d4d4",
                            "padding": "0.75rem 1rem",
                            "borderRadius": "var(--vc-r-md)",
                            "fontFamily": "var(--vc-font-mono)",
                            "fontSize": "0.8125rem",
                            "lineHeight": "1.5",
                            "whiteSpace": "pre-wrap",
                            "wordWrap": "break-word",
                        },
                    ),
                    dcc.Store(id="log-index-store", data=0),
                    dcc.Store(id="current-sample-id", data=None),
                    dcc.Interval(
                        id="log-poll-interval",
                        interval=2000,
                        disabled=True,
                        n_intervals=0,
                    ),
                ],
                id="aws-logs-container",
                style={"display": "none"},
            ),
        ],
        className="section-card",
        style={"marginTop": "1rem"},
    )


def _local_upload_section():
    """ZIP upload section using the FastAPI streaming endpoint via iframe."""
    return html.Div(
        [
            html.H3("Upload run archive"),
            html.P(
                "Upload a ZIP archive of DRAGEN outputs. Large files use the FastAPI "
                "streaming endpoint to avoid browser timeouts.",
                style={"color": "var(--vc-ink-500)", "fontSize": "0.95rem",
                       "marginBottom": "1.25rem"},
            ),
            html.Iframe(
                src="/api/v1/upload/form",
                style={
                    "width": "100%",
                    "height": "640px",
                    "border": "none",
                    "background": "transparent",
                    "display": "block",
                },
            ),
        ],
        className="section-card",
        style={"marginTop": "1rem"},
    )


def _upload_tab():
    return html.Div(
        [_aws_section(), _local_upload_section()],
        style={"display": "flex", "flexDirection": "column", "gap": "1rem"},
    )


def _manage_tab():
    return html.Div(
        [
            html.H3("Manage existing runs"),
            html.P(
                "Select a run, review what's already benchmarked, and launch the "
                "remaining tools.",
                style={"color": "var(--vc-ink-500)", "fontSize": "0.95rem",
                       "marginBottom": "1.5rem"},
            ),
            html.Div(id="alert-message"),
            html.Div(
                [
                    html.Label("Run", htmlFor="run-dropdown",
                               style={"fontWeight": 600, "fontSize": "0.875rem",
                                      "marginBottom": "0.5rem", "display": "block",
                                      "color": "var(--vc-ink-700)"}),
                    dcc.Dropdown(
                        id="run-dropdown",
                        placeholder="Choose a run to manage",
                        style={"maxWidth": "480px"},
                    ),
                ],
                style={"marginBottom": "1.5rem"},
            ),
            html.Div(
                id="run-details-section",
                children=[
                    html.Div(
                        [
                            html.H4("Completed benchmarking",
                                    style={"color": "var(--vc-success-700)"}),
                            html.Div(id="completed-benchmarking",
                                     style={"padding": "1rem",
                                            "background": "var(--vc-success-100)",
                                            "borderRadius": "var(--vc-r-md)",
                                            "marginBottom": "1.5rem"}),
                        ]
                    ),
                    html.Div(
                        [
                            html.H4("Available benchmarking",
                                    style={"color": "var(--vc-brand-700)"}),
                            html.Div(
                                [
                                    dcc.Checklist(
                                        id="benchmarking-checkboxes",
                                        options=[
                                            {'label': ' hap.py (small variants)', 'value': 'happy'},
                                            {'label': ' stratified (requires hap.py)', 'value': 'stratified'},
                                            {'label': ' truvari (structural variants)', 'value': 'truvari'},
                                            {'label': ' csv (CSV export)', 'value': 'csv'},
                                        ],
                                        value=[],
                                        labelStyle={"display": "block",
                                                    "margin": "0 0 0.5rem 0",
                                                    "fontSize": "0.95rem"},
                                    ),
                                    html.Button(
                                        "Launch selected benchmarking",
                                        id="launch-benchmarking-btn",
                                        n_clicks=0,
                                        disabled=True,
                                        className="btn btn-success",
                                        style={"marginTop": "1rem"},
                                    ),
                                ],
                                style={"padding": "1rem",
                                       "background": "var(--vc-bg)",
                                       "border": "1px solid var(--vc-border)",
                                       "borderRadius": "var(--vc-r-md)"},
                            ),
                        ]
                    ),
                ],
                style={"display": "none"},
            ),
            dcc.Link(
                html.Button("← Back to overview",
                            className="btn btn-ghost",
                            style={"marginTop": "1.5rem"}),
                href="/",
            ),
        ],
        className="section-card",
        style={"marginTop": "1rem"},
    )


def create_launch_layout():
    """Pipeline page: upload runs / manage existing runs."""
    return html.Div(
        [
            _site_header(),
            html.Main(
                dcc.Tabs(
                    id="main-tabs",
                    value="upload-tab",
                    children=[
                        dcc.Tab(label='Upload run', value="upload-tab",
                                children=[_upload_tab()],
                                className="tab", selected_className="tab--selected"),
                        dcc.Tab(label='Manage runs', value="manage-tab",
                                children=[_manage_tab()],
                                className="tab", selected_className="tab--selected"),
                    ],
                ),
                className="page-section",
            ),
        ],
        style={"minHeight": "100vh", "background": "var(--vc-bg)"},
    )


# Callback to load all runs into dropdown
@callback(
    Output("run-dropdown", "options"),
    Input("run-dropdown", "id")
)
def load_all_runs(_):
    """Load all available runs from the API"""
    print("load_all_runs")
    try:
        # Call your API to get all runs
        response = requests.get(f"{API_BASE_URL}/runs", timeout=4)
        response.raise_for_status()
        runs = response.json()
        
        if runs:
            return [
                {"label": f"{run['run_name']} ({run.get('status', 'Unknown')})", "value": run["run_name"]} 
                for run in runs
            ]
        else:
            return [{"label": "No runs available", "value": "", "disabled": True}]
            
    except Exception as e:
        print(f"Error loading runs: {e}")
        return [{"label": "Error loading runs", "value": "", "disabled": True}]


# Callback to show/hide run details section and update completed benchmarking
@callback(
    [Output("run-details-section", "style"),
     Output("completed-benchmarking", "children")],
    Input("run-dropdown", "value")
)
def update_run_details(selected_run):
    """Show run details when a run is selected and display completed benchmarking"""
    print(f"update_run_details: {selected_run}")
    
    if not selected_run:
        return {"display": "none"}, ""
    
    try:
        response = requests.get(f"{API_BASE_URL}/runs/{selected_run}/benchmarking", timeout=4)
        if response.status_code == 200:
            run_data = response.json()
            
            # Mock completed benchmarking - replace with actual data from your API
            completed = []
            if run_data.get("happy"):
                completed.append("✅ hap.py (Small variant benchmarking)")
            if run_data.get("stratified"):
                completed.append("✅ hap.py stratified (Stratified hap.py results)")
            if run_data.get("truvari"):
                completed.append("✅ truvari (Structural variant benchmarking)")
            
            if completed:
                completed_display = html.Ul([
                    html.Li(item, style={"margin-bottom": "5px", "color": "#28a745"}) 
                    for item in completed
                ], style={"list-style": "none", "padding-left": "0"})
            else:
                completed_display = html.P("No benchmarking completed yet.", 
                                         style={"color": "#6c757d", "font-style": "italic"})
            
            return {"display": "block"}, completed_display
            
        else:
            return {"display": "block"}, html.P("Error loading run details.", 
                                              style={"color": "#dc3545"})
            
    except Exception as e:
        print(f"Error fetching run details: {e}")
        return {"display": "block"}, html.P(f"Error: {str(e)}", 
                                          style={"color": "#dc3545"})


# Callback to enable/disable stratified based on happy selection and filter completed benchmarking
@callback(
    Output("benchmarking-checkboxes", "options"),
    [Input("benchmarking-checkboxes", "value"),
     Input("run-dropdown", "value")]
)
def update_benchmarking_options(selected_values, selected_run):
    """Enable/disable stratified option based on happy selection and show only non-completed benchmarking"""
    print(f"update_benchmarking_options: {selected_values}, run: {selected_run}")
    
    # Default all options
    all_options = [
        {'label': ' hap.py (Happy benchmarking)', 'value': 'happy'},
        {'label': ' stratified (requires hap.py)', 'value': 'stratified'},
        {'label': ' truvari (Structural variant benchmarking)', 'value': 'truvari'},
        {'label': ' csv (CSV output formatting)', 'value': 'csv'}
    ]
    
    # If no run is selected, return all options (disabled)
    if not selected_run:
        for option in all_options:
            option['disabled'] = True
        return all_options
    
    # Get completed benchmarking for the selected run
    try:
        response = requests.get(f"{API_BASE_URL}/runs/{selected_run}/benchmarking", timeout=4)
        if response.status_code == 200:
            run_data = response.json()
            completed_benchmarking = []
            
            # Check which benchmarking is completed
            if run_data.get("happy"):
                completed_benchmarking.append("happy")
            if run_data.get("stratified"):
                completed_benchmarking.append("stratified")
            if run_data.get("truvari"):
                completed_benchmarking.append("truvari")
            if run_data.get("csv"):
                completed_benchmarking.append("csv")
            
            # Filter out completed options
            available_options = []
            for option in all_options:
                if option['value'] not in completed_benchmarking:
                    available_options.append(option.copy())
            
            # Apply stratified dependency rule (only if stratified is still available)
            stratified_option = next((opt for opt in available_options if opt['value'] == 'stratified'), None)
            if stratified_option:
                # Disable stratified if happy is not selected OR if happy is completed
                if 'happy' not in (selected_values or []) or 'happy' in completed_benchmarking:
                    stratified_option['disabled'] = True
                else:
                    stratified_option['disabled'] = False
            
            return available_options
            
    except Exception as e:
        print(f"Error fetching benchmarking status: {e}")
        # On error, return all options but disabled
        for option in all_options:
            option['disabled'] = True
        return all_options
    
    # Fallback: return all options with stratified rule
    if 'happy' not in (selected_values or []):
        all_options[1]['disabled'] = True
    else:
        all_options[1]['disabled'] = False
    
    return all_options


@callback(
    [Output("launch-benchmarking-btn", "disabled"),
     Output("launch-benchmarking-btn", "className")],
    [Input("benchmarking-checkboxes", "value"),
     Input("run-dropdown", "value")]
)
def update_launch_button(selected_benchmarking, selected_run):
    """Enable launch button only when both a run and at least one option are selected."""
    if selected_run and selected_benchmarking:
        return False, "btn btn-success"
    return True, "btn btn-secondary"


# Callback to handle launch button click
@callback(
    Output("alert-message", "children"),
    Input("launch-benchmarking-btn", "n_clicks"),
    [State("run-dropdown", "value"),
     State("benchmarking-checkboxes", "value")],
    prevent_initial_call=True
)
def launch_benchmarking(n_clicks, selected_run, selected_benchmarking):
    """Launch the selected benchmarking processes"""
    print(f"launch_benchmarking: run={selected_run}, benchmarking={selected_benchmarking}")
    
    if n_clicks and selected_run and selected_benchmarking:
        try:
            # Prepare the API call data
            benchmarking_str = ','.join(selected_benchmarking)
            
            # Call your processing endpoint with benchmarking as query parameter
            response = requests.post(
                f"{API_BASE_URL}/runs/{selected_run}/benchmarking",
                params={"benchmarking": benchmarking_str},
                timeout=10,
            )
            
            if response.status_code == 200:
                benchmarking_list = ', '.join(selected_benchmarking)
                return html.Div(
                    f"Launched benchmarking for '{selected_run}': {benchmarking_list}.",
                    className="alert alert-success",
                )
            return html.Div(
                f"API returned {response.status_code}: {response.text[:200]}",
                className="alert alert-error",
            )
        except requests.exceptions.RequestException as exc:
            return html.Div(
                f"Couldn't reach the API: {exc}",
                className="alert alert-error",
            )

    return ""

# AWS Import Callbacks -------------------------------------------------------------------------

# Callback to enable/disable stratified based on happy selection for AWS import
@callback(
    Output("aws-benchmarking-checkboxes", "options"),
    Input("aws-benchmarking-checkboxes", "value")
)
def update_aws_benchmarking_options(selected_values):
    """Enable/disable stratified option based on happy selection for AWS imports"""
    print(f"update_aws_benchmarking_options: {selected_values}")
    
    all_options = [
        {'label': ' hap.py (Happy benchmarking)', 'value': 'happy'},
        {'label': ' stratified (requires hap.py)', 'value': 'stratified'},
        {'label': ' truvari (Structural variant benchmarking)', 'value': 'truvari'},
        {'label': ' csv (CSV output formatting)', 'value': 'csv'}
    ]
    
    # Disable stratified if happy is not selected
    if 'happy' not in (selected_values or []):
        all_options[1]['disabled'] = True
    else:
        all_options[1]['disabled'] = False
    
    return all_options


# Callback to enable/disable import button based on sample_id input
@callback(
    [Output("aws-import-btn", "disabled"),
     Output("aws-import-btn", "style")],
    Input("aws-sample-id", "value")
)
def update_aws_import_button(sample_id):
    """Enable import button only when sample_id is provided"""
    print(f"update_aws_import_button: sample_id={sample_id}")
    
    base_style = {
        "padding": "12px 24px",
        "border": "none",
        "border-radius": "6px",
        "font-size": "16px",
        "font-weight": "bold"
    }
    
    if sample_id and sample_id.strip():
        return False, {
            **base_style,
            "background-color": "#28a745",
            "color": "white",
            "cursor": "pointer"
        }
    else:
        return True, {
            **base_style,
            "background-color": "#6c757d",
            "color": "#adb5bd",
            "cursor": "not-allowed"
        }


# Callback to handle AWS import button click
@callback(
    [Output("aws-status-message", "children"),
     Output("aws-logs-container", "style"),
     Output("log-poll-interval", "disabled"),
     Output("current-sample-id", "data"),
     Output("log-index-store", "data"),
     Output("aws-logs-console", "children")],
    Input("aws-import-btn", "n_clicks"),
    [State("aws-sample-id", "value"),
     State("aws-benchmarking-checkboxes", "value"),
     State("aws-auto-process", "value")],
    prevent_initial_call=True
)
def launch_aws_import(n_clicks, sample_id, selected_benchmarking, auto_process):
    """Launch the AWS import process"""
    print(f"launch_aws_import: sample_id={sample_id}, benchmarking={selected_benchmarking}, auto_process={auto_process}")
    
    if n_clicks and sample_id and sample_id.strip():
        try:
            # Prepare the API call data
            benchmarking_str = ','.join(selected_benchmarking) if selected_benchmarking else ""
            auto_process_bool = 'auto' in (auto_process or [])
            
            payload = {
                "sample_id": sample_id.strip(),
                "benchmarking": benchmarking_str,
                "auto_process": auto_process_bool
            }
            
            # Call the AWS import endpoint
            response = requests.post(
                f"{API_BASE_URL}/upload/aws",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                benchmarking_list = ', '.join(selected_benchmarking) if selected_benchmarking else 'None'
                status_msg = html.Div([
                    html.H4("AWS Import Initiated!", style={"color": "#155724", "margin-bottom": "10px"}),
                    html.P(f"Sample ID: {data['sample_id']}"),
                    html.P(f"Run Name: {data['run_name']}"),
                    html.P(f"Benchmarking: {benchmarking_list}"),
                    html.P(f"Auto Process: {'Yes' if auto_process_bool else 'No'}"),
                    html.P(data.get('message', ''), style={"font-style": "italic", "margin-top": "10px"})
                ], style={
                    "padding": "15px",
                    "background-color": "#d4edda",
                    "border": "1px solid #c3e6cb",
                    "border-radius": "6px",
                    "color": "#155724"
                })
                
                # Show logs console and start polling
                logs_style = {"display": "block", "margin-top": "20px"}
                poll_disabled = False
                current_sid = data['sample_id']
                log_idx = 0
                initial_log = "Initializing download process..."
                
                return status_msg, logs_style, poll_disabled, current_sid, log_idx, initial_log
            else:
                error_detail = response.json().get('detail', response.text) if response.text else 'Unknown error'
                error_msg = html.Div(
                    f"Error: {error_detail}",
                    style={
                        "padding": "15px",
                        "background-color": "#f8d7da",
                        "border": "1px solid #f5c6cb",
                        "border-radius": "6px",
                        "color": "#721c24"
                    }
                )
                # Don't show logs on error, disable polling
                logs_style = {"display": "none", "margin-top": "20px"}
                return error_msg, logs_style, True, None, 0, ""
                
        except Exception as e:
            error_msg = html.Div(
                f"Connection error: {str(e)}",
                style={
                    "padding": "15px",
                    "background-color": "#f8d7da",
                    "border": "1px solid #f5c6cb",
                    "border-radius": "6px",
                    "color": "#721c24"
                }
            )
            logs_style = {"display": "none", "margin-top": "20px"}
            return error_msg, logs_style, True, None, 0, ""
    
    # Default return when n_clicks is 0
    logs_style = {"display": "none", "margin-top": "20px"}
    return "", logs_style, True, None, 0, ""

# Callback to poll logs from the API
@callback(
    [Output("aws-logs-console", "children", allow_duplicate=True),
     Output("log-index-store", "data", allow_duplicate=True),
     Output("log-poll-interval", "disabled", allow_duplicate=True)],
    Input("log-poll-interval", "n_intervals"),
    [State("current-sample-id", "data"),
     State("log-index-store", "data")],
    prevent_initial_call=True
)
def poll_logs(n_intervals, sample_id, current_log_index):
    """Poll the API for new logs"""
    if not sample_id:
        return "", 0, True
    
    try:
        # Fetch logs from API
        response = requests.get(
            f"{API_BASE_URL}/download/logs/{sample_id}",
            params={"since": current_log_index}
        )
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get("logs", [])
            status = data.get("status", "running")
            total_logs = data.get("total_logs", 0)
            
            if not logs and current_log_index == 0:
                # No logs yet, keep polling
                return "Waiting for process to start...", 0, False
            
            # Format logs with colors based on level
            log_lines = []
            for log_entry in logs:
                timestamp = log_entry.get("timestamp", "")
                message = log_entry.get("message", "")
                level = log_entry.get("level", "info")
                
                # Simple timestamp formatting
                time_str = timestamp.split("T")[1][:8] if "T" in timestamp else timestamp
                
                # Color coding based on level
                color = "#d4d4d4"  # Default gray
                if level == "success":
                    color = "#4ec9b0"  # Green
                elif level == "error":
                    color = "#f48771"  # Red
                elif level == "warning":
                    color = "#dcdcaa"  # Yellow
                elif level == "progress":
                    color = "#569cd6"  # Blue
                
                log_lines.append(
                    html.Div([
                        html.Span(f"[{time_str}] ", style={"color": "#808080"}),
                        html.Span(message, style={"color": color})
                    ])
                )
            
            # Check if process is completed or errored
            stop_polling = status in ["completed", "error"]
            
            if stop_polling:
                if status == "completed":
                    log_lines.append(
                        html.Div(
                            "✅ Process completed successfully!",
                            style={"color": "#4ec9b0", "margin-top": "10px", "font-weight": "bold"}
                        )
                    )
                elif status == "error":
                    log_lines.append(
                        html.Div(
                            "❌ Process failed. Check logs above for details.",
                            style={"color": "#f48771", "margin-top": "10px", "font-weight": "bold"}
                        )
                    )
            
            return log_lines, total_logs, stop_polling
        else:
            # API error, keep current logs but stop polling
            return f"Error fetching logs: {response.status_code}", current_log_index, True
            
    except Exception as e:
        return f"Error: {str(e)}", current_log_index, True


# Old upload callbacks removed - now using FastAPI iframe for uploads
# Old benchmarking options callback removed - replaced with new manage runs functionality
