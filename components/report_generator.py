"""
components/report_generator.py
Generación de reportes industriales:
  - generate_pdf_report() → bytes  (fpdf2, matplotlib, paleta EA)
  - generate_html_report() → str   (HTML whitepaper autocontenido, JS/SVG interactivo, Plotly CDN)

Ambas funciones son 100 % independientes de Streamlit en tiempo de ejecución,
por lo que pueden ser llamadas desde control_panel.py y devueltas via
st.download_button sin efectos secundarios.
"""

from __future__ import annotations

import base64
import io
import json
import os
from datetime import datetime
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # backend sin pantalla (para Streamlit Cloud)
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paleta EA (copiada de config.settings para evitar dependencia circular)
# ---------------------------------------------------------------------------
_BG       = "#0E1117"
_BG2      = "#1A1C24"
_RED      = "#D32F2F"
_RED_DARK = "#B71C1C"
_RED_ALERT= "#5C1A1A"
_GOLD     = "#FFC107"
_GOLD2    = "#FFA000"
_WHITE    = "#FFFFFF"
_GRAY     = "#CCCCCC"
_BORDER   = "#2D2D3A"

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "EA_2.png")
_COMPANY   = "EA Innovation & Solutions"
_REPORT_T  = f"Digital VSM Report — {_COMPANY}"

# ---------------------------------------------------------------------------
# Textos del resumen ejecutivo (reutilizados en PDF y HTML)
# ---------------------------------------------------------------------------
_INTRO_VSM = (
    "El Value Stream Mapping (VSM) es una herramienta fundamental de la metodología "
    "Lean Manufacturing que permite visualizar, analizar y optimizar el flujo completo "
    "de materiales e información desde el proveedor hasta el cliente. A diferencia de "
    "los diagramas de proceso convencionales, el VSM cuantifica el tiempo de valor "
    "agregado (VA) frente al tiempo total de ciclo (Lead Time), exponiendo las pérdidas "
    "ocultas —sobreproducción, esperas, inventarios excesivos— que reducen la eficiencia "
    "operativa. Su aplicación sistemática permite identificar el estado actual (current "
    "state), diseñar un estado futuro optimizado (future state) y construir un plan de "
    "implementación basado en datos reales de la línea de producción."
)

_INTERPRETATION = (
    "Takt Time (TT): Ritmo al que el cliente consume las unidades. Se calcula como "
    "tiempo disponible / demanda diaria. Todo proceso con C/T > TT genera un cuello "
    "de botella que limita el throughput de la línea. "
    "Lead Time (LT): Tiempo total que tarda una unidad en recorrer toda la cadena de "
    "valor, incluyendo esperas e inventarios intermedios. Un LT elevado implica mayor "
    "capital inmovilizado y menor capacidad de respuesta al cliente. "
    "Process Cycle Efficiency (PCE): Relacion porcentual VA/LT. La industria automotriz "
    "y manufactura discreta de clase mundial típicamente alcanza PCE > 25%. Valores "
    "inferiores al 10% indican oportunidades de mejora significativas en la reducción "
    "de inventarios y tiempos de espera. "
    "Cuello de Botella (Bottleneck): Proceso con mayor C/T relativo al Takt Time. "
    "Toda mejora de capacidad debe comenzar en este proceso; de lo contrario el "
    "throughput total no aumentará (Teoría de las Restricciones — TOC)."
)

_METHODOLOGY = (
    "La presente evaluación sigue el ciclo DMAIC (Define-Measure-Analyze-Improve-Control) "
    "adaptado al contexto VSM: (1) Definición del flujo de valor y límites del mapa; "
    "(2) Medición de tiempos de ciclo, cambios de herramental, WIP y disponibilidad de "
    "equipos (uptime); (3) Análisis mediante indicadores Lean (TT, LT, PCE, bottleneck, "
    "VA vs NVA); (4) Diseño del estado futuro con kaizens orientados a flujo y pull; "
    "(5) Control mediante seguimiento de indicadores en tiempo real."
)


# =============================================================================
# A — PDF INDUSTRIAL TÉCNICO
# =============================================================================

def generate_pdf_report(
    df: pd.DataFrame,
    metrics: dict,
    available_sec: float,
    demand: float,
) -> bytes:
    """
    Genera un PDF técnico industrial con:
      - Header logo EA + título + fecha
      - Resumen ejecutivo (VSM, métricas, metodología)
      - Tabla de procesos con colores EA
      - Sección de métricas clave con interpretación técnica
      - Diagrama VSM simplificado (matplotlib → imagen embebida)
      - Gráfica VA/NVA horizontal (matplotlib → imagen embebida)
      - Footer branding EA

    Retorna bytes listos para st.download_button(data=...).
    """
    try:
        from fpdf import FPDF
    except ImportError:
        raise ImportError("fpdf2 no instalado. Ejecutar: pip install fpdf2")

    takt          = metrics.get("takt", 0)
    total_va      = metrics.get("total_va", 0)
    total_lt      = metrics.get("total_lead_time", 0)
    pce           = metrics.get("pce", 0)
    bottleneck    = metrics.get("bottleneck", "N/A")
    process_list  = metrics.get("process_metrics", [])
    has_violation = metrics.get("has_violation", False)

    # ---- Instancia FPDF2 --------------------------------------------------
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()

    # ---- Helpers de color --------------------------------------------------
    def set_fill(hex_color: str):
        r, g, b = _hex2rgb(hex_color)
        pdf.set_fill_color(r, g, b)

    def set_text(hex_color: str):
        r, g, b = _hex2rgb(hex_color)
        pdf.set_text_color(r, g, b)

    def set_draw(hex_color: str):
        r, g, b = _hex2rgb(hex_color)
        pdf.set_draw_color(r, g, b)

    # =====================================================================
    # HEADER
    # =====================================================================
    logo_exists = os.path.isfile(_LOGO_PATH)

    # Banda superior roja
    set_fill(_RED)
    pdf.rect(0, 0, 210, 32, style="F")

    # Logo
    if logo_exists:
        pdf.image(_LOGO_PATH, x=12, y=6, h=20)
        title_x = 55
    else:
        title_x = 15

    # Título principal
    set_text(_WHITE)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(title_x, 8)
    pdf.cell(0, 7, _REPORT_T, ln=True)

    # Subtítulo fecha
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(title_x, 16)
    fecha = datetime.now().strftime("%d %B %Y — %H:%M")
    pdf.cell(0, 5, f"Generado el {fecha}", ln=True)

    # Modo de análisis
    pdf.set_xy(title_x, 22)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Análisis: Estado Actual de la cadena de valor", ln=True)

    pdf.ln(10)  # espacio post-header

    # =====================================================================
    # RESUMEN EJECUTIVO
    # =====================================================================
    _pdf_section_title(pdf, "1. Resumen Ejecutivo — ¿Qué es el VSM y cómo interpretarlo?")

    _pdf_body(pdf, _INTRO_VSM)
    pdf.ln(3)
    _pdf_body(pdf, _INTERPRETATION)
    pdf.ln(3)
    _pdf_body(pdf, _METHODOLOGY)
    pdf.ln(5)

    # =====================================================================
    # MÉTRICAS CLAVE
    # =====================================================================
    _pdf_section_title(pdf, "2. Métricas Clave del Estado Actual")

    # Conclusión automática basada en datos
    conclusions = _build_conclusions(takt, total_lt, pce, bottleneck, has_violation, process_list, demand)
    _pdf_body(pdf, conclusions)
    pdf.ln(4)

    # Tabla de métricas 2×2
    metrics_data = [
        ("Takt Time", f"{takt:.1f} s/u",
         "Ritmo de consumo del cliente. Todos los procesos deben operar por debajo de este valor."),
        ("Lead Time Total", f"{total_lt:.1f} s  ({total_lt/3600:.2f} h)",
         "Tiempo total de puerta a puerta incluyendo esperas e inventarios."),
        ("PCE (Process Cycle Efficiency)", f"{pce:.1f} %",
         "Proporción de tiempo de valor agregado sobre Lead Time total. Meta industria: >25%."),
        ("Cuello de Botella", str(bottleneck) if bottleneck else "N/A",
         "Proceso limitante del throughput. Aplicar kaizen aquí primero (TOC)."),
        ("Tiempo VA Total", f"{total_va:.1f} s",
         "Suma de todos los C/T. Tiempo real de transformación del producto."),
        ("Demanda Diaria", f"{int(demand)} u/día",
         f"Requiere {takt:.1f} s disponibles por unidad con {available_sec/3600:.1f} h de turno."),
    ]

    col_w = [50, 35, 95]
    _pdf_table_header(pdf, ["Indicador", "Valor", "Interpretación"], col_w)
    for i, (ind, val, interp) in enumerate(metrics_data):
        row_bg = _BG2 if i % 2 == 0 else "#222436"
        _pdf_table_row(pdf, [ind, val, interp], col_w, row_bg)
    pdf.ln(6)

    # =====================================================================
    # TABLA DE PROCESOS
    # =====================================================================
    _pdf_section_title(pdf, "3. Tabla Detallada de Procesos")

    if df.empty or not process_list:
        set_text(_GRAY)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "No hay datos de procesos disponibles.", ln=True)
    else:
        proc_cols = ["Proceso", "C/T (s)", "C/O (s)", "WIP", "Uptime %", "VA (s)", "NVA (s)", "Violación"]
        proc_widths = [32, 18, 18, 14, 20, 18, 18, 22]
        _pdf_table_header(pdf, proc_cols, proc_widths, font_size=8)

        for i, pm in enumerate(process_list):
            nva_val = pm.get("nva", 0)
            violation = "SI ⚠" if pm.get("ct_violation") else "no"
            violation_color = _RED if pm.get("ct_violation") else _GRAY
            row_bg = _RED_ALERT if pm.get("ct_violation") else (_BG2 if i % 2 == 0 else "#222436")
            row = [
                pm["name"],
                f"{pm['ct']:.0f}",
                f"{pm['co']:.0f}",
                str(pm["wip"]),
                f"{pm['uptime']:.0f}%",
                f"{pm['va']:.0f}",
                f"{nva_val:.0f}",
                violation,
            ]
            _pdf_table_row(pdf, row, proc_widths, row_bg, font_size=8, last_col_color=violation_color)

    pdf.ln(8)

    # =====================================================================
    # DIAGRAMA VSM (matplotlib)
    # =====================================================================
    _pdf_section_title(pdf, "4. Diagrama VSM — Estado Actual")

    pdf.set_font("Helvetica", "I", 8)
    set_text(_GRAY)
    pdf.cell(0, 5, "Representación esquemática del flujo de valor. Cajas rojas = proceso viola Takt Time.", ln=True)
    pdf.ln(1)

    vsm_img_bytes = _render_vsm_matplotlib(process_list, takt)
    if vsm_img_bytes:
        # Guardar en archivo temporal en memoria via BytesIO y pasar a fpdf
        with _tmp_image(vsm_img_bytes, ".png") as tmp_path:
            pdf.image(tmp_path, x=15, w=180)
    pdf.ln(5)

    # =====================================================================
    # GRÁFICA VA/NVA (matplotlib)
    # =====================================================================
    _pdf_section_title(pdf, "5. Análisis Value-Added vs. Non-Value-Added")

    nva_img_bytes = _render_va_nva_matplotlib(process_list)
    if nva_img_bytes:
        with _tmp_image(nva_img_bytes, ".png") as tmp_path:
            pdf.image(tmp_path, x=15, w=180)
    pdf.ln(5)

    # =====================================================================
    # RECOMENDACIONES
    # =====================================================================
    _pdf_section_title(pdf, "6. Recomendaciones y Próximos Pasos")

    recs = _build_recommendations(pce, bottleneck, has_violation, process_list, takt)
    for idx, rec in enumerate(recs, 1):
        set_text(_GOLD)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(6, 5, f"{idx}.", ln=False)
        set_text(_WHITE)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, rec)
        pdf.ln(1)

    # =====================================================================
    # FOOTER (en cada página via FPDF override no es trivial — se añade al final)
    # =====================================================================
    _pdf_footer_last_page(pdf)

    return bytes(pdf.output())


