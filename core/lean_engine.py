"""
core/lean_engine.py
Motor de cálculo Lean — métricas VSM cacheadas y gestión de estado de simulación.
"""

import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# Cálculo de métricas Lean (cacheado por hash del DataFrame)
# ------------------------------------------------------------
@st.cache_data
def compute_metrics(df: pd.DataFrame, available_sec: float, demand: float) -> dict:
    """
    Calcula todas las métricas Lean a partir del DataFrame de procesos.

    Parámetros:
        df            : DataFrame con columnas cycle_time, changeover_time, wip, uptime, name.
        available_sec : Segundos disponibles por turno (horas * 3600).
        demand        : Demanda diaria en unidades.

    Retorna dict con:
        takt           : Takt Time en segundos.
        total_va       : Tiempo de valor agregado total (suma C/T).
        total_lead_time: Lead Time total (VA + espera NVA).
        pce            : Process Cycle Efficiency en % (VA / LT * 100).
        process_metrics: Lista de dicts por proceso con ct, co, wip, nva, va, uptime, ct_violation.
        has_violation  : True si algún proceso supera el Takt Time.
        bottleneck     : Nombre del proceso con mayor C/T relativo al Takt.
    """
    if df.empty:
        return {
            "takt": 0,
            "total_va": 0,
            "total_lead_time": 0,
            "pce": 0,
            "process_metrics": [],
            "has_violation": False,
            "bottleneck": None,
        }

    takt = available_sec / demand if demand > 0 else 0
    df = df.copy()

    total_va = df["cycle_time"].sum()
    df["nva_waiting"] = df["wip"] * takt
    total_lead_time = total_va + df["nva_waiting"].sum()
    pce = (total_va / total_lead_time * 100) if total_lead_time > 0 else 0
    has_violation = bool(any(df["cycle_time"] > takt)) if takt > 0 else False

    # Cuello de botella: proceso con mayor ratio C/T / Takt
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
            "ct": float(row["cycle_time"]),
            "co": float(row["changeover_time"]),
            "wip": int(row["wip"]),
            "nva": float(row.get("nva_waiting", 0)),
            "va": float(row["cycle_time"]),
            "uptime": float(row["uptime"]),
            "ct_violation": bool(row["cycle_time"] > takt) if takt > 0 else False,
            "is_bottleneck": row["name"] == bottleneck,
        })

    return {
        "takt": takt,
        "total_va": total_va,
        "total_lead_time": total_lead_time,
        "pce": pce,
        "process_metrics": process_metrics,
        "has_violation": has_violation,
        "bottleneck": bottleneck,
    }


# ------------------------------------------------------------
# Gestión de estado de simulación (session_state)
# ------------------------------------------------------------
def init_simulation_state(real_df: pd.DataFrame):
    """
    Inicializa las claves de session_state necesarias para el modo simulación.
    Solo escribe si las claves aún no existen (idempotente).
    """
    if "sim_df" not in st.session_state:
        st.session_state.sim_df = real_df.copy()
    if "sim_mode_active" not in st.session_state:
        st.session_state.sim_mode_active = False


def get_active_df(real_df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna el DataFrame activo según el modo actual:
    - Modo simulación: st.session_state.sim_df
    - Modo real: real_df
    """
    if st.session_state.get("sim_mode_active", False):
        return st.session_state.sim_df if st.session_state.sim_df is not None else real_df
    return real_df


def reset_simulation(real_df: pd.DataFrame):
    """Resetea el DataFrame de simulación a los datos reales actuales."""
    st.session_state.sim_df = real_df.copy()


def toggle_simulation(active: bool):
    """Activa o desactiva el modo simulación."""
    st.session_state.sim_mode_active = active
