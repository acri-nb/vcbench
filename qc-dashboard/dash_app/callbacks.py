import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import callback_context
from dash.dependencies import Input, Output, ALL
import json
from dash import Input, Output, html, dcc
from dash.dependencies import State, MATCH

# imports relatifs
from .config        import INT_METRICS, FILE_TYPES, DATA_DIR, PROCESSED_DIR
from .data_loader   import list_files, load_data
from .visualization import create_row_plot, create_bar_plot

def build_two_column_tables(df: pd.DataFrame, metrics: list[str], ref: str, height: int = 150):
    """
    Découpe la liste `metrics` en deux moitiés, génère deux html.Table avec mini-boxplots,
    et retourne (table_left, table_right).
    """
    header = html.Tr([html.Th("Parameter"), html.Th(ref), html.Th("Distribution")])
    mid = len(metrics) // 2

    def make_table_slice(slice_metrics):
        rows = [header]
        for metric in slice_metrics:
            vals    = df.loc[metric].dropna().tolist()
            ref_val = df.loc[metric, ref]
            if metric in INT_METRICS and pd.notna(ref_val):
                disp = f"{int(ref_val):,}"
            elif pd.notna(ref_val):
                disp = f"{ref_val:.4f}"
            else:
                disp = ""
            plot_html = create_row_plot(vals, ref_val, height=height)

            # <-- On ajoute "overflow": "hidden" ICI
            iframe_style = {
                "width":  "100%",
                "height": f"{height}px",
                "border": "none",
                "overflow": "hidden"
            }

            rows.append(html.Tr([
                html.Td(metric),
                html.Td(disp),
                html.Td(
                    html.Iframe(
                        srcDoc=plot_html,
                        style=iframe_style
                    ),
                    className="dist-cell"
                )
            ]))
        return html.Table(rows, style={"width":"100%","borderCollapse":"collapse"})

    table_left  = make_table_slice(metrics[:mid])
    table_right = make_table_slice(metrics[mid:])
    return table_left, table_right