# =============================================================================
# B — HTML WHITEPAPER PROFESIONAL
# =============================================================================

def generate_html_report(df: pd.DataFrame, metrics: dict) -> str:
    """
    Genera un whitepaper HTML autocontenido con:
      - CSS dark theme EA embebido
      - Header con branding
      - Resumen ejecutivo técnico completo
      - Diagrama VSM interactivo (JS/SVG con tooltips y hovers)
      - Tabla de procesos sortable (vanilla JS)
      - Gráficas Plotly embebidas (plotly.js CDN)
      - Sección de análisis con conclusiones automáticas
      - Footer profesional

    Retorna string HTML listo para st.download_button(data=..., mime='text/html').
    """
    takt         = metrics.get("takt", 0)
    total_va     = metrics.get("total_va", 0)
    total_lt     = metrics.get("total_lead_time", 0)
    pce          = metrics.get("pce", 0)
    bottleneck   = metrics.get("bottleneck", "N/A")
    process_list = metrics.get("process_metrics", [])
    has_violation= metrics.get("has_violation", False)

    fecha     = datetime.now().strftime("%d de %B de %Y, %H:%M")
    data_json = json.dumps({"processes": process_list, "takt": round(takt, 2)})

    # ---------- Secciones HTML individuales ---------------------------------
    exec_summary_html  = _html_exec_summary(takt, total_va, total_lt, pce, bottleneck, has_violation, process_list)
    vsm_diagram_html   = _html_vsm_diagram(data_json)
    table_html         = _html_process_table(process_list, takt)
    plotly_charts_html = _html_plotly_charts(process_list, takt, pce)
    analysis_html      = _html_analysis_section(takt, total_va, total_lt, pce, bottleneck, has_violation, process_list)
    recs_html          = _html_recommendations(pce, bottleneck, has_violation, process_list, takt)

    # ---------- Logo base64 (si existe) -------------------------------------
    logo_b64 = ""
    if os.path.isfile(_LOGO_PATH):
        with open(_LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()

    logo_img = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="EA Logo" class="logo">'
        if logo_b64 else
        f'<span class="logo-text">{_COMPANY}</span>'
    )

    # ---------- Ensamblado final --------------------------------------------
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_REPORT_T}</title>
{_HTML_CSS}
</head>
<body>

<!-- ═══════════════════════════════════════════════ COVER ═══ -->
<div class="cover">
  <div class="cover-inner">
    <div class="cover-logo">{logo_img}</div>
    <h1 class="cover-title">Digital VSM Report</h1>
    <p class="cover-sub">Value Stream Mapping &amp; Operational Intelligence</p>
    <p class="cover-company">{_COMPANY}</p>
    <p class="cover-date">Generado el {fecha}</p>
    <div class="cover-badge">Estado Actual — Current State Analysis</div>
  </div>
</div>

<!-- ═══════════════════════════════════════════ CONTENIDO ═══ -->
<div class="container">

  <!-- ÍNDICE -->
  <nav class="toc">
    <h3>Contenido</h3>
    <ol>
      <li><a href="#sec-exec">Resumen Ejecutivo</a></li>
      <li><a href="#sec-vsm">Diagrama VSM Interactivo</a></li>
      <li><a href="#sec-metrics">Métricas Clave</a></li>
      <li><a href="#sec-table">Tabla de Procesos</a></li>
      <li><a href="#sec-charts">Análisis Gráfico</a></li>
      <li><a href="#sec-analysis">Análisis Técnico y Conclusiones</a></li>
      <li><a href="#sec-recs">Recomendaciones</a></li>
    </ol>
  </nav>

  <!-- 1. RESUMEN EJECUTIVO -->
  <section id="sec-exec">
    <h2 class="section-title"><span class="section-num">1</span> Resumen Ejecutivo</h2>
    {exec_summary_html}
  </section>

  <!-- 2. DIAGRAMA VSM -->
  <section id="sec-vsm">
    <h2 class="section-title"><span class="section-num">2</span> Diagrama VSM Interactivo</h2>
    <p class="section-intro">
      El diagrama siguiente representa el flujo de valor de puerta a puerta. Pase el cursor
      sobre cada proceso para ver sus indicadores detallados. Las cajas con borde rojo intenso
      indican procesos que violan el Takt Time (cuellos de botella activos).
    </p>
    {vsm_diagram_html}
  </section>

  <!-- 3. MÉTRICAS CLAVE -->
  <section id="sec-metrics">
    <h2 class="section-title"><span class="section-num">3</span> Métricas Clave del Estado Actual</h2>
    <div class="kpi-grid">
      {_html_kpi_cards(takt, total_va, total_lt, pce, bottleneck)}
    </div>
  </section>

  <!-- 4. TABLA DE PROCESOS -->
  <section id="sec-table">
    <h2 class="section-title"><span class="section-num">4</span> Tabla Detallada de Procesos</h2>
    <p class="section-intro">
      Haga clic en el encabezado de cualquier columna para ordenar la tabla.
      Las filas con fondo rojo oscuro indican violación del Takt Time.
    </p>
    {table_html}
  </section>

  <!-- 5. GRÁFICAS -->
  <section id="sec-charts">
    <h2 class="section-title"><span class="section-num">5</span> Análisis Gráfico</h2>
    {plotly_charts_html}
  </section>

  <!-- 6. ANÁLISIS -->
  <section id="sec-analysis">
    <h2 class="section-title"><span class="section-num">6</span> Análisis Técnico y Conclusiones</h2>
    {analysis_html}
  </section>

  <!-- 7. RECOMENDACIONES -->
  <section id="sec-recs">
    <h2 class="section-title"><span class="section-num">7</span> Recomendaciones y Próximos Pasos</h2>
    {recs_html}
  </section>

