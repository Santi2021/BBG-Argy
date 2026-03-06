"""
CER — Bonos ajustados por CER
  Subtab 1: Tabla + curva TIR vs Duración
  Subtab 2: BREAKEVEN (placeholder)
"""
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_eco_bonos_by_index, fmt_price


# ═══════════════════════════════════════════════════════════════════════════════
#  PARSE
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_precio(val):
    try:
        return float(str(val).replace(".", "").replace(",", ".").strip())
    except:
        return None


def _parse_num(val):
    try:
        return float(str(val).replace(",", ".").strip())
    except:
        return None


def _parse_cer_df(df):
    if df is None or df.empty:
        return []

    if hasattr(df.columns, 'levels'):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip() for c in df.columns]

    # Siempre usamos posición — TABLE 8 tiene exactamente 7 columnas:
    # 0=Especie, 1=Último, 2=%Día, 3=%Mes, 4=%Año, 5=%TIR, 6=Dur.
    cols = list(df.columns)
    if len(cols) < 7:
        return []

    # Tickers CER conocidos para filtrar filas basura
    VALID_TICKERS = {
        "CUAP", "DICP", "DIP0", "PAP0", "PARP",
        "TX26", "TX28", "TX29", "TX30", "TX31",
        "TZX26", "TZX27", "TZX28", "TZX29", "TZX30",
    }

    result = []
    for _, row in df.iterrows():
        especie = str(row.iloc[0]).strip()
        # Filtrar headers repetidos, filas vacías y filas basura
        if not especie or especie.lower() in ("nan", "especie", ""):
            continue
        # Descartar filas que no son tickers válidos (ej: la fila concatenada)
        if len(especie) > 6:
            continue

        ultimo = _parse_precio(row.iloc[1])
        # Ecovalores devuelve porcentajes como enteros sin decimal (-1 = -0.1%, -11 = -1.1%)
        dia    = _parse_num(row.iloc[2])
        mes    = _parse_num(row.iloc[3])
        anio   = _parse_num(row.iloc[4])
        tir    = _parse_num(row.iloc[5])
        dur_raw = _parse_num(row.iloc[6])

        def _fix_pct(v):
            if v is None: return None
            # Si viene como entero grande (ej: -11 para -1.1%), dividir por 10
            # TIR viene correcta (88 = 8.8%) — también dividir por 10
            return round(v / 10, 1)

        dur = round(dur_raw / 10, 1) if dur_raw is not None else None

        result.append({
            "especie": especie,
            "ultimo":  ultimo,
            "dia":     _fix_pct(dia),
            "mes":     _fix_pct(mes),
            "anio":    _fix_pct(anio),
            "tir":     _fix_pct(tir),
            "dur":     dur,
        })

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _pct_html(val):
    if val is None:
        return '<span style="color:#555">—</span>'
    c = "#00ff41" if val > 0 else ("#ff3b3b" if val < 0 else "#555")
    s = "+" if val > 0 else ""
    return f'<span style="color:{c};font-weight:bold">{s}{val:.1f}%</span>'


def _tir_html(val):
    if val is None:
        return '<span style="color:#555">—</span>'
    return f'<span style="color:#ff6600;font-weight:bold">{val:.1f}%</span>'


def _dur_html(val):
    if val is None:
        return '<span style="color:#555">—</span>'
    return f'<span style="color:#555">{val:.1f}</span>'


# ═══════════════════════════════════════════════════════════════════════════════
#  TABLA
# ═══════════════════════════════════════════════════════════════════════════════

