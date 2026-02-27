import streamlit as st

st.set_page_config(
    page_title="ARG Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
#  BLOOMBERG TERMINAL CSS — Matching the notebook style exactly
#  Black bg, orange (#ff6600) accents, Courier New, ultra-dense tables
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Reset & Base — pure black, Courier ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #000 !important;
    color: #ccc !important;
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 12px !important;
}

/* Hide ALL Streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* Kill all Streamlit padding */
[data-testid="stAppViewContainer"] { padding: 0 !important; }
[data-testid="block-container"] { padding: 0 8px !important; max-width: 100% !important; }
.main .block-container { padding: 0 8px !important; max-width: 100% !important; }

/* ── Header — orange border bottom like the notebook ── */
.bbg-header {
    background: #000;
    border-bottom: 2px solid #ff6600;
    padding: 8px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 1000;
}
.bbg-logo {
    font-family: 'Courier New', Courier, monospace;
    font-weight: bold;
    font-size: 20px;
    color: #ff6600;
    letter-spacing: 3px;
}
.bbg-clock {
    font-family: 'Courier New', Courier, monospace;
    font-size: 11px;
    color: #ff6600;
    text-align: right;
}
.bbg-clock .dt {
    color: #fff;
    font-size: 13px;
    display: block;
}

/* ── Tab Bar — Bloomberg function key style ── */
[data-testid="stTabs"] { margin: 0; padding: 0; }
[data-testid="stTabBar"] {
    background: #000 !important;
    border-bottom: 1px solid #333 !important;
    padding: 0 !important;
    gap: 0 !important;
}
[data-testid="stTabBar"] button {
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 11px !important;
    font-weight: bold !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    color: #666 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 4px 12px !important;
    height: 28px !important;
    transition: all 0.1s !important;
    white-space: nowrap !important;
}
[data-testid="stTabBar"] button:hover {
    color: #fff !important;
    background: #0a0a0a !important;
}
[data-testid="stTabBar"] button[aria-selected="true"] {
    color: #ff6600 !important;
    border-bottom: 2px solid #ff6600 !important;
    background: transparent !important;
}
[data-testid="stTabBar"] [role="presentation"] { display: none !important; }

/* ── Content Area ── */
[data-testid="stTabsContent"] {
    background: #000 !important;
    padding: 4px 8px !important;
}

/* ── Section Header — orange underline ── */
.sec-header {
    color: #ff6600;
    font-family: 'Courier New', Courier, monospace;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-bottom: 1px solid #333;
    padding-bottom: 4px;
    margin-bottom: 6px;
    margin-top: 12px;
}
.sec-header:first-child { margin-top: 0; }