</div><!-- /container -->

<!-- ════════════════════════════════════════════════ FOOTER ═══ -->
<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-logo">{logo_img}</div>
    <div class="footer-info">
      <strong>{_COMPANY}</strong><br>
      Digital VSM &amp; Operational Intelligence Platform v2.0<br>
      <em>Reporte generado automáticamente — {fecha}</em>
    </div>
    <div class="footer-badge">
      <span>Lean Manufacturing</span>
      <span>Value Stream Mapping</span>
      <span>Industrial Analytics</span>
    </div>
  </div>
  <p class="footer-copy">
    © {datetime.now().year} {_COMPANY}. Documento de uso interno. Metodología VSM basada en
    estándares Lean Institute y Toyota Production System.
  </p>
</footer>

{_HTML_TABLE_SORT_JS}
</body>
</html>"""

    return html


# =============================================================================
# HELPERS — PDF
# =============================================================================

def _hex2rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _pdf_section_title(pdf, text: str):
    from fpdf import FPDF
    r, g, b = _hex2rgb(_GOLD)
    pdf.set_text_color(r, g, b)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, text, ln=True)
    # Línea separadora dorada
    r2, g2, b2 = _hex2rgb(_GOLD)
    pdf.set_draw_color(r2, g2, b2)
    pdf.set_line_width(0.4)
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(3)


def _pdf_body(pdf, text: str):
    r, g, b = _hex2rgb(_GRAY)
    pdf.set_text_color(r, g, b)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, text)


def _pdf_table_header(pdf, cols: list[str], widths: list[int], font_size: int = 9):
    r, g, b = _hex2rgb(_RED)
    pdf.set_fill_color(r, g, b)
    r2, g2, b2 = _hex2rgb(_WHITE)
    pdf.set_text_color(r2, g2, b2)
    pdf.set_font("Helvetica", "B", font_size)
    pdf.set_draw_color(70, 70, 70)
    pdf.set_line_width(0.3)
    for col, w in zip(cols, widths):
        pdf.cell(w, 7, col, border=1, fill=True, align="C")
    pdf.ln()


def _pdf_table_row(
    pdf,
    row: list[str],
    widths: list[int],
    bg_hex: str,
    font_size: int = 9,
    last_col_color: Optional[str] = None,
):
    r, g, b = _hex2rgb(bg_hex)
    pdf.set_fill_color(r, g, b)
    pdf.set_font("Helvetica", "", font_size)
    pdf.set_draw_color(60, 60, 60)
    pdf.set_line_width(0.2)

    for i, (cell, w) in enumerate(zip(row, widths)):
        is_last = i == len(row) - 1
        if is_last and last_col_color:
            rr, gg, bb = _hex2rgb(last_col_color)
            pdf.set_text_color(rr, gg, bb)
        else:
            rr, gg, bb = _hex2rgb(_WHITE)
            pdf.set_text_color(rr, gg, bb)
        pdf.cell(w, 6, str(cell), border=1, fill=True)
    pdf.ln()


def _pdf_footer_last_page(pdf):
    pdf.set_y(-18)
    r, g, b = _hex2rgb(_BORDER)
    pdf.set_draw_color(r, g, b)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(1)
    r2, g2, b2 = _hex2rgb(_GRAY)
    pdf.set_text_color(r2, g2, b2)
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(
        0, 5,
        f"{_COMPANY}  |  Digital VSM & Operational Intelligence v2.0  "
        f"|  {datetime.now().strftime('%Y-%m-%d')}  |  Pag. {pdf.page_no()}",
        align="C",
    )


# ---- Matplotlib: diagrama VSM para PDF ------------------------------------

def _render_vsm_matplotlib(process_list: list, takt: float) -> Optional[bytes]:
    """Renderiza el VSM como figura matplotlib y retorna PNG bytes."""
    if not process_list:
        return None

    n     = len(process_list)
    fig_w = max(12, n * 2.4 + 3)
    fig, ax = plt.subplots(figsize=(fig_w, 4.2))
    ax.set_facecolor(_BG)
    fig.patch.set_facecolor(_BG)
    ax.axis("off")

    BOX_W, BOX_H = 1.8, 1.1
    TRI_SIZE     = 0.28
    START_X      = 1.0
    MID_Y        = 2.2
    STEP         = (fig_w - 2.6) / max(n, 1)

    # Takt line punteada
    if takt > 0:
        ax.axhline(y=MID_Y + BOX_H + 0.35, color=_GOLD, linewidth=1,
                   linestyle="--", alpha=0.7)
        ax.text(START_X - 0.5, MID_Y + BOX_H + 0.42,
                f"Takt: {takt:.0f}s", color=_GOLD, fontsize=7, va="bottom")

    # ENTRY node
    entry_rect = mpatches.FancyBboxPatch(
        (START_X - 0.55, MID_Y - 0.1), 0.9, BOX_H * 0.85,
        boxstyle="round,pad=0.05",
        linewidth=1.5, edgecolor=_GOLD, facecolor="#1A1C24",
    )
    ax.add_patch(entry_rect)
    ax.text(START_X, MID_Y + BOX_H * 0.42 - 0.1, "ENTRY",
            ha="center", va="center", color=_WHITE, fontsize=7, fontweight="bold")

    for i, pm in enumerate(process_list):
        bx = START_X + STEP * 0.5 + STEP * i
        by = MID_Y

        # Triángulo de inventario (antes del proceso)
        tri_x = bx - STEP * 0.40
        tri_pts = np.array([
            [tri_x, by + BOX_H * 0.6],
            [tri_x - TRI_SIZE, by - 0.05],
            [tri_x + TRI_SIZE, by - 0.05],
        ])
        tri = mpatches.Polygon(tri_pts, closed=True,
                               facecolor=_RED, edgecolor=_GOLD, linewidth=1.2)
        ax.add_patch(tri)
        ax.text(tri_x, by + 0.08, str(pm["wip"]),
                ha="center", va="center", color=_WHITE, fontsize=6, fontweight="bold")

        # Caja del proceso
        box_color = _RED_ALERT if pm.get("ct_violation") else _BG2
        rect = mpatches.FancyBboxPatch(
            (bx - BOX_W / 2, by), BOX_W, BOX_H,
            boxstyle="round,pad=0.04",
            linewidth=2.0, edgecolor=_GOLD, facecolor=box_color,
        )
        ax.add_patch(rect)

        # Borde interior rojo
        rect2 = mpatches.FancyBboxPatch(
            (bx - BOX_W / 2 + 0.06, by + 0.06),
            BOX_W - 0.12, BOX_H - 0.12,
            boxstyle="round,pad=0.02",
            linewidth=0.8, edgecolor=_RED, facecolor="none",
        )
        ax.add_patch(rect2)

        # Nombre del proceso
        ax.text(bx, by + BOX_H * 0.78, pm["name"],
                ha="center", va="center", color=_WHITE,
                fontsize=7.5, fontweight="bold")

        # C/T
        ct_color = _RED if pm.get("ct_violation") else _GOLD
        ax.text(bx, by + BOX_H * 0.50,
                f"C/T: {pm['ct']:.0f}s",
                ha="center", va="center", color=ct_color, fontsize=6.5)

        # WIP label
        ax.text(bx, by + BOX_H * 0.24,
                f"WIP: {pm['wip']}",
                ha="center", va="center", color=_GRAY, fontsize=6)

        # Flecha hacia la siguiente caja (o hacia CUSTOMER)
        if i < n - 1:
            arrow_start = bx + BOX_W / 2
            arrow_end   = bx + STEP - BOX_W / 2 - TRI_SIZE * 2 - 0.06
            ax.annotate(
                "", xy=(arrow_end, by + BOX_H / 2),
                xytext=(arrow_start, by + BOX_H / 2),
                arrowprops=dict(arrowstyle="->", color=_GOLD,
                                lw=1.5, mutation_scale=12),
            )
        else:
            # Flecha hacia CUSTOMER
            last_bx = bx + BOX_W / 2
            ax.annotate(
                "", xy=(last_bx + STEP * 0.35, by + BOX_H / 2),
                xytext=(last_bx, by + BOX_H / 2),
                arrowprops=dict(arrowstyle="->", color=_GOLD,
                                lw=1.5, mutation_scale=12),
            )

    # CUSTOMER node
    cust_x = START_X + STEP * 0.5 + STEP * (n - 1) + STEP * 0.5
    cust_rect = mpatches.FancyBboxPatch(
        (cust_x - 0.5, MID_Y - 0.1), 0.9, BOX_H * 0.85,
        boxstyle="round,pad=0.05",
        linewidth=1.5, edgecolor=_GOLD, facecolor="#1A1C24",
    )
    ax.add_patch(cust_rect)
    ax.text(cust_x + 0.0, MID_Y + BOX_H * 0.42 - 0.1, "CUST.",
            ha="center", va="center", color=_WHITE, fontsize=7, fontweight="bold")

    # Lean labels en la parte inferior
    lean_labels = ["Flow", "Results", "Tiempo", "Smooth", "Tamaño"]
    for li, lbl in enumerate(lean_labels):
        lx = START_X + (fig_w - 2) * li / (len(lean_labels) - 1)
        ax.text(lx, MID_Y - 0.55, lbl,
                ha="center", va="center", color=_GOLD,
                fontsize=7, alpha=0.8,
                bbox=dict(boxstyle="round,pad=0.2", facecolor=_BG2,
                          edgecolor=_BORDER, linewidth=0.5))

    ax.set_xlim(0, fig_w - 0.3)
    ax.set_ylim(MID_Y - 0.85, MID_Y + BOX_H + 0.75)
    plt.tight_layout(pad=0.2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---- Matplotlib: gráfica VA/NVA horizontal para PDF ----------------------

def _render_va_nva_matplotlib(process_list: list) -> Optional[bytes]:
    if not process_list:
        return None

    names = [pm["name"] for pm in process_list]
    va_vals  = [pm["va"]  for pm in process_list]
    nva_vals = [pm.get("nva", 0) for pm in process_list]

    fig, ax = plt.subplots(figsize=(10, max(2.4, len(names) * 0.55)))
    ax.set_facecolor(_BG2)
    fig.patch.set_facecolor(_BG)

    y = np.arange(len(names))
    bar_h = 0.42
    bars_va  = ax.barh(y, va_vals,  bar_h, label="Value-Added",     color=_GOLD,  edgecolor=_BG)
    bars_nva = ax.barh(y, nva_vals, bar_h, left=va_vals, label="Non-Value-Added", color=_RED, edgecolor=_BG)

    ax.set_yticks(y)
    ax.set_yticklabels(names, color=_WHITE, fontsize=8)
    ax.set_xlabel("Tiempo (s)", color=_GRAY, fontsize=8)
    ax.set_title("Value-Added vs. Non-Value-Added Time", color=_GOLD,
                 fontsize=10, fontweight="bold", pad=8)
    ax.tick_params(colors=_GRAY)
    ax.spines[["top","right","bottom","left"]].set_edgecolor(_BORDER)
    ax.xaxis.label.set_color(_GRAY)
    ax.tick_params(axis="x", colors=_GRAY)
    ax.legend(loc="lower right", facecolor=_BG2, edgecolor=_BORDER,
              labelcolor=_WHITE, fontsize=7)

    plt.tight_layout(pad=0.4)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---- Context manager para archivo temporal (fpdf.image necesita path) ----

import contextlib
import tempfile

@contextlib.contextmanager
def _tmp_image(img_bytes: bytes, suffix: str = ".png"):
    """Escribe bytes a un archivo temporal y retorna su path."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name
    try:
        yield tmp_path
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---- Textos auxiliares -----------------------------------------------------

