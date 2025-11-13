from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import requests

from ..config import API_BASE_URL

def create_truvari_layout():
    """Create the Truvari benchmarking results page layout"""
    return html.Div([
        html.H1("Truvari - Structural Variant Benchmarking Results", style={
            "text-align": "center",
            "color": "#2c3e50",
            "margin-bottom": "30px"
        }),
        
        html.Div([
            html.Label("Select Run:", style={"font-weight": "bold", "margin-bottom": "10px"}),
            dcc.Dropdown(
                id="truvari-run-dropdown",
                placeholder="Select a run to view Truvari results...",
                style={"width": "100%"}
            )
        ], style={
            "max-width": "600px",
            "margin": "0 auto 30px auto",
            "padding": "20px",
            "background": "white",
            "border-radius": "8px",
            "box-shadow": "0 2px 4px rgba(0,0,0,0.1)"
        }),
        
        html.Div(id="truvari-results-container")
        
    ], style={
        "padding": "20px",
        "max-width": "1400px",
        "margin": "0 auto"
    })


@callback(
    Output("truvari-run-dropdown", "options"),
    Input("truvari-run-dropdown", "id")
)
def load_truvari_runs(_):
    """Load runs that have Truvari results"""
    try:
        response = requests.get(f"{API_BASE_URL}/runs")
        if response.status_code == 200:
            all_runs = response.json()
            # Filter runs that have Truvari benchmarking
            runs_with_truvari = []
            for run in all_runs:
                run_name = run["run_name"]
                try:
                    bench_response = requests.get(f"{API_BASE_URL}/runs/{run_name}/benchmarking")
                    if bench_response.status_code == 200:
                        benchmarks = bench_response.json()
                        if benchmarks.get("truvari"):
                            runs_with_truvari.append({
                                "label": run_name,
                                "value": run_name
                            })
                except:
                    continue
            
            if runs_with_truvari:
                return runs_with_truvari
            else:
                return [{"label": "No runs with Truvari results found", "value": "", "disabled": True}]
    except Exception as e:
        print(f"Error loading runs: {e}")
        return [{"label": "Error loading runs", "value": "", "disabled": True}]


