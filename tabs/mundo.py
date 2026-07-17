"""
MUNDO — 9-Panel Grid (equity-focused)
  Row 1: ETFs Países | ETFs Sectores SPDR | ETFs Industrias
  Row 2: Stocks #1-13 | #14-26 | #27-39
  Row 3: Stocks #40-52 | #53-65 | #66-78
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import fmt_price, fmt_change, HEADERS, _get_closes, get_finviz_screener, _finviz_cache_bucket

TTL = 60


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _pct_html(val):
    if val is None or val == "—":
        return '<span style="color:#555">—</span>'
    try:
        v = float(str(val).replace("%","").replace(",",".").strip())
        c = "#00ff41" if v > 0 else ("#ff3b3b" if v < 0 else "#555")
        s = "+" if v >= 0 else ""
        a = "▲" if v >= 0 else "▼"
        return f'<span style="color:{c};font-weight:bold">{a} {s}{v:.2f}%</span>'
    except:
        return f'<span style="color:#555">{val}</span>'


def _panel_html(title, headers, rows_html, max_height=340):
    ths = "".join(f"<th>{h}</th>" for h in headers)
    return f"""<div style="border:1px solid #333;background:#000;height:{max_height}px;display:flex;flex-direction:column;overflow:hidden">
  <div style="background:#111;color:#ff6600;font-size:9px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;padding:3px 8px;border-bottom:1px solid #ff6600;flex-shrink:0">{title}</div>
  <div style="overflow-y:auto;flex:1">
    <table class="t" style="border-collapse:collapse;width:100%">
      <thead><tr style="position:sticky;top:0;z-index:2;background:#111">{ths}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════════
#  ETF DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

COUNTRY_ETFS = {
    "SPY":  "🇺🇸 USA",
    "EWC":  "🇨🇦 Canada",
    "EWW":  "🇲🇽 México",
    "EWZ":  "🇧🇷 Brasil",
    "ECH":  "🇨🇱 Chile",
    "ARGT": "🇦🇷 Argentina",
    "COLO": "🇨🇴 Colombia",
    "EWG":  "🇩🇪 Alemania",
    "EWU":  "🇬🇧 UK",
    "EWQ":  "🇫🇷 Francia",
    "EWI":  "🇮🇹 Italia",
    "EWL":  "🇨🇭 Suiza",
    "EWP":  "🇪🇸 España",
    "EPOL": "🇵🇱 Polonia",
    "TUR":  "🇹🇷 Turquía",
    "EZA":  "🇿🇦 Sudáfrica",
    "KSA":  "🇸🇦 Arabia S.",
    "EIS":  "🇮🇱 Israel",
    "MCHI": "🇨🇳 China",
    "EWJ":  "🇯🇵 Japón",
    "EWY":  "🇰🇷 Corea S.",
    "EWT":  "🇹🇼 Taiwan",
    "INDA": "🇮🇳 India",
    "EWA":  "🇦🇺 Australia",
    "EIDO": "🇮🇩 Indonesia",
    "EWS":  "🇸🇬 Singapur",
    "EWM":  "🇲🇾 Malasia",
    "THD":  "🇹🇭 Tailandia",
    "VNM":  "🇻🇳 Vietnam",
}

SECTOR_ETFS = {
    "XLK":  "Technology",
    "XLF":  "Financials",
    "XLV":  "Health Care",
    "XLE":  "Energy",
    "XLI":  "Industrials",
    "XLY":  "Cons. Discret.",
    "XLP":  "Cons. Staples",
    "XLB":  "Materials",
    "XLU":  "Utilities",
    "XLRE": "Real Estate",
    "XLC":  "Comm. Services",
}

