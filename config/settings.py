# =============================================================================
# config/settings.py — Constantes globales, paleta EA y configuración general
# Proyecto: Digital VSM & Operational Intelligence - EA Innovation & Solutions
# =============================================================================

# -----------------------------------------------------------------------------
# PALETA DE COLORES EA (extraída del logo EA_2.png)
# -----------------------------------------------------------------------------
COLOR_BG_PRIMARY      = "#0E1117"   # Negro fondo principal
COLOR_BG_SECONDARY    = "#1A1C24"   # Negro secundario / cards
COLOR_RED_MAIN        = "#D32F2F"   # Rojo EA principal
COLOR_RED_DARK        = "#B71C1C"   # Rojo oscuro hover
COLOR_RED_ALERT       = "#5C1A1A"   # Rojo oscuro alertas / fondo violación
COLOR_GOLD            = "#FFC107"   # Dorado / Amber EA
COLOR_GOLD_DARK       = "#FFA000"   # Dorado oscuro
COLOR_WHITE           = "#FFFFFF"   # Blanco texto principal
COLOR_TEXT_SECONDARY  = "#CCCCCC"   # Gris texto secundario
COLOR_BORDER          = "#2D2D3A"   # Gris bordes

# Colores adicionales para gráficas (serie por proceso)
CHART_COLORS = [
    COLOR_RED_MAIN,   # #D32F2F
    COLOR_GOLD,       # #FFC107
    COLOR_GOLD_DARK,  # #FFA000
    "#FF6B35",        # Naranja cálido
    "#C62828",        # Rojo profundo
    "#FF8F00",        # Ámbar oscuro
    "#E64A19",        # Naranja quemado
    "#AD1457",        # Rosa oscuro
]

# -----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE LA APLICACIÓN
# -----------------------------------------------------------------------------
PAGE_TITLE      = "Digital VSM & Operational Intelligence - EA Innovation & Solutions"
PAGE_ICON       = "🏭"
APP_LAYOUT      = "wide"
COMPANY_NAME    = "EA Innovation & Solutions"
APP_VERSION     = "2.0.0"

# Rutas de assets (relativas a la raíz del proyecto)
LOGO_PATH       = "assets/EA_2.png"
REF_IMAGE_PATH  = "assets/Gemini_Generated_Image_hovoawhovoawhovo.png"

# -----------------------------------------------------------------------------
# PARÁMETROS POR DEFECTO DE LÍNEA
# -----------------------------------------------------------------------------
AVAILABLE_HOURS_DEFAULT = 8.0    # Horas disponibles por turno
DAILY_DEMAND_DEFAULT    = 600    # Unidades demandadas por día

# Nombre de la tabla en Supabase
SUPABASE_TABLE = "processes_vsm"

# -----------------------------------------------------------------------------
# DATOS FALLBACK — Se usan cuando Supabase no está disponible
# Formato: lista de dicts con todos los campos requeridos
# -----------------------------------------------------------------------------
DEFAULT_PROCESSES = [
    {
        "id": 1,
        "name": "Corte",
        "cycle_time": 48,           # segundos por unidad
        "changeover_time": 120,     # segundos de cambio de herramienta
        "wip": 30,                  # unidades en inventario antes del proceso
        "uptime": 95.0,             # porcentaje de disponibilidad
        "process_order": 1,
        "va_ratio": 0.70,           # ratio de tiempo de valor agregado
        "operators": 2,
        "batch_size": 1,
    },
    {
        "id": 2,
        "name": "Prensa",
        "cycle_time": 52,
        "changeover_time": 90,
        "wip": 25,
        "uptime": 98.0,
        "process_order": 2,
        "va_ratio": 0.65,
        "operators": 1,
        "batch_size": 1,
    },
    {
        "id": 3,
        "name": "Ensamble",
        "cycle_time": 52,
        "changeover_time": 150,
        "wip": 40,
        "uptime": 92.0,
        "process_order": 3,
        "va_ratio": 0.60,
        "operators": 3,
        "batch_size": 1,
    },
    {
        "id": 4,
        "name": "Prueba",
        "cycle_time": 53,
        "changeover_time": 60,
        "wip": 20,
        "uptime": 99.0,
        "process_order": 4,
        "va_ratio": 0.80,
        "operators": 1,
        "batch_size": 1,
    },
    {
        "id": 5,
        "name": "Corrosión",
        "cycle_time": 46,
        "changeover_time": 180,
        "wip": 35,
        "uptime": 96.0,
        "process_order": 5,
        "va_ratio": 0.55,
        "operators": 2,
        "batch_size": 1,
    },
]