/* ── Data Table — Bloomberg dense, matching notebook exactly ── */
.bbg-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Courier New', Courier, monospace;
    font-size: 12px;
    margin-bottom: 12px;
}
.bbg-table thead tr {
    background: #111;
}
.bbg-table thead th {
    color: #ff6600;
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
    text-align: left;
    padding: 4px 8px;
    border-bottom: 1px solid #ff6600;
    white-space: nowrap;
}
.bbg-table tbody tr {
    border-bottom: 1px solid #111;
    transition: background 0.05s;
}
.bbg-table tbody tr:hover { background: #0a0a0a; }
.bbg-table tbody td {
    padding: 4px 8px;
    text-align: left;
    color: #ccc;
    font-size: 12px;
    white-space: nowrap;
}
/* First column: white bold (ticker/name) */
.bbg-table tbody td:first-child {
    color: #fff;
    font-weight: bold;
}
/* Price column styling */
.bbg-table .price { color: #ffcc00; }
/* Exchange/market column */
.bbg-table .mkt { color: #666; font-size: 10px; }

/* Color classes */
.up { color: #00ff41 !important; }
.down { color: #ff3b3b !important; }
.flat { color: #666 !important; }
.neutral { color: #666 !important; }

/* ── Ticker Cards — compact grid ── */
.ticker-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 1px;
    background: #111;
    border: 1px solid #333;
    margin-bottom: 8px;
}
.ticker-card {
    background: #000;
    padding: 4px 8px;
    cursor: default;
}
.ticker-card:hover { background: #0a0a0a; }
.ticker-card .t-symbol {
    font-family: 'Courier New', Courier, monospace;
    font-size: 11px;
    font-weight: bold;
    color: #fff;
    letter-spacing: 1px;
}
.ticker-card .t-name {
    font-size: 9px;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ticker-card .t-price {
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
    font-weight: bold;
    color: #ffcc00;
    line-height: 1.2;
}
.ticker-card .t-change {
    font-family: 'Courier New', Courier, monospace;
    font-size: 11px;
    font-weight: bold;
}
.ticker-card .t-change.up { color: #00ff41; }
.ticker-card .t-change.down { color: #ff3b3b; }
.ticker-card .t-change.flat { color: #666; }

/* ── KPI Strip — top dashboard bar ── */
.kpi-strip {
    display: flex;
    gap: 1px;
    background: #333;
    border: 1px solid #333;
    margin-bottom: 8px;
}
.kpi-item {
    background: #000;
    padding: 6px 12px;
    flex: 1;
    min-width: 90px;
}
.kpi-label {
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #ff6600;
    margin-bottom: 2px;
}
.kpi-value {
    font-family: 'Courier New', Courier, monospace;
    font-size: 16px;
    font-weight: bold;
    color: #ffcc00;
    line-height: 1;
}
.kpi-sub {
    font-family: 'Courier New', Courier, monospace;
    font-size: 10px;
    font-weight: bold;
    margin-top: 1px;
}
.kpi-sub.up { color: #00ff41; }
.kpi-sub.down { color: #ff3b3b; }
.kpi-sub.flat { color: #666; }

/* ── Footer ── */
.bbg-footer {
    border-top: 1px solid #333;
    padding-top: 8px;
    color: #444;
    font-size: 10px;
    text-align: center;
    letter-spacing: 1px;
    margin-top: 16px;
}

/* ── Loading spinner ── */
.stSpinner > div { border-top-color: #ff6600 !important; }

/* ── Plotly ── */
.js-plotly-plot .plotly { background: transparent !important; }

/* ── Layout density — kill Streamlit gaps ── */
[data-testid="stHorizontalBlock"] { gap: 4px !important; }
[data-testid="column"] { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0.1rem !important; }

/* ── Scrollbar — thin dark ── */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 0; }
::-webkit-scrollbar-thumb:hover { background: #555; }

/* ── Text input (watchlist) ── */
.stTextInput > div > div > input {
    background: #000 !important;
    border: 1px solid #333 !important;
    border-radius: 0 !important;
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 12px !important;
    color: #fff !important;
    padding: 4px 8px !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #111 !important;
    border: 1px solid #ff6600 !important;
    border-radius: 0 !important;
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 11px !important;
    font-weight: bold !important;
    color: #ff6600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    padding: 4px 12px !important;
}
.stButton > button:hover {
    background: #1a1a00 !important;
}

/* ── Selectbox ── */
.stSelectbox label {
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 10px !important;
    color: #ff6600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}
.stSelectbox > div > div {
    background: #000 !important;
    border: 1px solid #333 !important;
    border-radius: 0 !important;
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 11px !important;
    color: #ccc !important;
}

/* Sub-tabs */
[data-testid="stTabBar"] [data-baseweb="tab-list"] {
    background: transparent !important;
}

/* Code blocks (debug tab) */
pre {
    background: #0a0a0a !important;
    border: 1px solid #333 !important;
    font-size: 10px !important;
    color: #ccc !important;
}
</style>
""", unsafe_allow_html=True)

from datetime import datetime
import pytz

# ── Header ────────────────────────────────────────────────────────────────────
now_ar = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
now_et = datetime.now(pytz.timezone("America/New_York"))

st.markdown(f"""
<div class="bbg-header">
  <div class="bbg-logo">BLOOMBERG TERMINAL</div>
  <div class="bbg-clock">
    ULTIMA ACTUALIZACION
    <span class="dt">
      {now_ar.strftime('%d/%m/%Y')} &nbsp; ART {now_ar.strftime('%H:%M:%S')} &nbsp;·&nbsp; ET {now_et.strftime('%H:%M:%S')}
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
from tabs import overview, argentina, bonos, futuros, mundo, watchlist

tabs = st.tabs([
    "OVERVIEW",
    "🇦🇷 ARGENTINA",
    "BONOS",
    "FUTUROS & CURVA",
    "MUNDO",
    "WATCHLIST",
])

with tabs[0]:
    overview.render()

with tabs[1]:
    argentina.render()

with tabs[2]:
    bonos.render()

with tabs[3]:
    futuros.render()

with tabs[4]:
    mundo.render()

with tabs[5]:
    watchlist.render()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown('<div class="bbg-footer">DATA VIA YAHOO FINANCE / DATA912 / BONDTERMINAL / DOLARAPI / ECOVALORES - SOLO FINES INFORMATIVOS</div>', unsafe_allow_html=True)
