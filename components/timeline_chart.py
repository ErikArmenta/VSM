# =============================================================================
# components/timeline_chart.py — Gráfica área apilada Lead Time vs PCE
# Proyecto: Digital VSM & Operational Intelligence - EA Innovation & Solutions
# =============================================================================

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import (
    CHART_COLORS,
    COLOR_BG_PRIMARY,
    COLOR_BG_SECONDARY,
    COLOR_GOLD,
    COLOR_TEXT_SECONDARY,
    COLOR_WHITE,
    UI_STRINGS,
)

# Número de días a proyectar en la gráfica
N_DAYS = 5


# -----------------------------------------------------------------------------
# Cálculo de datos de la gráfica (cacheado)
# -----------------------------------------------------------------------------
@st.cache_data
def _build_stacked_data(
    df: pd.DataFrame,
    takt_time: float,
    n_days: int = N_DAYS,
    seed_offset: int = 0,
) -> tuple[list[str], list[dict]]:
    """
    Construye los datos de Lead Time por proceso para n_days días.

    La contribución de cada proceso al Lead Time total es:
        LT_proceso = WIP * takt_time (espera NVA) + cycle_time (VA)

    Se aplica una variación senoidal por día (±5%) para simular
    fluctuaciones reales de producción, reproducible por nombre de proceso.

    Retorna:
        days   : ['Day 1', ..., 'Day N']
        traces : lista de dicts {name, values} con Lead Time por proceso por día
                 Los valores son ACUMULADOS (para fill='tonexty' de Plotly).
    """
    if df.empty or takt_time <= 0:
        return [f"Day {i}" for i in range(1, n_days + 1)], []

    days = [f"Day {i}" for i in range(1, n_days + 1)]

    # Calcular contribución base de cada proceso al Lead Time
    process_lt = []
    for _, row in df.iterrows():
        base_lt = float(row["wip"]) * takt_time + float(row["cycle_time"])
        # Semilla reproducible basada en el nombre del proceso + offset
        name_seed = sum(ord(c) for c in str(row["name"])) + seed_offset
        # Variación por día: oscilación senoidal suave (±4%)
        daily_values = [
            max(base_lt * (1.0 + 0.04 * np.sin(i * 1.1 + name_seed % 7)), 0)
            for i in range(n_days)
        ]
        process_lt.append({"name": row["name"], "values": daily_values})

    # Acumular para stacked chart: cada trace empieza donde termina el anterior
    cumulative = [0.0] * n_days
    stacked_traces = []
    for proc in process_lt:
        cumulative = [cumulative[i] + proc["values"][i] for i in range(n_days)]
        stacked_traces.append({"name": proc["name"], "values": list(cumulative)})

    return days, stacked_traces


@st.cache_data
def _build_sim_line(
    sim_df: pd.DataFrame,
    takt_time: float,
    n_days: int = N_DAYS,
) -> tuple[list[str], list[float]]:
    """
    Calcula la línea de Lead Time total del estado futuro (simulación)
    como valores ACUMULADOS sumados sobre todos los procesos.
    """
    if sim_df is None or sim_df.empty or takt_time <= 0:
        return [f"Day {i}" for i in range(1, n_days + 1)], []

    _, stacked = _build_stacked_data(sim_df, takt_time, n_days, seed_offset=42)
    if not stacked:
        return [f"Day {i}" for i in range(1, n_days + 1)], []

    # La línea del estado futuro es el último trace acumulado (total)
    return [f"Day {i}" for i in range(1, n_days + 1)], stacked[-1]["values"]