def _build_conclusions(takt, total_lt, pce, bottleneck, has_violation, process_list, demand) -> str:
    lines = []
    if takt > 0:
        lines.append(
            f"Con una demanda de {int(demand)} unidades/día y tiempo disponible de "
            f"{takt * demand / 3600:.1f} horas/día, el Takt Time resultante es {takt:.1f} s/u. "
        )
    if total_lt > 0:
        lines.append(
            f"El Lead Time total de la cadena es {total_lt:.1f} s ({total_lt/3600:.2f} h), "
            f"mientras que el tiempo de valor agregado acumulado es solo "
            f"{sum(p['va'] for p in process_list):.1f} s, lo que representa una PCE de {pce:.1f}%. "
        )
    if pce > 0:
        pce_level = "excelente" if pce >= 25 else ("aceptable" if pce >= 10 else "bajo")
        lines.append(
            f"El PCE de {pce:.1f}% es considerado {pce_level} según estándares industriales. "
        )
    if bottleneck:
        lines.append(
            f"El proceso '{bottleneck}' actúa como cuello de botella y determina el throughput "
            f"máximo de la línea. Cualquier mejora en procesos no limitantes no incrementará "
            f"la producción total hasta que este proceso sea atendido. "
        )
    if has_violation:
        viol_names = [p["name"] for p in process_list if p.get("ct_violation")]
        lines.append(
            f"ALERTA: Los procesos {', '.join(viol_names)} superan el Takt Time, "
            f"generando desequilibrio en el flujo y riesgo de incumplimiento de la demanda. "
        )
    return " ".join(lines)


def _build_recommendations(pce, bottleneck, has_violation, process_list, takt) -> list[str]:
    recs = []
    if bottleneck:
        recs.append(
            f"Kaizen de capacidad en '{bottleneck}': analizar causa raíz de C/T elevado. "
            "Opciones: reducción de changeover (SMED), balanceo de operadores, "
            "automatización parcial o división del lote."
        )
    if pce < 25:
        recs.append(
            f"Reducción de WIP entre procesos: el PCE actual ({pce:.1f}%) indica que "
            "el mayor tiempo se pierde en esperas e inventarios. Implementar sistema "
            "pull (Kanban/CONWIP) para limitar WIP máximo por estación."
        )
    if has_violation:
        recs.append(
            "Balanceo de línea: redistribuir operaciones entre estaciones para alinear "
            "todos los C/T al Takt Time. Usar diagrama de balanceo (yamazumi chart) "
            "para visualizar la carga por operador."
        )
    recs.append(
        "Diseño del Estado Futuro: con base en los hallazgos del estado actual, "
        "construir el mapa VSM del estado futuro con los kaizens identificados, "
        "y establecer un plan de implementación con responsables y fechas."
    )
    recs.append(
        "Monitoreo continuo: implementar OEE y ciclo de producción como KPIs de "
        "control para validar las mejoras implementadas en el siguiente período "
        "de revisión (recomendado: revisión mensual)."
    )
    return recs


# =============================================================================
# HELPERS — HTML
# =============================================================================

def _html_exec_summary(takt, total_va, total_lt, pce, bottleneck, has_violation, process_list) -> str:
    conc = _build_conclusions(takt, total_lt, pce, bottleneck, has_violation, process_list, 0)
    # re-calcular demand desde takt (takt = avail/demand → demand = avail/takt)
    # (no disponemos de demand aquí, se usa texto genérico)
    return f"""
<div class="exec-card">
  <h3>¿Qué es el Value Stream Mapping?</h3>
  <p>{_INTRO_VSM}</p>
</div>

<div class="exec-card">
  <h3>¿Cómo interpretar los indicadores?</h3>
  <p>{_INTERPRETATION}</p>
</div>

<div class="exec-card">
  <h3>Metodología aplicada</h3>
  <p>{_METHODOLOGY}</p>
</div>

<div class="exec-card highlight">
  <h3>Hallazgos del Estado Actual</h3>
  <p>{conc if conc else "Calcule las métricas con datos de procesos para ver los hallazgos."}</p>
</div>
"""


