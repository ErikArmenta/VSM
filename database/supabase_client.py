# =============================================================================
# database/supabase_client.py — Conexión Supabase con fallback data
# Proyecto: Digital VSM & Operational Intelligence - EA Innovation & Solutions
# =============================================================================

import streamlit as st
import pandas as pd
from supabase import create_client, Client

from config.settings import DEFAULT_PROCESSES, SUPABASE_TABLE


# -----------------------------------------------------------------------------
# Conexión — @st.cache_resource para reutilizar la misma instancia
# -----------------------------------------------------------------------------
@st.cache_resource
def init_connection() -> Client | None:
    """
    Intenta conectar a Supabase usando st.secrets.
    Retorna el cliente si tiene éxito, None si falla (sin secrets, sin red, etc.).
    """
    try:
        url = st.secrets["supabase"]["URL"]
        key = st.secrets["supabase"]["KEY"]
        client = create_client(url, key)
        return client
    except Exception:
        # Sin secrets configurados, entorno local sin Supabase — modo fallback
        return None


# -----------------------------------------------------------------------------
# Helpers internos
# -----------------------------------------------------------------------------
def _get_client() -> Client | None:
    """Devuelve el cliente Supabase ya cacheado."""
    return init_connection()


def is_connected() -> bool:
    """Retorna True si hay conexión activa a Supabase."""
    return _get_client() is not None


# -----------------------------------------------------------------------------
# Lectura de procesos — @st.cache_data con TTL de 5 minutos
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_processes() -> pd.DataFrame:
    """
    Carga procesos desde Supabase si hay conexión, de lo contrario
    retorna el DataFrame con los datos DEFAULT_PROCESSES de settings.py.

    Returns:
        pd.DataFrame con columnas: id, name, cycle_time, changeover_time,
        wip, uptime, process_order, va_ratio, operators, batch_size
    """
    supabase = _get_client()
    if supabase is None:
        # Modo offline / fallback
        return pd.DataFrame(DEFAULT_PROCESSES)

    try:
        response = (
            supabase
            .table(SUPABASE_TABLE)
            .select("*")
            .order("process_order")
            .execute()
        )
        if response.data:
            return pd.DataFrame(response.data)
        # Tabla vacía — usar fallback
        return pd.DataFrame(DEFAULT_PROCESSES)
    except Exception:
        return pd.DataFrame(DEFAULT_PROCESSES)


# -----------------------------------------------------------------------------
# Escritura — guardar / añadir / eliminar / reemplazar
# -----------------------------------------------------------------------------
def save_processes(df: pd.DataFrame) -> None:
    """
    Sincroniza el DataFrame con la tabla Supabase:
    - Elimina filas que ya no existen en el DataFrame
    - Actualiza filas existentes (con id)
    - Inserta filas nuevas (sin id o id NaN)

    Si no hay conexión, no hace nada (modo fallback).
    """
    supabase = _get_client()
    if supabase is None:
        return

    try:
        current = load_processes()
        new_ids: set[int] = set()
        if "id" in df.columns:
            new_ids = set(
                df[df["id"].notna()]["id"].astype(int)
            )

        # Eliminar procesos que desaparecieron del DataFrame
        for _, row in current.iterrows():
            if int(row["id"]) not in new_ids:
                supabase.table(SUPABASE_TABLE).delete().eq("id", row["id"]).execute()

        # Actualizar o insertar
        for _, row in df.iterrows():
            record = row.to_dict()
            has_id = "id" in record and pd.notna(record.get("id"))
            if has_id:
                supabase.table(SUPABASE_TABLE).update(record).eq("id", record["id"]).execute()
            else:
                record.pop("id", None)
                supabase.table(SUPABASE_TABLE).insert(record).execute()
    finally:
        st.cache_data.clear()


def add_process_default() -> None:
    """
    Inserta un proceso vacío con valores por defecto en Supabase y
    fuerza la recarga de caché.
    Si no hay conexión, no hace nada.
    """
    supabase = _get_client()
    if supabase is None:
        return

    try:
        current_df = load_processes()
        max_order = len(current_df) + 1
        new_row = {
            "name": "Nuevo Proceso",
            "cycle_time": 50.0,
            "changeover_time": 100.0,
            "wip": 10,
            "uptime": 95.0,
            "process_order": max_order,
            "va_ratio": 0.65,
            "operators": 1,
            "batch_size": 1,
        }
        supabase.table(SUPABASE_TABLE).insert(new_row).execute()
    finally:
        st.cache_data.clear()


def delete_process(process_id: int) -> None:
    """
    Elimina el proceso con el id dado de Supabase.
    Si no hay conexión, no hace nada.
    """
    supabase = _get_client()
    if supabase is None:
        return

    try:
        supabase.table(SUPABASE_TABLE).delete().eq("id", process_id).execute()
    finally:
        st.cache_data.clear()


def replace_all_processes(df: pd.DataFrame) -> None:
    """
    Reemplaza TODA la tabla con los datos del DataFrame recibido.
    Útil para importación masiva desde Excel.

    Si no hay conexión, no hace nada (los datos se mantienen en sesión).
    """
    supabase = _get_client()
    if supabase is None:
        return

    try:
        # Eliminar todos los registros existentes
        supabase.table(SUPABASE_TABLE).delete().neq("id", 0).execute()

        # Insertar registros nuevos sin llevar id
        for _, row in df.iterrows():
            record = row.to_dict()
            record.pop("id", None)
            supabase.table(SUPABASE_TABLE).insert(record).execute()
    finally:
        st.cache_data.clear()