@callback(
    Output("truvari-results-container", "children"),
    Input("truvari-run-dropdown", "value")
)
def display_truvari_results(selected_run):
    """Display Truvari benchmarking results for the selected run"""
    if not selected_run:
        return html.Div("Please select a run to view results.", style={
            "text-align": "center",
            "padding": "40px",
            "color": "#95a5a6",
            "font-style": "italic"
        })
    
    try:
        response = requests.get(f"{API_BASE_URL}/runs/{selected_run}/truvari_metrics")
        if response.status_code != 200:
            return html.Div(f"No Truvari results found for {selected_run}", style={
                "text-align": "center",
                "padding": "40px",
                "color": "#e74c3c"
            })
        
        metrics = response.json()
        
        # Create summary cards
        summary_cards = html.Div([
            html.H2("Performance Metrics", style={"margin-bottom": "20px", "color": "#34495e"}),
            html.Div([
                # Precision card
                html.Div([
                    html.H3("Precision", style={"color": "#3498db", "margin-bottom": "10px"}),
                    html.P(f"{metrics['precision']:.2%}", style={"font-size": "32px", "font-weight": "bold", "margin": "0"}),
                    html.P("TP / (TP + FP)", style={"color": "#7f8c8d", "font-size": "14px", "margin-top": "5px"})
                ], style={
                    "flex": "1",
                    "padding": "20px",
                    "background": "#ecf0f1",
                    "border-radius": "8px",
                    "text-align": "center"
                }),
                
                # Recall card
                html.Div([
                    html.H3("Recall", style={"color": "#2ecc71", "margin-bottom": "10px"}),
                    html.P(f"{metrics['recall']:.2%}", style={"font-size": "32px", "font-weight": "bold", "margin": "0"}),
                    html.P("TP / (TP + FN)", style={"color": "#7f8c8d", "font-size": "14px", "margin-top": "5px"})
                ], style={
                    "flex": "1",
                    "padding": "20px",
                    "background": "#ecf0f1",
                    "border-radius": "8px",
                    "text-align": "center"
                }),
                
                # F1 Score card
                html.Div([
                    html.H3("F1 Score", style={"color": "#9b59b6", "margin-bottom": "10px"}),
                    html.P(f"{metrics['f1']:.4f}", style={"font-size": "32px", "font-weight": "bold", "margin": "0"}),
                    html.P("Harmonic Mean", style={"color": "#7f8c8d", "font-size": "14px", "margin-top": "5px"})
                ], style={
                    "flex": "1",
                    "padding": "20px",
                    "background": "#ecf0f1",
                    "border-radius": "8px",
                    "text-align": "center"
                }),
                
                # GT Concordance card
                html.Div([
                    html.H3("GT Concordance", style={"color": "#e67e22", "margin-bottom": "10px"}),
                    html.P(f"{metrics['gt_concordance']:.2%}", style={"font-size": "32px", "font-weight": "bold", "margin": "0"}),
                    html.P("Genotype Accuracy", style={"color": "#7f8c8d", "font-size": "14px", "margin-top": "5px"})
                ], style={
                    "flex": "1",
                    "padding": "20px",
                    "background": "#ecf0f1",
                    "border-radius": "8px",
                    "text-align": "center"
                }),
                
            ], style={
                "display": "flex",
                "gap": "20px",
                "margin-bottom": "30px"
            })
        ])
        
        # Create confusion matrix visualization
        confusion_matrix = go.Figure(data=go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=["True Reference", "Query Calls", "True Positives", "False Positives", "False Negatives"],
                color=["#3498db", "#2ecc71", "#27ae60", "#e74c3c", "#e67e22"]
            ),
            link=dict(
                source=[0, 0, 1, 1],
                target=[2, 4, 2, 3],
                value=[metrics['tp_base'], metrics['fn'], metrics['tp_comp'], metrics['fp']],
                color=["rgba(39, 174, 96, 0.4)", "rgba(230, 126, 34, 0.4)", 
                       "rgba(39, 174, 96, 0.4)", "rgba(231, 76, 60, 0.4)"]
            )
        ))
        confusion_matrix.update_layout(
            title="Variant Classification Flow",
            font=dict(size=14),
            height=400
        )
        
        # Create variant counts bar chart
        variant_counts = go.Figure(data=[
            go.Bar(name='Base (Reference)', x=['Total', 'TP', 'FN'], 
                   y=[metrics['base_cnt'], metrics['tp_base'], metrics['fn']],
                   marker_color='#3498db'),
            go.Bar(name='Comp (Query)', x=['Total', 'TP', 'FP'], 
                   y=[metrics['comp_cnt'], metrics['tp_comp'], metrics['fp']],
                   marker_color='#2ecc71')
        ])
        variant_counts.update_layout(
            title="Variant Counts",
            barmode='group',
            xaxis_title="Category",
            yaxis_title="Count",
            height=400
        )
        
        # Create genotype concordance breakdown
        gt_breakdown = go.Figure(data=[
            go.Bar(name='Correct GT', x=['TP-base', 'TP-comp'], 
                   y=[metrics['tp_base_tp_gt'], metrics['tp_comp_tp_gt']],
                   marker_color='#27ae60'),
            go.Bar(name='Incorrect GT', x=['TP-base', 'TP-comp'], 
                   y=[metrics['tp_base_fp_gt'], metrics['tp_comp_fp_gt']],
                   marker_color='#e74c3c')
        ])
        gt_breakdown.update_layout(
            title="Genotype Concordance Breakdown",
            barmode='stack',
            xaxis_title="Dataset",
            yaxis_title="Variant Count",
            height=400
        )
        
        # Detailed metrics table
        details_table = html.Div([
            html.H2("Detailed Metrics", style={"margin": "30px 0 20px 0", "color": "#34495e"}),
            html.Table([
                html.Thead(html.Tr([
                    html.Th("Metric", style={"text-align": "left", "padding": "12px", "background": "#34495e", "color": "white"}),
                    html.Th("Value", style={"text-align": "right", "padding": "12px", "background": "#34495e", "color": "white"})
                ])),
                html.Tbody([
                    html.Tr([html.Td("True Positives (Base)", style={"padding": "10px"}), html.Td(f"{metrics['tp_base']:,}", style={"text-align": "right", "padding": "10px"})]),
                    html.Tr([html.Td("True Positives (Comp)", style={"padding": "10px"}), html.Td(f"{metrics['tp_comp']:,}", style={"text-align": "right", "padding": "10px"})], style={"background": "#f8f9fa"}),
                    html.Tr([html.Td("False Positives", style={"padding": "10px"}), html.Td(f"{metrics['fp']:,}", style={"text-align": "right", "padding": "10px"})]),
                    html.Tr([html.Td("False Negatives", style={"padding": "10px"}), html.Td(f"{metrics['fn']:,}", style={"text-align": "right", "padding": "10px"})], style={"background": "#f8f9fa"}),
                    html.Tr([html.Td("Base Total (after filtering)", style={"padding": "10px"}), html.Td(f"{metrics['base_cnt']:,}", style={"text-align": "right", "padding": "10px"})]),
                    html.Tr([html.Td("Comp Total (after filtering)", style={"padding": "10px"}), html.Td(f"{metrics['comp_cnt']:,}", style={"text-align": "right", "padding": "10px"})], style={"background": "#f8f9fa"}),
                    html.Tr([html.Td("TP-base with correct GT", style={"padding": "10px"}), html.Td(f"{metrics['tp_base_tp_gt']:,}", style={"text-align": "right", "padding": "10px"})]),
                    html.Tr([html.Td("TP-base with incorrect GT", style={"padding": "10px"}), html.Td(f"{metrics['tp_base_fp_gt']:,}", style={"text-align": "right", "padding": "10px"})], style={"background": "#f8f9fa"}),
                    html.Tr([html.Td("TP-comp with correct GT", style={"padding": "10px"}), html.Td(f"{metrics['tp_comp_tp_gt']:,}", style={"text-align": "right", "padding": "10px"})]),
                    html.Tr([html.Td("TP-comp with incorrect GT", style={"padding": "10px"}), html.Td(f"{metrics['tp_comp_fp_gt']:,}", style={"text-align": "right", "padding": "10px"})], style={"background": "#f8f9fa"}),
                ])
            ], style={"width": "100%", "border-collapse": "collapse", "box-shadow": "0 2px 4px rgba(0,0,0,0.1)"})
        ])
        
        return html.Div([
            summary_cards,
            html.Div([
                html.Div([dcc.Graph(figure=confusion_matrix)], style={"flex": "1"}),
                html.Div([dcc.Graph(figure=variant_counts)], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "20px", "margin-bottom": "20px"}),
            html.Div([
                dcc.Graph(figure=gt_breakdown)
            ], style={"margin-bottom": "20px"}),
            details_table
        ])
        
    except Exception as e:
        print(f"Error displaying Truvari results: {e}")
        return html.Div(f"Error loading Truvari results: {str(e)}", style={
            "text-align": "center",
            "padding": "40px",
            "color": "#e74c3c"
        })