def _html_vsm_diagram(data_json: str) -> str:
    """Genera el diagrama VSM JS/SVG interactivo embebido (idéntico a vsm_diagram.py)."""
    return f"""
<div class="vsm-outer">
<div id="vsm-html-wrapper">
  <div id="vsm-scroll-container">
    <svg id="vsm-svg" xmlns="http://www.w3.org/2000/svg"></svg>
  </div>
  <div id="vsm-tooltip"></div>
</div>
</div>

<script>
(function() {{
  const DATA = {data_json};
  const processes = DATA.processes || [];
  const takt = DATA.takt || 0;

  const SVG_NS   = "http://www.w3.org/2000/svg";
  const C_BG     = "#0E1117";
  const C_BG2    = "#1A1C24";
  const C_RED    = "#D32F2F";
  const C_ALERT  = "#5C1A1A";
  const C_GOLD   = "#FFC107";
  const C_WHITE  = "#FFFFFF";
  const C_GRAY   = "#CCCCCC";
  const C_BORDER = "#2D2D3A";

  const BOX_W    = 130;
  const BOX_H    = 110;
  const TRI_W    = 30;
  const TRI_H    = 26;
  const MARGIN_L = 60;
  const ENTRY_W  = 80;
  const CUST_W   = 80;
  const GAP      = 60;   // gap between box right edge and next triangle center
  const STEP     = BOX_W + GAP + TRI_W + 10;
  const SVG_H    = 260;
  const MID_Y    = 90;
  const LEAN_Y   = SVG_H - 30;

  const n = processes.length;
  const SVG_W = MARGIN_L + ENTRY_W + 20 + n * STEP + GAP + CUST_W + 40;

  const svg = document.getElementById("vsm-svg");
  svg.setAttribute("width",  SVG_W);
  svg.setAttribute("height", SVG_H);
  svg.setAttribute("viewBox", "0 0 " + SVG_W + " " + SVG_H);
  svg.style.background = C_BG;

  function el(tag, attrs, parent) {{
    const e = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {{}})) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  }}
  function text(txt, x, y, opts, parent) {{
    const t = el("text", {{
      x, y,
      fill:        opts.fill        || C_WHITE,
      "font-size": opts.size        || "11",
      "font-weight": opts.weight    || "normal",
      "text-anchor": opts.anchor    || "middle",
      "dominant-baseline": "central",
      "font-family": "Segoe UI, Arial, sans-serif",
    }}, parent);
    t.textContent = txt;
    return t;
  }}

  // ── Takt Time punteada ──────────────────────────────────────────
  if (takt > 0) {{
    el("line", {{
      x1: 10, y1: MID_Y - 18,
      x2: SVG_W - 10, y2: MID_Y - 18,
      stroke: C_GOLD, "stroke-width": 1.2,
      "stroke-dasharray": "6 4", opacity: 0.65,
    }}, svg);
    text("Takt: " + takt.toFixed(1) + "s", 55, MID_Y - 24,
         {{fill: C_GOLD, size: "9", anchor: "middle"}}, svg);
  }}

  // ── ENTRY node ─────────────────────────────────────────────────
  const entryX = MARGIN_L - 10;
  el("rect", {{
    x: entryX, y: MID_Y,
    width: ENTRY_W, height: BOX_H * 0.75,
    rx: 6, ry: 6,
    fill: C_BG2, stroke: C_GOLD, "stroke-width": 2,
  }}, svg);
  text("ENTRY", entryX + ENTRY_W / 2, MID_Y + BOX_H * 0.375,
       {{fill: C_WHITE, size: "11", weight: "bold"}}, svg);

  // Flecha Entry → primer proceso
  const firstBoxX = MARGIN_L + ENTRY_W + 20 + TRI_W + 10;
  el("line", {{
    x1: entryX + ENTRY_W, y1: MID_Y + BOX_H * 0.375,
    x2: firstBoxX,        y2: MID_Y + BOX_H * 0.375,
    stroke: C_GOLD, "stroke-width": 1.8,
  }}, svg);
  el("polygon", {{
    points: (firstBoxX) + "," + (MID_Y + BOX_H * 0.375 - 5) + " " +
            (firstBoxX + 8) + "," + (MID_Y + BOX_H * 0.375) + " " +
            (firstBoxX) + "," + (MID_Y + BOX_H * 0.375 + 5),
    fill: C_GOLD,
  }}, svg);

  const tooltip = document.getElementById("vsm-tooltip");

  processes.forEach(function(pm, i) {{
    const boxX = MARGIN_L + ENTRY_W + 20 + i * STEP;
    const boxY = MID_Y;
    const cx   = boxX + BOX_W / 2;

    // Triángulo inventario
    const triCX = boxX - TRI_W / 2 - 8;
    const triTip = boxY - 4;
    el("polygon", {{
      points: triCX + "," + triTip + " " +
              (triCX - TRI_W / 2) + "," + (triTip + TRI_H) + " " +
              (triCX + TRI_W / 2) + "," + (triTip + TRI_H),
      fill: C_RED, stroke: C_GOLD, "stroke-width": 1.3,
    }}, svg);
    text(String(pm.wip), triCX, triTip + TRI_H / 2 + 3,
         {{fill: C_WHITE, size: "9", weight: "bold"}}, svg);

    // Caja proceso
    const boxFill = pm.ct_violation ? C_ALERT : C_BG2;
    el("rect", {{
      x: boxX, y: boxY,
      width: BOX_W, height: BOX_H,
      rx: 6, ry: 6,
      fill: boxFill, stroke: C_GOLD, "stroke-width": 2.2,
    }}, svg);
    el("rect", {{
      x: boxX + 5, y: boxY + 5,
      width: BOX_W - 10, height: BOX_H - 10,
      rx: 4, ry: 4,
      fill: "none", stroke: C_RED, "stroke-width": 0.9,
    }}, svg);

    // Nombre
    text(pm.name, cx, boxY + 22,
         {{fill: C_WHITE, size: "12", weight: "bold"}}, svg);

    // Indicador violación
    if (pm.ct_violation) {{
      const xIcon = el("text", {{
        x: boxX + BOX_W - 16, y: boxY + 16,
        fill: C_RED, "font-size": "15", "font-weight": "bold",
        "text-anchor": "middle", "dominant-baseline": "central",
        "font-family": "Arial",
      }}, svg);
      xIcon.textContent = "✕";
    }}
    if (pm.is_bottleneck) {{
      const star = el("text", {{
        x: boxX + 14, y: boxY + 16,
        fill: C_GOLD, "font-size": "13", "font-weight": "bold",
        "text-anchor": "middle", "dominant-baseline": "central",
      }}, svg);
      star.textContent = "★";
    }}

    // C/T
    const ctColor = pm.ct_violation ? C_RED : C_GOLD;
    const ctEl = el("text", {{
      x: cx, y: boxY + 48,
      fill: ctColor, "font-size": "11",
      "font-weight": "600",
      "text-anchor": "middle", "dominant-baseline": "central",
      "font-family": "Segoe UI, Arial, sans-serif",
    }}, svg);
    ctEl.textContent = "C/T: " + pm.ct.toFixed(0) + "s";

    if (takt > 0) {{
      const taktEl = el("text", {{
        x: cx, y: boxY + 65,
        fill: C_GOLD, "font-size": "10",
        "text-anchor": "middle", "dominant-baseline": "central",
        "font-family": "Segoe UI, Arial, sans-serif",
      }}, svg);
      taktEl.textContent = "Takt: " + takt.toFixed(0) + "s";
    }}

    const wipEl = el("text", {{
      x: cx, y: boxY + 82,
      fill: C_GRAY, "font-size": "10",
      "text-anchor": "middle", "dominant-baseline": "central",
      "font-family": "Segoe UI, Arial, sans-serif",
    }}, svg);
    wipEl.textContent = "WIP: " + pm.wip;

    const uptEl = el("text", {{
      x: cx, y: boxY + 97,
      fill: C_GRAY, "font-size": "9",
      "text-anchor": "middle", "dominant-baseline": "central",
      "font-family": "Segoe UI, Arial, sans-serif",
    }}, svg);
    uptEl.textContent = "Up: " + pm.uptime.toFixed(0) + "%";

    // Flecha hacia siguiente / customer
    if (i < n - 1) {{
      const arrowStartX = boxX + BOX_W;
      const arrowEndX   = boxX + STEP - TRI_W - 8;
      el("line", {{
        x1: arrowStartX, y1: boxY + BOX_H / 2,
        x2: arrowEndX,   y2: boxY + BOX_H / 2,
        stroke: C_GOLD, "stroke-width": 1.8,
      }}, svg);
      el("polygon", {{
        points: arrowEndX + "," + (boxY + BOX_H / 2 - 5) + " " +
                (arrowEndX + 8) + "," + (boxY + BOX_H / 2) + " " +
                arrowEndX + "," + (boxY + BOX_H / 2 + 5),
        fill: C_GOLD,
      }}, svg);
    }}

    // Hover interactivo
    const hitRect = el("rect", {{
      x: boxX, y: boxY,
      width: BOX_W, height: BOX_H,
      fill: "transparent", cursor: "pointer",
    }}, svg);

    hitRect.addEventListener("mouseenter", function(evt) {{
      const isBot = pm.is_bottleneck ? " ★ BOTTLENECK" : "";
      const viol  = pm.ct_violation  ? " ⚠ VIOLA TAKT" : "";
      tooltip.style.display   = "block";
      tooltip.innerHTML =
        "<strong style='color:" + C_GOLD + "'>" + pm.name + isBot + viol + "</strong><br>" +
        "C/T: <b>" + pm.ct.toFixed(1) + " s</b>" +
        (takt > 0 ? " / Takt: <b>" + takt.toFixed(1) + " s</b>" : "") + "<br>" +
        "C/O: <b>" + pm.co.toFixed(0) + " s</b><br>" +
        "WIP: <b>" + pm.wip + " u</b><br>" +
        "Uptime: <b>" + pm.uptime.toFixed(0) + "%</b><br>" +
        "NVA (espera): <b>" + (pm.nva || 0).toFixed(0) + " s</b><br>" +
        "LT acumulado: <b>" + (pm.cumulative_lt || 0).toFixed(1) + " s</b>";
    }});
    hitRect.addEventListener("mousemove", function(evt) {{
      tooltip.style.left = (evt.pageX + 14) + "px";
      tooltip.style.top  = (evt.pageY - 10) + "px";
    }});
    hitRect.addEventListener("mouseleave", function() {{
      tooltip.style.display = "none";
    }});
  }});

  // ── CUSTOMER node ─────────────────────────────────────────────
  const custBoxX = MARGIN_L + ENTRY_W + 20 + n * STEP - TRI_W + GAP / 2;
  el("rect", {{
    x: custBoxX, y: MID_Y,
    width: CUST_W, height: BOX_H * 0.75,
    rx: 6, ry: 6,
    fill: C_BG2, stroke: C_GOLD, "stroke-width": 2,
  }}, svg);
  text("CUSTOMER", custBoxX + CUST_W / 2, MID_Y + BOX_H * 0.375,
       {{fill: C_WHITE, size: "10", weight: "bold"}}, svg);

  // Flecha último proceso → CUSTOMER
  const lastBoxEndX = MARGIN_L + ENTRY_W + 20 + (n - 1) * STEP + BOX_W;
  el("line", {{
    x1: lastBoxEndX, y1: MID_Y + BOX_H * 0.375,
    x2: custBoxX,    y2: MID_Y + BOX_H * 0.375,
    stroke: C_GOLD, "stroke-width": 1.8,
  }}, svg);
  el("polygon", {{
    points: custBoxX + "," + (MID_Y + BOX_H * 0.375 - 5) + " " +
            (custBoxX + 8) + "," + (MID_Y + BOX_H * 0.375) + " " +
            custBoxX + "," + (MID_Y + BOX_H * 0.375 + 5),
    fill: C_GOLD,
  }}, svg);

  // ── Lean labels ───────────────────────────────────────────────
  const leanLabels = ["Flow", "Results", "Tiempo", "Smooth", "Tamaño"];
  leanLabels.forEach(function(lbl, li) {{
    const lx = 30 + (SVG_W - 60) * li / (leanLabels.length - 1);
    const g  = el("g", {{}}, svg);
    el("rect", {{
      x: lx - 28, y: LEAN_Y - 10,
      width: 56, height: 20,
      rx: 4, fill: C_BG2, stroke: C_BORDER, "stroke-width": 0.6,
    }}, g);
    text(lbl, lx, LEAN_Y, {{fill: C_GOLD, size: "9"}}, g);
  }});

}})();
</script>
"""


