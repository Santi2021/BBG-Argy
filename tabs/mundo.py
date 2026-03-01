"""
MUNDO — 9-Panel Grid (equity-focused)
  Row 1: ETFs Países | ETFs Sectores SPDR | ETFs Industrias
  Row 2: Top #1-10 Market Cap | #11-20 | #21-30
  Row 3: Top #31-40 | #41-50 | #51-60
"""
import streamlit as st
import yfinance as yf
import requests
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import fmt_price, fmt_change, HEADERS

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

# Country ETFs — iShares MSCI single-country (+ SPY for US)
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

# Sector ETFs — State Street SPDR Select Sector
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

# Industry ETFs — diversified providers, no repeats with sector
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
#  YFINANCE BATCH QUOTES
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL, show_spinner=False)
def _yf_batch(tickers: list):
    """Returns dict {ticker: {price, change_pct}}"""
    if not tickers:
        return {}
    try:
        raw = yf.download(
            tickers, period="2d", interval="1d", group_by="ticker",
            auto_adjust=True, progress=False, threads=True,
        )
        result = {}
        for sym in tickers:
            try:
                if len(tickers) == 1:
                    closes = raw["Close"]
                else:
                    try:
                        closes = raw[sym]["Close"]
                    except (KeyError, TypeError):
                        closes = raw["Close"][sym]
                closes = closes.dropna()
                if len(closes) >= 2:
                    price = float(closes.iloc[-1])
                    prev = float(closes.iloc[-2])
                    chg = (price - prev) / prev * 100
                else:
                    price = float(closes.iloc[-1]) if len(closes) else None
                    chg = 0.0
                result[sym] = {"price": price, "change_pct": round(chg, 2)}
            except Exception:
                result[sym] = {"price": None, "change_pct": 0.0}
        return result
    except Exception:
        return {t: {"price": None, "change_pct": 0.0} for t in tickers}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCRAPE TOP 60 COMPANIES BY MARKET CAP
# ═══════════════════════════════════════════════════════════════════════════════

# Hardcoded top 60 as fallback (tickers from companiesmarketcap.com, Feb 2026)
TOP60_FALLBACK = [
    ("NVDA", "NVIDIA"), ("AAPL", "Apple"), ("GOOG", "Alphabet"),
    ("MSFT", "Microsoft"), ("AMZN", "Amazon"), ("TSM", "TSMC"),
    ("META", "Meta"), ("AVGO", "Broadcom"), ("2222.SR", "Saudi Aramco"),
    ("TSLA", "Tesla"), ("BRK-B", "Berkshire H."), ("LLY", "Eli Lilly"),
    ("JPM", "JPMorgan"), ("WMT", "Walmart"), ("TCEHY", "Tencent"),
    ("V", "Visa"), ("005930.KS", "Samsung"), ("ORCL", "Oracle"),
    ("XOM", "Exxon Mobil"), ("MA", "Mastercard"), ("JNJ", "J&J"),
    ("ASML", "ASML"), ("BAC", "Bank of America"), ("HD", "Home Depot"),
    ("PG", "Procter&Gamble"), ("ABBV", "AbbVie"), ("COST", "Costco"),
    ("NFLX", "Netflix"), ("KO", "Coca-Cola"), ("CRM", "Salesforce"),
    ("SAP", "SAP"), ("BABA", "Alibaba"), ("AMD", "AMD"),
    ("MRK", "Merck"), ("NVO", "Novo Nordisk"), ("CVX", "Chevron"),
    ("PEP", "PepsiCo"), ("TMO", "Thermo Fisher"), ("SHEL", "Shell"),
    ("LIN", "Linde"), ("WFC", "Wells Fargo"), ("CSCO", "Cisco"),
    ("ACN", "Accenture"), ("AZN", "AstraZeneca"), ("ADBE", "Adobe"),
    ("MCD", "McDonald's"), ("IBM", "IBM"), ("TXN", "Texas Inst."),
    ("GE", "GE Aerospace"), ("PM", "Philip Morris"), ("ISRG", "Intuitive Surg."),
    ("ABT", "Abbott"), ("NOW", "ServiceNow"), ("QCOM", "Qualcomm"),
    ("DHR", "Danaher"), ("INTU", "Intuit"), ("AMGN", "Amgen"),
    ("DIS", "Disney"), ("CAT", "Caterpillar"), ("PDD", "PDD Holdings"),
]


