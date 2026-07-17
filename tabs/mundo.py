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
from data import fmt_price, fmt_change, HEADERS, _get_closes, get_finviz_screener

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


def _parse_num(s):
    try:
        return float(str(s).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _screener_filters(df: pd.DataFrame) -> pd.DataFrame:
    sectors = sorted(df["Sector"].dropna().unique().tolist()) if "Sector" in df.columns else []

    c1, c2, c3, c4 = st.columns([2, 1.3, 1.3, 3.4])
    with c1:
        sel_sectors = st.multiselect("Sector", sectors, default=[], key="scr_sector")
    with c2:
        pe_max = st.number_input("P/E máx.", min_value=0.0, value=0.0, step=1.0,
                                  key="scr_pe_max", help="0 = sin límite")
    with c3:
        div_min = st.number_input("Div. Yield mín. %", min_value=0.0, value=0.0, step=0.5,
                                   key="scr_div_min", help="0 = sin límite")

    out = df.copy()
    if sel_sectors:
        out = out[out["Sector"].isin(sel_sectors)]
    if pe_max > 0 and "P/E" in out.columns:
        pe_num = out["P/E"].apply(_parse_num)
        out = out[(pe_num.notna()) & (pe_num <= pe_max)]
    if div_min > 0 and "Dividend" in out.columns:
        div_num = out["Dividend"].apply(_parse_num)
        out = out[(div_num.notna()) & (div_num >= div_min)]

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
    with st.spinner("Cargando screener (Finviz · NASDAQ+NYSE · Market Cap ≥ $10B)..."):
        data = get_finviz_screener()

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
        f'<div style="color:{"#ff6600"};font-size:11px;font-weight:bold;'
        f'letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #333;'
        f'padding-bottom:4px;margin-bottom:10px;font-family:\'Courier New\',monospace">'
        f'SCREENER · NASDAQ+NYSE · MARKET CAP ≥ $10B · {len(data)} empresas</div>',
        unsafe_allow_html=True
    )

    filtered = _screener_filters(data)

    st.markdown(
        f'<div style="color:#888;font-size:10px;font-family:Courier New;'
        f'margin:6px 0 8px 0">MOSTRANDO {len(filtered)} DE {len(data)}</div>',
        unsafe_allow_html=True
    )

    subsubtabs = st.tabs(["OVERVIEW", "VALUATION", "FINANCIAL"])
    with subsubtabs[0]:
        _render_dataframe(filtered, _SCREENER_OVERVIEW_COLS)
    with subsubtabs[1]:
        _render_dataframe(filtered, _SCREENER_VALUATION_COLS)
    with subsubtabs[2]:
        _render_dataframe(filtered, _SCREENER_FINANCIAL_COLS)

    st.markdown(
        '<div style="color:#555;font-size:9px;font-family:Courier New;'
        'padding:6px 0;border-top:1px solid #1a1a1a;margin-top:6px">'
        'FUENTE: FINVIZ.COM · ACTUALIZACIÓN CADA 6 HORAS · '
        'UNIVERSO FIJO: NASDAQ+NYSE, MARKET CAP ≥ $10B'
        '</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL — sub-tabs dentro de Mundo
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    subtabs = st.tabs(["EQUITY GLOBAL", "SCREENER"])
    with subtabs[0]:
        _render_equity_grid()
    with subtabs[1]:
        _render_screener()