def _html_kpi_cards(takt, total_va, total_lt, pce, bottleneck) -> str:
    pce_class = "kpi-green" if pce >= 25 else ("kpi-yellow" if pce >= 10 else "kpi-red")

    def card(title, value, sub, extra_class=""):
        return f"""
<div class="kpi-card {extra_class}">
  <div class="kpi-label">{title}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-sub">{sub}</div>
</div>"""

    return (
        card("Takt Time",        f"{takt:.1f} s/u",    "Ritmo del cliente")
        + card("Lead Time Total", f"{total_lt:.1f} s",  f"{total_lt/3600:.2f} h")
        + card("PCE",            f"{pce:.1f} %",        "Meta: > 25%", pce_class)
        + card("VA Total",       f"{total_va:.1f} s",   "Tiempo transformación")
        + card("Bottleneck",     str(bottleneck) if bottleneck else "—", "Proceso limitante", "kpi-red")
    )


def _html_process_table(process_list: list, takt: float) -> str:
    if not process_list:
        return "<p class='no-data'>No hay datos de procesos.</p>"

    rows = ""
    for pm in process_list:
        viol_class = "row-violation" if pm.get("ct_violation") else ""
        bot_mark   = " ★" if pm.get("is_bottleneck") else ""
        viol_mark  = " ⚠" if pm.get("ct_violation") else ""
        rows += f"""
<tr class="{viol_class}">
  <td><strong>{pm['name']}{bot_mark}{viol_mark}</strong></td>
  <td>{pm['ct']:.0f}</td>
  <td>{pm['co']:.0f}</td>
  <td>{pm['wip']}</td>
  <td>{pm['uptime']:.0f}%</td>
  <td>{pm['va']:.0f}</td>
  <td>{pm.get('nva', 0):.0f}</td>
  <td>{"Sí ⚠" if pm.get("ct_violation") else "No"}</td>
</tr>"""

    return f"""
<div class="table-wrap">
<table id="proc-table" class="data-table sortable">
  <thead>
    <tr>
      <th data-col="0">Proceso ▲▼</th>
      <th data-col="1">C/T (s) ▲▼</th>
      <th data-col="2">C/O (s) ▲▼</th>
      <th data-col="3">WIP ▲▼</th>
      <th data-col="4">Uptime ▲▼</th>
      <th data-col="5">VA (s) ▲▼</th>
      <th data-col="6">NVA (s) ▲▼</th>
      <th data-col="7">Viola Takt</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
</div>
<p class="table-note">★ Bottleneck &nbsp;|&nbsp; ⚠ Viola Takt Time ({takt:.1f} s/u)</p>
"""


def _html_plotly_charts(process_list: list, takt: float, pce: float) -> str:
    if not process_list:
        return "<p class='no-data'>Sin datos para graficar.</p>"

    names    = [pm["name"]         for pm in process_list]
    va_vals  = [pm["va"]           for pm in process_list]
    nva_vals = [pm.get("nva", 0)   for pm in process_list]
    ct_vals  = [pm["ct"]           for pm in process_list]
    wip_vals = [pm["wip"]          for pm in process_list]

    chart_colors = ["#D32F2F","#FFC107","#FFA000","#FF6B35","#C62828","#FF8F00","#E64A19"]

    # VA/NVA horizontal
    va_nva_data = json.dumps([
        {"type":"bar","orientation":"h","name":"Value-Added",
         "y": names,"x": va_vals,
         "marker":{"color":"#FFC107","line":{"width":0.5,"color":"#0E1117"}}},
        {"type":"bar","orientation":"h","name":"Non-Value-Added",
         "y": names,"x": nva_vals,
         "marker":{"color":"#D32F2F","line":{"width":0.5,"color":"#0E1117"}}},
    ])
    va_nva_layout = json.dumps({
        "barmode":"stack","title":{"text":"Value-Added vs. Non-Value-Added Time","font":{"color":"#FFC107","size":14}},
        "paper_bgcolor":"#0E1117","plot_bgcolor":"#1A1C24",
        "font":{"color":"#CCCCCC","size":11},
        "xaxis":{"title":"Tiempo (s)","gridcolor":"#2D2D3A","color":"#CCCCCC"},
        "yaxis":{"autorange":"reversed","gridcolor":"#2D2D3A","color":"#CCCCCC"},
        "legend":{"bgcolor":"#1A1C24","bordercolor":"#2D2D3A"},
        "margin":{"l":80,"r":20,"t":50,"b":40},
        "height": 340,
    })

    # C/T vs Takt bar chart + takt line
    ct_shapes = []
    if takt > 0:
        ct_shapes.append({
            "type":"line","x0":-0.5,"x1":len(names)-0.5,"y0":takt,"y1":takt,
            "line":{"color":"#FFC107","width":2,"dash":"dash"},
        })

    ct_data = json.dumps([
        {"type":"bar","name":"Cycle Time (s)",
         "x": names,"y": ct_vals,
         "marker":{"color": [("#5C1A1A" if pm.get("ct_violation") else c)
                             for pm, c in zip(process_list, chart_colors)]},
        },
    ])
    ct_layout = json.dumps({
        "title":{"text":"Cycle Time por Proceso vs. Takt Time","font":{"color":"#FFC107","size":14}},
        "paper_bgcolor":"#0E1117","plot_bgcolor":"#1A1C24",
        "font":{"color":"#CCCCCC"},
        "xaxis":{"gridcolor":"#2D2D3A","color":"#CCCCCC"},
        "yaxis":{"title":"Segundos","gridcolor":"#2D2D3A","color":"#CCCCCC"},
        "shapes": ct_shapes,
        "annotations": ([{"x": len(names)/2 - 0.5,"y": takt + 3,
                          "text":"Takt Time","showarrow":False,
                          "font":{"color":"#FFC107","size":10}}] if takt > 0 else []),
        "margin":{"l":60,"r":20,"t":50,"b":50},
        "height": 300,
    })

    # WIP bar chart
    wip_data = json.dumps([
        {"type":"bar","name":"WIP","x": names,"y": wip_vals,
         "marker":{"color":"#FFA000","line":{"width":0.5,"color":"#0E1117"}}},
    ])
    wip_layout = json.dumps({
        "title":{"text":"WIP por Proceso (Inventario en Proceso)","font":{"color":"#FFC107","size":14}},
        "paper_bgcolor":"#0E1117","plot_bgcolor":"#1A1C24",
        "font":{"color":"#CCCCCC"},
        "xaxis":{"gridcolor":"#2D2D3A","color":"#CCCCCC"},
        "yaxis":{"title":"Unidades","gridcolor":"#2D2D3A","color":"#CCCCCC"},
        "margin":{"l":60,"r":20,"t":50,"b":50},
        "height": 280,
    })

    return f"""
<div class="charts-grid">
  <div class="chart-full">
    <div id="chart-vanva"></div>
  </div>
  <div class="chart-half">
    <div id="chart-ct"></div>
  </div>
  <div class="chart-half">
    <div id="chart-wip"></div>
  </div>
</div>

<script>
  Plotly.newPlot("chart-vanva", {va_nva_data}, {va_nva_layout}, {{responsive:true,displayModeBar:false}});
  Plotly.newPlot("chart-ct",    {ct_data},     {ct_layout},    {{responsive:true,displayModeBar:false}});
  Plotly.newPlot("chart-wip",   {wip_data},    {wip_layout},   {{responsive:true,displayModeBar:false}});
</script>
"""


