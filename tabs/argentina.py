"""
ARGENTINA — Equity por Sectores
  Tab 1: 9 paneles simétricos por sector (grilla 3x3)
  Tab 2: Heatmap treemap (tamaño = volumen, color = variación diaria)
"""
import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import fmt_price, fmt_change

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTOR DEFINITIONS — tickers BYMA en ARS
# ═══════════════════════════════════════════════════════════════════════════════

SECTORS = {
    "BANCOS & FINANCIERAS": {
        "tickers": ["GGAL", "BBAR", "BMA", "SUPV", "BYMA", "VALO", "BPAT", "BHIP"],
        "color": "#00bfff",
    },
    "ENERGÍA": {
        "tickers": ["YPFD", "PAMP", "CAPX", "COME"],
        "color": "#ff6600",
    },
    "UTILITIES": {
        "tickers": ["CEPU", "EDN", "TGNO4", "TGSU2", "METR", "TRAN",
                     "CECO2", "CGPA2", "DGCU2", "GBAN", "AUSO", "OEST"],
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
        "tickers": ["TECO2", "CVH", "GCLA"],
        "color": "#60a5fa",
    },
    "REAL ESTATE": {
        "tickers": ["IRSA", "CTIO", "CADO", "INVJ", "IEB"],
        "color": "#f59e0b",
    },
    "INDUSTRIA & CONSUMO": {
        "tickers": ["MIRG", "FERR", "GRIM", "LONG", "RICH", "RIGO",
                     "HAVA", "DOME", "ROSE"],
        "color": "#ec4899",
    },
    "OTROS": {
        "tickers": ["A3", "BOLT", "CARC", "FIPL", "GAMI", "GARO",
                     "GCDI", "INTR", "MERA", "POLL"],
        "color": "#555",
    },
}

ALL_TICKERS = []
for sec in SECTORS.values():
    for t in sec["tickers"]:
        if t not in ALL_TICKERS:
            ALL_TICKERS.append(t)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA FETCHING — yfinance batch
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def _fetch_arg_equity():
    """Fetch all Argentine equity data via yfinance .BA tickers."""
    import yfinance as yf
    import pandas as pd

    yf_symbols = [f"{t}.BA" for t in ALL_TICKERS]
    result = {}

    try:
        raw = yf.download(
            yf_symbols, period="5d", interval="1d", group_by="ticker",
            auto_adjust=True, progress=False, threads=True,
        )

        for ticker, yf_sym in zip(ALL_TICKERS, yf_symbols):
            try:
                if len(yf_symbols) == 1:
                    df = raw
                else:
                    try:
                        df = raw[yf_sym]
                    except (KeyError, TypeError):
                        try:
                            df = raw.xs(yf_sym, axis=1, level=0)
                        except Exception:
                            result[ticker] = {"price": None, "change_pct": 0, "volume": 0, "monto": 0}
                            continue

                if df is None or (hasattr(df, 'empty') and df.empty):
                    result[ticker] = {"price": None, "change_pct": 0, "volume": 0, "monto": 0}
                    continue

                closes = df["Close"].dropna()
                volumes = df["Volume"].dropna()

                if len(closes) >= 2:
                    price = float(closes.iloc[-1])
                    prev = float(closes.iloc[-2])
                    chg = (price - prev) / prev * 100 if prev != 0 else 0
                elif len(closes) == 1:
                    price = float(closes.iloc[-1])
                    chg = 0
                else:
                    price = None
                    chg = 0

                vol = int(volumes.iloc[-1]) if len(volumes) > 0 else 0
                monto = vol * price if (vol and price) else 0

                result[ticker] = {
                    "price": price,
                    "change_pct": round(chg, 2),
                    "volume": vol,
                    "monto": round(monto),
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
    """Build rows for a sector panel."""
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
    """Treemap heatmap: size=volume, color=change_pct, grouped by sector.
    Uses flat structure with explicit sector totals for maximum compatibility."""

    labels = []
    parents = []
    values = []
    colors = []
    text_lines = []
    hover_texts = []

    # Collect all sector data first
    sector_data = {}
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

    # Build flat arrays — root level sectors with "total" branchvalues
    total_market_monto = sum(s["total_monto"] for s in sector_data.values())

    # We use sqrt(monto) for treemap sizing to compress the scale —
    # otherwise YPF/GGAL dominate and smaller companies are invisible.
    # The color and hover still show real values.
    import math

    def _compress(v):
        """sqrt transform to compress size differences while preserving order."""
        return math.sqrt(max(v, 0))

    # Root
    root_compressed = sum(_compress(s["total_monto"]) for s in sector_data.values())
    labels.append("EQUITY ARG")
    parents.append("")
    values.append(root_compressed)
    colors.append(0)
    text_lines.append("")
    hover_texts.append(f"Monto total: {_vol_fmt(total_market_monto)}")

    for sector_name, sdata in sector_data.items():
        # Sector node — compressed value = sum of compressed children
        sector_compressed = sum(_compress(m) for _, _, _, m in sdata["children"])
        labels.append(sector_name)
        parents.append("EQUITY ARG")
        values.append(sector_compressed)
        colors.append(sdata["avg_chg"])
        text_lines.append(f"<b>{sector_name}</b><br>{sdata['avg_chg']:+.2f}%")
        hover_texts.append(
            f"<b>{sector_name}</b><br>"
            f"Variación promedio: {sdata['avg_chg']:+.2f}%<br>"
            f"Monto: {_vol_fmt(sdata['total_monto'])}<br>"
            f"Empresas: {len(sdata['children'])}"
        )

        # Company nodes
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

    # Color range from leaf nodes
    leaf_colors = [c for c, p in zip(colors, parents) if p not in ("", "EQUITY ARG")]
    max_abs = max(abs(c) for c in leaf_colors) if leaf_colors else 1
    max_abs = max(max_abs, 0.5)

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0, "#8b0000"],
                [0.15, "#cc2222"],
                [0.35, "#551515"],
                [0.5, "#222222"],
                [0.65, "#155515"],
                [0.85, "#22cc22"],
                [1.0, "#006400"],
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
            text="EQUITY ARG · HEATMAP POR SECTOR — TAMAÑO = MONTO OPERADO · COLOR = VARIACIÓN DIA",
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
