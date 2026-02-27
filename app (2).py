import streamlit as st

st.set_page_config(
    page_title="ARG Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Bloomberg DNA CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0a0a0a !important;
    color: #e8e0d0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }

[data-testid="stAppViewContainer"] { padding: 0 !important; }
[data-testid="block-container"] { padding: 0 !important; max-width: 100% !important; }
.main .block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none; }

/* ── Bloomberg Header ── */
.bbg-header {
    background: #0a0a0a;
    border-bottom: 1px solid #1a1a1a;
    padding: 0 16px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 1000;
}
.bbg-logo {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 13px;
    color: #f5a623;
    letter-spacing: 0.12em;
}
.bbg-clock {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #555;
    letter-spacing: 0.05em;
}

/* ── Tab Bar ── */
.bbg-tabbar {
    background: #0d0d0d;
    border-bottom: 1px solid #1a1a1a;
    display: flex;
    align-items: stretch;
    gap: 0;
    padding: 0 8px;
    height: 32px;
    overflow-x: auto;
    scrollbar-width: none;
}
.bbg-tabbar::-webkit-scrollbar { display: none; }

/* Streamlit tab overrides */
[data-testid="stTabs"] { margin: 0; padding: 0; }
[data-testid="stTabBar"] {
    background: #0d0d0d !important;
    border-bottom: 1px solid #222 !important;
    padding: 0 8px !important;
    gap: 0 !important;
}
[data-testid="stTabBar"] button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #555 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 0 14px !important;
    height: 32px !important;
    transition: color 0.15s, border-color 0.15s !important;
}
[data-testid="stTabBar"] button:hover {
    color: #ccc !important;
    background: #111 !important;
}
[data-testid="stTabBar"] button[aria-selected="true"] {
    color: #f5a623 !important;
    border-bottom: 2px solid #f5a623 !important;
    background: transparent !important;
}
[data-testid="stTabBar"] [role="presentation"] { display: none !important; }

/* ── Content Area ── */
[data-testid="stTabsContent"] {
    background: #0a0a0a !important;
    padding: 12px 16px !important;
}

/* ── Section Header ── */
.sec-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #f5a623;
    border-bottom: 1px solid #1e1e1e;
    padding-bottom: 4px;
    margin-bottom: 8px;
    margin-top: 16px;
}
.sec-header:first-child { margin-top: 0; }

/* ── Ticker Cards (Overview row) ── */
.ticker-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 1px;
    background: #161616;
    border: 1px solid #1e1e1e;
    margin-bottom: 12px;
}
.ticker-card {
    background: #0d0d0d;
    padding: 8px 10px;
    cursor: default;
    transition: background 0.1s;
    position: relative;
}
.ticker-card:hover { background: #121212; }
.ticker-card .t-symbol {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    color: #f5a623;
    letter-spacing: 0.08em;
    margin-bottom: 2px;
}
.ticker-card .t-name {
    font-size: 9px;
    color: #444;
    letter-spacing: 0.03em;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ticker-card .t-price {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 15px;
    font-weight: 500;
    color: #e8e0d0;
    letter-spacing: 0.02em;
    line-height: 1;
}
.ticker-card .t-change {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    margin-top: 3px;
}
.ticker-card .t-change.up { color: #00c853; }
.ticker-card .t-change.down { color: #ff3d3d; }
.ticker-card .t-change.flat { color: #555; }

/* ── Data Table ── */
.bbg-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
}
.bbg-table thead tr {
    border-bottom: 1px solid #1e1e1e;
}
.bbg-table thead th {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #444;
    text-align: right;
    padding: 4px 8px;
}
.bbg-table thead th:first-child { text-align: left; }
.bbg-table tbody tr {
    border-bottom: 1px solid #111;
    transition: background 0.08s;
}
.bbg-table tbody tr:hover { background: #101010; }
.bbg-table tbody td {
    padding: 5px 8px;
    text-align: right;
    color: #b0a898;
    font-size: 11px;
}
.bbg-table tbody td:first-child {
    text-align: left;
    color: #f5a623;
    font-weight: 500;
}
.bbg-table .up { color: #00c853 !important; }
.bbg-table .down { color: #ff3d3d !important; }
.bbg-table .neutral { color: #555 !important; }

/* ── KPI Strip ── */
.kpi-strip {
    display: flex;
    gap: 1px;
    background: #161616;
    border: 1px solid #1e1e1e;
    margin-bottom: 12px;
}
.kpi-item {
    background: #0d0d0d;
    padding: 10px 16px;
    flex: 1;
    min-width: 120px;
}
.kpi-label {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #444;
    margin-bottom: 4px;
}
.kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 18px;
    font-weight: 500;
    color: #e8e0d0;
    line-height: 1;
}
.kpi-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    margin-top: 2px;
}
.kpi-sub.up { color: #00c853; }
.kpi-sub.down { color: #ff3d3d; }

/* ── Divider ── */
.bbg-divider {
    border: none;
    border-top: 1px solid #161616;
    margin: 12px 0;
}

/* ── Loading spinner ── */
.stSpinner > div { border-top-color: #f5a623 !important; }

/* ── Plotly chart bg ── */
.js-plotly-plot .plotly { background: transparent !important; }

/* ── Streamlit column gaps ── */
[data-testid="stHorizontalBlock"] { gap: 8px !important; }
[data-testid="column"] { padding: 0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #222; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #333; }

/* ── Auto-refresh selector hide ── */
.stSelectbox label { 
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    color: #444 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
.stSelectbox > div > div {
    background: #0d0d0d !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    color: #888 !important;
}

/* Sub-tabs inside tabs */
[data-testid="stTabBar"] [data-baseweb="tab-list"] {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

import time
from datetime import datetime
import pytz

# ── Header ────────────────────────────────────────────────────────────────────
now_ar = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
now_et = datetime.now(pytz.timezone("America/New_York"))

st.markdown(f"""
<div class="bbg-header">
  <span class="bbg-logo">◼ ARG TERMINAL</span>
  <span class="bbg-clock">
    ART {now_ar.strftime('%H:%M:%S')} &nbsp;·&nbsp; ET {now_et.strftime('%H:%M:%S')} &nbsp;·&nbsp; {now_ar.strftime('%d %b %Y')}
  </span>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
from tabs import overview, argentina, bonos, futuros, mundo, watchlist

tabs = st.tabs([
    "OVERVIEW",
    "🇦🇷  ARGENTINA",
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