INDUSTRY_ETFS = {
    "ITA":  "Aerospace/Def",
    "IBB":  "Biotech",
    "KBE":  "Banks",
    "XHB":  "Homebuilders",
    "SMH":  "Semiconductors",
    "HACK": "Cybersecurity",
    "BOTZ": "Robotics/AI",
    "ARKK": "Innovation",
    "XOP":  "Oil Explor.",
    "GDX":  "Gold Miners",
    "SIL":  "Silver Miners",
    "XME":  "Metals/Mining",
    "JETS": "Airlines",
    "BITE": "Food/Bev",
    "ITB":  "Construction",
    "IYT":  "Transport",
    "IGV":  "Software",
    "SOCL": "Social Media",
    "CIBR": "CyberSec+",
    "GAMR": "Video Games",
    "TAN":  "Solar",
    "LIT":  "Lithium/Batt",
    "KWEB": "China Internet",
    "XRT":  "Retail",
    "PBW":  "Clean Energy",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  YFINANCE BATCH — compatible con 0.2.58+ (MultiIndex field-first)
# ═══════════════════════════════════════════════════════════════════════════════

def _prev_close_fallback(sym: str) -> float | None:
    """Obtiene previousClose via fast_info — fallback cuando download devuelve < 2 filas."""
    try:
        fi = yf.Ticker(sym).fast_info
        return float(fi.get("previous_close") or fi.get("previousClose") or 0) or None
    except Exception:
        return None


@st.cache_data(ttl=TTL, show_spinner=False)
def _yf_batch(tickers: list):
    """
    Returns dict {ticker: {price, change_pct}} — robust para yfinance >= 0.2.58.
    Usa period='5d' para buffer ante feriados/baja liquidez.
    Fallback a fast_info.previous_close si download devuelve < 2 filas.
    """
    if not tickers:
        return {}
    n = len(tickers)
    try:
        raw = yf.download(
            tickers, period="5d", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )
        result = {}
        for sym in tickers:
            try:
                closes = _get_closes(raw, sym, n).dropna()
                if len(closes) >= 2:
                    price = float(closes.iloc[-1])
                    prev  = float(closes.iloc[-2])
                    chg   = (price - prev) / prev * 100
                elif len(closes) == 1:
                    price = float(closes.iloc[-1])
                    prev  = _prev_close_fallback(sym)
                    chg   = (price - prev) / prev * 100 if prev else 0.0
                else:
                    price = None
                    chg   = 0.0
                result[sym] = {"price": price, "change_pct": round(chg, 2)}
            except Exception:
                result[sym] = {"price": None, "change_pct": 0.0}
        return result
    except Exception:
        return {t: {"price": None, "change_pct": 0.0} for t in tickers}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCRAPE TOP 78 COMPANIES BY MARKET CAP
# ═══════════════════════════════════════════════════════════════════════════════

TOP78_FALLBACK = [
    ("NVDA", "NVIDIA"), ("AAPL", "Apple"), ("GOOG", "Alphabet"),
    ("MSFT", "Microsoft"), ("AMZN", "Amazon"), ("TSM", "TSMC"),
    ("META", "Meta"), ("AVGO", "Broadcom"), ("2222.SR", "Saudi Aramco"),
    ("TSLA", "Tesla"), ("BRK-B", "Berkshire H."), ("LLY", "Eli Lilly"),
    ("JPM", "JPMorgan"),
    # 14-26
    ("WMT", "Walmart"), ("TCEHY", "Tencent"),
    ("V", "Visa"), ("005930.KS", "Samsung"), ("ORCL", "Oracle"),
    ("XOM", "Exxon Mobil"), ("MA", "Mastercard"), ("JNJ", "J&J"),
    ("ASML", "ASML"), ("BAC", "Bank of America"), ("HD", "Home Depot"),
    ("PG", "Procter&Gamble"), ("ABBV", "AbbVie"), ("COST", "Costco"),
    # 27-39
    ("NFLX", "Netflix"), ("KO", "Coca-Cola"), ("CRM", "Salesforce"),
    ("SAP", "SAP"), ("BABA", "Alibaba"), ("AMD", "AMD"),
    ("MRK", "Merck"), ("NVO", "Novo Nordisk"), ("CVX", "Chevron"),
    ("PEP", "PepsiCo"), ("TMO", "Thermo Fisher"), ("SHEL", "Shell"),
    ("LIN", "Linde"),
    # 40-52
    ("WFC", "Wells Fargo"), ("CSCO", "Cisco"),
    ("ACN", "Accenture"), ("AZN", "AstraZeneca"), ("ADBE", "Adobe"),
    ("MCD", "McDonald's"), ("IBM", "IBM"), ("TXN", "Texas Inst."),
    ("GE", "GE Aerospace"), ("PM", "Philip Morris"), ("ISRG", "Intuitive Surg."),
    ("ABT", "Abbott"), ("NOW", "ServiceNow"),
    # 53-65
    ("QCOM", "Qualcomm"),
    ("DHR", "Danaher"), ("INTU", "Intuit"), ("AMGN", "Amgen"),
    ("DIS", "Disney"), ("CAT", "Caterpillar"), ("PDD", "PDD Holdings"),
    ("AMAT", "Applied Mat."), ("UBER", "Uber"), ("GS", "Goldman Sachs"),
    ("BX", "Blackstone"), ("AXP", "Amex"), ("T", "AT&T"),
    # 66-78
    ("LOW", "Lowe's"), ("MS", "Morgan Stanley"), ("SYK", "Stryker"),
    ("BKNG", "Booking"), ("MDLZ", "Mondelez"), ("VRTX", "Vertex"),
    ("BLK", "BlackRock"), ("PANW", "Palo Alto"), ("REGN", "Regeneron"),
    ("GILD", "Gilead"), ("CB", "Chubb"), ("MMC", "Marsh McL."),
    ("LRCX", "Lam Research"),
]

COMPANIES_PER_PANEL = 13


@st.cache_data(ttl=300, show_spinner=False)
def _scrape_top78():
    try:
        from bs4 import BeautifulSoup
        r = requests.get("https://companiesmarketcap.com/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")

        rows = soup.select("table tr")
        result = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue

            name_cell = cells[1]
            company_name = ""
            ticker = ""

            name_div = name_cell.find("div", class_="company-name")
            code_div = name_cell.find("div", class_="company-code")

            if name_div:
                company_name = name_div.get_text(strip=True)
            if code_div:
                ticker = code_div.get_text(strip=True)

            if not ticker:
                link = name_cell.find("a")
                if link:
                    text = link.get_text(strip=True)
                    parts = text.rsplit(None, 1)
                    if len(parts) >= 2:
                        company_name = parts[0].strip()
                        ticker = parts[1].strip()

            country_cell = cells[-1]
            country = country_cell.get_text(strip=True)

            if ticker and company_name:
                if len(company_name) > 16:
                    company_name = company_name[:14] + ".."
                result.append((ticker, company_name, country))

            if len(result) >= 78:
                break

        return result if len(result) >= 30 else None
    except Exception:
        return None


def _get_top_companies():
    scraped = _scrape_top78()
    if scraped:
        return scraped
    return [(t, n, "") for t, n in TOP78_FALLBACK]


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _build_etf_panel(etf_dict, quotes):
    rows = ""
    for ticker, desc in etf_dict.items():
        q = quotes.get(ticker, {})
        p = q.get("price")
        chg = q.get("change_pct", 0)
        rows += f'<tr><td>{ticker}</td><td style="color:#ffcc00">{fmt_price(p, 2)}</td><td>{_pct_html(chg)}</td><td class="mkt">{desc}</td></tr>'
    return rows


def _build_company_panel(companies, quotes, start_rank=1):
    rows = ""
    for i, entry in enumerate(companies):
        ticker = entry[0]
        name = entry[1]
        q = quotes.get(ticker, {})
        p = q.get("price")
        chg = q.get("change_pct", 0)
        rank = start_rank + i
        rows += f'<tr><td style="color:#555;font-size:9px">{rank}</td><td>{ticker}</td><td class="mkt">{name}</td><td style="color:#ffcc00">{fmt_price(p, 2)}</td><td>{_pct_html(chg)}</td></tr>'
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1: EQUITY GLOBAL — el grid de 9 paneles (contenido original de Mundo)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_equity_grid():
    N = COMPANIES_PER_PANEL  # 13

    with st.spinner(""):
        all_etf_tickers = list(COUNTRY_ETFS.keys()) + list(SECTOR_ETFS.keys()) + list(INDUSTRY_ETFS.keys())

        top = _get_top_companies()

        company_tickers = [t[0] for t in top]

        all_tickers = all_etf_tickers + company_tickers
        seen = set()
        unique_tickers = []
        for t in all_tickers:
            if t not in seen:
                seen.add(t)
                unique_tickers.append(t)

        quotes = _yf_batch(unique_tickers)

    # Build ETF panels
    r_countries  = _build_etf_panel(COUNTRY_ETFS,  quotes)
    r_sectors    = _build_etf_panel(SECTOR_ETFS,   quotes)
    r_industries = _build_etf_panel(INDUSTRY_ETFS, quotes)

    # Build company panels — 13 per panel
    r_co1 = _build_company_panel(top[0*N:1*N], quotes, 0*N + 1)
    r_co2 = _build_company_panel(top[1*N:2*N], quotes, 1*N + 1)
    r_co3 = _build_company_panel(top[2*N:3*N], quotes, 2*N + 1)
    r_co4 = _build_company_panel(top[3*N:4*N], quotes, 3*N + 1)
    r_co5 = _build_company_panel(top[4*N:5*N], quotes, 4*N + 1)
    r_co6 = _build_company_panel(top[5*N:6*N], quotes, 5*N + 1)

    PH = 340

    p1 = _panel_html("PAÍSES · ETFs iSHARES",  ["TICKER","PRECIO","% DIA","PAÍS"],     r_countries,  PH)
    p2 = _panel_html("SECTORES · SPDR",         ["TICKER","PRECIO","% DIA","SECTOR"],   r_sectors,    PH)
    p3 = _panel_html("INDUSTRIAS · ETFs",        ["TICKER","PRECIO","% DIA","INDUSTRIA"],r_industries, PH)

    p4 = _panel_html(f"STOCKS · #1-{N}",          ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co1, PH)
    p5 = _panel_html(f"STOCKS · #{N+1}-{2*N}",    ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co2, PH)
    p6 = _panel_html(f"STOCKS · #{2*N+1}-{3*N}",  ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co3, PH)

    p7 = _panel_html(f"STOCKS · #{3*N+1}-{4*N}",  ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co4, PH)
    p8 = _panel_html(f"STOCKS · #{4*N+1}-{5*N}",  ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co5, PH)
    p9 = _panel_html(f"STOCKS · #{5*N+1}-{6*N}",  ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co6, PH)

    grid_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:auto auto auto;gap:4px;margin-top:4px">
      <div>{p1}</div><div>{p2}</div><div>{p3}</div>
      <div>{p4}</div><div>{p5}</div><div>{p6}</div>
      <div>{p7}</div><div>{p8}</div><div>{p9}</div>
    </div>"""

    st.markdown(grid_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2: SCREENER — motor propio (Finviz Overview+Valuation+Financial merged)
#  Universo fijo: NASDAQ+NYSE, market cap >= $10B. Filtros finos (sector,
#  P/E, dividend yield) se aplican acá con pandas sobre los datos ya bajados
#  — no dependen de los códigos de filtro de Finviz.
# ═══════════════════════════════════════════════════════════════════════════════

_SCREENER_OVERVIEW_COLS  = ["Ticker","Company","Sector","Industry","Country",
                            "Market Cap","Price","Change","Volume"]
_SCREENER_VALUATION_COLS = ["Ticker","Company","Market Cap","P/E","Forward P/E","PEG",
                            "P/S","P/B","P/C","P/FCF","EPS This Y","EPS Next Y",
                            "EPS Past 5Y","EPS Next 5Y","Sales Past 5Y","Price","Change"]
_SCREENER_FINANCIAL_COLS = ["Ticker","Company","Market Cap","Dividend","ROA","ROE","ROIC",
                            "Curr R","Quick R","LTDebt/Eq","Debt/Eq","Gross M","Oper M",
                            "Profit M","Earnings","Price","Change"]

# Filtros finos "estilo Finviz Fundamental tab" — todos calculados con pandas
# sobre las columnas que ya bajamos (Overview+Valuation+Financial merged).
# Cada filtro ahora soporta rango (mín. y máx.) — 0 en cualquiera de los dos
# significa "sin límite" en esa punta.
# (columna_df, etiqueta, step)
_NUMERIC_FILTERS = [
    ("P/E",         "P/E",               1.0),
    ("Forward P/E", "Forward P/E",       1.0),
    ("PEG",         "PEG",               0.1),
    ("P/S",         "P/S",               0.5),
    ("P/B",         "P/B",               0.5),
    ("P/C",         "P/Cash",            1.0),
    ("P/FCF",       "P/FCF",             1.0),
    ("Dividend",    "Div. Yield %",      0.5),
    ("ROA",         "ROA %",             1.0),
    ("ROE",         "ROE %",             1.0),
    ("ROIC",        "ROIC %",            1.0),
    ("Curr R",      "Current Ratio",     0.1),
    ("Quick R",     "Quick Ratio",       0.1),
    ("LTDebt/Eq",   "LT Debt/Eq",        0.1),
    ("Debt/Eq",     "Debt/Eq",           0.1),
    ("Gross M",     "Gross Margin %",    1.0),
    ("Oper M",      "Oper Margin %",     1.0),
    ("Profit M",    "Profit Margin %",   1.0),
    ("Change",      "Change hoy %",      0.5),
]

_SUBNAV_CSS = """
<style>
  div[role="radiogroup"][aria-label="SECCIÓN"] button[data-selected="true"],
  div[role="radiogroup"][aria-label="VISTA"] button[data-selected="true"] {
    background: #1a0900 !important;
    color: #ff6600 !important;
    border-color: #ff6600 !important;
  }
</style>
"""


def _parse_num(s):
    try:
        return float(str(s).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _screener_filters(df: pd.DataFrame) -> pd.DataFrame:
    sectors    = sorted(df["Sector"].dropna().unique().tolist())   if "Sector" in df.columns else []
    industries = sorted(df["Industry"].dropna().unique().tolist()) if "Industry" in df.columns else []
    countries  = sorted(df["Country"].dropna().unique().tolist())  if "Country" in df.columns else []

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        sel_sectors = st.multiselect("Sector", sectors, default=[], key="scr_sector")
    with c2:
        sel_industries = st.multiselect("Industry", industries, default=[], key="scr_industry")
    with c3:
        sel_countries = st.multiselect("Country", countries, default=[], key="scr_country")

    out = df.copy()
    if sel_sectors:
        out = out[out["Sector"].isin(sel_sectors)]
    if sel_industries:
        out = out[out["Industry"].isin(sel_industries)]
    if sel_countries:
        out = out[out["Country"].isin(sel_countries)]

    vals = {}
    with st.expander("FILTROS", expanded=False):
        row_cols = None
        for i, (col, label, step) in enumerate(_NUMERIC_FILTERS):
            if i % 4 == 0:
                row_cols = st.columns(4)
            with row_cols[i % 4]:
                st.markdown(
                    f'<div style="color:#ff6600;font-size:11px;font-weight:bold;'
                    f'font-family:\'Courier New\',monospace;letter-spacing:1px;'
                    f'text-transform:uppercase;margin:8px 0 4px 0">{label}</div>',
                    unsafe_allow_html=True,
                )
                key_base = col.replace("/", "_").replace(" ", "_")
                mc1, mc2 = st.columns(2)
                with mc1:
                    st.markdown(
                        '<div style="color:#555;font-size:8px;font-weight:bold;'
                        'letter-spacing:1px;text-transform:uppercase;margin-bottom:1px">MÍN.</div>',
                        unsafe_allow_html=True,
                    )
                    vmin = st.number_input(
                        "mín.", value=0.0, step=step,
                        key=f"scr_num_{key_base}_min",
                        label_visibility="collapsed",
                    )
                with mc2:
                    st.markdown(
                        '<div style="color:#555;font-size:8px;font-weight:bold;'
                        'letter-spacing:1px;text-transform:uppercase;margin-bottom:1px">MÁX.</div>',
                        unsafe_allow_html=True,
                    )
                    vmax = st.number_input(
                        "máx.", value=0.0, step=step,
                        key=f"scr_num_{key_base}_max",
                        label_visibility="collapsed",
                    )
                vals[col] = (vmin, vmax)

    for col, label, step in _NUMERIC_FILTERS:
        vmin, vmax = vals.get(col, (0.0, 0.0))
        if col not in out.columns:
            continue
        if vmin == 0.0 and vmax == 0.0:
            continue
        num = out[col].apply(_parse_num)
        if vmin != 0.0:
            out = out[(num.notna()) & (num >= vmin)]
        if vmax != 0.0:
            out = out[(num.notna()) & (num <= vmax)]

    return out


def _render_dataframe(df: pd.DataFrame, cols: list):
    available = [c for c in cols if c in df.columns]
    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        height=560,
    )


def _render_screener():
    st.markdown(_SUBNAV_CSS, unsafe_allow_html=True)

    with st.spinner("Cargando screener (Finviz · NASDAQ+NYSE · Market Cap ≥ $10B)..."):
        data = get_finviz_screener(_finviz_cache_bucket())

    if isinstance(data, dict) and "error" in data:
        st.markdown(
            f'<p style="color:#555;font-family:Courier New;font-size:11px">'
            f'Screener error: {data["error"]}</p>',
            unsafe_allow_html=True
        )
        return
    if not isinstance(data, pd.DataFrame) or data.empty:
        st.markdown(
            '<p style="color:#555;font-family:Courier New;font-size:11px">'
            'Sin datos del screener.</p>',
            unsafe_allow_html=True
        )
        return

    st.markdown(
        '<div style="color:#ff6600;font-size:11px;font-weight:bold;'
        'letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #333;'
        'padding-bottom:4px;margin-bottom:10px;font-family:\'Courier New\',monospace">'
        'SCREENER</div>',
        unsafe_allow_html=True
    )

    filtered = _screener_filters(data)

    total = len(data)
    shown = len(filtered)
    pct = (shown / total * 100) if total else 0
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;background:#0a0a0a;'
        f'border:1px solid #333;padding:6px 10px;margin:8px 0 10px 0;'
        f'font-family:\'Courier New\',monospace">'
        f'<div style="color:#ff6600;font-size:9px;font-weight:bold;letter-spacing:1px;'
        f'text-transform:uppercase;white-space:nowrap">RESULTADOS</div>'
        f'<div style="color:#ffcc00;font-size:17px;font-weight:bold;line-height:1">{shown}</div>'
        f'<div style="color:#555;font-size:11px;white-space:nowrap">/ {total}</div>'
        f'<div style="flex:1;height:5px;background:#1a1a1a;border-radius:2px;overflow:hidden">'
        f'<div style="height:100%;width:{pct:.1f}%;background:#ff6600;border-radius:2px"></div>'
        f'</div>'
        f'<div style="color:#888;font-size:10px;white-space:nowrap">{pct:.0f}%</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    view_sel = st.segmented_control(
        "VISTA",
        options=["overview", "valuation", "financial"],
        format_func=lambda v: {"overview": "OVERVIEW", "valuation": "VALUATION",
                                "financial": "FINANCIAL"}[v],
        default="overview",
        key="scr_view",
        label_visibility="collapsed",
    )
    view = view_sel or st.session_state.get("_scr_view_last", "overview")
    st.session_state["_scr_view_last"] = view

    cols_map = {
        "overview": _SCREENER_OVERVIEW_COLS,
        "valuation": _SCREENER_VALUATION_COLS,
        "financial": _SCREENER_FINANCIAL_COLS,
    }
    _render_dataframe(filtered, cols_map[view])

    st.markdown(
        '<div style="color:#555;font-size:9px;font-family:Courier New;'
        'padding:6px 0;border-top:1px solid #1a1a1a;margin-top:6px">'
        'FUENTE: FINVIZ.COM · ACTUALIZACIÓN CADA 1H (10-18HS) / CONGELADO FUERA DE HORARIO · '
        'UNIVERSO FIJO: NASDAQ+NYSE, MARKET CAP ≥ $10B'
        '</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL — sub-navegación dentro de Mundo
#  NOTA: antes esto usaba st.tabs() anidado (Mundo > EQUITY/SCREENER > Screener >
#  OVERVIEW/VALUATION/FINANCIAL = 3 niveles de tabs anidados dentro del tab bar
#  principal de app.py). Eso causaba que el contenido de OTRAS pestañas
#  (Calendar, Graficadora) apareciera renderizado y visible debajo del Screener
#  en vez de quedar oculto — bug conocido de Streamlit con tabs anidados varios
#  niveles. Se reemplaza por st.segmented_control() (mismo patrón ya probado y
#  funcionando en Calendar), que no tiene ese problema.
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    st.markdown(_SUBNAV_CSS, unsafe_allow_html=True)
    section_sel = st.segmented_control(
        "SECCIÓN",
        options=["equity", "screener"],
        format_func=lambda v: "EQUITY GLOBAL" if v == "equity" else "SCREENER",
        default="equity",
        key="mundo_section",
        label_visibility="collapsed",
    )
    section = section_sel or st.session_state.get("_mundo_section_last", "equity")
    st.session_state["_mundo_section_last"] = section

    if section == "equity":
        _render_equity_grid()
    else:
        _render_screener()
