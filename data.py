"""
Centralized data fetching — all sources, cached at 60s.
Sources:
  - data912 (Milton)  → acciones, CEDEARs, MEP/CCL, bonos ARS
  - BondTerminal      → bonos USD soberanos/corp/prov, riesgo país
  - Ecovalores        → futuros dólar, curva rendimientos, bonos ARS
  - dolarapi.com      → tipos de cambio (blue, oficial, tarjeta…)
  - yfinance          → índices globales, commodities, sectores US
"""

import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,*/*",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

TTL = 60  # seconds

# ── dolarapi ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=TTL, show_spinner=False)
def get_dolar():
    try:
        r = requests.get("https://dolarapi.com/v1/dolares", headers=HEADERS, timeout=8)
        data = r.json()
        result = {}
        for d in data:
            key = d.get("casa", "").lower()
            result[key] = {
                "nombre": d.get("nombre", key),
                "compra": d.get("compra"),
                "venta": d.get("venta"),
            }
        return result
    except Exception as e:
        return {"error": str(e)}


# ── BondTerminal ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=TTL, show_spinner=False)
def get_bondterminal_bootstrap():
    try:
        r = requests.get("https://bondterminal.com/api/landing/bootstrap",
                         headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=TTL, show_spinner=False)
def get_riesgo_pais():
    try:
        r = requests.get("https://bondterminal.com/api/riesgo-pais",
                         headers=HEADERS, timeout=8)
        d = r.json()
        return {
            "bps": round(d.get("weightedSpreadBps", 0)),
            "bps_ambito": d.get("ambitoValue"),
            "delta_1d": round(d.get("deltas", {}).get("oneDay", 0), 1),
            "delta_1w": round(d.get("deltas", {}).get("oneWeek", 0), 1),
            "delta_1m": round(d.get("deltas", {}).get("oneMonth", 0), 1),
            "data_quality": d.get("dataQuality", ""),
            "as_of": d.get("asOf", ""),
        }
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=TTL, show_spinner=False)
def get_live_prices_bt():
    try:
        r = requests.get("https://bondterminal.com/api/bonds/live-prices",
                         headers=HEADERS, timeout=10)
        d = r.json()
        return d.get("prices", {}), d.get("changes", {})
    except Exception:
        return {}, {}


# ── data912 ───────────────────────────────────────────────────────────────────

BASE912 = "https://data912.com/live"

@st.cache_data(ttl=TTL, show_spinner=False)
def get_912(endpoint: str):
    try:
        r = requests.get(f"{BASE912}/{endpoint}", headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        return []


def get_acciones():     return get_912("arg_stocks")
def get_cedears():      return get_912("arg_cedears")
def get_mep():          return get_912("mep")
def get_ccl():          return get_912("ccl")
def get_bonos_ars():    return get_912("arg_bonds")
def get_letras():       return get_912("arg_notes")
def get_adrs():         return get_912("usa_adrs")


# ── Ecovalores (scraping HTML estático) ───────────────────────────────────────

ECO_URL = "https://bonos.ecovalores.com.ar//eco/"

@st.cache_data(ttl=TTL, show_spinner=False)
def get_ecovalores_raw():
    try:
        r = requests.get(ECO_URL, headers=HEADERS, timeout=12)
        r.encoding = "latin-1"
        return r.text
    except Exception:
        return ""


@st.cache_data(ttl=TTL, show_spinner=False)
def get_futuros_dolar():
    html = get_ecovalores_raw()
    if not html:
        return pd.DataFrame()
    try:
        soup = BeautifulSoup(html, "html.parser")
        tables = pd.read_html(html, flavor="lxml")
        for df in tables:
            cols = [str(c).lower() for c in df.columns if isinstance(c, str)]
            flat = " ".join(str(c) for c in df.columns.tolist()).lower()
            if "tna" in flat or "pase" in flat:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(-1)
                df = df.dropna(how="all")
                df.columns = [str(c).strip() for c in df.columns]
                needed = [c for c in df.columns if any(k in c.lower() for k in ["especie","ltimo","tna","pase","var"])]
                if len(needed) >= 3:
                    sub = df[needed].copy()
                    sub = sub[sub.iloc[:,0].str.match(r"[A-Z]{3}\d{2}", na=False)]
                    sub.columns = ["Especie","Último","Var.Día","TNA%","Pase%"][:len(sub.columns)]
                    return sub.reset_index(drop=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=TTL, show_spinner=False)
def get_curva_rendimientos():
    """Returns (data_cer, data_usd) as lists of [duration, yield, label]"""
    html = get_ecovalores_raw()
    if not html:
        return [], []
    try:
        m_cer = re.search(r'fut_data00\s*=\s*(\[\[.*?\]\])\s*;', html, re.DOTALL)
        m_usd = re.search(r'fut_data02\s*=\s*(\[\[.*?\]\])\s*;', html, re.DOTALL)

        def parse_js_array(match):
            if not match:
                return []
            import json
            try:
                return json.loads(match.group(1))
            except Exception:
                return []

        return parse_js_array(m_cer), parse_js_array(m_usd)
    except Exception:
        return [], []


@st.cache_data(ttl=TTL, show_spinner=False)
def get_tasas_implicitas():
    """Returns list of [days, tna_pct, label] for futures TNA curve"""
    html = get_ecovalores_raw()
    if not html:
        return []
    try:
        m = re.search(r'var data00\s*=\s*(\[\[.*?\]\])\s*;', html, re.DOTALL)
        if not m:
            return []
        import json
        return json.loads(m.group(1))
    except Exception:
        return []


@st.cache_data(ttl=TTL, show_spinner=False)
def get_eco_bonos_ars():
    """Bonos ARS (CER, tasa fija, dollar linked) from Ecovalores"""
    html = get_ecovalores_raw()
    if not html:
        return {}
    result = {}
    try:
        tables = pd.read_html(html, flavor="lxml")
        categories = {
            "CER": ["cer", "ajustados"],
            "TasaFija": ["tasa fija"],
            "DollarLinked": ["dollar linked", "dólar linked"],
            "BOPREAL": ["bopreal"],
            "USDduro": ["bonos en dólares d"],
        }
        for df in tables:
            flat_header = " ".join(str(c) for c in df.columns).lower()
            for cat, keywords in categories.items():
                if any(k in flat_header for k in keywords):
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(-1)
                    df.columns = [str(c).strip() for c in df.columns]
                    df = df.dropna(how="all")
                    result[cat] = df.reset_index(drop=True)
                    break
        return result
    except Exception:
        return {}


# ── yfinance — índices globales ───────────────────────────────────────────────

WORLD_TICKERS = {
    "S&P 500":   "^GSPC",
    "NASDAQ":    "^IXIC",
    "DOW":       "^DJI",
    "VIX":       "^VIX",
    "DAX":       "^GDAXI",
    "FTSE 100":  "^FTSE",
    "NIKKEI":    "^N225",
    "HANG SENG": "^HSI",
    "MERVAL":    "^MERV",
    "BOVESPA":   "^BVSP",
    "IPC MEX":   "^MXX",
}

COMMODITY_TICKERS = {
    "GOLD":      "GC=F",
    "SILVER":    "SI=F",
    "WTI":       "CL=F",
    "BRENT":     "BZ=F",
    "NAT GAS":   "NG=F",
    "COPPER":    "HG=F",
    "SOJA":      "ZS=F",
    "MAIZ":      "ZC=F",
    "TRIGO":     "ZW=F",
}

SECTOR_ETFS = {
    "Tech":        "XLK",
    "Financials":  "XLF",
    "Health":      "XLV",
    "Energy":      "XLE",
    "Industrials": "XLI",
    "ConsDisc":    "XLY",
    "ConsStap":    "XLP",
    "Materials":   "XLB",
    "Utilities":   "XLU",
    "RealEstate":  "XLRE",
    "CommSvcs":    "XLC",
}

FX_TICKERS = {
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "JPY=X",
    "GBP/USD": "GBPUSD=X",
    "USD/BRL": "BRL=X",
    "USD/MXN": "MXN=X",
    "USD/CLP": "CLP=X",
    "DXY":     "DX-Y.NYB",
}


@st.cache_data(ttl=TTL, show_spinner=False)
def get_yf_quotes(tickers_dict: dict):
    """Batch download current quotes. Returns dict: {name: {price, change_pct, prev_close}}"""
    symbols = list(tickers_dict.values())
    names   = list(tickers_dict.keys())
    try:
        raw = yf.download(
            symbols,
            period="2d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        result = {}
        for name, sym in zip(names, symbols):
            try:
                if len(symbols) == 1:
                    closes = raw["Close"]
                else:
                    closes = raw["Close"][sym]
                closes = closes.dropna()
                if len(closes) >= 2:
                    price = float(closes.iloc[-1])
                    prev  = float(closes.iloc[-2])
                    chg   = (price - prev) / prev * 100
                else:
                    price = float(closes.iloc[-1]) if len(closes) else None
                    chg   = 0.0
                result[name] = {"price": price, "change_pct": round(chg, 2), "symbol": sym}
            except Exception:
                result[name] = {"price": None, "change_pct": 0.0, "symbol": sym}
        return result
    except Exception as e:
        return {n: {"price": None, "change_pct": 0.0} for n in names}


def fmt_price(val, decimals=2):
    if val is None:
        return "N/A"
    if val >= 1000:
        return f"{val:,.0f}"
    return f"{val:,.{decimals}f}"


def fmt_change(chg):
    if chg is None:
        return "—", "flat"
    sign = "+" if chg >= 0 else ""
    css  = "up" if chg > 0.005 else ("down" if chg < -0.005 else "flat")
    return f"{sign}{chg:.2f}%", css
