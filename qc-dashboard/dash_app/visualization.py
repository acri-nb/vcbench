import plotly.graph_objects as go
from .config import INT_METRICS

def create_row_plot(values, ref_value, height=100):
    fig = go.Figure()

    # 1) Boîte horizontale, sans points et sans hover
    fig.add_trace(go.Box(
        x=values,
        y=[0] * len(values),
        orientation='h',
        boxpoints=False,
        hoverinfo='skip',      # désactive le tooltip sur la boîte
        fillcolor='rgba(173,216,230,0.4)',
        line_color='steelblue',
        showlegend=False
    ))

    # 2) Croix de référence, avec tooltip uniquement sur la croix
    fig.add_trace(go.Scatter(
        x=[ref_value],
        y=[0],
        mode='markers',
        marker=dict(color='red', size=10, symbol='x'),
        hovertemplate='Réf: %{x:,}<extra></extra>',
        showlegend=False
    ))

    # 3) Layout épuré, axes fixes (pas de zoom/pan)
    fig.update_layout(
        autosize=True,
        height=height,
        margin=dict(l=2, r=2, t=2, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=True,
            tickfont=dict(size=10),
            fixedrange=True,
            tickangle=0,
            automargin=True
        ),
        yaxis=dict(visible=False, fixedrange=True),
        dragmode=False
    )

    # 4) Export HTML interactif (hover uniquement sur la croix)
    return fig.to_html(
        full_html=False,
        include_plotlyjs='cdn',
        config={
            'displayModeBar': False  # barre d’outils désactivée
            # on NE met PAS 'staticPlot' ici pour garder le hover sur la croix
        }
    )





def create_bar_plot(categories, values, title="Barplot"):
    """
    Trace un barplot simple : catégories en abscisse, values en ordonnée.
    """
    fig = go.Figure(go.Bar(x=categories, y=values))
    fig.update_layout(
        title=title,
        xaxis_tickangle=-45,
        margin=dict(l=20, r=20, t=40, b=40),
        height=300
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def create_histogram(values, title="Histogramme"):
    """
    Trace un histogramme simple de la liste values.
    """
    fig = go.Figure(go.Histogram(x=values))
    fig.update_layout(
        title=title,
        margin=dict(l=20, r=20, t=40, b=40),
        height=300
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')
