# -*- coding: utf-8 -*-
"""
Digital Value Stream Mapping (VSM) - EA Innovation & Solutions
Lean Manufacturing Intelligence con Streamlit, Supabase y visualización interactiva.
Versión con importación/exportación Excel y VSM mejorado.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from supabase import create_client, Client
from io import BytesIO

# ------------------------------------------------------------
# Configuración de página y estilos oscuros premium
# ------------------------------------------------------------
st.set_page_config(
    page_title="Digital VSM - EA Innovation & Solutions",
    layout="wide",
    page_icon="🏭"
)

# CSS personalizado
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #FFC107 !important;
        font-family: 'Segoe UI', sans-serif;
    }
    .stMetric {
        background-color: #1E1E1E;
        border: 1px solid #D32F2F;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .stMetric label {
        color: #FFFFFF !important;
        font-weight: 500;
    }
    .stMetric .metric-value {
        color: #FFC107 !important;
        font-size: 1.8rem;
    }
    .css-1offfwp, .css-1kyxreq, .stDataFrame {
        background-color: #1A1C24;
        border-radius: 12px;
        border: 1px solid #2D2D3A;
    }
    .stButton button {
        background-color: #D32F2F;
        color: white;
        border-radius: 8px;
        border: none;
        transition: 0.2s;
    }
    .stButton button:hover {
        background-color: #B71C1C;
        color: #FFC107;
    }
    .stAlert {
        background-color: #2D2D3A;
        color: #FFC107;
    }
    .simulation-badge {
        background-color: #FFC107;
        color: #0E1117;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Inicialización de conexión a Supabase
# ------------------------------------------------------------
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["URL"]
    key = st.secrets["supabase"]["KEY"]
    return create_client(url, key)

supabase = init_connection()

# ------------------------------------------------------------
# Funciones de acceso a datos (CRUD real contra Supabase)
# ------------------------------------------------------------
def load_processes():
    response = supabase.table("processes_vsm").select("*").order("process_order").execute()
    return pd.DataFrame(response.data)

def save_processes(df: pd.DataFrame):
    current = load_processes()
    new_ids = set(df[df['id'].notna()]['id'].astype(int)) if 'id' in df else set()
    for _, row in current.iterrows():
        if row['id'] not in new_ids:
            supabase.table("processes_vsm").delete().eq("id", row['id']).execute()
    for _, row in df.iterrows():
        record = row.to_dict()
        if 'id' in record and pd.notna(record['id']):
            supabase.table("processes_vsm").update(record).eq("id", record['id']).execute()
        else:
            record.pop('id', None)
            supabase.table("processes_vsm").insert(record).execute()
    st.cache_data.clear()

def add_process_default():
    max_order = len(load_processes()) + 1
    new_row = {
        "name": "Nuevo Proceso",
        "cycle_time": 50.0,
        "changeover_time": 100.0,
        "wip": 10,
        "uptime": 95.0,
        "process_order": max_order
    }
    supabase.table("processes_vsm").insert(new_row).execute()
    st.cache_data.clear()
    st.rerun()

def delete_process(process_id: int):
    supabase.table("processes_vsm").delete().eq("id", process_id).execute()
    st.cache_data.clear()
    st.rerun()

def replace_all_processes(df: pd.DataFrame):
    """Reemplaza toda la tabla con los datos de un DataFrame (útil para importación)"""
    # Limpiar tabla
    supabase.table("processes_vsm").delete().neq("id", 0).execute()  # elimina todos
    # Insertar nuevos
    for _, row in df.iterrows():
        record = row.to_dict()
        record.pop('id', None)  # que no lleve id
        supabase.table("processes_vsm").insert(record).execute()
    st.cache_data.clear()

# ------------------------------------------------------------
# Motor de cálculo Lean
# ------------------------------------------------------------
def compute_metrics(df: pd.DataFrame, available_sec: float, demand: float) -> dict:
    if df.empty:
        return {
            "takt": 0, "total_va": 0, "total_lead_time": 0, "pce": 0,
            "process_metrics": [], "has_violation": False, "bottleneck": None
        }
    takt = available_sec / demand if demand > 0 else 0
    df = df.copy()
    total_va = df["cycle_time"].sum()
    df["nva_waiting"] = df["wip"] * takt
    total_lead_time = total_va + df["nva_waiting"].sum()
    pce = (total_va / total_lead_time * 100) if total_lead_time > 0 else 0
    has_violation = any(df["cycle_time"] > takt) if takt > 0 else False

    # Identificar cuello de botella (mayor C/T relativo al takt)
    if takt > 0:
        df["ct_ratio"] = df["cycle_time"] / takt
        bottleneck_idx = df["ct_ratio"].idxmax()
        bottleneck = df.loc[bottleneck_idx, "name"] if not df.empty else None
    else:
        bottleneck = None

    process_metrics = []
    for _, row in df.iterrows():
        process_metrics.append({
            "name": row["name"],
            "ct": row["cycle_time"],
            "co": row["changeover_time"],
            "wip": row["wip"],
            "nva": row["nva_waiting"],
            "va": row["cycle_time"],
            "uptime": row["uptime"],
            "ct_violation": row["cycle_time"] > takt if takt > 0 else False
        })
    return {
        "takt": takt,
        "total_va": total_va,
        "total_lead_time": total_lead_time,
        "pce": pce,
        "process_metrics": process_metrics,
        "has_violation": has_violation,
        "bottleneck": bottleneck
    }

# ------------------------------------------------------------
# Visualización VSM INTERACTIVA ESTILO "Su/hr" (unidades por hora)
# ------------------------------------------------------------
def render_vsm(df: pd.DataFrame, takt_time: float):
    """
    Dibuja un diagrama VSM estilo industrial: cajas con nombre, Su/hr, WIP,
    triángulos de inventario, flechas, línea de Takt.
    """
    if df.empty:
        st.warning("Sin procesos para mostrar el VSM.")
        return

    n = len(df)
    x_positions = list(range(n))
    box_width = 0.9
    box_height = 1.1

    fig = go.Figure()

    # Calcular lead time acumulado (para hover y posible uso futuro)
    df = df.copy()
    df["cum_lead"] = 0.0
    cum = 0.0
    for i in range(n):
        cum += df.iloc[i]["cycle_time"] + (df.iloc[i]["wip"] * takt_time if takt_time > 0 else 0)
        df.iloc[i, df.columns.get_loc("cum_lead")] = cum

    # ---------- 1. Dibujar rectángulos ----------
    for i, (idx, row) in enumerate(df.iterrows()):
        xc = x_positions[i]
        x0 = xc - box_width/2
        x1 = xc + box_width/2
        y0 = -box_height/2
        y1 = box_height/2

        # Color de fondo: rojo si C/T > Takt, gris normal
        fillcolor = "#5C1A1A" if row["cycle_time"] > takt_time else "#2A2A2A"
        # Borde doble
        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            line=dict(color="#FFC107", width=2.5),
            fillcolor=fillcolor, opacity=0.95,
            layer="above"
        )
        fig.add_shape(
            type="rect", x0=x0+0.03, y0=y0+0.03, x1=x1-0.03, y1=y1-0.03,
            line=dict(color="#D32F2F", width=1),
            fillcolor="rgba(0,0,0,0)",
            layer="above"
        )

        # Nombre del proceso
        fig.add_annotation(
            x=xc, y=y1 - 0.15, text=row["name"],
            showarrow=False, font=dict(color="white", size=13, family="Arial Black"),
            xanchor="center", yanchor="top"
        )
        # Su/hr (unidades por hora)
        units_per_hour = 3600 / row["cycle_time"] if row["cycle_time"] > 0 else 0
        fig.add_annotation(
            x=xc, y=y0 + 0.55,
            text=f"{units_per_hour:.1f} Su/hr",
            showarrow=False, font=dict(color="#FFC107", size=11),
            xanchor="center"
        )
        # WIP dentro de la caja
        fig.add_annotation(
            x=xc, y=y0 + 0.2,
            text=f"WIP: {row['wip']}",
            showarrow=False, font=dict(color="white", size=11),
            xanchor="center"
        )
        # Opcional: mostrar C/T pequeño (para referencia)
        fig.add_annotation(
            x=xc, y=y0 - 0.25,
            text=f"C/T: {row['cycle_time']:.0f}s",
            showarrow=False, font=dict(color="#CCCCCC", size=9),
            xanchor="center"
        )

        # Hover con detalles
        hover_text = (f"<b>{row['name']}</b><br>"
                      f"⚙️ C/T: {row['cycle_time']}s<br>"
                      f"📦 WIP: {row['wip']}<br>"
                      f"📈 Uptime: {row['uptime']}%<br>"
                      f"🔄 C/O: {row['changeover_time']}s<br>"
                      f"⏱️ Lead Time acum.: {row['cum_lead']:.0f}s")
        fig.add_trace(go.Scatter(
            x=[xc], y=[0],
            mode="markers", marker=dict(size=0, opacity=0),
            hoverinfo="text", text=hover_text,
            hoverlabel=dict(bgcolor="#1E1E1E", font_size=12),
            showlegend=False
        ))

    # ---------- 2. Triángulos de inventario entre procesos ----------
    for i in range(n - 1):
        x_center = (x_positions[i] + x_positions[i+1]) / 2
        wip_value = df.iloc[i]["wip"]
        y_base = 0.0
        fig.add_shape(
            type="path",
            path=f"M {x_center - 0.2} {y_base - 0.2} L {x_center + 0.2} {y_base} L {x_center - 0.2} {y_base + 0.2} Z",
            line=dict(color="#FFC107", width=1),
            fillcolor="#D32F2F",
            opacity=0.9
        )
        fig.add_annotation(
            x=x_center + 0.12, y=y_base,
            text=str(wip_value), showarrow=False,
            font=dict(color="white", size=10), xanchor="left"
        )

    # ---------- 3. Flechas ----------
    for i in range(n - 1):
        x_start = x_positions[i] + box_width/2
        x_end = x_positions[i+1] - box_width/2
        fig.add_annotation(
            x=x_end, y=0, ax=x_start, ay=0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2,
            arrowcolor="#FFC107", standoff=12
        )

    # ---------- 4. Línea de Takt (opcional pero la dejamos) ----------
    if takt_time > 0:
        y_takt = 0.95
        fig.add_shape(
            type="line", x0=-0.5, y0=y_takt, x1=n-0.5, y1=y_takt,
            line=dict(color="#FFC107", width=1.5, dash="dot"), opacity=0.6
        )
        fig.add_annotation(
            x=n-0.5, y=y_takt+0.08, text=f"Takt: {takt_time:.1f}s",
            showarrow=False, font=dict(color="#FFC107", size=9), xanchor="right"
        )
        # Marcadores de exceso
        for i, row in df.iterrows():
            if row["cycle_time"] > takt_time:
                xc = x_positions[i]
                fig.add_annotation(
                    x=xc, y=y_takt - 0.15, text="⚠️",
                    showarrow=False, font=dict(color="#D32F2F", size=14), xanchor="center"
                )

    # Layout final
    fig.update_layout(
        title=dict(text="Value Stream Map (VSM)", font=dict(color="#FFC107"), x=0.5),
        xaxis=dict(showgrid=False, zeroline=False, visible=False, range=[-1.2, n+0.2], fixedrange=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False, range=[-1.6, 1.5], fixedrange=False),
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        height=550, autosize=True, margin=dict(l=20, r=20, t=60, b=20),
        hovermode="closest", dragmode="pan",
        modebar=dict(orientation="v", bgcolor="rgba(30,30,30,0.8)", color="#FFC107")
    )
    st.plotly_chart(fig, use_container_width=True, config=dict(scrollZoom=True, displayModeBar=True, responsive=True))

# ------------------------------------------------------------
# NUEVA FUNCIÓN: Timeline comparativa Current vs Target State
# ------------------------------------------------------------
def render_timeline_comparison(current_df: pd.DataFrame, sim_df: pd.DataFrame, takt_time: float):
    """
    Muestra una línea de tiempo comparativa entre el estado actual y el futuro (simulación).
    Basado en la imagen: Wait Time y Process Time acumulados por día (0 a 10).
    """
    if current_df.empty:
        return

    # Función para calcular tiempos totales (VA y espera total)
    def build_times(df):
        total_va = df["cycle_time"].sum()
        total_wait = (df["wip"] * takt_time).sum() if takt_time > 0 else 0
        return total_va, total_wait

    va_current, wait_current = build_times(current_df)
    va_sim, wait_sim = build_times(sim_df) if sim_df is not None and not sim_df.empty else (va_current, wait_current)

    # Días de 0 a 10 (simulamos una progresión lineal)
    days = list(range(11))
    def cumulative_times(va_total, wait_total):
        cum_va = [va_total * (d / 10) for d in days]
        cum_wait = [wait_total * (d / 10) for d in days]
        return cum_va, cum_wait

    va_cur_cum, wait_cur_cum = cumulative_times(va_current, wait_current)
    va_sim_cum, wait_sim_cum = cumulative_times(va_sim, wait_sim)

    # Construir DataFrame para Plotly
    df_cur = pd.DataFrame({"Día": days, "Tipo": "Current - Process Time", "Segundos": va_cur_cum})
    df_cur_wait = pd.DataFrame({"Día": days, "Tipo": "Current - Wait Time", "Segundos": wait_cur_cum})
    df_sim = pd.DataFrame({"Día": days, "Tipo": "Target - Process Time", "Segundos": va_sim_cum})
    df_sim_wait = pd.DataFrame({"Día": days, "Tipo": "Target - Wait Time", "Segundos": wait_sim_cum})
    plot_df = pd.concat([df_cur, df_cur_wait, df_sim, df_sim_wait])

    fig = px.line(plot_df, x="Día", y="Segundos", color="Tipo",
                  title="Timeline: Current vs. Target State",
                  line_dash="Tipo",
                  line_dash_map={
                      "Current - Process Time": "solid",
                      "Current - Wait Time": "solid",
                      "Target - Process Time": "dash",
                      "Target - Wait Time": "dash"
                  },
                  color_discrete_map={
                      "Current - Process Time": "#FFC107",
                      "Current - Wait Time": "#D32F2F",
                      "Target - Process Time": "#FFA500",
                      "Target - Wait Time": "#B71C1C"
                  })
    fig.update_layout(plot_bgcolor="#1A1C24", paper_bgcolor="#0E1117", font=dict(color="white"),
                      xaxis_title="Día", yaxis_title="Tiempo acumulado (segundos)",
                      legend_title="Estado y tipo de tiempo")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# Funciones para importar/exportar Excel
# ------------------------------------------------------------
def generate_excel_template():
    """Genera un archivo Excel con la estructura esperada y datos de ejemplo."""
    template_df = pd.DataFrame({
        "name": ["Corte", "Prensa", "Ensamble", "Prueba", "Corrosión"],
        "cycle_time": [48, 52, 52, 53, 46],
        "changeover_time": [120, 90, 150, 60, 180],
        "wip": [30, 25, 40, 20, 35],
        "uptime": [95, 98, 92, 99, 96],
        "process_order": [1, 2, 3, 4, 5]
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name="VSM_Data")
    return output.getvalue()

def import_excel_file(uploaded_file):
    """Lee un archivo Excel, valida columnas y devuelve DataFrame limpio."""
    try:
        df = pd.read_excel(uploaded_file)
        required_cols = ["name", "cycle_time", "changeover_time", "wip", "uptime", "process_order"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"El archivo debe contener las columnas: {', '.join(required_cols)}")
            return None
        # Validar tipos
        df["cycle_time"] = pd.to_numeric(df["cycle_time"], errors="coerce")
        df["changeover_time"] = pd.to_numeric(df["changeover_time"], errors="coerce")
        df["wip"] = pd.to_numeric(df["wip"], errors="coerce").astype(int)
        df["uptime"] = pd.to_numeric(df["uptime"], errors="coerce")
        df["process_order"] = pd.to_numeric(df["process_order"], errors="coerce").astype(int)
        # Eliminar filas con valores inválidos
        df = df.dropna(subset=required_cols)
        if df.empty:
            st.error("No hay datos válidos en el archivo.")
            return None
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

# ------------------------------------------------------------
# Gráficos de KPIs (Lead Time vs PCE, VA/NVA, inventario)
# ------------------------------------------------------------
def render_kpi_dashboard(metrics: dict, df: pd.DataFrame):
    col1, col2, col3, col4 = st.columns(4)
    takt_val = metrics["takt"]
    col1.metric("Takt Time", f"{takt_val:.1f} s" if takt_val > 0 else "N/A", help="Segundos por unidad requerida")
    col2.metric("Lead Time Total", f"{metrics['total_lead_time']:.1f} s", help="VA + Esperas por WIP")
    col3.metric("PCE (Process Cycle Efficiency)", f"{metrics['pce']:.1f} %", help="VA / Lead Time")
    col4.metric("Cuello de Botella", metrics["bottleneck"] if metrics["bottleneck"] else "N/A")

    # Gauge de PCE
    fig_lead = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=metrics['pce'],
        title={"text": "Eficiencia del Proceso (PCE)", "font": {"color": "white"}},
        delta={'reference': 40, 'increasing': {'color': "#FFC107"}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': "white"},
            'bar': {'color': "#D32F2F"},
            'steps': [
                {'range': [0, 30], 'color': "#4A1A1A"},
                {'range': [30, 70], 'color': "#2D2D2D"},
                {'range': [70, 100], 'color': "#1E5631"}
            ],
            'threshold': {'line': {'color': "#FFC107", 'width': 4}, 'thickness': 0.75, 'value': 70}
        }
    ))
    fig_lead.update_layout(paper_bgcolor="#0E1117", font=dict(color="white"))
    st.plotly_chart(fig_lead, use_container_width=True)

    # Barras apiladas VA vs NVA
    if metrics["process_metrics"]:
        va_nva_df = pd.DataFrame([
            {"Proceso": p["name"], "Tipo": "Valor Agregado (VA)", "Segundos": p["va"]}
            for p in metrics["process_metrics"]
        ] + [
            {"Proceso": p["name"], "Tipo": "Espera por WIP (NVA)", "Segundos": p["nva"]}
            for p in metrics["process_metrics"]
        ])
        fig_bar = px.bar(va_nva_df, x="Proceso", y="Segundos", color="Tipo",
                         barmode="stack",
                         color_discrete_map={"Valor Agregado (VA)": "#FFC107", "Espera por WIP (NVA)": "#D32F2F"},
                         title="Comparación VA / NVA por estación")
        fig_bar.update_layout(plot_bgcolor="#1A1C24", paper_bgcolor="#0E1117", font=dict(color="white"))
        st.plotly_chart(fig_bar, use_container_width=True)

    # Área de inventario
    if not df.empty:
        wip_chart = alt.Chart(df).mark_area(opacity=0.6, color="#FFC107").encode(
            x=alt.X("name:N", title="Proceso", sort=None),
            y=alt.Y("wip:Q", title="Inventario WIP (unidades)"),
            tooltip=["name", "wip"]
        ).properties(title="Comportamiento de Inventario por Etapa", height=350)
        st.altair_chart(wip_chart, use_container_width=True)

# ------------------------------------------------------------
# Modo simulación: gestión de estado futuro
# ------------------------------------------------------------
def init_simulation_state(real_df: pd.DataFrame):
    if "sim_df" not in st.session_state:
        st.session_state.sim_df = real_df.copy()
    if "sim_mode_active" not in st.session_state:
        st.session_state.sim_mode_active = False

def run_simulation_toggle():
    st.session_state.sim_mode_active = st.toggle("🔮 Modo Simulación (Estado Futuro)", value=st.session_state.sim_mode_active)
    if st.session_state.sim_mode_active:
        if st.session_state.sim_df is None or st.session_state.sim_df.empty:
            st.session_state.sim_df = load_processes().copy()
        st.info("⚙️ Modo simulación activo. Los cambios **no afectan** la base real. Ajusta los valores abajo.")
    else:
        st.success("✅ Modo real activo. Los cambios se guardarán en la base de datos.")

def show_editor_and_actions():
    real_df = load_processes()
    init_simulation_state(real_df)

    # ---- Botones de importación/exportación en sidebar ----
    st.sidebar.markdown("### 📂 Importar / Exportar Datos")
    template_bytes = generate_excel_template()
    st.sidebar.download_button(
        label="📥 Descargar plantilla Excel",
        data=template_bytes,
        file_name="plantilla_vsm.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Descarga una plantilla con la estructura correcta y datos de ejemplo."
    )
    uploaded_file = st.sidebar.file_uploader("📂 Subir archivo Excel", type=["xlsx", "xls"])
    if uploaded_file is not None:
        df_imported = import_excel_file(uploaded_file)
        if df_imported is not None:
            st.sidebar.success(f"✅ {len(df_imported)} procesos cargados. ¿Reemplazar datos actuales?")
            if st.sidebar.button("🔄 Sí, reemplazar todos los datos"):
                with st.spinner("Reemplazando datos en Supabase..."):
                    replace_all_processes(df_imported)
                st.sidebar.success("Datos importados correctamente. Recargando...")
                st.rerun()
    st.sidebar.divider()

    run_simulation_toggle()

    if st.session_state.sim_mode_active:
        st.markdown("<span class='simulation-badge'>SIMULANDO ESTADO FUTURO</span>", unsafe_allow_html=True)
        edited_df = st.data_editor(
            st.session_state.sim_df,
            num_rows="dynamic",
            use_container_width=True,
            key="sim_editor",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "name": "Proceso",
                "cycle_time": st.column_config.NumberColumn("C/T (s)", min_value=0.1, step=1.0),
                "changeover_time": st.column_config.NumberColumn("C/O (s)", min_value=0, step=10),
                "wip": st.column_config.NumberColumn("WIP", min_value=0, step=1),
                "uptime": st.column_config.NumberColumn("Uptime (%)", min_value=0, max_value=100, step=1),
                "process_order": st.column_config.NumberColumn("Orden", step=1)
            }
        )
        if not edited_df.equals(st.session_state.sim_df):
            st.session_state.sim_df = edited_df
            st.rerun()
        df_to_use = st.session_state.sim_df
        if st.button("↺ Reiniciar simulación desde datos reales"):
            st.session_state.sim_df = load_processes().copy()
            st.rerun()
    else:
        edited_real = st.data_editor(
            real_df,
            num_rows="dynamic",
            use_container_width=True,
            key="real_editor",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "name": "Proceso",
                "cycle_time": st.column_config.NumberColumn("C/T (s)", min_value=0.1, step=1.0),
                "changeover_time": st.column_config.NumberColumn("C/O (s)", min_value=0, step=10),
                "wip": st.column_config.NumberColumn("WIP", min_value=0, step=1),
                "uptime": st.column_config.NumberColumn("Uptime (%)", min_value=0, max_value=100, step=1),
                "process_order": st.column_config.NumberColumn("Orden", step=1)
            }
        )
        col_save, col_add, _ = st.columns([1, 1, 3])
        with col_save:
            if st.button("💾 Guardar cambios en base real"):
                save_processes(edited_real)
                st.success("Datos actualizados en Supabase")
                st.rerun()
        with col_add:
            if st.button("➕ Agregar nuevo proceso"):
                add_process_default()
                st.rerun()
        df_to_use = edited_real

    return df_to_use

# ------------------------------------------------------------
# Sidebar: parámetros operativos
# ------------------------------------------------------------
with st.sidebar:
    st.image("EA_2.png", width=200)
    st.markdown("## ⚙️ Parámetros de Línea")
    available_hours = st.number_input("Horas disponibles por turno", min_value=1.0, value=8.0, step=0.5)
    available_sec = available_hours * 3600
    daily_demand = st.number_input("Demanda diaria (unidades)", min_value=1, value=600, step=50)
    st.divider()
    st.caption("Digital VSM - EA Innovation & Solutions")
    st.caption("Lean Manufacturing Intelligence")

# ------------------------------------------------------------
# Main Layout
# ------------------------------------------------------------
st.title("🏭 Digital Value Stream Mapping")
st.subheader("Operational Intelligence - EA Innovation & Solutions")

current_df = show_editor_and_actions()

if not current_df.empty:
    current_df = current_df.sort_values("process_order").reset_index(drop=True)
    metrics = compute_metrics(current_df, available_sec, daily_demand)

    # Marcar el bottleneck en el dataframe para que el VSM lo resalte
    if metrics["bottleneck"]:
        current_df["is_bottleneck"] = current_df["name"] == metrics["bottleneck"]
    else:
        current_df["is_bottleneck"] = False

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.markdown("### 📊 Diagrama VSM")
        render_vsm(current_df, metrics["takt"])

    with col_right:
        st.markdown("### 🔍 Indicadores Clave")
        violating = [p for p in metrics["process_metrics"] if p["ct_violation"]]
        if violating:
            st.warning(f"⚠️ {len(violating)} proceso(s) con C/T > Takt: {', '.join([v['name'] for v in violating])}")
        else:
            st.success("✅ Todos los C/T respetan el Takt Time")
        st.metric("Lead Time Total", f"{metrics['total_lead_time']:.1f} s  ({metrics['total_lead_time']/60:.1f} min)")
        st.metric("Takt Time objetivo", f"{metrics['takt']:.1f} s")
        if metrics["bottleneck"]:
            st.info(f"🔥 Cuello de botella: **{metrics['bottleneck']}**")

    st.divider()
    render_kpi_dashboard(metrics, current_df)

    # NUEVA SECCIÓN: Timeline comparativa
    st.markdown("### 📅 Timeline: Current vs. Target State")
    # Si estamos en modo simulación, usamos sim_df; si no, ambos iguales
    if st.session_state.get("sim_mode_active", False) and st.session_state.get("sim_df") is not None:
        sim_df_for_timeline = st.session_state.sim_df.sort_values("process_order").reset_index(drop=True)
    else:
        sim_df_for_timeline = current_df
    render_timeline_comparison(current_df, sim_df_for_timeline, metrics["takt"])

else:
    st.warning("No hay procesos cargados. Agrega algunos usando el editor, la plantilla Excel o inserta datos en Supabase.")

st.divider()

# ------------------------------------------------------------
# FOOTER PROFESIONAL
# ------------------------------------------------------------
st.markdown("""
<style>
.footer {
    background-color: #1A1C24;
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1rem;
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
</style>

<div class="footer">
    <div class="quote">
        “La exactitud es nuestra firma e innovar es nuestra naturaleza”
    </div>
    <div class="info">
        <div>
            <strong><span class="badge">📊</span> EA Simplex Production Optimizer v2.0</strong><br>
            Digital Value Stream Mapping<br>
            Lean Manufacturing Intelligence
        </div>
        <div>
            <strong><span class="badge">👨‍🔧</span> Ing. Maestro Erik Armenta</strong><br>
            Operational Excellence & Industry 4.0
        </div>
        <div>
            <strong><span class="badge">📍</span> EA Innovation & Solutions</strong><br>
            Cd. Juárez, MX
        </div>
        <div>
            <strong><span class="badge">⚙️</span> Tecnologías</strong><br>
            Streamlit · Supabase · Plotly · Altair
        </div>
        <div>
            <strong><span class="badge">🔬</span> Funcionalidades</strong><br>
            CRUD · Simulación What-If · VSM Dinámico<br>
            Cálculo Takt / Lead Time / PCE · Import/Export Excel
        </div>
        <div>
            <strong><span class="badge">💾</span> Persistencia</strong><br>
            Supabase PostgreSQL · Escenarios What-If<br>
            Comparador de escenarios
        </div>
    </div>
    <hr>
    <div style="text-align: center; font-size: 0.75rem; opacity: 0.7;">
        © EA Innovation & Solutions — Lean Digital VSM | Data persistente con Supabase
    </div>
</div>
""", unsafe_allow_html=True)