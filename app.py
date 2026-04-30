"""app.py — Entry point principal Digital VSM & Operational Intelligence."""
import streamlit as st

from config.styles import inject_css, render_footer
from components.sidebar import render_sidebar
from components.vsm_diagram import render_vsm_diagram
from components.timeline_chart import render_timeline_chart
from components.kpi_dashboard import render_kpi_dashboard
from components.control_panel import render_control_panel
from core.lean_engine import compute_metrics

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Digital VSM - EA Innovation & Solutions",
    layout="wide",
    page_icon="🏭",
)
inject_css()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#FFC107;margin-bottom:0'>🏭 Digital VSM &amp; Operational Intelligence"
    " — EA Innovation &amp; Solutions</h1>",
    unsafe_allow_html=True,
)
st.divider()

# ── Sidebar → parámetros y datos ─────────────────────────────────────────────
available_sec, daily_demand, df_to_use, sim_mode = render_sidebar()

# ── Validación de datos ───────────────────────────────────────────────────────
if df_to_use.empty:
    st.warning("⚠️ No hay procesos cargados. Verifica la conexión a Supabase o importa un archivo Excel.")
    render_footer()
    st.stop()

# ── Cálculo de métricas ───────────────────────────────────────────────────────
metrics = compute_metrics(df_to_use, available_sec, daily_demand)

# FIX: BUG-5 layout VSM full-width
# VSM a todo ancho (fuera de columns)
render_vsm_diagram(df_to_use, metrics)
st.divider()

# Gráficas + panel debajo en columns
col_charts, col_panel = st.columns([3, 1])

with col_charts:
    col_tl, col_kpi = st.columns(2)
    with col_tl:
        render_timeline_chart(df_to_use, None, metrics.get("takt", 0))  # FIX: BUG-1 corrección clave takt
    with col_kpi:
        render_kpi_dashboard(metrics, df_to_use)

with col_panel:
    render_control_panel(df_to_use, metrics, available_sec, daily_demand)  # FIX: BUG-2 pasar available_sec y daily_demand

# ── Footer ────────────────────────────────────────────────────────────────────
render_footer()
