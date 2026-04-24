# -*- coding: utf-8 -*-
"""
components/kpi_dashboard.py
KPI Dashboard: métricas Lean, gauge PCE, barras horizontales VA vs NVA, inventario WIP.
EA Innovation & Solutions — Digital VSM
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt


def render_kpi_dashboard(metrics: dict, df: pd.DataFrame):
    """
    Renderiza el dashboard de KPIs Lean:
      (a) 4 st.metric: Takt Time, Lead Time Total, PCE%, Cuello de Botella
      (b) Gauge PCE con colores EA
      (c) Barras HORIZONTALES VA vs NVA por proceso
      (d) Gráfica de área WIP por proceso (Altair)

    Parámetros
    ----------
    metrics : dict
        Resultado de compute_metrics() — claves: takt, total_va, total_lead_time,
        pce, process_metrics, has_violation, bottleneck.
    df : pd.DataFrame
        DataFrame de procesos con columnas: name, cycle_time, wip, uptime, etc.
    """

    # ----------------------------------------------------------------
    # (a) Cuatro métricas principales en columnas
    # ----------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    takt_val = metrics.get("takt", 0)
    lead_time = metrics.get("total_lead_time", 0)
    pce_val = metrics.get("pce", 0)
    bottleneck = metrics.get("bottleneck")

    col1.metric(
        label="Takt Time",
        value=f"{takt_val:.1f} s" if takt_val > 0 else "N/A",
        help="Ritmo de producción requerido: Tiempo disponible / Demanda diaria"
    )
    col2.metric(
        label="Lead Time Total",
        value=f"{lead_time:.1f} s",
        delta=f"{lead_time / 60:.1f} min",
        help="Tiempo total desde inicio hasta fin del flujo: VA + Esperas por WIP"
    )
    col3.metric(
        label="PCE %",
        value=f"{pce_val:.1f} %",
        help="Process Cycle Efficiency: Valor Agregado / Lead Time Total × 100"
    )
    col4.metric(
        label="Cuello de Botella",
        value=bottleneck if bottleneck else "N/A",
        help="Proceso con mayor C/T relativo al Takt Time"
    )

    # ----------------------------------------------------------------
    # (b) Gauge de PCE — go.Indicator idéntico al original
    # ----------------------------------------------------------------
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pce_val,
        title={"text": "Eficiencia del Proceso (PCE)", "font": {"color": "white", "size": 16}},
        delta={"reference": 40, "increasing": {"color": "#FFC107"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "white"},
            "bar": {"color": "#D32F2F"},
            "steps": [
                {"range": [0, 30], "color": "#4A1A1A"},
                {"range": [30, 70], "color": "#2D2D2D"},
                {"range": [70, 100], "color": "#1E5631"},
            ],
            "threshold": {
                "line": {"color": "#FFC107", "width": 4},
                "thickness": 0.75,
                "value": 70,
            },
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="#0E1117",
        font=dict(color="white"),
        height=300,
        margin=dict(l=30, r=30, t=60, b=20),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # ----------------------------------------------------------------
    # (c) Barras HORIZONTALES Value-Added vs Non-Value-Added
    # ----------------------------------------------------------------
    if metrics.get("process_metrics"):
        # Construir DataFrame largo con una fila por proceso/tipo
        rows = []
        for p in metrics["process_metrics"]:
            rows.append({
                "Proceso": p["name"],
                "Tipo": "Value-Added",
                "Segundos": p["va"],
            })
            rows.append({
                "Proceso": p["name"],
                "Tipo": "Non-Value-Added",
                "Segundos": p["nva"],
            })
        va_nva_df = pd.DataFrame(rows)

        # Orden de categorías: conservar el orden original de los procesos
        process_order = [p["name"] for p in metrics["process_metrics"]]

        fig_bars = px.bar(
            va_nva_df,
            x="Segundos",
            y="Proceso",
            color="Tipo",
            orientation="h",
            barmode="stack",
            title="Value-Added vs. Non-Value-Added Time",
            color_discrete_map={
                "Value-Added": "#FFC107",
                "Non-Value-Added": "#D32F2F",
            },
            category_orders={"Proceso": process_order},
            labels={"Segundos": "Value-Added vs. Non-Value-Added Time", "Proceso": ""},
        )
        fig_bars.update_layout(
            plot_bgcolor="#1A1C24",
            paper_bgcolor="#0E1117",
            font=dict(color="white"),
            legend=dict(
                title="",
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
            margin=dict(l=10, r=20, t=60, b=30),
            xaxis=dict(
                title="Value-Added vs. Non-Value-Added Time (s)",
                gridcolor="#2D2D3A",
                tickfont=dict(color="#CCCCCC"),
            ),
            yaxis=dict(
                tickfont=dict(color="white"),
                gridcolor="#2D2D3A",
            ),
            title_font=dict(color="#FFC107", size=15),
            height=max(250, len(process_order) * 55 + 80),
        )
        fig_bars.update_traces(marker_line_width=0)
        st.plotly_chart(fig_bars, use_container_width=True)

    # ----------------------------------------------------------------
    # (d) Comportamiento de Inventario WIP por proceso (Altair)
    # ----------------------------------------------------------------
    if not df.empty:
        wip_chart = (
            alt.Chart(df)
            .mark_area(opacity=0.6, color="#FFC107")
            .encode(
                x=alt.X("name:N", title="Proceso", sort=None),
                y=alt.Y("wip:Q", title="Inventario WIP (unidades)"),
                tooltip=["name", "wip"],
            )
            .properties(
                title="Comportamiento de Inventario por Etapa",
                height=350,
            )
            .configure_view(fill="#1A1C24")
            .configure_title(color="#FFC107")
            .configure_axis(
                labelColor="#CCCCCC",
                titleColor="#CCCCCC",
                gridColor="#2D2D3A",
            )
        )
        st.altair_chart(wip_chart, use_container_width=True)
