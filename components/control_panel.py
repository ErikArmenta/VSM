"""
components/control_panel.py
Panel derecho "Generate Data Control" — sliders de Takt Time, botones de estado,
botón de reporte y tabla compacta de procesos con C/T y WIP.
"""

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config.settings import (
    COLOR_BG_SECONDARY,
    COLOR_GOLD,
    COLOR_RED_MAIN,
    COLOR_RED_DARK,
    COLOR_WHITE,
    COLOR_BORDER,
    COLOR_TEXT_SECONDARY,
)


# ---------------------------------------------------------------------------
# CSS local del panel (inyectado una sola vez por render)
# ---------------------------------------------------------------------------

_PANEL_CSS = f"""
<style>
/* ── Título del panel ── */
.cp-title {{
    color: {COLOR_GOLD};
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
    font-family: 'Segoe UI', sans-serif;
}}

/* ── Etiquetas de slider ── */
.stSlider label {{
    color: {COLOR_GOLD} !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
}}

/* ── Track del slider: rojo EA ── */
.stSlider [data-testid="stSlider"] div[class*="StyledThumb"] {{
    background: {COLOR_RED_MAIN} !important;
    border-color: {COLOR_RED_MAIN} !important;
}}
.stSlider [data-testid="stSlider"] [class*="stSliderTrackActive"] {{
    background: {COLOR_RED_MAIN} !important;
}}

/* ── Botones de estado (Estado Actual / Estado Futuro) ── */
.state-btn-active > div > button {{
    background-color: {COLOR_RED_MAIN} !important;
    color: {COLOR_WHITE} !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
}}
.state-btn-active > div > button:hover {{
    background-color: {COLOR_RED_DARK} !important;
}}
.state-btn-inactive > div > button {{
    background-color: #2D2D3A !important;
    color: {COLOR_TEXT_SECONDARY} !important;
    border: 1px solid {COLOR_BORDER} !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
}}
.state-btn-inactive > div > button:hover {{
    background-color: #3A3A4A !important;
    color: {COLOR_WHITE} !important;
}}

/* ── Botón Generate Report ── */
.report-btn > div > button {{
    background-color: {COLOR_RED_MAIN} !important;
    color: {COLOR_WHITE} !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1rem !important;
    width: 100% !important;
    letter-spacing: 0.04em;
}}
.report-btn > div > button:hover {{
    background-color: {COLOR_RED_DARK} !important;
    box-shadow: 0 0 10px rgba(211,47,47,0.5);
}}

/* ── Tabla compacta ── */
.cp-table-wrap {{
    margin-top: 0.5rem;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid {COLOR_BORDER};
}}
.cp-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: 'Segoe UI', monospace;
    font-size: 0.78rem;
    background: {COLOR_BG_SECONDARY};
}}
.cp-table thead tr {{
    background: #0E1117;
}}
.cp-table thead th {{
    color: {COLOR_GOLD};
    font-weight: 700;
    padding: 6px 8px;
    text-align: left;
    border-bottom: 1px solid {COLOR_BORDER};
    letter-spacing: 0.06em;
    font-size: 0.72rem;
    text-transform: uppercase;
}}
.cp-table tbody tr {{
    border-bottom: 1px solid {COLOR_BORDER};
    transition: background 0.15s;
}}
.cp-table tbody tr:hover {{
    background: #22253A;
}}
.cp-table tbody tr:last-child {{
    border-bottom: none;
}}
.cp-table tbody td {{
    color: {COLOR_WHITE};
    padding: 5px 8px;
}}
.cp-table tbody td.bottleneck-row {{
    color: {COLOR_RED_MAIN};
    font-weight: 600;
}}
.cp-table tbody td.ct-violation {{
    color: #FF6B6B;
}}
.cp-badge-violation {{
    display: inline-block;
    background: {COLOR_RED_MAIN};
    color: white;
    font-size: 0.62rem;
    padding: 1px 4px;
    border-radius: 3px;
    margin-left: 4px;
    vertical-align: middle;
}}
.cp-badge-bottleneck {{
    display: inline-block;
    background: #FFC107;
    color: #000;
    font-size: 0.62rem;
    padding: 1px 4px;
    border-radius: 3px;
    margin-left: 4px;
    vertical-align: middle;
}}

/* ── Divisor ── */
.cp-divider {{
    border: none;
    border-top: 1px solid {COLOR_BORDER};
    margin: 0.75rem 0;
}}

/* ── Minutero de Takt ── */
.cp-takt-min {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 0.75rem;
    margin-top: -0.4rem;
    margin-bottom: 0.6rem;
    font-family: monospace;
}}
.cp-takt-min span {{
    color: {COLOR_GOLD};
    font-weight: 700;
}}
</style>
"""


