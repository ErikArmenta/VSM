# -*- coding: utf-8 -*-
"""
config/styles.py — CSS global dark theme para Digital VSM EA Innovation & Solutions
Centraliza todos los estilos: fondo, headers, métricas, botones, DataFrames,
scrollbar, sidebar, badges, footer profesional y animaciones hover.
"""

import streamlit as st


def get_global_css() -> str:
    """
    Retorna el string CSS completo del dark theme EA.
    Incluye: fondo, tipografía, métricas, botones, DataFrames, scrollbar,
    sidebar, badges de simulación, animaciones @keyframes y footer profesional.
    """
    return """
    <style>
    /* ============================================================
       FONDO PRINCIPAL Y TIPOGRAFÍA GLOBAL
    ============================================================ */
    .stApp {
        background-color: #0E1117;
        font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
    }

    /* ============================================================
       HEADERS h1 / h2 / h3
    ============================================================ */
    h1, h2, h3,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #FFC107 !important;
        font-family: 'Segoe UI', sans-serif;
        letter-spacing: 0.02em;
    }

    h1 { font-size: 2rem; font-weight: 700; }
    h2 { font-size: 1.5rem; font-weight: 600; }
    h3 { font-size: 1.2rem; font-weight: 600; }

    /* ============================================================
       MÉTRICAS — borde rojo EA, fondo oscuro, animación hover
    ============================================================ */
    .stMetric {
        background-color: #1E1E1E;
        border: 1px solid #D32F2F;
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .stMetric:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(211, 47, 47, 0.35);
    }

    .stMetric label {
        color: #CCCCCC !important;
        font-weight: 500;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .stMetric .metric-value,
    [data-testid="stMetricValue"] {
        color: #FFC107 !important;
        font-size: 1.8rem;
        font-weight: 700;
    }

    [data-testid="stMetricDelta"] {
        color: #CCCCCC !important;
    }

    /* ============================================================
       BOTONES — rojo EA con hover oscuro
    ============================================================ */
    .stButton > button {
        background-color: #D32F2F;
        color: #FFFFFF;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.5rem 1.2rem;
        transition: background-color 0.2s ease, color 0.2s ease, transform 0.15s ease;
        letter-spacing: 0.03em;
    }

    .stButton > button:hover {
        background-color: #B71C1C;
        color: #FFC107;
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0px);
        background-color: #5C1A1A;
    }

    .stDownloadButton > button {
        background-color: #1A1C24;
        color: #FFC107;
        border: 1px solid #FFC107;
        border-radius: 8px;
        font-weight: 600;
        transition: background-color 0.2s ease, color 0.2s ease;
    }

    .stDownloadButton > button:hover {
        background-color: #FFC107;
        color: #0E1117;
    }

    /* ============================================================
       DATAFRAMES — fondo oscuro secundario
    ============================================================ */
    .css-1offfwp, .css-1kyxreq,
    [data-testid="stDataFrame"],
    .stDataFrame {
        background-color: #1A1C24 !important;
        border-radius: 12px;
        border: 1px solid #2D2D3A;
    }

    [data-testid="stDataFrame"] table {
        background-color: #1A1C24 !important;
        color: #FFFFFF !important;
    }

    [data-testid="stDataFrame"] thead th {
        background-color: #D32F2F !important;
        color: #FFFFFF !important;
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
    }

    [data-testid="stDataFrame"] tbody tr:nth-child(even) td {
        background-color: #22242E !important;
    }

    [data-testid="stDataFrame"] tbody tr:hover td {
        background-color: #2D2D3A !important;
    }

    /* ============================================================
       SCROLLBAR PERSONALIZADA — dark theme webkit
    ============================================================ */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #0E1117;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: #2D2D3A;
        border-radius: 4px;
        border: 2px solid #0E1117;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #D32F2F;
    }

    ::-webkit-scrollbar-corner {
        background: #0E1117;
    }

    /* ============================================================
       SIDEBAR — estilizado oscuro con acento EA
    ============================================================ */
    [data-testid="stSidebar"] {
        background-color: #12141B !important;
        border-right: 2px solid #D32F2F;
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #FFC107 !important;
    }

    [data-testid="stSidebar"] label {
        color: #CCCCCC !important;
        font-size: 0.875rem;
    }

    [data-testid="stSidebar"] .stNumberInput input,
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stSelectbox select {
        background-color: #1A1C24 !important;
        color: #FFFFFF !important;
        border: 1px solid #2D2D3A !important;
        border-radius: 6px;
    }

    [data-testid="stSidebar"] .stNumberInput input:focus,
    [data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #FFC107 !important;
        box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.2) !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #2D2D3A;
        margin: 1rem 0;
    }

    /* ============================================================
       SLIDERS — acento dorado/rojo EA
    ============================================================ */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background-color: #D32F2F !important;
        border-color: #FFC107 !important;
    }

    .stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
        color: #FFC107 !important;
    }

    /* ============================================================
       ALERTS / INFO / WARNING / SUCCESS
    ============================================================ */
    .stAlert {
        background-color: #1A1C24;
        border-radius: 8px;
        border-left: 4px solid #FFC107;
    }

    .stAlert [data-baseweb="notification"] {
        background-color: #1A1C24 !important;
        color: #CCCCCC !important;
    }

    /* ============================================================
       TABS — estilo EA
    ============================================================ */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #12141B;
        border-bottom: 2px solid #2D2D3A;
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #CCCCCC;
        border-radius: 6px 6px 0 0;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        transition: color 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1A1C24 !important;
        color: #FFC107 !important;
        border-bottom: 2px solid #D32F2F !important;
    }

    /* ============================================================
       EXPANDER
    ============================================================ */
    .streamlit-expanderHeader {
        background-color: #1A1C24;
        color: #FFC107 !important;
        border-radius: 8px;
        border: 1px solid #2D2D3A;
    }

    .streamlit-expanderContent {
        background-color: #12141B;
        border: 1px solid #2D2D3A;
        border-top: none;
        border-radius: 0 0 8px 8px;
    }

    /* ============================================================
       FILE UPLOADER
    ============================================================ */
    [data-testid="stFileUploader"] {
        background-color: #1A1C24;
        border: 2px dashed #2D2D3A;
        border-radius: 12px;
        transition: border-color 0.2s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #D32F2F;
    }

    [data-testid="stFileUploader"] label {
        color: #CCCCCC !important;
    }

    /* ============================================================
       SELECTBOX / MULTISELECT
    ============================================================ */
    .stSelectbox [data-baseweb="select"] div,
    .stMultiSelect [data-baseweb="select"] div {
        background-color: #1A1C24 !important;
        color: #FFFFFF !important;
        border-color: #2D2D3A !important;
    }

    /* ============================================================
       DIVIDER
    ============================================================ */
    hr {
        border-color: #2D2D3A !important;
        margin: 1rem 0;
    }

    /* ============================================================
       BADGE DE SIMULACIÓN
    ============================================================ */
    .simulation-badge {
        background-color: #FFC107;
        color: #0E1117;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        animation: pulse-badge 2s infinite;
    }

    .simulation-badge-active {
        background-color: #D32F2F;
        color: #FFFFFF;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        animation: pulse-badge 1.5s infinite;
    }

    /* ============================================================
       ANIMACIONES @keyframes
    ============================================================ */
    @keyframes pulse-badge {
        0%   { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.5); }
        70%  { box-shadow: 0 0 0 8px rgba(255, 193, 7, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 193, 7, 0); }
    }

    @keyframes fade-in-up {
        from {
            opacity: 0;
            transform: translateY(16px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes shimmer {
        0%   { background-position: -200% center; }
        100% { background-position: 200% center; }
    }

    /* Animación de entrada para el bloque principal */
    .main .block-container {
        animation: fade-in-up 0.4s ease both;
    }

    /* Cards / contenedores con hover elevado */
    .ea-card {
        background-color: #1A1C24;
        border: 1px solid #2D2D3A;
        border-radius: 12px;
        padding: 1.2rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }

    .ea-card:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 24px rgba(211, 47, 47, 0.25);
        border-color: #D32F2F;
    }

    /* ============================================================
       FOOTER PROFESIONAL — copiado de VSM.py original
    ============================================================ */
    .footer {
        background-color: #1A1C24;
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 1.5rem;
        border-top: 2px solid #D32F2F;
        color: #CCCCCC;
        font-family: 'Segoe UI', sans-serif;
    }

    .footer .quote {
        color: #FFC107;
        font-size: 1.2rem;
        font-style: italic;
        font-weight: 500;
        text-align: center;
        margin-bottom: 1rem;
    }

    .footer .info {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 1rem;
        font-size: 0.9rem;
    }

    .footer .info div {
        flex: 1;
        min-width: 180px;
    }

    .footer .info strong {
        color: #FFC107;
    }

    .footer .badge {
        background-color: #D32F2F;
        color: white;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.7rem;
        display: inline-block;
        margin-right: 6px;
    }

    .footer hr {
        border-color: #2D2D3A;
        margin: 1rem 0;
    }

    /* ============================================================
       CONTENEDOR PRINCIPAL — padding ajustado
    ============================================================ */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }

    /* ============================================================
       TEXTO GENERAL
    ============================================================ */
    p, .stMarkdown p, .stText {
        color: #CCCCCC;
        line-height: 1.6;
    }

    small, .stCaption {
        color: #888888 !important;
    }

    /* ============================================================
       NUMBER INPUT / TEXT INPUT en contenido principal
    ============================================================ */
    .stNumberInput input,
    .stTextInput input {
        background-color: #1A1C24 !important;
        color: #FFFFFF !important;
        border: 1px solid #2D2D3A !important;
        border-radius: 6px;
    }

    .stNumberInput input:focus,
    .stTextInput input:focus {
        border-color: #FFC107 !important;
        box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.2) !important;
    }

    /* ============================================================
       PROGRESS BAR — rojo EA
    ============================================================ */
    .stProgress [data-testid="stProgressBar"] > div {
        background-color: #D32F2F !important;
    }

    /* ============================================================
       TOOLTIP (nativo Streamlit)
    ============================================================ */
    [data-baseweb="tooltip"] {
        background-color: #1A1C24 !important;
        color: #FFFFFF !important;
        border: 1px solid #2D2D3A !important;
    }
    </style>
    """


