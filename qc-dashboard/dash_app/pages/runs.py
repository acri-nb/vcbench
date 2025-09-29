from dash import dcc, html, callback, Input, Output, State
import requests


def create_launch_layout():
    """Create the launch page layout equivalent to launch.html"""
    return html.Div([
        # Header section
        html.Header([
            # Left section (image)
            html.Div([
                html.Img(
                    src="/assets/logo_institut.png",
                    alt="Logo Institut",
                    style={
                        "height": "60px",
                        "background": "#FFFFFF",
                        "padding": "4px",
                        "border-radius": "4px",
                        "box-shadow": "0 2px 6px rgba(0,0,0,0.3)"
                    }
                )
            ], style={"flex": "1"}),  # Takes 1/3 of space
        
            # Center section (title)
            html.Div([
                html.H1("Run Management", style={
                    "margin": "0",
                    "font-size": "1.8rem",
                    "color": "#FFFFFF",
                    "text-align": "center"
                })
            ], style={"flex": "1"}),  # Takes 1/3 of space
    
            # Right section (empty for balance)
            html.Div(style={"flex": "1"})  # Takes 1/3 of space
        ], className="site-header", style={
            "display": "flex", 
            "align-items": "center", 
            "height": "100px",
            "background": "#004A8F",
            "padding": "0 20px"
        }),
        # Tabs for either uploading or managing runs
        dcc.Tabs(id="main-tabs", value="upload-tab", children=[
            dcc.Tab(label='Upload Run', value="upload-tab", children=[
                html.Div([
                    html.H3("Upload Run Data", style={"margin-bottom": "20px"}),
                    
                    # FastAPI Upload Form (embedded via iframe)
                    html.Div([
                        html.H4("Upload via FastAPI (Recommended for Large Files)", style={"margin-bottom": "15px", "color": "#004A8F"}),
                        html.Iframe(
                            src="/api/v1/upload/form",
                            style={
                                "width": "100%",
                                "height": "600px",
                                "border": "1px solid #ddd",
                                "border-radius": "8px"
                            }
                        )
                    ], style={"margin-bottom": "30px"}),
                ], style={"padding": "20px"})
            ]),
            
            dcc.Tab(label='Manage Runs', value="manage-tab", children=[
                html.Div([
                    html.H3("Manage Existing Runs", style={"margin-bottom": "20px"}),
                    
                    # Alert messages
                    html.Div(id="alert-message", style={"margin-bottom": "20px"}),

                    # Run selection section
                    html.Div([
                        html.Label("Select Run:", htmlFor="run-dropdown", style={"margin-right": "10px"}),
                        
                        dcc.Dropdown(
                            id="run-dropdown",
                            placeholder="Choose a run to manage",
                            style={"width": "400px"}
                        )
                    ], style={"margin-bottom": "30px", "display": "flex", "align-items": "center"}),

                    # Run details section (appears when run is selected)
                    html.Div(id="run-details-section", children=[
                        # Completed benchmarking status
                        html.Div([
                            html.H4("Completed Benchmarking:", style={"margin-bottom": "15px", "color": "#28a745"}),
                            html.Div(id="completed-benchmarking", style={
                                "padding": "15px",
                                "background-color": "#f8f9fa",
                                "border-radius": "8px",
                                "margin-bottom": "25px"
                            })
                        ]),

                        # Available benchmarking options
                        html.Div([
                            html.H4("Available Benchmarking Options:", style={"margin-bottom": "15px", "color": "#007bff"}),
                            html.Div([
                                dcc.Checklist(
                                    id="benchmarking-checkboxes",
                                    options=[
                                        {'label': ' hap.py (Happy benchmarking)', 'value': 'happy'},
                                        {'label': ' stratified (requires hap.py)', 'value': 'stratified'},
                                        {'label': ' truvari (Structural variant benchmarking)', 'value': 'truvari'},
                                        {'label': ' csv (CSV output formatting)', 'value': 'csv'}
                                    ],
                                    value=[],
                                    style={"margin-bottom": "20px"},
                                    labelStyle={"display": "block", "margin-bottom": "8px"}
                                ),
                                
                                html.Button(
                                    "Launch Selected Benchmarking",
                                    id="launch-benchmarking-btn",
                                    n_clicks=0,
                                    disabled=True,
                                    style={
                                        "padding": "12px 24px",
                                        "background-color": "#28a745",
                                        "color": "white",
                                        "border": "none",
                                        "border-radius": "6px",
                                        "cursor": "pointer",
                                        "font-size": "16px",
                                        "font-weight": "bold"
                                    }
                                )
                            ], style={
                                "padding": "15px",
                                "background-color": "#f8f9fa",
                                "border-radius": "8px",
                                "margin-bottom": "25px"
                            })
                        ])
                    ], style={"display": "none"}),  # Hidden until run is selected

                    # Back button
                    html.P([
                        dcc.Link(
                            html.Button(
                                "← Return to index",
                                type="button",
                                style={
                                    "padding": "8px 15px",
                                    "background-color": "#6c757d",
                                    "color": "white",
                                    "border": "none",
                                    "border-radius": "4px",
                                    "cursor": "pointer"
                                }
                            ),
                            href="/"
                        )
                    ], style={"margin-top": "1.5rem"})
                ], style={"padding": "20px"})
            ])
        ]),
    ], style={
        "font-family": "Arial, sans-serif",
        "min-height": "100vh",
        "background-color": "#ffffff"
    })


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
        response = requests.get("http://127.0.0.1:8000/api/v1/runs")
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
        # Get run details from API (you'll need to implement this endpoint)
        response = requests.get(f"http://127.0.0.1:8000/api/v1/runs/{selected_run}/benchmarking")
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
        response = requests.get(f"http://127.0.0.1:8000/api/v1/runs/{selected_run}/benchmarking")
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


