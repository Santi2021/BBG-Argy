import streamlit as st

st.set_page_config(
    page_title="ARG Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
#  Bloomberg DNA CSS — Ultra dense, dark terminal aesthetic
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0a0a0a !important;
    color: #e8e0d0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
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
    background: linear-gradient(180deg, #111 0%, #0a0a0a 100%);
    border-bottom: 1px solid #f5a623;
    padding: 0 12px;
    height: 28px;
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
    font-size: 12px;
    color: #f5a623;
    letter-spacing: 0.15em;
}
.bbg-clock {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #666;
    letter-spacing: 0.05em;
}

/* ── Tab Bar — Bloomberg function keys ── */
[data-testid="stTabs"] { margin: 0; padding: 0; }
[data-testid="stTabBar"] {
    background: #0c0c0c !important;
    border-bottom: 1px solid #1a1a1a !important;
    padding: 0 4px !important;
    gap: 0 !important;
}
[data-testid="stTabBar"] button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #555 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 0 10px !important;
    height: 26px !important;
    transition: all 0.1s !important;
    white-space: nowrap !important;
}
[data-testid="stTabBar"] button:hover {
    color: #e8e0d0 !important;
    background: #141414 !important;
}
[data-testid="stTabBar"] button[aria-selected="true"] {
    color: #f5a623 !important;
    border-bottom: 2px solid #f5a623 !important;
    background: #111 !important;
}
[data-testid="stTabBar"] [role="presentation"] { display: none !important; }

/* ── Content Area ── */
[data-testid="stTabsContent"] {
    background: #0a0a0a !important;
    padding: 4px 8px !important;
}

/* ── Section Header — Bloomberg section dividers ── */
.sec-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f5a623;
    border-bottom: 1px solid #1a1a1a;
    padding-bottom: 2px;
    margin-bottom: 4px;
    margin-top: 8px;
}
.sec-header:first-child { margin-top: 0; }

/* ── Ticker Cards ── */
.ticker-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 1px;
    background: #1a1a1a;
    border: 1px solid #1a1a1a;
    margin-bottom: 6px;
}
.ticker-card {
    background: #0c0c0c;
    padding: 4px 8px;
    cursor: default;
    transition: background 0.08s;
}
.ticker-card:hover { background: #111; }
.ticker-card .t-symbol {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    color: #f5a623;
    letter-spacing: 0.08em;
}
.ticker-card .t-name {
    font-size: 8px;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ticker-card .t-price {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: #e8e0d0;
    line-height: 1.2;
}
.ticker-card .t-change {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 500;
}
.ticker-card .t-change.up { color: #00c853; }
.ticker-card .t-change.down { color: #ff3d3d; }
.ticker-card .t-change.flat { color: #555; }

/* ── Data Table — Bloomberg ultra-dense ── */
.bbg-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    line-height: 1.3;
}
.bbg-table thead tr {
    border-bottom: 1px solid #222;
}
.bbg-table thead th {
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #555;
    text-align: right;
    padding: 2px 5px;
    white-space: nowrap;
    position: sticky;
    top: 0;
    background: #0a0a0a;
}
.bbg-table thead th:first-child { text-align: left; }
.bbg-table tbody tr {
    border-bottom: 1px solid #0e0e0e;
    transition: background 0.05s;
}
.bbg-table tbody tr:hover { background: #0f0f0f; }
.bbg-table tbody td {
    padding: 2px 5px;
    text-align: right;
    color: #999;
    font-size: 10px;
    white-space: nowrap;
}
.bbg-table tbody td:first-child {
    text-align: left;
    color: #f5a623;
    font-weight: 500;
}

/* ── KPI Strip — Bloomberg top bar ── */
.kpi-strip {
    display: flex;
    gap: 1px;
    background: #1a1a1a;
    border: 1px solid #1a1a1a;
    margin-bottom: 6px;
}
.kpi-item {
    background: #0c0c0c;
    padding: 6px 12px;
    flex: 1;
    min-width: 90px;
}
.kpi-label {
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #555;
    margin-bottom: 2px;
}
.kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 16px;
    font-weight: 500;
    color: #e8e0d0;
    line-height: 1;
}
.kpi-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    margin-top: 1px;
}
.kpi-sub.up { color: #00c853; }
.kpi-sub.down { color: #ff3d3d; }
.kpi-sub.flat { color: #444; }

/* ── Divider ── */
.bbg-divider {
    border: none;
    border-top: 1px solid #141414;
    margin: 6px 0;
}

/* ── Loading spinner ── */
.stSpinner > div { border-top-color: #f5a623 !important; }

/* ── Plotly chart bg ── */
.js-plotly-plot .plotly { background: transparent !important; }

/* ── Streamlit layout density ── */
[data-testid="stHorizontalBlock"] { gap: 4px !important; }
[data-testid="column"] { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0.15rem !important; }

/* ── Scrollbar — thin ── */
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #222; border-radius: 1px; }
::-webkit-scrollbar-thumb:hover { background: #333; }

/* ── Text input ── */
.stTextInput > div > div > input {
    background: #0c0c0c !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    color: #e8e0d0 !important;
    padding: 3px 6px !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #111 !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px !important;
    color: #f5a623 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 4px 12px !important;
}
.stButton > button:hover {
    background: #1a1a1a !important;
    border-color: #f5a623 !important;
}

/* ── Selectbox ── */
.stSelectbox label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px !important;
    color: #444 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
.stSelectbox > div > div {
    background: #0c0c0c !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    color: #888 !important;
}

/* Sub-tabs */
[data-testid="stTabBar"] [data-baseweb="tab-list"] {
    background: transparent !important;
}

/* ── Code blocks (for debug) ── */
.stCodeBlock {
    font-size: 9px !important;
}
pre {
    background: #0c0c0c !important;
    border: 1px solid #1a1a1a !important;
    font-size: 9px !important;
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
    ART {now_ar.strftime('%H:%M:%S')} &nbsp;·&nbsp; ET {now_et.strftime('%H:%M:%S')} &nbsp;·&nbsp; {now_ar.strftime('%d %b %Y').upper()}
  </span>
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
