"""
components/vsm_diagram.py
Diagrama VSM interactivo renderizado con SVG/JavaScript puro embebido
via st.components.v1.html().

Flujo: ENTRY (fábrica) → △WIP → [Proceso] → △WIP → ... → CUSTOMER (camión)

Características:
- Cajas de proceso con borde dorado exterior y borde rojo interior
- Fondo rojo oscuro (#5C1A1A) si C/T viola el Takt Time
- Triángulos de inventario rojos con borde dorado y número WIP
- Flechas doradas de flujo
- Línea de Takt Time punteada superior con label
- Etiquetas Lean en la parte inferior
- Hover con tooltip dark completo (C/T, C/O, WIP, Uptime, Lead Time acum., bottleneck)
- Scroll horizontal automático si hay muchos procesos
"""

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ---------------------------------------------------------------------------
# Función pública principal
# ---------------------------------------------------------------------------

def render_vsm_diagram(df: pd.DataFrame, metrics: dict) -> None:
    """
    Renderiza el diagrama VSM completo con SVG/JS embebido en un iframe.

    Parámetros:
        df      : DataFrame de procesos (puede estar vacío si no hay datos).
        metrics : Dict retornado por core.lean_engine.compute_metrics().
                  Claves usadas: 'process_metrics', 'takt'.
    """
    process_list: list = metrics.get("process_metrics", [])
    takt: float = float(metrics.get("takt", 0))

    # Enriquecer cada proceso con el lead time acumulado hasta ese punto
    cumulative = 0.0
    enriched = []
    for pm in process_list:
        cumulative += pm["ct"] + pm.get("nva", 0)
        enriched.append({**pm, "cumulative_lt": round(cumulative, 1)})

    data_json = json.dumps({
        "processes": enriched,
        "takt": round(takt, 1) if takt > 0 else 0,
    })

    html = _build_vsm_html(data_json)
    components.html(html, height=520, scrolling=False)


# ---------------------------------------------------------------------------
# Constructor del HTML/JS
# ---------------------------------------------------------------------------