def _html_analysis_section(takt, total_va, total_lt, pce, bottleneck, has_violation, process_list) -> str:
    conc = _build_conclusions(takt, total_lt, pce, bottleneck, has_violation, process_list, 0)
    bottleneck_detail = ""
    if bottleneck:
        bn = next((p for p in process_list if p["name"] == bottleneck), None)
        if bn:
            excess = bn["ct"] - takt if takt > 0 else 0
            bottleneck_detail = f"""
<div class="analysis-highlight">
  <strong>Análisis del Cuello de Botella: {bottleneck}</strong><br>
  C/T actual: <strong>{bn['ct']:.1f} s</strong> —
  Takt Time: <strong>{takt:.1f} s</strong> —
  Exceso: <strong style="color:#D32F2F">{excess:.1f} s ({excess/takt*100:.1f}% sobre takt)</strong><br>
  Uptime: {bn['uptime']:.0f}% | WIP acumulado: {bn['wip']} u | C/O: {bn['co']:.0f} s<br>
  <em>Para eliminar la restricción se debe reducir el C/T en al menos {excess:.0f} s mediante
  mejoras de proceso, redistribución de operaciones o reducción de changeover (SMED).</em>
</div>
"""

    pce_analysis = ""
    if pce > 0:
        waste_pct = 100 - pce
        nva_total = total_lt - total_va
        pce_analysis = f"""
<div class="analysis-card">
  <h4>Eficiencia del Ciclo de Proceso (PCE)</h4>
  <p>
    Del tiempo total de Lead Time ({total_lt:.1f} s), solo <strong>{total_va:.1f} s ({pce:.1f}%)</strong>
    representan tiempo de valor agregado. El restante <strong>{nva_total:.1f} s ({waste_pct:.1f}%)</strong>
    corresponde a desperdicio de esperas e inventarios intermedios (muda tipo espera y sobreproducción).
  </p>
  <p>
    {'El PCE supera el umbral de referencia industrial (25%), indicando una línea relativamente eficiente.' if pce >= 25 else
     ('El PCE está en rango aceptable pero con oportunidad de mejora. Meta: reducir WIP para elevar PCE > 25%.' if pce >= 10 else
      'El PCE es bajo (< 10%). Existe una oportunidad crítica de reducción de desperdicios. Implementar sistema pull y reducción de WIP como prioridad.')}
  </p>
</div>
"""

    return f"""
<div class="analysis-intro">
  <p>{conc}</p>
</div>
{bottleneck_detail}
{pce_analysis}
<div class="analysis-card">
  <h4>Clasificación de desperdicios identificados (8 Mudas)</h4>
  <ul class="muda-list">
    <li><strong>Inventario (Muri):</strong> WIP acumulado entre procesos = {sum(p['wip'] for p in process_list)} u en total.</li>
    <li><strong>Espera (Muda):</strong> Tiempo NVA total = {sum(p.get('nva',0) for p in process_list):.0f} s por ciclo de producción.</li>
    {"<li><strong>Sobreproducción:</strong> Procesos con C/T > Takt generan inventario no requerido aguas abajo.</li>" if has_violation else ""}
    <li><strong>Transporte/Movimiento:</strong> Evaluar layout de planta para minimizar distancias entre estaciones.</li>
    <li><strong>Procesamiento innecesario:</strong> Revisar changeover times (C/O). Total C/O suma: {sum(p['co'] for p in process_list):.0f} s — candidato a SMED.</li>
  </ul>
</div>
"""


def _html_recommendations(pce, bottleneck, has_violation, process_list, takt) -> str:
    recs = _build_recommendations(pce, bottleneck, has_violation, process_list, takt)
    items = ""
    icons = ["🔧", "📦", "⚖️", "🗺️", "📊"]
    for i, rec in enumerate(recs):
        icon = icons[i] if i < len(icons) else "▶"
        items += f"""
<div class="rec-card">
  <div class="rec-num">{icon}</div>
  <div class="rec-text"><p>{rec}</p></div>
</div>"""
    return items


# =============================================================================
# CSS Y JS EMBEBIDOS
# =============================================================================

