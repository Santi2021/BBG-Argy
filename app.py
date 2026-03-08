"""
app.py — ARG Terminal · Entry point · CSS global · Layout principal
Bloomberg-style financial terminal for Argentine markets + US Macro
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

/* ── Header bar ── */
.bbg-header {
    background: #000; border-bottom: 2px solid #ff6600;
    padding: 4px 16px 6px 16px; display: flex; align-items: center;
    justify-content: space-between;
}
.bbg-logo { font-weight: bold; font-size: 18px; color: #ff6600; letter-spacing: 3px; }
.bbg-clock { font-size: 11px; color: #ff6600; text-align: right; }
.bbg-clock .dt { color: #fff; font-size: 12px; display: block; }

/* ── News ticker tape ── */
.ticker-row {
    display: flex;
    align-items: stretch;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    height: 22px;
}
.ticker-row-intl { background: #0a0a0a; border-bottom: 1px solid #1a1a1a; }
.ticker-row-arg  { background: #050505; border-bottom: 1px solid #333; }

.ticker-label {
    flex-shrink: 0;
    width: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 8px;
    font-weight: bold;
    letter-spacing: 1px;
    border-right: 1px solid #222;
}
.ticker-label-intl { color: #ff6600; background: #0f0800; }
.ticker-label-arg  { color: #00ff41; background: #000f00; }

.ticker-scroll {
    flex: 1;
    overflow: hidden;
    white-space: nowrap;
    line-height: 22px;
}
.ticker-scroll a { color: #ccc; text-decoration: none; }
.ticker-scroll a:hover { color: #fff; text-decoration: underline; }
.ticker-inner { display: inline-block; padding-left: 100%; }
.ticker-row-intl .ticker-inner { animation: tick-intl 220s linear infinite; }
.ticker-row-arg  .ticker-inner { animation: tick-arg  180s linear infinite; }
@keyframes tick-intl { 0% { transform: translateX(0); } 100% { transform: translateX(-100%); } }
@keyframes tick-arg  { 0% { transform: translateX(0); } 100% { transform: translateX(-100%); } }

/* ── Tabs ── */
[data-testid="stTabs"] { margin: 0 !important; padding: 0 !important; }
[data-testid="stTabBar"] {
    background: #000 !important; border-bottom: 1px solid #333 !important;
    padding: 0 !important; gap: 0 !important; margin-top: 0 !important;
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

[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:first-child {
    margin-top: 0 !important; padding-top: 0 !important;
}

/* ── Tables ── */
.sh { color:#ff6600; font-size:10px; font-weight:bold; letter-spacing:2px;
      text-transform:uppercase; border-bottom:1px solid #333;
      padding-bottom:3px; margin-bottom:4px; margin-top:8px; }

.t { width:100%; border-collapse:collapse; font-family:'Courier New',monospace; font-size:11px; }
.t thead tr { background:#111; }
.t thead th { color:#ff6600; font-size:8px; font-weight:bold; letter-spacing:1px;
              text-transform:uppercase; text-align:left; padding:2px 6px;
              border-bottom:1px solid #ff6600; white-space:nowrap; }
.t tbody tr { border-bottom:1px solid #0a0a0a; }
.t tbody tr:hover { background:#0a0a0a; }
.t tbody td { padding:2px 6px; text-align:left; color:#ccc; font-size:11px; white-space:nowrap; }
.t tbody td:first-child { color:#fff; font-weight:bold; }

.bbg-table { width:100%; border-collapse:collapse; font-family:'Courier New',monospace; font-size:11px; }
.bbg-table thead tr { background:#111; }
.bbg-table thead th { color:#ff6600; font-size:8px; font-weight:bold; letter-spacing:1px;
                      text-transform:uppercase; text-align:left; padding:2px 6px;
                      border-bottom:1px solid #ff6600; white-space:nowrap; }
.bbg-table tbody tr { border-bottom:1px solid #0a0a0a; }
.bbg-table tbody tr:hover { background:#0a0a0a; }
.bbg-table tbody td { padding:2px 6px; text-align:left; color:#ccc; font-size:11px; white-space:nowrap; }
.bbg-table tbody td:first-child { color:#fff; font-weight:bold; }

.sec-header { color:#ff6600; font-size:10px; font-weight:bold; letter-spacing:2px;
              text-transform:uppercase; border-bottom:1px solid #333;
              padding-bottom:3px; margin-bottom:4px; margin-top:8px; }

/* ── KPI strip ── */
.kpi-strip { display:flex; gap:1px; background:#333; border:1px solid #333; margin-bottom:10px; }
.kpi-item { background:#000; padding:5px 10px; flex:1; min-width:80px; }
.kpi-label { font-size:8px; font-weight:bold; letter-spacing:1px;
             text-transform:uppercase; color:#ff6600; font-family:'Courier New',monospace; }
.kpi-value { font-size:15px; font-weight:bold; color:#ffcc00; line-height:1.1;
             font-family:'Courier New',monospace; }
.kpi-sub   { font-size:9px; font-weight:bold; font-family:'Courier New',monospace; }
.kpi-sub.up   { color:#00ff41; }
.kpi-sub.down { color:#ff3b3b; }
.kpi-sub.flat { color:#555; }

/* ── Color helpers ── */
.up   { color: #00ff41 !important; }
.down { color: #ff3b3b !important; }
.flat { color: #555    !important; }
.price { color: #ffcc00 !important; }
.mkt   { color: #555; font-size: 9px; }

/* ── Footer ── */
.ft { border-top:1px solid #333; padding:6px 0; color:#333;
      font-size:9px; text-align:center; letter-spacing:1px; margin-top:8px; }

/* ── Misc ── */
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
    font-size:10px !important; font-weight:bold !important;
    color:#ff6600 !important; padding:3px 10px !important;
}
.stRadio > div { gap: 4px !important; }
.stRadio label { font-family:'Courier New',monospace !important; font-size:10px !important; color:#555 !important; }
.stRadio [aria-checked="true"] + div { color:#ff6600 !important; }
pre { background:#050505 !important; border:1px solid #222 !important; font-size:9px !important; }
[data-testid="stTabBar"] [data-baseweb="tab-list"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  HEADER + DUAL NEWS TICKER
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime
import pytz
from data import get_news_international, get_news_argentina

now_ar = datetime.now(pytz.timezone("America/Argentina/Buenos_Aires"))
now_et = datetime.now(pytz.timezone("America/New_York"))

SOURCE_COLORS = {
    "REUTERS":  "#ff6600",
    "CNBC":     "#00bfff",
    "FT":       "#f5a0a0",
    "INVESTING":"#ffcc00",
    "WSJ":      "#4ade80",
    "ÁMBITO":   "#00ff41",
    "BL LÍNEA": "#a855f7",
    "INFOBAE":  "#ff3b3b",
    "CRONISTA": "#60a5fa",
    "iPROF":    "#c084fc",
}

CLEAN_SUFFIXES = [
    " - Reuters", " - Financial Times", " - WSJ", " - El Cronista",
    " - bloomberglinea.com", " - bloomberg",
]

def _build_ticker_html(headlines, max_items=25):
    spans = []
    for h in headlines[:max_items]:
        src   = h.get("source", "")
        title = h.get("title", "").replace('"', '&quot;').replace("<", "&lt;").replace(">", "&gt;")
        link  = h.get("link", "")
        for sfx in CLEAN_SUFFIXES:
            title = title.replace(sfx, "")
        if len(title) > 100:
            title = title[:97] + "..."
        col      = SOURCE_COLORS.get(src, "#ff6600")
        src_span = f'<span style="color:{col};font-weight:bold;font-size:10px">{src}</span>'
        if link:
            title_span = f'<a href="{link}" target="_blank">{title}</a>'
        else:
            title_span = f'<span style="color:#ccc">{title}</span>'
        spans.append(f'{src_span}&nbsp;{title_span}')
    return '&nbsp;&nbsp;<span style="color:#333">│</span>&nbsp;&nbsp;'.join(spans)

intl_news = get_news_international()
arg_news  = get_news_argentina()
intl_html = _build_ticker_html(intl_news)
arg_html  = _build_ticker_html(arg_news)

st.markdown(f"""
<div style="margin-bottom:6px">
  <div class="bbg-header">
    <div class="bbg-logo">MARKETS TERMINAL</div>
    <div class="bbg-clock">ULTIMA ACTUALIZACION<span class="dt">{now_ar.strftime('%d/%m/%Y')} &nbsp; ART {now_ar.strftime('%H:%M:%S')} · ET {now_et.strftime('%H:%M:%S')}</span></div>
  </div>
  <div class="ticker-row ticker-row-intl">
    <div class="ticker-label ticker-label-intl">INTL</div>
    <div class="ticker-scroll"><div class="ticker-inner">{intl_html}</div></div>
  </div>
  <div class="ticker-row ticker-row-arg">
    <div class="ticker-label ticker-label-arg">ARG</div>
    <div class="ticker-scroll"><div class="ticker-inner">{arg_html}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════════════════════════

from tabs import overview, argentina, bonos, cer, futuros, mundo, watchlist, macro_us, calendar

tabs = st.tabs([
    "OVERVIEW",
    "ARGENTINA",
    "BONOS",
    "CER",
    "FUTUROS",
    "MUNDO",
    "MACRO US",
    "CALENDAR",
    "GRAFICADORA",
])

with tabs[0]: overview.render()
with tabs[1]: argentina.render()
with tabs[2]: bonos.render()
with tabs[3]: cer.render()
with tabs[4]: futuros.render()
with tabs[5]: mundo.render()
with tabs[6]: macro_us.render()
with tabs[7]: calendar.render()
with tabs[8]: watchlist.render()

st.markdown('<div class="ft">MARKET DATA — ALL RIGHTS RESERVED</div>', unsafe_allow_html=True)