def _build_vsm_html(data_json: str) -> str:
    """
    Retorna el HTML completo con SVG y JavaScript embebidos.
    data_json se inyecta directamente como literal JS en el template.
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: #0E1117;
    font-family: 'Segoe UI', Arial, sans-serif;
    overflow: hidden;
  }}

  #vsm-wrapper {{
    width: 100%;
    height: 520px;
    overflow-x: auto;
    overflow-y: hidden;
    background: #0E1117;
    scrollbar-width: thin;
    scrollbar-color: #FFC107 #1A1C24;
  }}

  #vsm-wrapper::-webkit-scrollbar {{
    height: 6px;
  }}
  #vsm-wrapper::-webkit-scrollbar-track {{
    background: #1A1C24;
  }}
  #vsm-wrapper::-webkit-scrollbar-thumb {{
    background: #FFC107;
    border-radius: 3px;
  }}

  #vsm-svg {{
    display: block;
  }}

  /* ── Tooltip ─────────────────────────────────────────────────────── */
  #vsm-tooltip {{
    position: fixed;
    display: none;
    background: #1A1C24;
    border: 1.5px solid #FFC107;
    border-radius: 8px;
    padding: 12px 16px;
    color: #FFFFFF;
    font-size: 12px;
    font-family: 'Segoe UI', Arial, sans-serif;
    z-index: 9999;
    pointer-events: none;
    min-width: 210px;
    max-width: 270px;
    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.75);
    line-height: 1.8;
  }}

  .tt-title {{
    color: #FFC107;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #2D2D3A;
    letter-spacing: 0.4px;
  }}

  .tt-row {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }}

  .tt-label {{
    color: #AAAAAA;
    font-size: 11px;
  }}

  .tt-value {{
    color: #FFFFFF;
    font-weight: 600;
    font-size: 11px;
    text-align: right;
  }}

  .tt-bottleneck {{
    margin-top: 7px;
    padding: 4px 8px;
    background: rgba(255, 107, 53, 0.18);
    color: #FF6B35;
    font-weight: 700;
    font-size: 11px;
    border-radius: 4px;
    border-left: 3px solid #FF6B35;
  }}

  .tt-violation {{
    margin-top: 5px;
    padding: 4px 8px;
    background: rgba(211, 47, 47, 0.2);
    color: #FF5252;
    font-weight: 700;
    font-size: 11px;
    border-radius: 4px;
    border-left: 3px solid #D32F2F;
  }}
</style>
</head>
<body>

<div id="vsm-wrapper">
  <svg id="vsm-svg" xmlns="http://www.w3.org/2000/svg"></svg>
</div>
<div id="vsm-tooltip"></div>

<script>
(function () {{
  'use strict';

  /* ═══════════════════════════════════════════════════════════════════
     DATOS INYECTADOS DESDE PYTHON
  ═══════════════════════════════════════════════════════════════════ */
  const DATA      = {data_json};
  const processes = DATA.processes || [];
  const takt      = DATA.takt || 0;
  const n         = processes.length;

  /* ═══════════════════════════════════════════════════════════════════
     CONSTANTES DE LAYOUT
  ═══════════════════════════════════════════════════════════════════ */
  const PAD      = 28;          // padding horizontal exterior

  const ENTRY_W  = 84;          // nodo Entry (fábrica)
  const ENTRY_H  = 98;

  const BOX_W    = 134;         // caja de proceso
  const BOX_H    = 114;

  const CUST_W   = 84;          // nodo Customer (camión)
  const CUST_H   = 98;

  const TRI_W    = 50;          // triángulo de inventario
  const TRI_H    = 38;

  const ARROW    = 40;          // longitud de flecha entre nodos
  const GAP      = 6;           // espacio entre triángulo y caja de proceso

  // Avance horizontal por cada proceso: TRI + GAP + BOX + ARROW_NEXT
  const SEGMENT  = TRI_W + GAP + BOX_W + ARROW;  // = 230px

  // Alturas verticales
  const SVG_H    = 418;
  const FLOW_Y   = 178;         // centro vertical del flujo principal
  const TAKT_Y   = 44;          // y de la línea Takt punteada
  const LEAN_Y   = 378;         // y de las etiquetas Lean inferiores

  /* ═══════════════════════════════════════════════════════════════════
     DIMENSIONES DEL SVG
  ═══════════════════════════════════════════════════════════════════ */
  const rawW = n > 0
    ? PAD + ENTRY_W + ARROW + n * SEGMENT + CUST_W + PAD
    : PAD + ENTRY_W + ARROW + CUST_W + PAD;
  const svgW = Math.max(rawW, 860);

  const svg = document.getElementById('vsm-svg');
  svg.setAttribute('width',  svgW);
  svg.setAttribute('height', SVG_H);

  /* ═══════════════════════════════════════════════════════════════════
     FUNCIONES HELPERS
  ═══════════════════════════════════════════════════════════════════ */
  const NS = 'http://www.w3.org/2000/svg';

  /** Crea y añade un elemento SVG con atributos dados */
  function el(tag, attrs, parent) {{
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {{}}))
      e.setAttribute(k, String(v));
    if (parent) parent.appendChild(e);
    return e;
  }}

  /** Crea un elemento <text> SVG */
  function txt(content, attrs, parent) {{
    const e = el('text', attrs, parent);
    e.textContent = String(content);
    return e;
  }}

  /* ═══════════════════════════════════════════════════════════════════
     DEFS — marcador de punta de flecha
  ═══════════════════════════════════════════════════════════════════ */
  const defs = el('defs', {{}}, svg);
  const mkr = el('marker', {{
    id: 'arr',
    markerWidth: 9, markerHeight: 7,
    refX: 8, refY: 3.5,
    orient: 'auto'
  }}, defs);
  el('polygon', {{ points: '0 0, 9 3.5, 0 7', fill: '#FFC107' }}, mkr);

  /* ═══════════════════════════════════════════════════════════════════
     FONDO
  ═══════════════════════════════════════════════════════════════════ */
  el('rect', {{ x: 0, y: 0, width: svgW, height: SVG_H, fill: '#0E1117' }}, svg);

  /* ═══════════════════════════════════════════════════════════════════
     POSICIONES X
  ═══════════════════════════════════════════════════════════════════ */
  const xEntryR = PAD + ENTRY_W;  // borde derecho de Entry

  function xTri(i)  {{ return xEntryR + ARROW + i * SEGMENT; }}
  function xBox(i)  {{ return xTri(i) + TRI_W + GAP; }}
  function xCust()  {{ return xEntryR + ARROW + n * SEGMENT; }}

  /* ═══════════════════════════════════════════════════════════════════
     LÍNEA TAKT TIME PUNTEADA (parte superior)
  ═══════════════════════════════════════════════════════════════════ */
  if (takt > 0 && n > 0) {{
    const lx1 = xEntryR + 6;
    const lx2 = xCust() - 6;

    el('line', {{
      x1: lx1, y1: TAKT_Y, x2: lx2, y2: TAKT_Y,
      stroke: '#FFC107', 'stroke-width': 1.5,
      'stroke-dasharray': '9,5',
      opacity: 0.9
    }}, svg);

    // Badge de label
    const lblW = 126;
    el('rect', {{
      x: lx1 + 4, y: TAKT_Y - 20,
      width: lblW, height: 19,
      fill: '#1A1C24',
      stroke: '#FFC107', 'stroke-width': 0.8,
      rx: 4, opacity: 0.92
    }}, svg);
    txt(`⏱ Takt Time: ${{takt}} s`, {{
      x: lx1 + 4 + lblW / 2, y: TAKT_Y - 7,
      fill: '#FFC107', 'font-size': '10.5px', 'font-weight': '700',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, svg);
  }}

  /* ═══════════════════════════════════════════════════════════════════
     NODO ENTRY (izquierda — icono de fábrica)
  ═══════════════════════════════════════════════════════════════════ */
  (function drawEntry() {{
    const x  = PAD;
    const y  = FLOW_Y - ENTRY_H / 2;
    const cx = x + ENTRY_W / 2;
    const g  = el('g', {{}}, svg);

    // Caja exterior
    el('rect', {{
      x, y, width: ENTRY_W, height: ENTRY_H,
      fill: '#1A1C24', stroke: '#FFC107', 'stroke-width': 2,
      rx: 5
    }}, g);

    // ── Icono fábrica ────────────────────────────────────────────────
    const iy = y + 10;   // posición vertical del icono

    // Base del edificio
    el('rect', {{ x: cx - 20, y: iy + 14, width: 40, height: 26, fill: '#FFC107', rx: 1 }}, g);

    // Techo triangular (frontón)
    el('polygon', {{
      points: `${{cx}},${{iy}} ${{cx - 24}},${{iy + 16}} ${{cx + 24}},${{iy + 16}}`,
      fill: '#FFA000'
    }}, g);

    // Chimenea
    el('rect', {{ x: cx + 8, y: iy - 10, width: 8, height: 18, fill: '#FFA000' }}, g);
    // Humo (círculos pequeños)
    el('circle', {{ cx: cx + 12, cy: iy - 14, r: 3, fill: '#2D2D3A', opacity: 0.7 }}, g);
    el('circle', {{ cx: cx + 14, cy: iy - 19, r: 2, fill: '#2D2D3A', opacity: 0.5 }}, g);

    // Puerta
    el('rect', {{ x: cx - 6, y: iy + 26, width: 12, height: 14, fill: '#1A1C24' }}, g);

    // Ventanas
    el('rect', {{ x: cx - 18, y: iy + 17, width: 9, height: 8, fill: '#1A1C24', rx: 1 }}, g);
    el('rect', {{ x: cx + 9,  y: iy + 17, width: 9, height: 8, fill: '#1A1C24', rx: 1 }}, g);

    // Etiquetas
    txt('ENTRY', {{
      x: cx, y: y + ENTRY_H - 22,
      fill: '#FFC107', 'font-size': '11px', 'font-weight': '700',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);
    txt('SUPPLIER', {{
      x: cx, y: y + ENTRY_H - 8,
      fill: '#CCCCCC', 'font-size': '9px',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);
  }})();

  /* ═══════════════════════════════════════════════════════════════════
     NODO CUSTOMER (derecha — icono de camión)
  ═══════════════════════════════════════════════════════════════════ */
  (function drawCustomer() {{
    const x  = xCust();
    const y  = FLOW_Y - CUST_H / 2;
    const cx = x + CUST_W / 2;
    const g  = el('g', {{}}, svg);

    // Caja exterior
    el('rect', {{
      x, y, width: CUST_W, height: CUST_H,
      fill: '#1A1C24', stroke: '#FFC107', 'stroke-width': 2,
      rx: 5
    }}, g);

    // ── Icono camión ─────────────────────────────────────────────────
    const ty = y + 14;

    // Remolque (caja de carga)
    el('rect', {{ x: cx - 30, y: ty + 2, width: 38, height: 22, fill: '#FFC107', rx: 2 }}, g);

    // Cabina
    el('rect', {{ x: cx + 8, y: ty, width: 24, height: 24, fill: '#FFA000', rx: 3 }}, g);

    // Parabrisas
    el('rect', {{ x: cx + 11, y: ty + 3, width: 16, height: 11, fill: '#1A1C24', rx: 2 }}, g);

    // Ruedas
    el('circle', {{ cx: cx - 14, cy: ty + 26, r: 8, fill: '#2D2D3A', stroke: '#FFC107', 'stroke-width': 1.5 }}, g);
    el('circle', {{ cx: cx - 14, cy: ty + 26, r: 3.5, fill: '#0E1117' }}, g);

    el('circle', {{ cx: cx + 18, cy: ty + 26, r: 8, fill: '#2D2D3A', stroke: '#FFC107', 'stroke-width': 1.5 }}, g);
    el('circle', {{ cx: cx + 18, cy: ty + 26, r: 3.5, fill: '#0E1117' }}, g);

    // Parrilla frontal
    el('rect', {{ x: cx + 8, y: ty + 18, width: 4, height: 6, fill: '#2D2D3A', rx: 1 }}, g);

    // Etiquetas
    txt('CUSTOMER', {{
      x: cx, y: y + CUST_H - 22,
      fill: '#FFC107', 'font-size': '10px', 'font-weight': '700',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);
    txt('DEMAND', {{
      x: cx, y: y + CUST_H - 8,
      fill: '#CCCCCC', 'font-size': '9px',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);
  }})();

  /* ═══════════════════════════════════════════════════════════════════
     HELPER — FLECHA PUSH
  ═══════════════════════════════════════════════════════════════════ */
  function drawArrow(x1, y1, x2, y2) {{
    el('line', {{
      x1, y1,
      x2: x2 - 2, y2,
      stroke: '#FFC107', 'stroke-width': 2,
      'marker-end': 'url(#arr)'
    }}, svg);
  }}

  /* ═══════════════════════════════════════════════════════════════════
     PRIMER CONECTOR: Entry → primer triángulo (o Customer si n=0)
  ═══════════════════════════════════════════════════════════════════ */
  if (n === 0) {{
    drawArrow(xEntryR, FLOW_Y, xCust(), FLOW_Y);

    // Mensaje de estado vacío
    el('rect', {{
      x: svgW / 2 - 230, y: FLOW_Y + 60,
      width: 460, height: 34,
      fill: '#1A1C24', stroke: '#2D2D3A', 'stroke-width': 1, rx: 6
    }}, svg);
    txt('Sin procesos cargados. Importa un Excel o agrega procesos en la base de datos.', {{
      x: svgW / 2, y: FLOW_Y + 82,
      fill: '#CCCCCC', 'font-size': '12px',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, svg);
  }} else {{
    drawArrow(xEntryR, FLOW_Y, xTri(0), FLOW_Y);
  }}

  /* ═══════════════════════════════════════════════════════════════════
     PROCESOS — triángulo + caja + flecha
  ═══════════════════════════════════════════════════════════════════ */
  processes.forEach(function (proc, i) {{

    /* ── Triángulo de inventario (WIP) ─────────────────────────────── */
    const tx   = xTri(i);
    const tcx  = tx + TRI_W / 2;
    const tapy = FLOW_Y - TRI_H / 2;  // vértice superior (ápice)
    const tby  = FLOW_Y + TRI_H / 2;  // base inferior

    const tg = el('g', {{}}, svg);

    el('polygon', {{
      points: `${{tcx}},${{tapy}} ${{tx}},${{tby}} ${{tx + TRI_W}},${{tby}}`,
      fill: '#D32F2F', stroke: '#FFC107', 'stroke-width': 1.5
    }}, tg);

    // Número de WIP dentro del triángulo
    txt(proc.wip, {{
      x: tcx, y: FLOW_Y + 5,
      fill: '#FFFFFF', 'font-size': '12px', 'font-weight': '700',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle', 'dominant-baseline': 'middle'
    }}, tg);

    // Etiqueta "WIP" sobre el triángulo
    txt('WIP', {{
      x: tcx, y: tapy - 7,
      fill: '#CCCCCC', 'font-size': '9px',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, tg);

    /* ── Conector corto triángulo → caja ───────────────────────────── */
    el('line', {{
      x1: tx + TRI_W, y1: FLOW_Y,
      x2: xBox(i), y2: FLOW_Y,
      stroke: '#FFC107', 'stroke-width': 1.5
    }}, svg);

    /* ── Caja de proceso ───────────────────────────────────────────── */
    const bx = xBox(i);
    const by = FLOW_Y - BOX_H / 2;

    // Colores según estado
    const isViol  = proc.ct_violation;
    const isBott  = proc.is_bottleneck;
    const bgFill  = isViol ? '#5C1A1A' : '#2A2A2A';
    const hdrFill = isBott ? '#7B3500' : '#B71C1C';
    const bdrClr  = isBott ? '#FF6B35' : '#FFC107';
    const bdrW    = isBott ? 3.2 : 2.5;

    const g = el('g', {{ 'data-idx': i, style: 'cursor: pointer;' }}, svg);

    // Fondo principal
    el('rect', {{
      x: bx, y: by, width: BOX_W, height: BOX_H,
      fill: bgFill, rx: 5
    }}, g);

    // Franja de cabecera (los 29px superiores)
    el('rect', {{
      x: bx, y: by, width: BOX_W, height: 29,
      fill: hdrFill, rx: 5
    }}, g);
    // Rectángulo extra para aplanar las esquinas inferiores del header
    el('rect', {{
      x: bx, y: by + 22, width: BOX_W, height: 7,
      fill: hdrFill
    }}, g);

    // Borde exterior (dorado o naranja si es bottleneck)
    el('rect', {{
      x: bx, y: by, width: BOX_W, height: BOX_H,
      fill: 'none', stroke: bdrClr, 'stroke-width': bdrW,
      rx: 5
    }}, g);

    // Borde interior (rojo)
    el('rect', {{
      x: bx + 4, y: by + 4,
      width: BOX_W - 8, height: BOX_H - 8,
      fill: 'none', stroke: '#D32F2F', 'stroke-width': 1,
      rx: 3
    }}, g);

    /* Nombre del proceso (en cabecera) */
    const maxChars = 13;
    const dispName = proc.name.length > maxChars
      ? proc.name.substring(0, maxChars - 1) + '…'
      : proc.name;

    // Centrar el nombre, dejando espacio para íconos laterales
    const hasLeft  = isBott;
    const hasRight = isViol;
    const offsetX  = (hasLeft ? 7 : 0) - (hasRight ? 7 : 0);

    txt(dispName, {{
      x: bx + BOX_W / 2 + offsetX,
      y: by + 18,
      fill: '#FFFFFF', 'font-size': '12.5px', 'font-weight': '700',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle', 'dominant-baseline': 'middle'
    }}, g);

    // Ícono ✕ (violación Takt)
    if (isViol) {{
      txt('✕', {{
        x: bx + BOX_W - 11, y: by + 18,
        fill: '#FF5252', 'font-size': '13px', 'font-weight': '900',
        'font-family': 'Segoe UI, Arial, sans-serif',
        'text-anchor': 'middle', 'dominant-baseline': 'middle'
      }}, g);
    }}

    // Ícono ▲ (cuello de botella)
    if (isBott) {{
      txt('▲', {{
        x: bx + 11, y: by + 18,
        fill: '#FF6B35', 'font-size': '11px',
        'font-family': 'Segoe UI, Arial, sans-serif',
        'text-anchor': 'middle', 'dominant-baseline': 'middle'
      }}, g);
    }}

    /* Métricas en el cuerpo de la caja */
    const my = by + 38;   // y de la primera línea de métricas
    const ml = 18;        // line-height entre métricas

    txt(`Takt: ${{takt}}s`, {{
      x: bx + BOX_W / 2, y: my,
      fill: '#FFC107', 'font-size': '11px', 'font-weight': '600',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);

    txt(`C/T: ${{proc.ct}}s`, {{
      x: bx + BOX_W / 2, y: my + ml,
      fill: '#FFFFFF', 'font-size': '11px',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);

    txt(`WIP: ${{proc.wip}}`, {{
      x: bx + BOX_W / 2, y: my + ml * 2,
      fill: '#FFFFFF', 'font-size': '11px',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);

    txt(`Up: ${{proc.uptime}}%`, {{
      x: bx + BOX_W / 2, y: my + ml * 3,
      fill: '#AAAAAA', 'font-size': '10px',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, g);

    /* ── Flecha hacia el siguiente segmento ────────────────────────── */
    const nextX = (i < n - 1) ? xTri(i + 1) : xCust();
    drawArrow(bx + BOX_W, FLOW_Y, nextX, FLOW_Y);

    /* ── Eventos hover para el tooltip ────────────────────────────── */
    g.addEventListener('mouseenter', function (e) {{ showTip(e, proc); }});
    g.addEventListener('mousemove',  function (e) {{ moveTip(e); }});
    g.addEventListener('mouseleave', function ()  {{ hideTip(); }});
  }});

  /* ═══════════════════════════════════════════════════════════════════
     ETIQUETAS LEAN (fila inferior)
  ═══════════════════════════════════════════════════════════════════ */
  const leanLabels = ['Flow', 'Results', 'Tiempo', 'Smooth', 'Tamaño'];
  const leanSpacing = svgW / (leanLabels.length + 1);

  // Línea divisoria
  el('line', {{
    x1: PAD, y1: LEAN_Y - 26,
    x2: svgW - PAD, y2: LEAN_Y - 26,
    stroke: '#2D2D3A', 'stroke-width': 1
  }}, svg);

  leanLabels.forEach(function (lbl, i) {{
    const lx = leanSpacing * (i + 1);

    el('rect', {{
      x: lx - 32, y: LEAN_Y - 18,
      width: 64, height: 22,
      fill: '#1A1C24', stroke: '#2D2D3A', 'stroke-width': 1,
      rx: 4
    }}, svg);

    txt(lbl, {{
      x: lx, y: LEAN_Y - 2,
      fill: '#FFC107', 'font-size': '11px', 'font-weight': '600',
      'font-family': 'Segoe UI, Arial, sans-serif',
      'text-anchor': 'middle'
    }}, svg);
  }});

  /* ═══════════════════════════════════════════════════════════════════
     TOOLTIP
  ═══════════════════════════════════════════════════════════════════ */
  const tooltip = document.getElementById('vsm-tooltip');

  function showTip(e, p) {{
    const bnHTML = p.is_bottleneck
      ? '<div class="tt-bottleneck">▲ CUELLO DE BOTELLA</div>'
      : '';
    const violHTML = p.ct_violation
      ? '<div class="tt-violation">✕ VIOLA TAKT TIME</div>'
      : '';

    tooltip.innerHTML = `
      <div class="tt-title">${{p.name}}</div>
      <div class="tt-row">
        <span class="tt-label">Cycle Time</span>
        <span class="tt-value">${{p.ct}} s</span>
      </div>
      <div class="tt-row">
        <span class="tt-label">Changeover (C/O)</span>
        <span class="tt-value">${{p.co}} s</span>
      </div>
      <div class="tt-row">
        <span class="tt-label">WIP</span>
        <span class="tt-value">${{p.wip}} uds</span>
      </div>
      <div class="tt-row">
        <span class="tt-label">Uptime</span>
        <span class="tt-value">${{p.uptime}} %</span>
      </div>
      <div class="tt-row">
        <span class="tt-label">Takt Time</span>
        <span class="tt-value">${{takt}} s</span>
      </div>
      <div class="tt-row">
        <span class="tt-label">Lead Time Acum.</span>
        <span class="tt-value">${{p.cumulative_lt}} s</span>
      </div>
      ${{bnHTML}}${{violHTML}}
    `;
    tooltip.style.display = 'block';
    moveTip(e);
  }}

  function moveTip(e) {{
    let x = e.clientX + 16;
    let y = e.clientY - 12;
    if (x + 280 > window.innerWidth)  x = e.clientX - 286;
    if (y + 260 > window.innerHeight) y = e.clientY - 265;
    tooltip.style.left = x + 'px';
    tooltip.style.top  = y + 'px';
  }}

  function hideTip() {{
    tooltip.style.display = 'none';
  }}

}})();
</script>
</body>
</html>"""