def register_nav_callbacks(app):

    @app.callback(
        Output("save-status-msg", "children"),
        Input("save-report-btn", "n_clicks"),
        State("ref-dropdown", "value"),
        State({"type": "status-selector", "index": ALL}, "value"),
        State({"type": "status-selector", "index": ALL}, "id"),
        prevent_initial_call=True
    )
    def save_custom_report(n_clicks, sample, values, ids):
        print("save_custom_report")
        if not sample:
            return "⚠️ Aucun échantillon sélectionné."

        lines = [f"------------------------\nNOM : {sample}\n------------------------\n"]
        for val, id_dict in zip(values, ids):
            ftype = id_dict["index"]
            statut = val or "non défini"
            lines.append(f"------------------------\n{ftype}\n------------------------\nStatut : {statut}\n")

        out_dir = os.path.join(PROCESSED_DIR, sample)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{sample}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return html.Span([
            "✅ Fichier généré :", html.Br(), f"{sample}.txt"
        ])

    @app.callback(
        Output("type-dropdown", "value"),
        Input({"type": "nav-item", "index": ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def on_nav_click(n_clicks):
        ctx = callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate
        triggered_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
        return triggered_id["index"]

    return app
def register_nav_active_callback(app):
    @app.callback(
        Output({'type': 'nav-item', 'index': ALL}, 'className'),
        Input({'type': 'nav-item', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def set_active(n_clicks_list):
        print("set_active")
        ctx = callback_context
        if not ctx.triggered:
            # Aucun clic déclencheur -> on ne met pas à jour
            raise dash.exceptions.PreventUpdate

        # Récupère l'index du bouton cliqué
        triggered_index = ctx.triggered_id['index']

        # Met à jour la classe de chaque bouton en comparant son id["index"]
        return [
            "nav-item active" if btn['id']['index'] == triggered_index else "nav-item"
            for btn in ctx.inputs_list[0]
        ]

    return app
def register_callbacks(app):
    @app.callback(
        Output("manual-status-container", "children"),
        Input("ref-dropdown", "value")
    )
    def update_manual_status_ui(sample):
        print("update_manual_status_ui")
        if not sample:
            return html.P("Select a run to define metrics status")

        dropdowns = []
        for ftype in FILE_TYPES:
            dropdowns.append(html.Div([
                html.Label(f"{ftype} :", style={"fontWeight": "bold", "marginTop": "10px"}),
                dcc.Dropdown(
                    id={"type": "status-selector", "index": ftype},
                    options=[
                        {"label": "✅ pass", "value": "pass", "className": "status-pass"},
                        {"label": "⚠️ warning", "value": "warning", "className": "status-warning"},
                        {"label": "❌ fail", "value": "fail", "className": "status-fail"}
                    ],
                    placeholder="Select Status",
                    clearable=False,
                    style={"width": "220px", "marginBottom": "12px"}
                )
            ]))
        return dropdowns
    @app.callback(
        [
            Output("table-container", "children"),
            Output("ref-dropdown",  "options"),
            Output("ref-dropdown",  "value")
        ],
        [
            Input("type-dropdown", "value"),
            Input("ref-dropdown",  "value")
        ]
    )
    def update_table(file_type, ref_sample):
        print("update_table")
        # 1) Lister les fichiers
        files = list_files(file_type)
        if not files:
            return html.P("Aucun fichier disponible"), [], None

        # 2a) Cas spécial ROH + Het/Hom (ratio uniquement)
        if file_type == "ROH_metrics":
            df_roh    = load_data("ROH_metrics").dropna(how="all")
            df_hethom = load_data("HeThom").dropna(how="all")

            samples = df_roh.columns.tolist()
            ref     = ref_sample if ref_sample in samples else samples[0]
            options = [{"label": s, "value": s} for s in samples]

            # Préparation des données
            ratio_metrics = [m for m in df_hethom.index if "het/hom" in m.lower()]
            values        = [df_hethom.loc[m, ref] for m in ratio_metrics]
            # on garde chaque étiquette courte : tout ce qui précède le premier espace
            labels = [m.split()[0] for m in ratio_metrics]

            # Inline barplot avec libellé commun centré sous l'axe X
            fig = go.Figure(go.Bar(x=ratio_metrics, y=values))
            fig.update_layout(
                title=f"Ratio Het/Hom pour {ref}",
                margin=dict(l=20, r=20, t=40, b=60),
                height=300
            )
            fig.update_xaxes(
                ticktext=labels,        # valeurs sous chaque barre
                tickvals=ratio_metrics, # position sur les mêmes catégories
                tickangle=0,
                title_text="het/hom"     # libellé commun centré
            )

            bar_html = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn",
                config={"displayModeBar": False}
            )

            # Tableau + boxplots ROH (inchangé)
            header = html.Tr([html.Th("Parameter"), html.Th(ref), html.Th("Distribution")])
            rows   = [header]
            for metric in df_roh.index:
                vals    = df_roh.loc[metric].dropna().tolist()
                ref_val = df_roh.loc[metric, ref]
                if metric in INT_METRICS and pd.notna(ref_val):
                    disp = f"{int(ref_val):,}"
                elif pd.notna(ref_val):
                    disp = f"{ref_val:.4f}"
                else:
                    disp = ""
                plot_html = create_row_plot(vals, ref_val)
                rows.append(html.Tr([
                    html.Td(metric),
                    html.Td(disp),
                    html.Td(
                        html.Iframe(
                            srcDoc=plot_html,
                            style={"width":"100%","height":"150px","border":"none"}
                        ),
                        className="dist-cell"
                    )
                ]))
            table = html.Table(
                rows,
                style={"width":"100%","borderCollapse":"collapse","marginTop":"20px"}
            )

            return (
                html.Div([
                    html.H2("Barplot Het/Hom", style={"marginTop":"10px"}),
                    html.Iframe(srcDoc=bar_html,
                                style={"width":"100%","height":"300px","border":"none"}),
                    html.H2("Métriques ROH",      style={"marginTop":"20px"}),
                    table
                ]),
                options,
                ref
            )



        # 2b) Cas spécial Ploidy
        elif file_type == "Ploidy":
            df_ploidy = load_data("Ploidy").dropna(how="all")

            samples = df_ploidy.columns.tolist()
            ref     = ref_sample if ref_sample in samples else samples[0]
            options = [{"label": s, "value": s} for s in samples]

            # Séparation des métriques
            metrics = df_ploidy.index.tolist()
            first3  = metrics[:3]
            last2   = metrics[-2:]
            rest    = metrics[3:-2]

            # — Barplot pour les métriques intermédiaires —
            # labels réduits (ex. "1", "2", … ou autre clé avant le slash)
            labels = [m.split()[0] for m in rest]

            fig = go.Figure(go.Bar(
                x=labels,
                y=[df_ploidy.loc[m, ref] for m in rest]
            ))
            fig.update_layout(
                title=f"Ploidy estimation pour {ref}",
                # seul intitulé centré sous l'axe X :
                xaxis_title="Median / Autosomal median",
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=40, b=60),
                height=300
            )
            bar_html = fig.to_html(
                full_html=False,
                include_plotlyjs="cdn",
                config={"displayModeBar": False}
            )

            # — Tableau + boxplots pour les 3 premières et les 2 dernières —
            header = html.Tr([html.Th("Parameter"), html.Th(ref), html.Th("Distribution")])
            rows   = [header]
            for metric in first3 + last2:
                vals    = df_ploidy.loc[metric].dropna().tolist()
                ref_val = df_ploidy.loc[metric, ref]
                if metric in INT_METRICS and pd.notna(ref_val):
                    disp = f"{int(ref_val):,}"
                elif pd.notna(ref_val):
                    disp = f"{ref_val:.4f}"
                else:
                    disp = ""
                plot_html = create_row_plot(vals, ref_val)
                rows.append(html.Tr([
                    html.Td(metric),
                    html.Td(disp),
                    html.Td(
                        html.Iframe(
                            srcDoc=plot_html,
                            style={"width":"100%","height":"150px","border":"none"}
                        ),
                        className="dist-cell"
                    )
                ]))
            table = html.Table(
                rows,
                style={"width":"100%","borderCollapse":"collapse","marginTop":"20px"}
            )

            return (
                html.Div([
                    html.H2("Ploidy estimation",      style={"marginTop":"10px"}),
                    html.Iframe(srcDoc=bar_html,      style={"width":"100%","height":"300px","border":"none"}),
                    html.H2("Metrics sélectionnées",  style={"marginTop":"20px"}),
                    table
                ]),
                options,
                ref
            )
         # 2c) Cas spécial Bed coverage
        elif file_type == "bed_coverage":
            # charge les données
            df_cov  = load_data("bed_coverage").dropna(how="all")
            samples = df_cov.columns.tolist()
            ref     = ref_sample if ref_sample in samples else samples[0]
            options = [{"label": s, "value": s} for s in samples]

            # repérer les intervalles [ ... : ... )
            intervals = [
                m for m in df_cov.index
                if "[" in m and ":" in m and m.strip().endswith(")")
            ]
            inf_ints = [m for m in intervals if "inf" in m.lower()]
            reg_ints = [m for m in intervals if m not in inf_ints]
            rest     = [m for m in df_cov.index if m not in intervals]

            # labels = juste la partie entre crochets
            labels_inf = [m[m.find("["):] for m in inf_ints]
            labels_reg = [m[m.find("["):] for m in reg_ints]

            # import nécessaire en haut du fichier
            # import plotly.graph_objects as go

            # Barplot ≥ inf
            fig_inf = go.Figure(go.Bar(
                x=labels_inf,
                y=[df_cov.loc[m, ref] for m in inf_ints]
            ))
            fig_inf.update_layout(
                title=f"Coverage ≥ inf pour {ref}",
                xaxis_title="PCT of genome with coverage",
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=40, b=60),
                height=300
            )
            bar_html1 = fig_inf.to_html(
                full_html=False, include_plotlyjs="cdn",
                config={"displayModeBar": False}
            )

            # Barplot intervalles
            fig_reg = go.Figure(go.Bar(
                x=labels_reg,
                y=[df_cov.loc[m, ref] for m in reg_ints]
            ))
            fig_reg.update_layout(
                title=f"Coverage intervalles pour {ref}",
                xaxis_title="PCT of genome with coverage",
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=40, b=60),
                height=300
            )
            bar_html2 = fig_reg.to_html(
                full_html=False, include_plotlyjs="cdn",
                config={"displayModeBar": False}
            )

            # Tableau + boxplots pour le reste
            header = html.Tr([html.Th("Parameter"), html.Th(ref), html.Th("Distribution")])
            rows   = [header]
            for metric in rest:
                vals    = df_cov.loc[metric].dropna().tolist()
                ref_val = df_cov.loc[metric, ref]
                disp    = (
                    f"{int(ref_val):,}" if metric in INT_METRICS and pd.notna(ref_val)
                    else f"{ref_val:.4f}" if pd.notna(ref_val)
                    else ""
                )
                plot_html = create_row_plot(vals, ref_val)
                rows.append(html.Tr([
                    html.Td(metric),
                    html.Td(disp),
                    html.Td(
                        html.Iframe(
                            srcDoc=plot_html,
                            style={"width":"100%","height":"150px","border":"none"}
                        ),
                        className="dist-cell"
                    )
                ]))
            table = html.Table(
                rows,
                style={"width":"100%","borderCollapse":"collapse","marginTop":"20px"}
            )

            # … après avoir calculé rest, df_cov, samples, options, ref, bar_html1, bar_html2 …
            rest = [m for m in df_cov.index if m not in intervals]
            table_left, table_right = build_two_column_tables(df_cov, rest, ref, height=100)

            return (
                html.Div([
                    # ── Ligne du haut : les deux barplots full-width ──
                    html.Div([
                        html.H2("Coverage ≥ inf", style={"marginTop": "10px"}),
                        html.Iframe(
                            srcDoc=bar_html1,
                            style={"width": "100%", "height": "300px", "border": "none"}
                        ),
                        html.H2("Coverage par intervalles", style={"marginTop": "20px"}),
                        html.Iframe(
                            srcDoc=bar_html2,
                            style={"width": "100%", "height": "300px", "border": "none"}
                        )
                    ], style={"width": "100%", "marginBottom": "40px"}),

                    # ── Ligne du bas : deux tables côte à côte ──
                    html.Div([
                        html.Div(table_left,  className="left"),
                        html.Div(table_right, className="right")
                    ], className="section-container")

                ]),
                options,
                ref
            )

        # 2d) Cas WGS_contig_mean_cov → deux barplots (value & mean_coverage)
        elif file_type == "WGS_contig_mean_cov":
            # 1) Charger tous les CSV et construire data_dict[sample] = DataFrame[…, ['value','mean_coverage']]
            suffix    = FILE_TYPES["WGS_contig_mean_cov"].lower()
            data_dict = {}
            for root, _, files in os.walk(PROCESSED_DIR):
                for f in files:
                    if f.lower().endswith(suffix):
                        sample = os.path.basename(os.path.dirname(os.path.join(root, f)))
                        dfc = pd.read_csv(os.path.join(root, f), usecols=["chromosome", "value", "mean_coverage"])
                        dfc = dfc.set_index("chromosome")
                        data_dict[sample] = dfc

            # 2) Préparer dropdown
            samples = sorted(data_dict.keys())
            options = [{"label": s, "value": s} for s in samples]
            ref     = ref_sample if ref_sample in samples else (samples[0] if samples else None)
            if ref is None:
                return html.P("Aucun fichier WGS_contig_mean_cov trouvé"), [], None

            # 3) Extraire le DataFrame du sample choisi
            df = data_dict[ref].dropna()

            # 4) Forcer l’ordre exact chr1→chr22→chrX→chrY→chrM
            contig_order = [f"chr{i}" for i in range(1,23)] + ["chrX","chrY","chrM"]
            df = df.loc[df.index.intersection(contig_order)]
            df.index = pd.Categorical(df.index, categories=contig_order, ordered=True)
            df = df.sort_index()

            # 5) Créer les deux barplots
            fig_val = px.bar(
                x=df.index, y=df["value"],
                title=f"Value – {ref} (chr1→chrM)",
                labels={"x":"Contig","y":"Value"}
            )
            fig_val.update_yaxes(type="log")
            fig_cov = px.bar(
                x=df.index, y=df["mean_coverage"],
                title=f"Mean Coverage – {ref} (chr1→chrM)",
                labels={"x":"Contig","y":"Mean Coverage"}
            )
            fig_cov.update_yaxes(type="log")
            # rotation et marges
            for fig in (fig_val, fig_cov):
                fig.update_layout(xaxis_tickangle=-45, margin={"t":40,"b":120})

            # 6) Retourner un conteneur avec les deux Graph
            container = html.Div([
                html.Div(dcc.Graph(figure=fig_val), style={"marginBottom":"40px"}),
                html.Div(dcc.Graph(figure=fig_cov))
            ])
            return container, options, ref
               # ── 2e) Cas mapping_metrics → histogrammes + deux-colonnes mini-boxplots ──
        elif file_type == "mapping_metrics":
            suffix = FILE_TYPES["mapping_metrics"].lower()
            data_val, data_pct = {}, {}

            # 1) Charger tous les mapping_metrics.csv sans exiger la colonne "percentage"
            for root, _, files in os.walk(PROCESSED_DIR):
                for f in files:
                    if f.lower().endswith(suffix):
                        path   = os.path.join(root, f)
                        sample = os.path.basename(root)
                        dfc    = pd.read_csv(path)
                        if not {"parameter", "value"}.issubset(dfc.columns):
                            continue
                        dfc = dfc.set_index("parameter")
                        data_val[sample] = pd.to_numeric(dfc["value"], errors="coerce")
                        if "percentage" in dfc.columns:
                            data_pct[sample] = pd.to_numeric(dfc["percentage"], errors="coerce")

            # 2) Dropdown des échantillons
            samples = sorted(data_val.keys())
            options = [{"label": s, "value": s} for s in samples]
            ref     = ref_sample if ref_sample in samples else (samples[0] if samples else None)
            if ref is None:
                return html.P("Aucun fichier mapping_metrics trouvé"), [], None

            # 3) DataFrames globaux
            df_val = pd.DataFrame(data_val).dropna(how="all")
            df_pct = pd.DataFrame(data_pct).dropna(how="all")

            # 4) Sélection des buckets MAPQ
            mapq_metrics = [m for m in df_val.index if "Reads with MAPQ" in m]

            # 5) Préparer et afficher les histogrammes MAPQ
            labels, vals, pcts = [], [], []
            for m in mapq_metrics:
                rng = m[m.find("[")+1 : m.find(")")]
                rng = rng.replace(":", "-").replace("inf", "+")
                labels.append(rng)
                vals.append(df_val.at[m, ref] if m in df_val.index else 0)
                pcts.append(
                    df_pct.at[m, ref]
                    if (m in df_pct.index and ref in df_pct.columns)
                    else 0
                )

            charts = [
                html.H2("Distribution MAPQ (raw counts)", style={"marginBottom":"10px"}),
                dcc.Graph(
                    figure=px.bar(
                        pd.DataFrame({"MAPQ": labels, "Reads": vals}),
                        x="MAPQ", y="Reads",
                        title=f"Reads by MAPQ – {ref}"
                    ).update_layout(xaxis_tickangle=-45, margin={"t":40,"b":80}, height=300)
                )
            ]
            if not df_pct.empty:
                charts += [
                    html.H2("Distribution MAPQ (% reads)", style={"marginTop":"30px","marginBottom":"10px"}),
                    dcc.Graph(
                        figure=px.bar(
                            pd.DataFrame({"MAPQ": labels, "% Reads": pcts}),
                            x="MAPQ", y="% Reads",
                            title=f"% Reads by MAPQ – {ref}"
                        ).update_layout(xaxis_tickangle=-45, margin={"t":40,"b":80}, height=300)
                    )
                ]
            charts_container = html.Div(charts, style={"marginBottom":"40px"})

            # 6) Autres metrics → mini-boxplots en deux colonnes
            other_metrics = [m for m in df_val.index if m not in mapq_metrics]
            mid = len(other_metrics) // 2
            left_metrics, right_metrics = other_metrics[:mid], other_metrics[mid:]

            header_row = html.Tr([html.Th("Parameter"), html.Th(ref), html.Th("Distribution")])
            rows_left, rows_right = [header_row], [header_row]

            def make_rows(metrics_list, rows):
                for metric in metrics_list:
                    sub = df_val.loc[metric]
                    if isinstance(sub, pd.DataFrame):
                        vals_dist = sub.values.flatten().tolist()
                        ref_val   = sub[ref].iloc[0]
                    else:
                        vals_dist = sub.dropna().tolist()
                        ref_val   = sub.get(ref, None)

                    if metric in INT_METRICS and pd.notna(ref_val):
                        disp = f"{int(ref_val):,}"
                    elif pd.notna(ref_val):
                        disp = f"{ref_val:.4f}"
                    else:
                        disp = ""

                    plot_html = create_row_plot(vals_dist, ref_val)
                    rows.append(html.Tr([
                        html.Td(metric),
                        html.Td(disp),
                        html.Td(
                            html.Iframe(
                                srcDoc=plot_html,
                                style={"width":"100%","height":"150px","border":"none"}
                            ),
                            className="dist-cell"
                        )
                    ]))

            make_rows(left_metrics,  rows_left)
            make_rows(right_metrics, rows_right)

            table_left  = html.Table(rows_left,  style={"width":"100%","borderCollapse":"collapse"})
            table_right = html.Table(rows_right, style={"width":"100%","borderCollapse":"collapse"})

            tables_header = html.H2(
                "Other Metrics (values + distribution)",
                style={"marginTop": "0"}
            )
            tables_flex = html.Div([
                html.Div(table_left,  className="left"),
                html.Div(table_right, className="right")
            ], className="section-container")

            # 7) Retourne le conteneur complet
            container = html.Div([charts_container, tables_header, tables_flex])
            return container, options, ref


        # ── 3) Cas générique ──
        df = load_data(file_type).dropna(how="all")
        if df.empty:
            return html.P("Aucune donnée affichable…"), [], None

        samples = df.columns.tolist()
        ref     = ref_sample if ref_sample in samples else samples[0]
        options = [{"label": s, "value": s} for s in samples]

        # on récupère la liste des métriques, et on coupe en deux
        metrics = df.index.tolist()
        mid = len(metrics) // 2

        # construction des lignes pour chaque moitié
        header = html.Tr([html.Th("Parameter"), html.Th(ref), html.Th("Distribution")])

        rows_left = [header]
        for metric in metrics[:mid]:
            vals    = df.loc[metric].dropna().tolist()
            ref_val = df.loc[metric, ref]
            if metric in INT_METRICS and pd.notna(ref_val):
                disp = f"{int(ref_val):,}"
            elif ref_val == "SNP":
                continue
            elif pd.notna(ref_val):
                disp = f"{ref_val:.4f}"
            else:
                disp = ""
            plot_html = create_row_plot(vals, ref_val)
            rows_left.append(html.Tr([
                html.Td(metric),
                html.Td(disp),
                html.Td(html.Iframe(srcDoc=plot_html,
                                    style={"width":"100%","height":"150px","border":"none"}),
                        className="dist-cell")
            ]))

        rows_right = [header]
        for metric in metrics[mid:]:
            vals    = df.loc[metric].dropna().tolist()
            ref_val = df.loc[metric, ref]
            if metric in INT_METRICS and pd.notna(ref_val):
                disp = f"{int(ref_val):,}"
            elif pd.notna(ref_val):
                disp = f"{ref_val:.4f}"
            else:
                disp = ""
            plot_html = create_row_plot(vals, ref_val)
            rows_right.append(html.Tr([
                html.Td(metric),
                html.Td(disp),
                html.Td(html.Iframe(srcDoc=plot_html,
                                    style={"width":"100%","height":"150px","border":"none"}),
                        className="dist-cell")
            ]))

        # création des deux tables
        table_left  = html.Table(rows_left,  style={"width":"100%","borderCollapse":"collapse"})
        table_right = html.Table(rows_right, style={"width":"100%","borderCollapse":"collapse"})

        # on renvoie la grid 2-colonnes
        return (
            html.Div([
                html.Div(table_left,  className="left"),
                html.Div(table_right, className="right")
            ], className="section-container"),
            options,
            ref
        )