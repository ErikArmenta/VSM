# =============================================================================
# components/sidebar.py — Sidebar: logo EA, parámetros, import/export, toggle simulación
# Proyecto: Digital VSM & Operational Intelligence - EA Innovation & Solutions
# =============================================================================

import streamlit as st
import pandas as pd

from database.supabase_client import (
    load_processes,
    save_processes,
    add_process_default,
    replace_all_processes,
    is_connected,
)
from core.excel_handler import (
    generate_excel_template,
    import_excel_file,
    show_import_preview,
)


# -----------------------------------------------------------------------------
# HELPERS DE ESTADO DE SIMULACIÓN
# (extraídos del VSM.py original, líneas 503-507)
# -----------------------------------------------------------------------------
def _init_simulation_state(real_df: pd.DataFrame) -> None:
    """Inicializa session_state para simulación si aún no existe."""
    if "sim_df" not in st.session_state:
        st.session_state.sim_df = real_df.copy()
    if "sim_mode_active" not in st.session_state:
        st.session_state.sim_mode_active = False


# -----------------------------------------------------------------------------
# SECCIÓN: Import / Export Excel
# -----------------------------------------------------------------------------
def _render_import_export(real_df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Renderiza la sección de importación/exportación Excel dentro del sidebar.
    Retorna el DataFrame importado y confirmado, o None si no hubo importación.
    """
    st.markdown("### 📂 Importar / Exportar Datos")

    # ── Descarga de plantilla ──────────────────────────────────────────────
    template_bytes = generate_excel_template()
    st.download_button(
        label="📥 Descargar plantilla Excel",
        data=template_bytes,
        file_name="plantilla_vsm.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Descarga la plantilla con estructura correcta y datos de ejemplo.",
        use_container_width=True,
    )

    # ── Subida de archivo ─────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "📂 Subir archivo Excel",
        type=["xlsx", "xls"],
        help="Sube un archivo con la misma estructura que la plantilla.",
    )

    if uploaded_file is not None:
        df_imported, errors = import_excel_file(uploaded_file)

        if errors:
            for err in errors:
                st.error(err)
            return None

        if df_imported is not None and not df_imported.empty:
            # ── Preview antes de confirmar ─────────────────────────────────
            st.markdown("**Vista previa de datos importados:**")
            show_import_preview(df_imported)

            if st.button(
                "🔄 Confirmar importación",
                help="Reemplaza todos los datos actuales con el archivo subido.",
                use_container_width=True,
                type="primary",
            ):
                with st.spinner("Importando datos..."):
                    replace_all_processes(df_imported)
                st.success(f"✅ {len(df_imported)} procesos importados correctamente.")
                st.rerun()

    return None


# -----------------------------------------------------------------------------
# SECCIÓN: Toggle simulación Estado Actual / Estado Futuro
# (lógica del VSM.py original, líneas 509-516)
# -----------------------------------------------------------------------------
def _render_simulation_toggle() -> None:
    """Renderiza el toggle de modo simulación con badge y mensaje de estado."""
    st.session_state.sim_mode_active = st.toggle(
        "🔮 Modo Simulación (Estado Futuro)",
        value=st.session_state.get("sim_mode_active", False),
    )
    if st.session_state.sim_mode_active:
        # Asegurar que sim_df tiene datos si se activó el toggle
        if (
            st.session_state.get("sim_df") is None
            or st.session_state.sim_df.empty
        ):
            st.session_state.sim_df = load_processes().copy()
        st.info(
            "⚙️ Modo simulación activo. Los cambios **no afectan** la base real.",
            icon="🔮",
        )
    else:
        st.success("✅ Modo real activo.", icon="✅")


# -----------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL: render_sidebar()
# -----------------------------------------------------------------------------
def render_sidebar() -> tuple[float, int, pd.DataFrame, bool]:
    """
    Renderiza el sidebar completo con:
    - Logo EA
    - Parámetros operativos (horas disponibles, demanda diaria)
    - Sección Import/Export Excel
    - Toggle simulación Estado Actual / Estado Futuro
    - Editor de datos (real o simulación)
    - Footer de branding

    Returns:
        tuple: (available_sec, daily_demand, df_to_use, sim_mode_active)
            - available_sec (float): segundos disponibles por turno
            - daily_demand (int): unidades de demanda diaria
            - df_to_use (pd.DataFrame): DataFrame activo (real o simulación)
            - sim_mode_active (bool): True si el modo simulación está activo
    """
    real_df = load_processes()
    _init_simulation_state(real_df)

    with st.sidebar:
        # ── Logo EA ────────────────────────────────────────────────────────
        st.image("assets/EA_2.png", width=200)

        # ── Parámetros de línea ────────────────────────────────────────────
        st.markdown("## ⚙️ Parámetros de Línea")

        available_hours = st.number_input(
            "Horas disponibles por turno",
            min_value=1.0,
            max_value=24.0,
            value=8.0,
            step=0.5,
            help="Tiempo total disponible para producción (en horas).",
        )
        available_sec = available_hours * 3600.0

        daily_demand = st.number_input(
            "Demanda diaria (unidades)",
            min_value=1,
            value=600,
            step=50,
            help="Cantidad de unidades requeridas por día.",
        )

        st.divider()

        # ── Import / Export ────────────────────────────────────────────────
        _render_import_export(real_df)

        st.divider()

        # ── Toggle de simulación ───────────────────────────────────────────
        _render_simulation_toggle()

        # ── Badge de modo simulación (visible en el sidebar) ───────────────
        if st.session_state.sim_mode_active:
            st.markdown(
                "<span class='simulation-badge'>SIMULANDO ESTADO FUTURO</span>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Editor de datos (real o simulación) ───────────────────────────
        # (lógica del VSM.py original, líneas 546-598)
        _COLUMN_CONFIG = {
            "id":              st.column_config.NumberColumn("ID", disabled=True),
            "name":            "Proceso",
            "cycle_time":      st.column_config.NumberColumn("C/T (s)",    min_value=0.1, step=1.0),
            "changeover_time": st.column_config.NumberColumn("C/O (s)",    min_value=0,   step=10),
            "wip":             st.column_config.NumberColumn("WIP",        min_value=0,   step=1),
            "uptime":          st.column_config.NumberColumn("Uptime (%)", min_value=0,   max_value=100, step=1),
            "process_order":   st.column_config.NumberColumn("Orden",      step=1),
        }

        if st.session_state.sim_mode_active:
            # ── Modo simulación: editar sim_df ─────────────────────────────
            edited_df = st.data_editor(
                st.session_state.sim_df,
                num_rows="dynamic",
                use_container_width=True,
                key="sim_editor",
                column_config=_COLUMN_CONFIG,
            )
            if not edited_df.equals(st.session_state.sim_df):
                st.session_state.sim_df = edited_df
                st.rerun()
            df_to_use = st.session_state.sim_df

            if st.button(
                "↺ Reiniciar simulación desde datos reales",
                use_container_width=True,
            ):
                st.session_state.sim_df = load_processes().copy()
                st.rerun()

        else:
            # ── Modo real: editar real_df y guardar en Supabase ────────────
            edited_real = st.data_editor(
                real_df,
                num_rows="dynamic",
                use_container_width=True,
                key="real_editor",
                column_config=_COLUMN_CONFIG,
            )
            col_save, col_add = st.columns(2)
            with col_save:
                if st.button("💾 Guardar", use_container_width=True):
                    save_processes(edited_real)
                    st.success("Datos actualizados.")
                    st.rerun()
            with col_add:
                if st.button("➕ Agregar", use_container_width=True):
                    add_process_default()
                    st.rerun()
            df_to_use = edited_real

        st.divider()

        # ── Estado de conexión ────────────────────────────────────────────
        if is_connected():
            st.caption("🟢 Supabase conectado")
        else:
            st.caption("🟡 Modo offline (datos de ejemplo)")

        # ── Footer ────────────────────────────────────────────────────────
        st.caption("Digital VSM - EA Innovation & Solutions")
        st.caption("Lean Manufacturing Intelligence")

    return available_sec, int(daily_demand), df_to_use, st.session_state.sim_mode_active