# ---------------------------------------------------------------------------
# Función pública principal
# ---------------------------------------------------------------------------

def render_control_panel(
    df: pd.DataFrame,
    metrics: dict,
    on_state_change: callable = None,
) -> tuple[float | None, str]:
    """
    Renderiza el panel lateral derecho 'Generate Data Control'.

    Parámetros:
        df              : DataFrame de procesos activos.
        metrics         : Dict de compute_metrics() — usa 'takt' y 'process_metrics'.
        on_state_change : Callback opcional invocado cuando cambia el modo de estado.
                          Firma: on_state_change(state_mode: str) -> None.

    Retorna:
        takt_override : Valor del slider de Takt Time en segundos (float),
                        o None si no se modificó el valor calculado.
        state_mode    : 'actual' | 'futuro' — modo activo seleccionado.
    """
    # ── Inyectar CSS del panel ──────────────────────────────────────────────
    st.markdown(_PANEL_CSS, unsafe_allow_html=True)

    # ── Título ─────────────────────────────────────────────────────────────
    st.markdown('<div class="cp-title">Generate Data Control</div>', unsafe_allow_html=True)

    # ── Session state para persistencia ────────────────────────────────────
    if "cp_state_mode" not in st.session_state:
        st.session_state.cp_state_mode = "actual"

    state_mode: str = st.session_state.cp_state_mode

    # ── Slider: Takt Time (s/Me) ────────────────────────────────────────────
    calculated_takt = float(metrics.get("takt", 60.0))
    if calculated_takt <= 0:
        calculated_takt = 60.0

    # Rango dinámico: desde la mitad hasta el doble del takt calculado
    slider_min = max(1.0, round(calculated_takt * 0.25, 1))
    slider_max = round(calculated_takt * 2.5, 1)
    slider_step = max(0.5, round((slider_max - slider_min) / 200, 1))

    takt_sec = st.slider(
        "Takt Time (s/Me)",
        min_value=float(slider_min),
        max_value=float(slider_max),
        value=float(round(calculated_takt, 1)),
        step=float(slider_step),
        key="cp_takt_slider",
        help="Ajusta el Takt Time para análisis de escenarios. El valor base se calcula automáticamente.",
    )

    # Conversión a minutos con display compacto
    takt_min = takt_sec / 60.0
    st.markdown(
        f'<div class="cp-takt-min">= <span>{takt_min:.3f} min</span></div>',
        unsafe_allow_html=True,
    )

    takt_override = takt_sec if abs(takt_sec - calculated_takt) > 0.01 else None

    st.markdown('<hr class="cp-divider"/>', unsafe_allow_html=True)

    # ── Botones de estado ───────────────────────────────────────────────────
    col_actual, col_futuro = st.columns(2)

    actual_class = "state-btn-active" if state_mode == "actual" else "state-btn-inactive"
    futuro_class = "state-btn-active" if state_mode == "futuro" else "state-btn-inactive"

    with col_actual:
        st.markdown(f'<div class="{actual_class}">', unsafe_allow_html=True)
        if st.button("Estado Actual", key="cp_btn_actual", use_container_width=True):
            st.session_state.cp_state_mode = "actual"
            state_mode = "actual"
            if on_state_change:
                on_state_change("actual")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_futuro:
        st.markdown(f'<div class="{futuro_class}">', unsafe_allow_html=True)
        if st.button("Estado Futuro", key="cp_btn_futuro", use_container_width=True):
            st.session_state.cp_state_mode = "futuro"
            state_mode = "futuro"
            if on_state_change:
                on_state_change("futuro")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<hr class="cp-divider"/>', unsafe_allow_html=True)

    # ── Botón Generate Industrial VSM Report ───────────────────────────────
    _render_report_button(df, metrics, takt_sec)

    st.markdown('<hr class="cp-divider"/>', unsafe_allow_html=True)

    # ── Tabla compacta Data | C/T | WIP ────────────────────────────────────
    _render_process_table(metrics)

    return takt_override, state_mode


