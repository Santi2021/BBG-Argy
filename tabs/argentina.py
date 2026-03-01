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

# All tickers for yfinance (BYMA = .BA suffix)
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
    """Fetch all Argentine equity data from yfinance. Returns {ticker: {price, change_pct, volume, open, high, low, prev_close}}"""
    import yfinance as yf

    yf_symbols = [f"{t}.BA" for t in ALL_TICKERS]
    result = {}

    try:
        raw = yf.download(
            yf_symbols, period="2d", interval="1d", group_by="ticker",
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
                        df = raw.xs(yf_sym, axis=1, level=0) if hasattr(raw.columns, 'levels') else None

                if df is None or df.empty:
                    result[ticker] = {"price": None, "change_pct": 0, "volume": 0}
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

                last_row = df.iloc[-1]
                result[ticker] = {
                    "price": price,
                    "change_pct": round(chg, 2),
                    "volume": vol,
                    "open": float(last_row.get("Open", 0)) if last_row.get("Open") else None,
                    "high": float(last_row.get("High", 0)) if last_row.get("High") else None,
                    "low": float(last_row.get("Low", 0)) if last_row.get("Low") else None,
                    "prev_close": float(closes.iloc[-2]) if len(closes) >= 2 else None,
                }
            except Exception:
                result[ticker] = {"price": None, "change_pct": 0, "volume": 0}

    except Exception:
        for t in ALL_TICKERS:
            result[t] = {"price": None, "change_pct": 0, "volume": 0}

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


def _panel_html(title, headers, rows_html, accent_color="#ff6600", max_height=340):
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
    # Sort by volume descending
    items = []
    total_vol = 0
    for t in tickers:
        q = quotes.get(t, {})
        vol = q.get("volume", 0) or 0
        items.append((t, q, vol))
        total_vol += vol
    items.sort(key=lambda x: x[2], reverse=True)

    rows = ""
    for t, q, vol in items:
        p = q.get("price")
        chg = q.get("change_pct", 0)
        p_s = fmt_price(p) if p else "—"
        v_s = _vol_fmt(vol)
        rows += f'<tr><td>{t}</td><td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td><td style="color:#555">{v_s}</td></tr>'

    count = len(tickers)
    vol_s = _vol_fmt(total_vol)
    title = f"{sector_name} · {count} · VOL {vol_s}"
    return _panel_html(title, ["TICKER", "PRECIO", "% DIA", "VOL"], rows, accent_color)


# ═══════════════════════════════════════════════════════════════════════════════
#  HEATMAP — Plotly Treemap
# ═══════════════════════════════════════════════════════════════════════════════

def _build_heatmap(quotes):
    """Build a treemap heatmap: size=volume, color=change_pct, grouped by sector."""

    ids = []
    labels = []
    parents = []
    values = []
    colors = []
    custom_data = []  # [price, change_pct, volume, sector]

    # Root
    ids.append("MERVAL")
    labels.append("MERVAL")
    parents.append("")
    values.append(0)
    colors.append(0)
    custom_data.append([0, 0, 0, ""])

    for sector_name, sector_info in SECTORS.items():
        tickers = sector_info["tickers"]

        sector_vol = 0
        for t in tickers:
            q = quotes.get(t, {})
            sector_vol += (q.get("volume", 0) or 0)

        if sector_vol == 0:
            continue

        sector_id = f"S_{sector_name}"
        ids.append(sector_id)
        labels.append(sector_name)
        parents.append("MERVAL")
        values.append(0)
        colors.append(0)
        custom_data.append([0, 0, sector_vol, sector_name])

        for t in tickers:
            q = quotes.get(t, {})
            vol = q.get("volume", 0) or 0
            chg = q.get("change_pct", 0) or 0
            price = q.get("price")

            if vol <= 0:
                continue

            ids.append(f"{sector_id}_{t}")
            labels.append(t)
            parents.append(sector_id)
            values.append(vol)
            colors.append(chg)
            custom_data.append([price, chg, vol, sector_name])

    if len(ids) <= 1:
        return None

    # Color scale: red for negative, black for zero, green for positive
    max_abs = max(abs(c) for c in colors) if colors else 1
    max_abs = max(max_abs, 1)  # avoid division by zero

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0, "#8b0000"],
                [0.15, "#ff3b3b"],
                [0.4, "#551111"],
                [0.5, "#1a1a1a"],
                [0.6, "#115511"],
                [0.85, "#00ff41"],
                [1.0, "#006400"],
            ],
            cmid=0,
            cmin=-max_abs,
            cmax=max_abs,
            line=dict(color="#000", width=1.5),
            colorbar=dict(
                title=dict(text="% DIA", font=dict(size=9, color="#ff6600", family="Courier New")),
                tickfont=dict(size=8, color="#ccc", family="Courier New"),
                ticksuffix="%",
                bgcolor="rgba(0,0,0,0)",
                bordercolor="#333",
                borderwidth=1,
                len=0.6,
                thickness=12,
                x=1.01,
            ),
        ),
        customdata=custom_data,
        texttemplate="<b>%{label}</b><br>%{customdata[1]:+.2f}%",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Sector: %{customdata[3]}<br>"
            "Precio: $%{customdata[0]:,.2f}<br>"
            "Variación: %{customdata[1]:+.2f}%<br>"
            "Volumen: %{customdata[2]:,.0f}"
            "<extra></extra>"
        ),
        textfont=dict(family="Courier New", size=11, color="#fff"),
        tiling=dict(packing="squarify", pad=2),
        pathbar=dict(
            visible=True,
            textfont=dict(family="Courier New", size=9, color="#ff6600"),
            thickness=18,
            edgeshape=">",
            side="top",
        ),
        branchvalues="total",
        maxdepth=3,
    ))

    fig.update_layout(
        paper_bgcolor="#000",
        plot_bgcolor="#000",
        font=dict(family="Courier New", size=10, color="#ccc"),
        margin=dict(l=4, r=4, t=30, b=4),
        height=700,
        title=dict(
            text="EQUITY ARG · HEATMAP POR SECTOR — TAMAÑO = VOLUMEN · COLOR = VARIACIÓN DIA",
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
        PH = 340
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

        # Pad to 9 if needed
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
