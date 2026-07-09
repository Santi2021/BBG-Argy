"""
ARGENTINA — Equity por Sectores
  Tab 1: 9 paneles simétricos por sector (grilla 3x3)
  Tab 2: Heatmap treemap (tamaño = volumen, color = variación diaria)
"""
import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import fmt_price, fmt_change, _get_closes

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTOR DEFINITIONS — tickers BYMA en ARS
# ═══════════════════════════════════════════════════════════════════════════════

SECTORS = {
    "BANCOS & FINANCIERAS": {
        "tickers": ["GGAL", "BBAR", "BMA", "SUPV", "BYMA", "VALO", "BPAT", "BHIP"],
        "color": "#00bfff",
    },
    "ENERGÍA": {
        "tickers": ["YPFD", "PAMP", "CAPX", "VIST"],
        "color": "#ff6600",
    },
    "UTILITIES": {
        "tickers": ["CEPU", "EDN", "TGNO4", "TGSU2", "METR", "TRAN",
                     "CECO2", "CGPA2", "DGCU2", "GBAN", "AUSO", "OEST", "ECOG"],
        "color": "#ffcc00",
    },
    "MATERIALES": {
        "tickers": ["ALUA", "TXAR", "LOMA", "HARG", "CELU"],
        "color": "#cc66ff",
    },
    "AGRO & ALIMENTOS": {
        "tickers": ["CRES", "AGRO", "MOLA", "MOLI", "SEMI", "SAMI",
                     "LEDE", "MORI", "INAG", "PATA"],
        "color": "#00ff41",
    },
    "TELECOM & MEDIOS": {
        "tickers": ["TECO2", "CVH", "GCLA", "HSAT"],
        "color": "#60a5fa",
    },
    "REAL ESTATE": {
        "tickers": ["IRSA", "CTIO", "CADO", "INVJ", "IEB", "RAGH"],
        "color": "#f59e0b",
    },
    "INDUSTRIA & CONSUMO": {
        "tickers": ["MIRG", "FERR", "GRIM", "LONG", "RICH", "RIGO",
                     "HAVA", "DOME", "ROSE"],
        "color": "#ec4899",
    },
    "OTROS": {
        "tickers": ["A3", "BOLT", "CARC", "FIPL", "GAMI", "GARO",
                     "GCDI", "INTR", "MERA", "POLL", "COME"],
        "color": "#555",
    },
}

ALL_TICKERS = []
for sec in SECTORS.values():
    for t in sec["tickers"]:
        if t not in ALL_TICKERS:
            ALL_TICKERS.append(t)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA FETCHING — yfinance batch, compatible con 0.2.58+
# ═══════════════════════════════════════════════════════════════════════════════

def _prev_close_fallback(sym: str) -> float | None:
    """Obtiene previousClose via fast_info — fallback cuando download devuelve < 2 filas."""
    try:
        fi = yf.Ticker(sym).fast_info
        return float(fi.get("previous_close") or fi.get("previousClose") or 0) or None
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_arg_equity():
    """Fetch all Argentine equity data via yfinance .BA tickers."""
    import yfinance as yf
    import pandas as pd

    yf_symbols = [f"{t}.BA" for t in ALL_TICKERS]
    n = len(yf_symbols)
    result = {}

    try:
        raw = yf.download(
            yf_symbols, period="5d", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )

        for ticker, yf_sym in zip(ALL_TICKERS, yf_symbols):
            try:
                closes  = _get_closes(raw, yf_sym, n).dropna()
                # Volume — mismo patrón de acceso
                if isinstance(raw.columns, pd.MultiIndex):
                    level0 = raw.columns.get_level_values(0).tolist()
                    if "Volume" in level0:
                        volumes = raw["Volume"][yf_sym].dropna()
                    else:
                        volumes = raw[yf_sym]["Volume"].dropna()
                else:
                    volumes = pd.Series(dtype=float)

                if len(closes) >= 2:
                    price = float(closes.iloc[-1])
                    prev  = float(closes.iloc[-2])
                    chg   = (price - prev) / prev * 100 if prev != 0 else 0
                elif len(closes) == 1:
                    price = float(closes.iloc[-1])
                    prev  = _prev_close_fallback(yf_sym)
                    chg   = (price - prev) / prev * 100 if prev else 0
                else:
                    price = None
                    chg   = 0

                vol   = int(volumes.iloc[-1]) if len(volumes) > 0 else 0
                monto = vol * price if (vol and price) else 0

                result[ticker] = {
                    "price":      price,
                    "change_pct": round(chg, 2),
                    "volume":     vol,
                    "monto":      round(monto),
                }
            except Exception:
                result[ticker] = {"price": None, "change_pct": 0, "volume": 0, "monto": 0}

    except Exception:
        for t in ALL_TICKERS:
            result[t] = {"price": None, "change_pct": 0, "volume": 0, "monto": 0}

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _pct_html(val):
    if val is None or val == 0:
        return '<span style="color:#555">0.00%</span>'
    try:
        v = float(val)
        c = "#00ff41" if v > 0 else ("#ff3b3b" if v < 0 else "#555")
        s = "+" if v >= 0 else ""
        return f'<span style="color:{c};font-weight:bold">{s}{v:.2f}%</span>'
    except:
        return f'<span style="color:#555">{val}</span>'