# ---------------------------------------------------------------------------
# Sub-componente: botón de reporte
# ---------------------------------------------------------------------------

def _render_report_button(df: pd.DataFrame, metrics: dict, takt_sec: float) -> None:
    """Botón grande que genera y descarga los reportes PDF y HTML."""
    st.markdown('<div class="report-btn">', unsafe_allow_html=True)
    generate_clicked = st.button(
        "⚙ Generate Industrial VSM Report",
        key="cp_btn_report",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if generate_clicked:
        _handle_report_generation(df, metrics, takt_sec)


def _handle_report_generation(df: pd.DataFrame, metrics: dict, takt_sec: float) -> None:
    """Genera PDF y HTML y los expone como botones de descarga."""
    try:
        from components.report_generator import generate_pdf_report, generate_html_report
    except ImportError:
        st.error("report_generator no encontrado. Asegúrate de que components/report_generator.py existe.")
        return

    with st.spinner("Generando reporte…"):
        try:
            pdf_bytes = generate_pdf_report(df, metrics)
            html_str = generate_html_report(df, metrics)

            col_pdf, col_html = st.columns(2)
            with col_pdf:
                st.download_button(
                    label="📄 Descargar PDF",
                    data=pdf_bytes,
                    file_name="vsm_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="cp_dl_pdf",
                )
            with col_html:
                st.download_button(
                    label="🌐 Descargar HTML",
                    data=html_str.encode("utf-8"),
                    file_name="vsm_report.html",
                    mime="text/html",
                    use_container_width=True,
                    key="cp_dl_html",
                )
            st.success("Reporte generado exitosamente.")
        except Exception as exc:
            st.error(f"Error al generar el reporte: {exc}")


# ---------------------------------------------------------------------------
# Sub-componente: tabla de procesos
# ---------------------------------------------------------------------------

def _render_process_table(metrics: dict) -> None:
    """
    Tabla compacta dark con columnas Data | C/T | WIP.
    Headers dorados, fondo #1A1C24, texto blanco.
    Marca violaciones de Takt con badge rojo y cuello de botella en dorado.
    """
    process_metrics: list = metrics.get("process_metrics", [])
    takt: float = float(metrics.get("takt", 0))

    if not process_metrics:
        st.markdown(
            f'<p style="color:{COLOR_TEXT_SECONDARY}; font-size:0.8rem; text-align:center;">'
            "Sin datos de procesos</p>",
            unsafe_allow_html=True,
        )
        return

    # Construir filas HTML
    rows_html = ""
    for pm in process_metrics:
        name = pm.get("name", "—")
        ct = pm.get("ct", 0)
        wip = pm.get("wip", 0)
        is_violation = pm.get("ct_violation", False)
        is_bottleneck = pm.get("is_bottleneck", False)

        # Badges
        badges = ""
        if is_violation:
            badges += '<span class="cp-badge-violation">!</span>'
        if is_bottleneck:
            badges += '<span class="cp-badge-bottleneck">BN</span>'

        # Clase CSS para la celda de nombre
        name_class = "bottleneck-row" if is_bottleneck else ""
        ct_class = "ct-violation" if is_violation else ""

        rows_html += f"""
        <tr>
            <td class="{name_class}">{name}{badges}</td>
            <td class="{ct_class}">{ct:.0f}s</td>
            <td>{wip}</td>
        </tr>"""

    table_html = f"""
    <div class="cp-table-wrap">
        <table class="cp-table">
            <thead>
                <tr>
                    <th>Data</th>
                    <th>C/T</th>
                    <th>WIP</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """

    # Footer de la tabla: takt actual
    if takt > 0:
        table_html += (
            f'<div style="color:{COLOR_TEXT_SECONDARY}; font-size:0.7rem; '
            f'margin-top:4px; text-align:right; font-family:monospace;">'
            f'Takt base: <span style="color:{COLOR_GOLD};">{takt:.1f}s</span>'
            f" &nbsp;|&nbsp; ! = viola Takt &nbsp;|&nbsp; BN = Cuello de Botella"
            f"</div>"
        )

    st.markdown(table_html, unsafe_allow_html=True)