# Callback to enable/disable launch button based on selections
@callback(
    [Output("launch-benchmarking-btn", "disabled"),
     Output("launch-benchmarking-btn", "style")],
    [Input("benchmarking-checkboxes", "value"),
     Input("run-dropdown", "value")]
)
def update_launch_button(selected_benchmarking, selected_run):
    """Enable launch button only when both run and benchmarking options are selected"""
    print(f"update_launch_button: run={selected_run}, benchmarking={selected_benchmarking}")
    
    base_style = {
        "padding": "12px 24px",
        "border": "none",
        "border-radius": "6px",
        "font-size": "16px",
        "font-weight": "bold"
    }
    
    if selected_run and selected_benchmarking:
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
                f"http://127.0.0.1:8000/api/v1/runs/{selected_run}/benchmarking",
                params={"benchmarking": benchmarking_str}  # Changed from json to params
            )
            
            if response.status_code == 200:
                benchmarking_list = ', '.join(selected_benchmarking)
                return html.Div(
                    f"Successfully launched benchmarking for '{selected_run}': {benchmarking_list}",
                    style={
                        "padding": "15px",
                        "background-color": "#d4edda",
                        "border": "1px solid #c3e6cb",
                        "border-radius": "6px",
                        "color": "#155724"
                    }
                )
            else:
                return html.Div(
                    f"Error launching benchmarking: {response.text}",
                    style={
                        "padding": "15px",
                        "background-color": "#f8d7da",
                        "border": "1px solid #f5c6cb",
                        "border-radius": "6px",
                        "color": "#721c24"
                    }
                )
                
        except Exception as e:
            return html.Div(
                f"Connection error: {str(e)}",
                style={
                    "padding": "15px",
                    "background-color": "#f8d7da",
                    "border": "1px solid #f5c6cb",
                    "border-radius": "6px",
                    "color": "#721c24"
                }
            )
    
    return ""

# Old upload callbacks removed - now using FastAPI iframe for uploads
# Old benchmarking options callback removed - replaced with new manage runs functionality