FOOTER_HTML = """
<div class="footer">
    <div class="quote">
        "La exactitud es nuestra firma e innovar es nuestra naturaleza"
    </div>
    <div class="info">
        <div>
            <strong><span class="badge">&#128202;</span> EA Simplex Production Optimizer v2.0</strong><br>
            Digital Value Stream Mapping<br>
            Lean Manufacturing Intelligence
        </div>
        <div>
            <strong><span class="badge">&#128295;</span> Ing. Maestro Erik Armenta</strong><br>
            Operational Excellence &amp; Industry 4.0
        </div>
        <div>
            <strong><span class="badge">&#128205;</span> EA Innovation &amp; Solutions</strong><br>
            Cd. Ju&aacute;rez, MX
        </div>
        <div>
            <strong><span class="badge">&#9881;&#65039;</span> Tecnolog&iacute;as</strong><br>
            Streamlit &middot; Supabase &middot; Plotly &middot; Altair
        </div>
        <div>
            <strong><span class="badge">&#128300;</span> Funcionalidades</strong><br>
            CRUD &middot; Simulaci&oacute;n What-If &middot; VSM Din&aacute;mico<br>
            C&aacute;lculo Takt / Lead Time / PCE &middot; Import/Export Excel
        </div>
        <div>
            <strong><span class="badge">&#128190;</span> Persistencia</strong><br>
            Supabase PostgreSQL &middot; Escenarios What-If<br>
            Comparador de escenarios
        </div>
    </div>
    <hr>
    <div style="text-align: center; font-size: 0.75rem; opacity: 0.7;">
        &copy; EA Innovation &amp; Solutions &mdash; Lean Digital VSM | Data persistente con Supabase
    </div>
</div>
"""


def inject_css() -> None:
    """
    Inyecta el CSS global de dark theme EA en la app Streamlit.
    Llamar una sola vez al inicio de app.py, antes de renderizar cualquier componente.
    """
    st.markdown(get_global_css(), unsafe_allow_html=True)


def render_footer() -> None:
    """
    Renderiza el footer profesional EA al final de la página.
    Incluye quote, info de tecnologías, branding y copyright.
    """
    st.markdown(FOOTER_HTML, unsafe_allow_html=True)