_HTML_CSS = f"""
<style>
/* ── Reset / Base ─────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{
  background: {_BG};
  color: {_WHITE};
  font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  font-size: 15px;
  line-height: 1.7;
}}
a {{ color: {_GOLD}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ── Portada ──────────────────────────────────────────────── */
.cover {{
  min-height: 100vh;
  background: linear-gradient(160deg, #0e1117 0%, #1a0808 50%, #0e1117 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 3rem;
  border-bottom: 3px solid {_RED};
}}
.cover-inner {{ max-width: 680px; }}
.cover .logo {{ max-height: 80px; margin-bottom: 2rem; }}
.logo-text {{ font-size: 1.6rem; font-weight: 700; color: {_GOLD}; }}
.cover-title {{
  font-size: 3rem; font-weight: 800; color: {_WHITE};
  letter-spacing: -0.5px; margin-bottom: 0.5rem;
}}
.cover-sub  {{ font-size: 1.15rem; color: {_GOLD}; margin-bottom: 0.5rem; }}
.cover-company {{ font-size: 1rem; color: {_GRAY}; margin-bottom: 0.3rem; }}
.cover-date {{ font-size: 0.88rem; color: {_GRAY}; margin-bottom: 1.5rem; }}
.cover-badge {{
  display: inline-block;
  background: {_RED}; color: {_WHITE};
  padding: 0.4rem 1.2rem; border-radius: 20px;
  font-size: 0.85rem; font-weight: 600; letter-spacing: 0.05em;
}}

/* ── Layout ───────────────────────────────────────────────── */
.container {{ max-width: 1200px; margin: 0 auto; padding: 3rem 2rem 4rem; }}
section {{ margin-bottom: 4rem; }}

/* ── TOC ─────────────────────────────────────────────────── */
.toc {{
  background: {_BG2}; border-left: 4px solid {_GOLD};
  padding: 1.5rem 2rem; border-radius: 8px; margin-bottom: 3rem;
}}
.toc h3 {{ color: {_GOLD}; margin-bottom: 0.7rem; font-size: 1rem; }}
.toc ol {{ padding-left: 1.3rem; }}
.toc li {{ margin-bottom: 0.3rem; }}

/* ── Titles ──────────────────────────────────────────────── */
.section-title {{
  font-size: 1.55rem; font-weight: 700;
  color: {_WHITE}; margin-bottom: 1.2rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid {_RED};
  display: flex; align-items: center; gap: 0.6rem;
}}
.section-num {{
  background: {_RED}; color: {_WHITE};
  width: 30px; height: 30px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 0.9rem; font-weight: 700; flex-shrink: 0;
}}
.section-intro {{ color: {_GRAY}; margin-bottom: 1.2rem; font-size: 0.93rem; }}

/* ── Executive cards ─────────────────────────────────────── */
.exec-card {{
  background: {_BG2}; border: 1px solid {_BORDER};
  border-radius: 10px; padding: 1.5rem 1.8rem; margin-bottom: 1.2rem;
  border-left: 4px solid {_BORDER};
  transition: border-left-color 0.2s;
}}
.exec-card:hover {{ border-left-color: {_GOLD}; }}
.exec-card.highlight {{ border-left-color: {_RED}; background: #1c0c0c; }}
.exec-card h3 {{ color: {_GOLD}; font-size: 1rem; margin-bottom: 0.6rem; }}
.exec-card p  {{ color: {_GRAY}; line-height: 1.75; }}

/* ── VSM Wrapper ─────────────────────────────────────────── */
.vsm-outer {{
  background: {_BG};
  border: 1px solid {_BORDER};
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 0.5rem;
  position: relative;
}}
#vsm-html-wrapper {{
  position: relative;
  overflow-x: auto;
  min-height: 270px;
  padding: 10px 0 20px;
  scrollbar-width: thin;
  scrollbar-color: {_RED} {_BG2};
}}
#vsm-html-wrapper::-webkit-scrollbar {{ height: 7px; }}
#vsm-html-wrapper::-webkit-scrollbar-track {{ background: {_BG2}; }}
#vsm-html-wrapper::-webkit-scrollbar-thumb {{ background: {_RED}; border-radius: 4px; }}
#vsm-scroll-container {{ display: inline-block; padding: 0 20px; }}
#vsm-svg {{ display: block; }}

/* ── Tooltip ─────────────────────────────────────────────── */
#vsm-tooltip {{
  display: none;
  position: fixed;
  background: rgba(10,10,20,0.97);
  border: 1px solid {_GOLD};
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: {_WHITE};
  line-height: 1.6;
  pointer-events: none;
  z-index: 9999;
  max-width: 240px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.6);
}}

/* ── KPI Grid ────────────────────────────────────────────── */
.kpi-grid {{ display: flex; flex-wrap: wrap; gap: 1rem; }}
.kpi-card {{
  flex: 1 1 160px;
  background: {_BG2}; border: 1px solid {_BORDER};
  border-radius: 10px; padding: 1.2rem;
  text-align: center;
  transition: transform 0.2s, box-shadow 0.2s;
}}
.kpi-card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.4); }}
.kpi-label {{ color: {_GRAY}; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 0.4rem; }}
.kpi-value {{ color: {_GOLD}; font-size: 1.7rem; font-weight: 800; margin-bottom: 0.3rem; }}
.kpi-sub   {{ color: {_GRAY}; font-size: 0.78rem; }}
.kpi-red   {{ border-color: {_RED}; }}
.kpi-red .kpi-value {{ color: {_RED}; }}
.kpi-green {{ border-color: #2e7d32; }}
.kpi-green .kpi-value {{ color: #66bb6a; }}
.kpi-yellow .kpi-value {{ color: {_GOLD}; }}

/* ── Table ───────────────────────────────────────────────── */
.table-wrap {{ overflow-x: auto; }}
.data-table {{
  width: 100%; border-collapse: collapse; font-size: 0.9rem;
}}
.data-table th {{
  background: {_RED}; color: {_WHITE};
  padding: 0.7rem 1rem; text-align: left; font-weight: 600;
  cursor: pointer; user-select: none;
  border-bottom: 2px solid {_RED_DARK};
  white-space: nowrap;
}}
.data-table th:hover {{ background: {_RED_DARK}; }}
.data-table td {{
  padding: 0.6rem 1rem; border-bottom: 1px solid {_BORDER};
  color: {_GRAY}; vertical-align: middle;
}}
.data-table tr:nth-child(even) td {{ background: {_BG2}; }}
.data-table tr:hover td {{ background: #222436; }}
.row-violation td {{ background: {_RED_ALERT} !important; color: {_WHITE} !important; }}
.table-note {{ font-size: 0.8rem; color: {_GRAY}; margin-top: 0.5rem; }}
.no-data {{ color: {_GRAY}; font-style: italic; }}

/* ── Charts grid ─────────────────────────────────────────── */
.charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
.chart-full {{ grid-column: 1 / -1; }}
.chart-half {{ }}

/* ── Analysis ────────────────────────────────────────────── */
.analysis-intro {{ color: {_GRAY}; margin-bottom: 1.2rem; line-height: 1.8; }}
.analysis-highlight {{
  background: {_RED_ALERT}; border: 1px solid {_RED};
  border-radius: 8px; padding: 1.2rem 1.5rem; margin-bottom: 1.2rem;
  line-height: 1.75; color: {_WHITE};
}}
.analysis-card {{
  background: {_BG2}; border: 1px solid {_BORDER};
  border-radius: 8px; padding: 1.3rem 1.5rem; margin-bottom: 1.2rem;
}}
.analysis-card h4 {{ color: {_GOLD}; font-size: 0.95rem; margin-bottom: 0.6rem; }}
.analysis-card p  {{ color: {_GRAY}; margin-bottom: 0.5rem; }}
.muda-list {{ list-style: disc; padding-left: 1.5rem; color: {_GRAY}; }}
.muda-list li {{ margin-bottom: 0.35rem; }}

/* ── Recommendations ─────────────────────────────────────── */
.rec-card {{
  display: flex; gap: 1.2rem; align-items: flex-start;
  background: {_BG2}; border: 1px solid {_BORDER};
  border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 1rem;
  border-left: 4px solid {_GOLD};
  transition: border-left-color 0.2s;
}}
.rec-card:hover {{ border-left-color: {_RED}; }}
.rec-num {{ font-size: 1.5rem; flex-shrink: 0; }}
.rec-text p {{ color: {_GRAY}; line-height: 1.75; }}

/* ── Footer ──────────────────────────────────────────────── */
.site-footer {{
  background: #080a0f; border-top: 3px solid {_RED};
  padding: 2.5rem 2rem 1.5rem;
}}
.footer-inner {{
  max-width: 1200px; margin: 0 auto;
  display: flex; align-items: center; gap: 2rem;
  flex-wrap: wrap; margin-bottom: 1.5rem;
}}
.footer-logo .logo {{ max-height: 45px; }}
.footer-logo .logo-text {{ font-size: 1rem; color: {_GOLD}; font-weight: 700; }}
.footer-info {{ color: {_GRAY}; font-size: 0.85rem; line-height: 1.7; }}
.footer-badge {{ display: flex; gap: 0.6rem; flex-wrap: wrap; margin-left: auto; }}
.footer-badge span {{
  background: {_BG2}; color: {_GOLD};
  padding: 0.25rem 0.75rem; border-radius: 20px;
  border: 1px solid {_BORDER}; font-size: 0.78rem;
}}
.footer-copy {{
  max-width: 1200px; margin: 0 auto;
  color: #555; font-size: 0.78rem; text-align: center;
  border-top: 1px solid {_BORDER}; padding-top: 1rem;
}}

/* ── Scrollbar global ────────────────────────────────────── */
::-webkit-scrollbar {{ width: 7px; height: 7px; }}
::-webkit-scrollbar-track {{ background: {_BG2}; }}
::-webkit-scrollbar-thumb {{ background: {_RED}; border-radius: 4px; }}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 768px) {{
  .cover-title {{ font-size: 2rem; }}
  .charts-grid {{ grid-template-columns: 1fr; }}
  .chart-full {{ grid-column: 1; }}
  .footer-inner {{ flex-direction: column; }}
  .footer-badge {{ margin-left: 0; }}
}}

@media print {{
  .cover {{ page-break-after: always; }}
  section {{ page-break-inside: avoid; }}
}}
</style>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
"""

_HTML_TABLE_SORT_JS = """
<script>
// ── Sortable table ────────────────────────────────────────────────────────
document.querySelectorAll("table.sortable").forEach(function(table) {
  var tbody = table.tBodies[0];
  var headers = table.querySelectorAll("thead th");
  var sortDir = {};

  headers.forEach(function(th, colIdx) {
    th.style.cursor = "pointer";
    th.addEventListener("click", function() {
      var dir = sortDir[colIdx] === "asc" ? "desc" : "asc";
      sortDir = {};
      sortDir[colIdx] = dir;

      var rows = Array.from(tbody.querySelectorAll("tr"));
      rows.sort(function(a, b) {
        var aVal = a.cells[colIdx] ? a.cells[colIdx].innerText.trim() : "";
        var bVal = b.cells[colIdx] ? b.cells[colIdx].innerText.trim() : "";
        var aNum = parseFloat(aVal.replace(/[^0-9.\-]/g, ""));
        var bNum = parseFloat(bVal.replace(/[^0-9.\-]/g, ""));
        if (!isNaN(aNum) && !isNaN(bNum)) {
          return dir === "asc" ? aNum - bNum : bNum - aNum;
        }
        return dir === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      });
      rows.forEach(function(r) { tbody.appendChild(r); });
    });
  });
});
</script>
"""