@st.cache_data(ttl=300, show_spinner=False)
def _scrape_top60():
    """Scrape top 60 companies from companiesmarketcap.com. Returns [(ticker, name, country), ...]"""
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

            # Name cell: contains company name and ticker
            name_cell = cells[1]
            company_name = ""
            ticker = ""

            # Ticker in small text or .company-code
            name_div = name_cell.find("div", class_="company-name")
            code_div = name_cell.find("div", class_="company-code")

            if name_div:
                company_name = name_div.get_text(strip=True)
            if code_div:
                ticker = code_div.get_text(strip=True)

            if not ticker:
                # Try from link text
                link = name_cell.find("a")
                if link:
                    text = link.get_text(strip=True)
                    # Pattern: "Company Name  TICKER"
                    parts = text.rsplit(None, 1)
                    if len(parts) >= 2:
                        company_name = parts[0].strip()
                        ticker = parts[1].strip()

            # Country cell (last)
            country_cell = cells[-1]
            country = country_cell.get_text(strip=True)

            # Price cell
            price_cell = cells[3]
            price_text = price_cell.get_text(strip=True).replace("$","").replace(",","")

            # Change cell
            chg_cell = cells[4]
            chg_text = chg_cell.get_text(strip=True).replace("%","")

            if ticker and company_name:
                # Shorten name
                if len(company_name) > 16:
                    company_name = company_name[:14] + ".."
                result.append((ticker, company_name, country))

            if len(result) >= 60:
                break

        return result if len(result) >= 30 else None
    except Exception:
        return None


def _get_top60():
    """Get top 60 companies — try scraping, fallback to hardcoded."""
    scraped = _scrape_top60()
    if scraped:
        return scraped
    # Fallback
    return [(t, n, "") for t, n in TOP60_FALLBACK]


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _build_etf_panel(etf_dict, quotes):
    """Build rows for ETF panel: TICKER | PRECIO | % DIA | DESC"""
    rows = ""
    for ticker, desc in etf_dict.items():
        q = quotes.get(ticker, {})
        p = q.get("price")
        chg = q.get("change_pct", 0)
        rows += f'<tr><td>{ticker}</td><td style="color:#ffcc00">{fmt_price(p, 2)}</td><td>{_pct_html(chg)}</td><td class="mkt">{desc}</td></tr>'
    return rows


def _build_company_panel(companies, quotes, start_rank=1):
    """Build rows for company panel: # | TICKER | NOMBRE | PRECIO | % DIA"""
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
#  RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    with st.spinner(""):
        # Collect all tickers needed
        all_etf_tickers = list(COUNTRY_ETFS.keys()) + list(SECTOR_ETFS.keys()) + list(INDUSTRY_ETFS.keys())

        # Get top 60 companies
        top60 = _get_top60()

        # Filter out non-US tickers that yfinance may struggle with
        # Keep all — yfinance handles most, missing ones just show "—"
        company_tickers = [t[0] for t in top60]

        # Batch download all quotes
        all_tickers = all_etf_tickers + company_tickers
        # Remove dupes while preserving order
        seen = set()
        unique_tickers = []
        for t in all_tickers:
            if t not in seen:
                seen.add(t)
                unique_tickers.append(t)

        quotes = _yf_batch(unique_tickers)

    # Build panels
    r_countries = _build_etf_panel(COUNTRY_ETFS, quotes)
    r_sectors = _build_etf_panel(SECTOR_ETFS, quotes)
    r_industries = _build_etf_panel(INDUSTRY_ETFS, quotes)

    r_co1 = _build_company_panel(top60[0:10], quotes, 1)
    r_co2 = _build_company_panel(top60[10:20], quotes, 11)
    r_co3 = _build_company_panel(top60[20:30], quotes, 21)
    r_co4 = _build_company_panel(top60[30:40], quotes, 31)
    r_co5 = _build_company_panel(top60[40:50], quotes, 41)
    r_co6 = _build_company_panel(top60[50:60], quotes, 51)

    PH = 340

    p1 = _panel_html("PAÍSES · ETFs iSHARES", ["TICKER","PRECIO","% DIA","PAÍS"], r_countries, PH)
    p2 = _panel_html("SECTORES · SPDR", ["TICKER","PRECIO","% DIA","SECTOR"], r_sectors, PH)
    p3 = _panel_html("INDUSTRIAS · ETFs", ["TICKER","PRECIO","% DIA","INDUSTRIA"], r_industries, PH)

    p4 = _panel_html("TOP MARKET CAP · #1-10", ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co1, PH)
    p5 = _panel_html("TOP MARKET CAP · #11-20", ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co2, PH)
    p6 = _panel_html("TOP MARKET CAP · #21-30", ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co3, PH)

    p7 = _panel_html("TOP MARKET CAP · #31-40", ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co4, PH)
    p8 = _panel_html("TOP MARKET CAP · #41-50", ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co5, PH)
    p9 = _panel_html("TOP MARKET CAP · #51-60", ["#","TICKER","NOMBRE","PRECIO","% DIA"], r_co6, PH)

    grid_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:auto auto auto;gap:4px;margin-top:4px">
      <div>{p1}</div><div>{p2}</div><div>{p3}</div>
      <div>{p4}</div><div>{p5}</div><div>{p6}</div>
      <div>{p7}</div><div>{p8}</div><div>{p9}</div>
    </div>"""

    st.markdown(grid_html, unsafe_allow_html=True)
