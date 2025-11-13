from dash import dcc, html, callback, Input, Output
import requests
from ..config import API_BASE_URL


def create_index_layout():
    """Create the index/landing page layout equivalent to index.html"""
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
                html.H1("Institut Atlantique de Recherche sur le Cancer", style={
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
        # Main content
        html.Main([
            html.Div([
                html.H2("List of Runs", style={
                    "margin-bottom": "20px",
                    "color": "#333"
                }),
                
                # Runs table container
                html.Div(id="runs-table", style={
                    "margin-bottom": "30px"
                }),

                # Navigation buttons
                html.Div([
                    dcc.Link(
                        html.Button(
                            "Run Management",
                            className="btn",
                            style={
                                "background": "#F7941D",
                                "color": "#FFFFFF",
                                "border": "none",
                                "padding": "0.5rem 1rem",
                                "border-radius": "4px",
                                "cursor": "pointer",
                                "margin-right": "1rem"
                            }
                        ),
                        href="/runs"
                    ),
                    
                    dcc.Link(
                        html.Button(
                            "Run Dashboard",
                            className="btn btn-secondary",
                            style={
                                "background": "#F7941D",
                                "color": "#FFFFFF",
                                "border": "none",
                                "padding": "0.5rem 1rem",
                                "border-radius": "4px",
                                "cursor": "pointer",
                                "margin-right": "1rem"
                            }
                        ),
                        href="/home"
                    ),
                    
                    html.A(
                        html.Button(
                            "Admin Dashboard",
                            className="btn btn-secondary",
                            style={
                                "background": "#F7941D",
                                "color": "#FFFFFF",
                                "border": "none",
                                "padding": "0.5rem 1rem",
                                "border-radius": "4px",
                                "cursor": "pointer"
                            }
                        ),
                        href="/api/docs",
                        target="_blank"
                    )
                ], style={"margin-top": "1.5rem"})

            ], className="container", style={
                "width": "90%",
                "max-width": "960px",
                "margin": "2rem auto",
                "background": "rgba(255,255,255,0.9)",
                "padding": "1.5rem",
                "border-radius": "8px",
                "box-shadow": "0 0 10px rgba(0,0,0,0.1)"
            })
        ])
    ], className="index-page", style={
        "font-family": "Arial, sans-serif",
        "margin": "0",
        "color": "#333",
        "min-height": "100vh"
    })


# Callback to load runs data
@callback(
    Output("runs-table", "children"),
    Input("runs-table", "id")  # Trigger on component load
)
def load_runs_table(_):
    """Load and display runs data equivalent to the JavaScript fetch"""
    print("load_runs_table")
    try:
        response = requests.get(f"{API_BASE_URL}/runs")
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text[:200]}...")  # First 200 chars for debugging
        
        response.raise_for_status()
        runs = response.json()
        
        if runs:
            # Create run entries
            run_elements = []
            for run in runs:
                status_color = "#28a745" if run.get("approved_at") else "#ffc107"
                status_text = "Approved" if run.get("approved_at") else "Pending"
                
                run_elements.append(
                    html.Div([
                        html.Strong(run["run_name"], style={"margin-right": "10px"}),
                        html.Span(" - ", style={"margin-right": "5px"}),
                        html.Span(
                            status_text,
                            style={
                                "color": status_color,
                                "font-weight": "bold"
                            }
                        )
                    ], style={
                        "padding": "8px 0",
                        "border-bottom": "1px solid #e9ecef"
                    })
                )
            
            return run_elements
        else:
            return html.Div(
                "No runs found",
                style={
                    "text-align": "center",
                    "color": "#6c757d",
                    "font-style": "italic",
                    "padding": "20px"
                }
            )
            
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return html.Div(
            f"Connection error: {str(e)}",
            style={
                "text-align": "center",
                "color": "#dc3545",
                "padding": "20px",
                "background-color": "#f8d7da",
                "border": "1px solid #f5c6cb",
                "border-radius": "4px"
            }
        )
    except ValueError as e:
        print(f"JSON parsing error: {e}")
        return html.Div(
            f"Invalid response format: {str(e)}",
            style={
                "text-align": "center",
                "color": "#dc3545",
                "padding": "20px",
                "background-color": "#f8d7da",
                "border": "1px solid #f5c6cb",
                "border-radius": "4px"
            }
        )
    except Exception as e:
        print(f"Unexpected error: {e}")
        return html.Div(
            f"Error loading runs: {str(e)}",
            style={
                "text-align": "center",
                "color": "#dc3545",
                "padding": "20px",
                "background-color": "#f8d7da",
                "border": "1px solid #f5c6cb",
                "border-radius": "4px"
            }
        )