import streamlit as st

st.set_page_config(
    page_title="Markets Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #000 !important;
    color: #ccc !important;
    font-family: 'Courier New', Courier, monospace !important;
    font-size: 12px !important;
}

#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

[data-testid="stAppViewContainer"] { padding: 0 !important; }
[data-testid="stAppViewContainer"] > div { padding-top: 0 !important; margin-top: 0 !important; }
[data-testid="block-container"] { padding: 0 8px !important; max-width: 100% !important; }
.main .block-container { padding: 0 8px !important; max-width: 100% !important; }
.main { padding-top: 0 !important; }
[data-testid="stMain"] { padding-top: 0 !important; }
[data-testid="stMainBlockContainer"] { padding-top: 0 !important; }
.appview-container { padding-top: 0 !important; }
.stApp > div:first-child { padding-top: 0 !important; }
div[data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; }

.bbg-header {
    background: #000; border-bottom: 2px solid #ff6600;
    padding: 4px 16px 6px 16px; display: flex; align-items: center;
    justify-content: space-between; position: sticky; top: 0; z-index: 1000;
    margin-bottom: 0;
}
.bbg-logo { font-weight: bold; font-size: 18px; color: #ff6600; letter-spacing: 3px; }
.bbg-clock { font-size: 11px; color: #ff6600; text-align: right; }
.bbg-clock .dt { color: #fff; font-size: 12px; display: block; }

[data-testid="stTabs"] { margin: 0 !important; padding: 0 !important; }
[data-testid="stTabBar"] {
    background: #000 !important; border-bottom: 1px solid #333 !important;
    padding: 0 !important; gap: 0 !important;
    margin-top: 0 !important;
}
[data-testid="stTabBar"] button {
    font-family: 'Courier New', monospace !important;
    font-size: 10px !important; font-weight: bold !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
    color: #555 !important; background: transparent !important;
    border: none !important; border-bottom: 2px solid transparent !important;
    border-radius: 0 !important; padding: 3px 10px !important;
    height: 26px !important; white-space: nowrap !important;
}
[data-testid="stTabBar"] button:hover { color: #fff !important; background: #0a0a0a !important; }
[data-testid="stTabBar"] button[aria-selected="true"] {
    color: #ff6600 !important; border-bottom: 2px solid #ff6600 !important;
}
[data-testid="stTabBar"] [role="presentation"] { display: none !important; }
[data-testid="stTabsContent"] { background: #000 !important; padding: 4px 4px !important; }

/* Eliminate extra spacing between header and tabs */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

.sh { color:#ff6600; font-size:10px; font-weight:bold; letter-spacing:2px; text-transform:uppercase; border-bottom:1px solid #333; padding-bottom:3px; margin-bottom:4px; margin-top:8px; }

.t { width:100%; border-collapse:collapse; font-family:'Courier New',monospace; font-size:11px; }
.t thead tr { background:#111; }
.t thead th { color:#ff6600; font-size:8px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; text-align:left; padding:2px 6px; border-bottom:1px solid #ff6600; white-space:nowrap; }
.t tbody tr { border-bottom:1px solid #0a0a0a; }
.t tbody tr:hover { background:#0a0a0a; }
.t tbody td { padding:2px 6px; text-align:left; color:#ccc; font-size:11px; white-space:nowrap; }
.t tbody td:first-child { color:#fff; font-weight:bold; }

/* Keep bbg-table alias */
.bbg-table { width:100%; border-collapse:collapse; font-family:'Courier New',monospace; font-size:11px; }
.bbg-table thead tr { background:#111; }
.bbg-table thead th { color:#ff6600; font-size:8px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; text-align:left; padding:2px 6px; border-bottom:1px solid #ff6600; white-space:nowrap; }
.bbg-table tbody tr { border-bottom:1px solid #0a0a0a; }
.bbg-table tbody tr:hover { background:#0a0a0a; }
.bbg-table tbody td { padding:2px 6px; text-align:left; color:#ccc; font-size:11px; white-space:nowrap; }
.bbg-table tbody td:first-child { color:#fff; font-weight:bold; }
.sec-header { color:#ff6600; font-size:10px; font-weight:bold; letter-spacing:2px; text-transform:uppercase; border-bottom:1px solid #333; padding-bottom:3px; margin-bottom:4px; margin-top:8px; }

.kpi-strip { display:flex; gap:1px; background:#333; border:1px solid #333; margin-bottom:4px; }
.kpi-item { background:#000; padding:5px 10px; flex:1; min-width:80px; }
.kpi-label { font-size:8px; font-weight:bold; letter-spacing:1px; text-transform:uppercase; color:#ff6600; }
.kpi-value { font-size:15px; font-weight:bold; color:#ffcc00; line-height:1.1; }
.kpi-sub { font-size:9px; font-weight:bold; }
.kpi-sub.up { color:#00ff41; } .kpi-sub.down { color:#ff3b3b; } .kpi-sub.flat { color:#555; }

.up { color: #00ff41 !important; } .down { color: #ff3b3b !important; }
.flat { color: #555 !important; } .price { color: #ffcc00 !important; }
.mkt { color: #555; font-size: 9px; }

.ft { border-top:1px solid #333; padding:6px 0; color:#333; font-size:9px; text-align:center; letter-spacing:1px; margin-top:8px; }

[data-testid="stHorizontalBlock"] { gap: 4px !important; }
[data-testid="column"] { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0.05rem !important; }

.stSpinner > div { border-top-color: #ff6600 !important; }
.js-plotly-plot .plotly { background: transparent !important; }
::-webkit-scrollbar { width:3px; height:3px; }
::-webkit-scrollbar-track { background:#000; }
::-webkit-scrollbar-thumb { background:#333; }

.stTextInput > div > div > input {
    background:#000 !important; border:1px solid #333 !important;
    border-radius:0 !important; font-family:'Courier New',monospace !important;
    font-size:11px !important; color:#fff !important; padding:3px 6px !important;
}
.stButton > button {
    background:#111 !important; border:1px solid #ff6600 !important;
    border-radius:0 !important; font-family:'Courier New',monospace !important;
    font-size:10px !important; font-weight:bold !important; color:#ff6600 !important;
    padding:3px 10px !important;
}
pre { background:#050505 !important; border:1px solid #222 !important; font-size:9px !important; }
[data-testid="stTabBar"] [data-baseweb="tab-list"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

from datetime import datetime
import pytz

now_ar = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
now_et = datetime.now(pytz.timezone("America/New_York"))

st.markdown(f"""
<div class="bbg-header">
  <div class="bbg-logo">MARKETS TERMINAL</div>
  <div class="bbg-clock">ULTIMA ACTUALIZACION<span class="dt">{now_ar.strftime('%d/%m/%Y')} &nbsp; ART {now_ar.strftime('%H:%M:%S')} · ET {now_et.strftime('%H:%M:%S')}</span></div>
</div>
""", unsafe_allow_html=True)

from tabs import overview, argentina, bonos, futuros, mundo, watchlist

tabs = st.tabs(["OVERVIEW", "🇦🇷 ARGENTINA", "BONOS", "FUTUROS & CURVA", "MUNDO", "WATCHLIST"])

with tabs[0]: overview.render()
with tabs[1]: argentina.render()
with tabs[2]: bonos.render()
with tabs[3]: futuros.render()
with tabs[4]: mundo.render()
with tabs[5]: watchlist.render()

st.markdown('<div class="ft">DATA VIA YAHOO FINANCE / DATA912 / BONDTERMINAL / DOLARAPI / ECOVALORES — SOLO FINES INFORMATIVOS</div>', unsafe_allow_html=True)