def _tabla_cer(bonds):
    if not bonds:
        st.markdown('<p style="color:#555;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        return

    rows = ""
    for b in bonds:
        p = fmt_price(b["ultimo"]) if b["ultimo"] else "—"
        rows += f"""<tr>
            <td style="color:#fff;font-weight:bold">{b["especie"]}</td>
            <td style="color:#ffcc00">{p}</td>
            <td>{_pct_html(b["dia"])}</td>
            <td>{_pct_html(b["mes"])}</td>
            <td>{_pct_html(b["anio"])}</td>
            <td>{_tir_html(b["tir"])}</td>
            <td>{_dur_html(b["dur"])}</td>
        </tr>"""

    st.markdown(f"""<table class="t">
    <thead><tr>
        <th>ESPECIE</th><th>ÚLTIMO</th><th>% DÍA</th>
        <th>% MES</th><th>% AÑO</th><th>% TIR</th><th>DUR.</th>
    </tr></thead>
    <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  YIELD CURVE — TIR vs Duración
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_text_positions(points):
    n = len(points)
    positions = ["top center"] * n
    if n < 2:
        return positions
    dur_range = max(p["dur"] for p in points) - min(p["dur"] for p in points) or 1
    tir_range = max(p["tir"] for p in points) - min(p["tir"] for p in points) or 1
    options = ["top center", "bottom center", "top right", "bottom right",
               "top left", "bottom left", "middle right", "middle left"]
    for i in range(n):
        for j in range(i + 1, n):
            dx = abs(points[i]["dur"] - points[j]["dur"]) / dur_range
            dy = abs(points[i]["tir"] - points[j]["tir"]) / tir_range
            if dx < 0.12 and dy < 0.18:
                used = {positions[k] for k in range(j)}
                for opt in options:
                    if opt not in used:
                        positions[j] = opt
                        break
    return positions


def _add_series(fig, pts, color, name, show_fit=True):
    """Agrega una serie al gráfico: puntos + etiquetas + curva ajustada opcional."""
    if not pts:
        return
    pts = sorted(pts, key=lambda p: p["dur"])
    durs   = [p["dur"]     for p in pts]
    tirs   = [p["tir"]     for p in pts]
    labels = [p["especie"] for p in pts]

    if show_fit and len(pts) >= 2:
        try:
            deg = min(2, len(pts) - 1)
            coeffs = np.polyfit(durs, tirs, deg)
            poly   = np.poly1d(coeffs)
            x_smooth = np.linspace(min(durs) * 0.85, max(durs) * 1.08, 80)
            fig.add_trace(go.Scatter(
                x=x_smooth, y=poly(x_smooth),
                mode="lines",
                line=dict(color=color, width=1.2, dash="dot"),
                hoverinfo="skip", showlegend=False,
            ))
        except Exception:
            pass

    text_pos = _resolve_text_positions(pts)
    fig.add_trace(go.Scatter(
        x=durs, y=tirs,
        mode="markers+text",
        name=name,
        marker=dict(color=color, size=8, line=dict(color="#111", width=0.8)),
        text=labels,
        textposition=text_pos,
        textfont=dict(size=7, color=color, family="Courier New"),
        hovertemplate=f"<b>%{{text}}</b><br>Dur: %{{x:.1f}}<br>TIR: %{{y:.1f}}%<extra>{name}</extra>",
    ))


def _yield_curve_combined(cer_bonds, sov_bonds):
    cer_pts = [b for b in cer_bonds if b["tir"] and b["dur"] and b["dur"] > 0]
    sov_pts = [b for b in sov_bonds if b["tir"] and b["dur"] and b["dur"] > 0]

    all_pts = cer_pts + sov_pts
    if len(all_pts) < 2:
        return

    fig = go.Figure()
    _add_series(fig, cer_pts, "#00ff41", "CER",      show_fit=True)
    _add_series(fig, sov_pts, "#ff6600", "ALs / GDs", show_fit=True)

    all_tirs = [p["tir"] for p in all_pts]
    all_durs = [p["dur"] for p in all_pts]
    tir_pad  = (max(all_tirs) - min(all_tirs)) * 0.20 or 2
    dur_pad  = (max(all_durs) - min(all_durs)) * 0.08 or 1

    fig.update_layout(
        paper_bgcolor="#000", plot_bgcolor="#000",
        font=dict(family="Courier New", size=9, color="#555"),
        margin=dict(l=45, r=15, t=35, b=40),
        height=380,
        title=dict(
            text="CURVA TIR vs DURACIÓN · CER  vs  ALs / GDs",
            font=dict(family="Courier New", size=10, color="#ff6600"),
            x=0.01, xanchor="left",
        ),
        xaxis=dict(
            title=dict(text="DURACIÓN", font=dict(size=8, color="#ff6600")),
            gridcolor="#111", linecolor="#333", zerolinecolor="#333",
            tickfont=dict(size=8, color="#555", family="Courier New"),
            range=[min(all_durs) - dur_pad, max(all_durs) + dur_pad],
        ),
        yaxis=dict(
            title=dict(text="TIR %", font=dict(size=8, color="#ff6600")),
            gridcolor="#111", linecolor="#333", zerolinecolor="#333",
            tickfont=dict(size=8, color="#555", family="Courier New"),
            ticksuffix="%",
            range=[min(all_tirs) - tir_pad, max(all_tirs) + tir_pad],
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0.7)", bordercolor="#333", borderwidth=1,
            font=dict(size=9, color="#ccc", family="Courier New"),
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        ),
        showlegend=True,
        hoverlabel=dict(
            bgcolor="#111", bordercolor="#ff6600",
            font=dict(family="Courier New", size=9, color="#fff"),
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    subtabs = st.tabs(["BONOS CER", "BREAKEVEN"])

    with st.spinner(""):
        df_cer = get_eco_bonos_by_index(8)   # CER
        df_sov = get_eco_bonos_by_index(19)  # Soberanos USD en ARS (AL/GD)
        cer_bonds = _parse_cer_df(df_cer)
        sov_bonds = _parse_cer_df(df_sov)   # misma estructura de 7 columnas

    with subtabs[0]:
        st.markdown('<div class="sh">BONOS AJUSTADOS POR CER · ECOVALORES</div>', unsafe_allow_html=True)
        _tabla_cer(cer_bonds)
        _yield_curve_combined(cer_bonds, sov_bonds)

    with subtabs[1]:
        st.markdown("""
        <div style="border:1px solid #333;padding:24px;margin-top:8px;text-align:center">
            <div style="color:#ff6600;font-size:11px;font-weight:bold;letter-spacing:2px">BREAKEVEN INFLACIÓN</div>
            <div style="color:#555;font-size:10px;margin-top:8px">PRÓXIMAMENTE</div>
            <div style="color:#333;font-size:9px;margin-top:4px">TIR CER vs TIR Tasa Fija · Spread implícito de inflación esperada</div>
        </div>
        """, unsafe_allow_html=True)