def _vol_fmt(v):
    if not v or v == 0:
        return "—"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(v)


def _panel_html(title, headers, rows_html, accent_color="#ff6600", max_height=220):
    ths = "".join(f"<th>{h}</th>" for h in headers)
    return f"""<div style="border:1px solid #333;background:#000;height:{max_height}px;display:flex;flex-direction:column;overflow:hidden">
  <div style="background:#111;color:{accent_color};font-size:9px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;padding:3px 8px;border-bottom:1px solid {accent_color};flex-shrink:0">{title}</div>
  <div style="overflow-y:auto;flex:1">
    <table class="t" style="border-collapse:collapse;width:100%">
      <thead><tr style="position:sticky;top:0;z-index:2;background:#111">{ths}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>"""


def _build_sector_panel(sector_name, tickers, quotes, accent_color):
    items = []
    total_monto = 0
    for t in tickers:
        q = quotes.get(t, {})
        monto = q.get("monto", 0) or 0
        items.append((t, q, monto))
        total_monto += monto
    items.sort(key=lambda x: x[2], reverse=True)

    rows = ""
    for t, q, monto in items:
        p = q.get("price")
        chg = q.get("change_pct", 0)
        p_s = fmt_price(p) if p else "—"
        m_s = _vol_fmt(monto)
        rows += f'<tr><td>{t}</td><td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td><td style="color:#555">{m_s}</td></tr>'

    count = len(tickers)
    vol_s = _vol_fmt(total_monto)
    title = f"{sector_name} · {count} · MONTO {vol_s}"
    return _panel_html(title, ["TICKER", "PRECIO", "% DIA", "MONTO"], rows, accent_color)


# ═══════════════════════════════════════════════════════════════════════════════
#  HEATMAP — Plotly Treemap
# ═══════════════════════════════════════════════════════════════════════════════