# Columnas requeridas para importación de Excel
REQUIRED_EXCEL_COLUMNS = [
    "name",
    "cycle_time",
    "changeover_time",
    "wip",
    "uptime",
    "process_order",
]

# Columnas opcionales con valores por defecto al importar
OPTIONAL_EXCEL_COLUMNS = {
    "va_ratio": 0.65,
    "operators": 1,
    "batch_size": 1,
}

# -----------------------------------------------------------------------------
# RANGOS DE VALIDACIÓN DE DATOS
# -----------------------------------------------------------------------------
VALIDATION_RANGES = {
    "cycle_time":       (1,    3600),   # 1s a 1 hora
    "changeover_time":  (0,    7200),   # 0s a 2 horas
    "wip":              (0,    10000),  # unidades
    "uptime":           (0.0,  100.0), # porcentaje
    "process_order":    (1,    999),
    "va_ratio":         (0.0,  1.0),
    "operators":        (1,    100),
    "batch_size":       (1,    1000),
}

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DEL DIAGRAMA VSM
# -----------------------------------------------------------------------------
VSM_DIAGRAM_HEIGHT  = 520    # píxeles de altura del componente HTML
VSM_NODE_WIDTH      = 130    # píxeles de ancho por caja de proceso
VSM_NODE_HEIGHT     = 110    # píxeles de alto por caja de proceso
VSM_ENTRY_WIDTH     = 90     # ancho nodo entrada (Entry/Proveedor)
VSM_CUSTOMER_WIDTH  = 90     # ancho nodo salida (Customer)
VSM_ARROW_COLOR     = COLOR_GOLD
VSM_TRIANGLE_COLOR  = COLOR_RED_MAIN
VSM_BOX_BORDER_OUTER = COLOR_GOLD
VSM_BOX_BORDER_INNER = COLOR_RED_MAIN

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE REPORTES PDF/HTML
# -----------------------------------------------------------------------------
PDF_MARGIN_MM        = 15    # margen en mm para el PDF
PDF_FONT_FAMILY      = "Helvetica"
PDF_HEADER_HEIGHT    = 40    # altura del header en mm
PDF_FOOTER_HEIGHT    = 15    # altura del footer en mm
HTML_REPORT_TITLE    = f"Digital VSM Report — {COMPANY_NAME}"
PDF_REPORT_TITLE     = f"Digital VSM Report — {COMPANY_NAME}"

# -----------------------------------------------------------------------------
# TEXTOS DE UI (bilingüe: español/inglés donde aplique)
# -----------------------------------------------------------------------------
UI_STRINGS = {
    "sidebar_params_title":    "⚙️ Parámetros de Línea",
    "sidebar_import_title":    "📂 Importar / Exportar Datos",
    "sidebar_sim_title":       "🔄 Modo de Análisis",
    "sidebar_state_actual":    "Estado Actual",
    "sidebar_state_futuro":    "Estado Futuro",
    "control_panel_title":     "Generate Data Control",
    "btn_generate_pdf":        "Generate Industrial VSM Report",
    "btn_generate_html":       "Generate HTML Whitepaper",
    "btn_download_template":   "📥 Descargar Plantilla Excel",
    "kpi_takt":                "Takt Time",
    "kpi_lead_time":           "Lead Time Total",
    "kpi_pce":                 "PCE %",
    "kpi_bottleneck":          "Cuello de Botella",
    "chart_timeline_title":    "Lead Time vs. PCE",
    "chart_va_nva_title":      "Value-Added vs. Non-Value-Added Time",
    "chart_wip_title":         "WIP por Proceso",
    "diagram_takt_label":      "Takt Time",
    "diagram_entry_label":     "ENTRY",
    "diagram_customer_label":  "CUSTOMER",
    "lean_labels": [
        "Flow", "Results", "Tiempo", "Smooth", "Tamaño"
    ],
}