# -----------------------------------------------------------------------------
# Renderizado del componente
# -----------------------------------------------------------------------------
def render_timeline_chart(
    df: pd.DataFrame,
    sim_df: pd.DataFrame | None,
    takt_time: float,
) -> None:
    """
    Renderiza la gráfica de área apilada Lead Time vs PCE.

    Parámetros:
        df        : DataFrame del estado actual con columnas cycle_time, wip, name.
        sim_df    : DataFrame del estado futuro (puede ser None si no hay simulación).
        takt_time : Takt Time en segundos (para calcular NVA waiting time).
    """
    if df.empty:
        st.info("Sin datos de procesos para mostrar la gráfica de Lead Time.")
        return

    days, stacked_traces = _build_stacked_data(df, takt_time)

    if not stacked_traces:
        st.info("No se pudo calcular el Lead Time. Verificar Takt Time.")
        return

    fig = go.Figure()

    # ------------------------------------------------------------------
    # Trazas de área apilada — una por proceso (estado actual)
    # ------------------------------------------------------------------
    for idx, trace in enumerate(stacked_traces):
        color_hex = CHART_COLORS[idx % len(CHART_COLORS)]
        # Convertir hex a rgba para el relleno semitransparente
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        fill_color = f"rgba({r},{g},{b},0.55)"
        line_color = f"rgba({r},{g},{b},0.90)"

        fill_mode = "tozeroy" if idx == 0 else "tonexty"

        fig.add_trace(
            go.Scatter(
                x=days,
                y=trace["values"],
                name=trace["name"],
                mode="lines",
                fill=fill_mode,
                fillcolor=fill_color,
                line=dict(color=line_color, width=1.8),
                hovertemplate=(
                    f"<b>{trace['name']}</b><br>"
                    "Día: %{x}<br>"
                    "Lead Time acumulado: %{y:.0f}s<br>"
                    "<extra></extra>"
                ),
            )
        )

    # ------------------------------------------------------------------
    # Línea de estado futuro (simulación) — si está disponible
    # ------------------------------------------------------------------
    if sim_df is not None and not sim_df.empty:
        _, sim_values = _build_sim_line(sim_df, takt_time)
        if sim_values:
            fig.add_trace(
                go.Scatter(
                    x=days,
                    y=sim_values,
                    name="Estado Futuro (Total)",
                    mode="lines+markers",
                    line=dict(color=COLOR_GOLD, width=2.5, dash="dash"),
                    marker=dict(symbol="circle", size=7, color=COLOR_GOLD),
                    hovertemplate=(
                        "<b>Estado Futuro</b><br>"
                        "Día: %{x}<br>"
                        "Lead Time total: %{y:.0f}s<br>"
                        "<extra></extra>"
                    ),
                )
            )

    # ------------------------------------------------------------------
    # Línea de Takt Time como referencia horizontal
    # ------------------------------------------------------------------
    if takt_time > 0:
        fig.add_hline(
            y=takt_time,
            line_dash="dot",
            line_color=COLOR_GOLD,
            line_width=1.5,
            annotation_text=f"Takt: {takt_time:.0f}s",
            annotation_font_color=COLOR_GOLD,
            annotation_bgcolor="rgba(0,0,0,0)",
            annotation_position="top right",
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    fig.update_layout(
        title=dict(
            text=UI_STRINGS["chart_timeline_title"],
            font=dict(color=COLOR_WHITE, size=15, family="Arial"),
            x=0.0,
            xanchor="left",
        ),
        plot_bgcolor=COLOR_BG_SECONDARY,
        paper_bgcolor=COLOR_BG_PRIMARY,
        font=dict(color=COLOR_WHITE, family="Arial", size=11),
        xaxis=dict(
            title="Día de Producción",
            title_font=dict(color=COLOR_TEXT_SECONDARY, size=11),
            tickfont=dict(color=COLOR_TEXT_SECONDARY),
            gridcolor="#2D2D3A",
            linecolor="#2D2D3A",
            zeroline=False,
        ),
        yaxis=dict(
            title="Lead Time (s)",
            title_font=dict(color=COLOR_TEXT_SECONDARY, size=11),
            tickfont=dict(color=COLOR_TEXT_SECONDARY),
            gridcolor="#2D2D3A",
            linecolor="#2D2D3A",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color=COLOR_TEXT_SECONDARY, size=10),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        margin=dict(l=50, r=20, t=60, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)