def _build_heatmap(quotes):
    import math

    labels = []
    parents = []
    values = []
    colors = []
    text_lines = []
    hover_texts = []

    sector_data = {}
    all_leaf_changes = []

    for sector_name, sector_info in SECTORS.items():
        children = []
        sector_monto = 0
        sector_chg_w = 0
        for t in sector_info["tickers"]:
            q = quotes.get(t, {})
            monto = q.get("monto", 0) or 0
            chg = q.get("change_pct", 0) or 0
            price = q.get("price")
            if monto > 0 and price is not None:
                children.append((t, price, chg, monto))
                sector_monto += monto
                sector_chg_w += chg * monto
                all_leaf_changes.append(chg)
        if sector_monto > 0:
            avg_chg = sector_chg_w / sector_monto
            sector_data[sector_name] = {
                "children": children,
                "total_monto": sector_monto,
                "avg_chg": avg_chg,
                "color": sector_info["color"],
            }

    if not sector_data:
        return None

    if all_leaf_changes:
        actual_max = max(abs(c) for c in all_leaf_changes)
        max_abs = max(2.0, min(actual_max, 15.0))
    else:
        max_abs = 5.0

    def _compress(v):
        return math.sqrt(max(v, 0))

    sector_compressed_vals = {}
    for sector_name, sdata in sector_data.items():
        sector_compressed_vals[sector_name] = sum(_compress(m) for _, _, _, m in sdata["children"])

    root_val = sum(sector_compressed_vals.values())
    total_market_monto = sum(s["total_monto"] for s in sector_data.values())

    labels.append("EQUITY ARG")
    parents.append("")
    values.append(root_val)
    colors.append(0)
    text_lines.append("")
    hover_texts.append(f"Monto total: {_vol_fmt(total_market_monto)}")

    for sector_name, sdata in sector_data.items():
        labels.append(sector_name)
        parents.append("EQUITY ARG")
        values.append(sector_compressed_vals[sector_name])
        colors.append(sdata["avg_chg"])
        text_lines.append(f"<b>{sector_name}</b><br>{sdata['avg_chg']:+.2f}%")
        hover_texts.append(
            f"<b>{sector_name}</b><br>"
            f"Variación promedio: {sdata['avg_chg']:+.2f}%<br>"
            f"Monto: {_vol_fmt(sdata['total_monto'])}<br>"
            f"Empresas: {len(sdata['children'])}"
        )

        for t, price, chg, monto in sdata["children"]:
            p_str = f"${price:,.0f}" if price >= 100 else f"${price:,.2f}"
            labels.append(t)
            parents.append(sector_name)
            values.append(_compress(monto))
            colors.append(chg)
            text_lines.append(f"<b>{t}</b><br>{chg:+.2f}%")
            hover_texts.append(
                f"<b>{t}</b><br>"
                f"Sector: {sector_name}<br>"
                f"Precio: {p_str}<br>"
                f"Variación: {chg:+.2f}%<br>"
                f"Monto: {_vol_fmt(monto)}"
            )

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0,  "#8b0000"],
                [0.15, "#cc2222"],
                [0.35, "#551515"],
                [0.5,  "#222222"],
                [0.65, "#155515"],
                [0.85, "#22cc22"],
                [1.0,  "#006400"],
            ],
            cmid=0,
            cmin=-max_abs,
            cmax=max_abs,
            line=dict(color="#000", width=2),
            cornerradius=3,
            colorbar=dict(
                title=dict(text="% DIA", font=dict(size=9, color="#ff6600", family="Courier New")),
                tickfont=dict(size=8, color="#ccc", family="Courier New"),
                ticksuffix="%",
                bgcolor="rgba(0,0,0,0)",
                bordercolor="#333",
                borderwidth=1,
                len=0.5,
                thickness=12,
                x=1.01,
                tickvals=[-max_abs, -max_abs/2, 0, max_abs/2, max_abs],
                ticktext=[
                    f"{-max_abs:.1f}%",
                    f"{-max_abs/2:.1f}%",
                    "0%",
                    f"+{max_abs/2:.1f}%",
                    f"+{max_abs:.1f}%",
                ],
            ),
        ),
        text=text_lines,
        textinfo="text",
        hovertext=hover_texts,
        hoverinfo="text",
        textfont=dict(family="Courier New", size=12, color="#fff"),
        tiling=dict(packing="squarify", pad=3),
        pathbar=dict(
            visible=True,
            textfont=dict(family="Courier New", size=10, color="#ff6600"),
            thickness=20,
            edgeshape=">",
            side="top",
        ),
        maxdepth=3,
    ))

    fig.update_layout(
        paper_bgcolor="#000",
        plot_bgcolor="#000",
        font=dict(family="Courier New", size=10, color="#ccc"),
        margin=dict(l=4, r=4, t=35, b=4),
        height=720,
        title=dict(
            text=f"EQUITY ARG · HEATMAP POR SECTOR — TAMAÑO = MONTO OPERADO · COLOR = VARIACIÓN DIA · ESCALA ±{max_abs:.1f}%",
            font=dict(family="Courier New", size=10, color="#ff6600"),
            x=0.01, xanchor="left",
        ),
        hoverlabel=dict(
            bgcolor="#111",
            bordercolor="#ff6600",
            font=dict(family="Courier New", size=10, color="#fff"),
        ),
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    subtabs = st.tabs(["SECTORES", "HEATMAP"])

    with st.spinner(""):
        quotes = _fetch_arg_equity()

    with subtabs[0]:
        sector_list = list(SECTORS.items())

        panels = []
        for sector_name, sector_info in sector_list:
            p = _build_sector_panel(
                sector_name,
                sector_info["tickers"],
                quotes,
                sector_info["color"],
            )
            panels.append(p)

        while len(panels) < 9:
            panels.append(_panel_html("—", [], "", "#333"))

        grid_html = f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:auto auto auto;gap:4px;margin-top:4px">
          <div>{panels[0]}</div><div>{panels[1]}</div><div>{panels[2]}</div>
          <div>{panels[3]}</div><div>{panels[4]}</div><div>{panels[5]}</div>
          <div>{panels[6]}</div><div>{panels[7]}</div><div>{panels[8]}</div>
        </div>"""

        st.markdown(grid_html, unsafe_allow_html=True)

    with subtabs[1]:
        fig = _build_heatmap(quotes)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<p style="color:#555;font-size:10px">Sin datos para heatmap</p>', unsafe_allow_html=True)
