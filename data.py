"""
Centralized data fetching — all sources, cached at 60s.
Sources:
  - data912 (Milton)  → acciones, CEDEARs, MEP/CCL, bonos ARS
  - BondTerminal      → bonos USD soberanos/corp/prov
  - ArgentinaDatos    → riesgo país EMBI (JP Morgan)
  - Ecovalores        → futuros dólar, curva rendimientos, bonos ARS
  - dolarapi.com      → tipos de cambio (blue, oficial, tarjeta…)
  - yfinance          → índices globales, commodities, sectores US
  - IOL               → cauciones (scraping)
  - PPI               → letras ARS con TNA real (portfoliopersonal.com)
  - RSS feeds         → news ticker (Reuters, CNBC, FT, WSJ, Ámbito, etc.)
  - Investing.com     → calendario económico semanal (US + ARG)
"""

import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import re
import feedparser
import json as _json
import time as _time
from datetime import datetime as _dt, timedelta as _td
from itertools import zip_longest
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,*/*",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

TTL = 60  # seconds


# ═══════════════════════════════════════════════════════════════════════════════
#  YFINANCE COMPAT — Robust MultiIndex accessor for yfinance >= 0.2.58
# ═══════════════════════════════════════════════════════════════════════════════

def _get_closes(raw: pd.DataFrame, sym: str, n_tickers: int) -> pd.Series:
    if n_tickers == 1:
        if isinstance(raw.columns, pd.MultiIndex):
            return raw["Close"].iloc[:, 0]
        return raw["Close"]
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = raw.columns.get_level_values(0).tolist()
        if "Close" in level0:
            return raw["Close"][sym]
        else:
            return raw[sym]["Close"]
    else:
        return raw[sym]


# ═══════════════════════════════════════════════════════════════════════════════
#  FIELD NORMALIZATION — data912 returns varying field names
# ═══════════════════════════════════════════════════════════════════════════════

FIELD_ALIASES = {
    "ticker":     ["ticker", "symbol", "especie", "Ticker", "Symbol", "Especie", "name", "s"],
    "last":       ["last", "price", "ultimo", "Last", "Price", "Ultimo", "c", "close", "px", "lastPrice", "last_price"],
    "bid":        ["bid", "Bid", "bid_price", "bidPrice", "b"],
    "ask":        ["ask", "Ask", "ask_price", "askPrice", "offer", "a"],
    "pct_change": ["pct_change", "change_pct", "pctChange", "changePct", "variation",
                   "var", "change", "d", "percentChange", "percent_change", "pct"],
    "volume":     ["volume", "vol", "Volume", "Vol", "v", "totalVolume"],
    "mark":       ["mark", "Mark", "mid", "midPrice"],
    "open":       ["open", "Open", "o"],
    "high":       ["high", "High", "h"],
    "low":        ["low", "Low", "l"],
    "prev_close": ["prev_close", "prevClose", "previousClose", "pc"],
}


def _normalize_item(item: dict) -> dict:
    if not isinstance(item, dict):
        return item
    normalized = {}
    used_keys = set()
    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in item and alias not in used_keys:
                normalized[canonical] = item[alias]
                used_keys.add(alias)
                break
    for k, v in item.items():
        if k not in used_keys:
            normalized[k] = v
    return normalized


def _normalize_list(data: list) -> list:
    if not data or not isinstance(data, list):
        return data
    return [_normalize_item(item) for item in data]


# ═══════════════════════════════════════════════════════════════════════════════
#  DEBUG
# ═══════════════════════════════════════════════════════════════════════════════

def _log_fields(endpoint: str, data):
    if not hasattr(st, '_debug_fields'):
        st.session_state['_debug_fields'] = {}
    if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        st.session_state['_debug_fields'][endpoint] = {
            "keys": list(data[0].keys()),
            "sample": {k: data[0][k] for k in list(data[0].keys())[:10]},
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  dolarapi
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
#  BondTerminal
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL, show_spinner=False)
def get_bondterminal_bootstrap():
    try:
        r = requests.get("https://bondterminal.com/api/landing/bootstrap",
                         headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
#  Riesgo País — EMBI JP Morgan (multi-source)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL, show_spinner=False)
def get_riesgo_pais():
    result = {
        "bps": "—", "bps_ambito": "—",
        "delta_1d": 0, "delta_1w": 0, "delta_1m": 0,
        "data_quality": "", "as_of": "",
    }

    try:
        r = requests.get(
            "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list) and len(data) > 0:
                latest = data[-1]
                bps = latest.get("valor")
                if bps is not None:
                    result["bps"] = round(bps)
                    result["as_of"] = latest.get("fecha", "")
                    result["data_quality"] = "argentinadatos"
                    result["bps_ambito"] = round(bps)
                    if len(data) >= 2:
                        prev = data[-2].get("valor")
                        if prev is not None:
                            result["delta_1d"] = round(bps - prev, 1)
                    if len(data) >= 6:
                        prev_w = data[-6].get("valor")
                        if prev_w is not None:
                            result["delta_1w"] = round(bps - prev_w, 1)
                    if len(data) >= 23:
                        prev_m = data[-23].get("valor")
                        if prev_m is not None:
                            result["delta_1m"] = round(bps - prev_m, 1)
                    return result
    except Exception:
        pass

    try:
        r = requests.get(
            "https://mercados.ambito.com/riesgo-pais/historico-general",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list) and len(data) > 1:
                latest_row = data[1] if len(data) > 1 else None
                if latest_row and len(latest_row) >= 2:
                    bps_str = str(latest_row[1]).replace(".", "").replace(",", ".").strip()
                    try:
                        bps = float(bps_str)
                        result["bps"] = round(bps)
                        result["bps_ambito"] = round(bps)
                        result["data_quality"] = "ambito"
                        if len(data) > 2:
                            try:
                                prev_str = str(data[2][1]).replace(".", "").replace(",", ".").strip()
                                result["delta_1d"] = round(bps - float(prev_str), 1)
                            except Exception:
                                pass
                        if len(data) > 6:
                            try:
                                prev_w_str = str(data[6][1]).replace(".", "").replace(",", ".").strip()
                                result["delta_1w"] = round(bps - float(prev_w_str), 1)
                            except Exception:
                                pass
                        if len(data) > 23:
                            try:
                                prev_m_str = str(data[23][1]).replace(".", "").replace(",", ".").strip()
                                result["delta_1m"] = round(bps - float(prev_m_str), 1)
                            except Exception:
                                pass
                        return result
                    except (ValueError, TypeError):
                        pass
    except Exception:
        pass

    try:
        r = requests.get("https://bondterminal.com/api/riesgo-pais",
                         headers=HEADERS, timeout=8)
        d = r.json()
        ambito_val = d.get("ambitoValue")
        if ambito_val is not None:
            result["bps"] = round(float(ambito_val))
        else:
            result["bps"] = round(d.get("weightedSpreadBps", 0))
        result["bps_ambito"] = d.get("ambitoValue", result["bps"])
        result["delta_1d"] = round(d.get("deltas", {}).get("oneDay", 0), 1)
        result["delta_1w"] = round(d.get("deltas", {}).get("oneWeek", 0), 1)
        result["delta_1m"] = round(d.get("deltas", {}).get("oneMonth", 0), 1)
        result["data_quality"] = "bondterminal"
        result["as_of"] = d.get("asOf", "")
    except Exception as e:
        result["data_quality"] = f"error: {e}"

    return result


@st.cache_data(ttl=TTL, show_spinner=False)
def get_live_prices_bt():
    try:
        r = requests.get("https://bondterminal.com/api/bonds/live-prices",
                         headers=HEADERS, timeout=10)
        d = r.json()
        return d.get("prices", {}), d.get("changes", {})
    except Exception:
        return {}, {}


# ═══════════════════════════════════════════════════════════════════════════════
#  data912
# ═══════════════════════════════════════════════════════════════════════════════

BASE912 = "https://data912.com/live"

@st.cache_data(ttl=TTL, show_spinner=False)
def get_912_raw(endpoint: str):
    try:
        r = requests.get(f"{BASE912}/{endpoint}", headers=HEADERS, timeout=10)
        data = r.json()
        _log_fields(endpoint, data)
        return data
    except Exception as e:
        return []


def get_912(endpoint: str):
    raw = get_912_raw(endpoint)
    return _normalize_list(raw)


def get_acciones():     return get_912("arg_stocks")
def get_cedears():      return get_912("arg_cedears")
def get_mep():          return get_912("mep")
def get_ccl():          return get_912("ccl")
def get_bonos_ars():    return get_912("arg_bonds")
def get_letras():       return get_912("arg_notes")
def get_adrs():         return get_912("usa_adrs")


def get_debug_fields():
    return st.session_state.get('_debug_fields', {})


# ═══════════════════════════════════════════════════════════════════════════════
#  IOL — Cauciones (scraping HTML)
# ═══════════════════════════════════════════════════════════════════════════════

IOL_CAUCIONES_URL = "https://iol.invertironline.com/mercado/cotizaciones/argentina/cauciones/todas"

@st.cache_data(ttl=TTL, show_spinner=False)
def get_cauciones():
    try:
        r = requests.get(IOL_CAUCIONES_URL, headers=HEADERS, timeout=12)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", {"id": "cotizaciones"})
        if not table:
            table = soup.find("table", class_=re.compile(r"cotizacion"))
        if not table:
            return []
        tbody = table.find("tbody")
        if not tbody:
            return []
        rows = tbody.find_all("tr")
        result = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            plazo = cells[0].get_text(strip=True)
            moneda = cells[1].get_text(strip=True)
            monto_contado = cells[2].get_text(strip=True)
            monto_futuro = cells[3].get_text(strip=True)
            tasa_cell = cells[5]
            tasa_raw = tasa_cell.get("data-order") or tasa_cell.get_text(strip=True)
            tasa_str = str(tasa_raw).replace("%", "").replace(",", ".").replace(" ", "").strip()
            try:
                tasa = float(tasa_str)
            except (ValueError, TypeError):
                tasa = 0.0
            fecha = cells[6].get_text(strip=True) if len(cells) > 6 else ""
            result.append({
                "plazo": plazo,
                "moneda": moneda,
                "monto_contado": monto_contado,
                "monto_futuro": monto_futuro,
                "tasa": tasa,
                "fecha": fecha,
            })
        return result
    except Exception as e:
        return []


def get_cauciones_resumen():
    data = get_cauciones()
    if not data:
        return []
    pesos = [d for d in data if "PESOS" in d.get("moneda", "").upper()]
    by_plazo = {}
    for d in pesos:
        p = d["plazo"]
        if p not in by_plazo or d["tasa"] > by_plazo[p]["tasa"]:
            by_plazo[p] = d
    def plazo_sort(item):
        try:
            return int(re.sub(r'\D', '', item["plazo"]))
        except:
            return 999
    result = sorted(by_plazo.values(), key=plazo_sort)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  US Rates — NY Fed (SOFR, EFFR, OBFR) + Investing.com (yields) + FRED (TIPS/BEI)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL, show_spinner=False)
def get_us_rates():
    result = {}

    # ── NY Fed: SOFR / EFFR / OBFR — funcionan, no tocar ───────────────────
    for rate_type, path in [("SOFR", "secured/sofr"), ("EFFR", "unsecured/effr"), ("OBFR", "unsecured/obfr")]:
        try:
            r = requests.get(
                f"https://markets.newyorkfed.org/api/rates/{path}/last/1.json",
                headers=HEADERS, timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                rates = data.get("refRates", [])
                if rates:
                    result[rate_type] = {
                        "rate":        rates[0].get("percentRate"),
                        "date":        rates[0].get("effectiveDate", ""),
                        "target_from": rates[0].get("targetRateFrom"),
                        "target_to":   rates[0].get("targetRateTo"),
                    }
        except Exception:
            pass

    # ── Treasury yields — Investing.com (tiempo real, sin key) ──────────────
    try:
        inv_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer":         "https://www.investing.com/",
        }
        r = requests.get(
            "https://www.investing.com/rates-bonds/usa-government-bonds",
            headers=inv_headers, timeout=10
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            table = soup.find("table")
            if table:
                tenor_map = {
                    "U.S. 1M":  "UST_1M",  "U.S. 3M":  "UST_3M",
                    "U.S. 6M":  "UST_6M",  "U.S. 1Y":  "UST_1Y",
                    "U.S. 2Y":  "UST_2Y",  "U.S. 5Y":  "UST_5Y",
                    "U.S. 10Y": "UST_10Y", "U.S. 30Y": "UST_30Y",
                }
                for row in table.find_all("tr"):
                    cols = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cols) >= 8:
                        name = cols[1]
                        if name in tenor_map:
                            try:
                                result[tenor_map[name]] = {
                                    "rate":       float(cols[2]),
                                    "change":     cols[6],
                                    "change_pct": cols[7],
                                    "time":       cols[8] if len(cols) > 8 else "",
                                }
                            except (ValueError, IndexError):
                                pass
    except Exception:
        pass

    # ── TIPS y BEI — FRED API con key (lag 1D, aceptable para estos datos) ──
    fred_tips = {
        "TIPS_5Y":  "DFII5",
        "TIPS_10Y": "DFII10",
        "BEI_5Y":   "T5YIE",
        "BEI_10Y":  "T10YIE",
    }
    try:
        fred_key = st.secrets["keys"]["FRED_API_KEY"]
        for key, series_id in fred_tips.items():
            try:
                r = requests.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id":        series_id,
                        "api_key":          fred_key,
                        "file_type":        "json",
                        "sort_order":       "desc",
                        "limit":            1,
                    },
                    timeout=10
                )
                if r.status_code == 200:
                    obs = r.json().get("observations", [])
                    if obs and obs[0]["value"] != ".":
                        result[key] = {
                            "rate": float(obs[0]["value"]),
                            "date": obs[0]["date"],
                        }
            except Exception:
                pass
    except Exception:
        pass  # si no hay key en secrets, TIPS/BEI quedan vacíos sin romper nada

    return result
# ═══════════════════════════════════════════════════════════════════════════════
#  Ecovalores (scraping HTML estático)
# ═══════════════════════════════════════════════════════════════════════════════

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
        from io import StringIO
        tables = pd.read_html(StringIO(html), flavor="lxml")
        best = None
        for df in tables:
            if isinstance(df.columns, pd.MultiIndex):
                continue
            cols_lower = [str(c).lower() for c in df.columns]
            flat = " ".join(cols_lower)
            if "tna" not in flat or "pase" not in flat:
                continue
            if not any("especie" in c for c in cols_lower):
                continue
            df_clean = df.dropna(how="all")
            if len(df_clean) < 3:
                continue
            first_col = df_clean.iloc[:, 0].astype(str)
            has_contracts = first_col.str.match(r"[A-Z]{3}\d{2}", na=False).any()
            if not has_contracts:
                continue
            if best is None or len(df_clean) < len(best):
                best = df_clean.copy()
        if best is None:
            return pd.DataFrame()
        best = best[best.iloc[:, 0].astype(str).str.match(r"[A-Z]{3}\d{2}", na=False)]
        best.columns = ["Especie", "Último", "Var.Día", "TNA%", "Pase%"][:len(best.columns)]
        def fix_tna(val):
            try:
                v = float(str(val).replace(",", ".").replace("-", "").strip())
                if v > 100:
                    return round(v / 10, 1)
                return v
            except:
                return val
        if "TNA%" in best.columns:
            best["TNA%"] = best["TNA%"].apply(fix_tna)
        if "Pase%" in best.columns:
            best["Pase%"] = best["Pase%"].apply(fix_tna)
        return best.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=TTL, show_spinner=False)
def get_curva_rendimientos():
    html = get_ecovalores_raw()
    if not html:
        return [], []
    try:
        import json
        m_cer = re.search(r'fut_data00\s*=\s*(\[\[.*?\]\])\s*;', html, re.DOTALL)
        m_usd = re.search(r'fut_data02\s*=\s*(\[\[.*?\]\])\s*;', html, re.DOTALL)
        def parse_js_array(match):
            if not match:
                return []
            try:
                return json.loads(match.group(1))
            except Exception:
                return []
        return parse_js_array(m_cer), parse_js_array(m_usd)
    except Exception:
        return [], []


@st.cache_data(ttl=TTL, show_spinner=False)
def get_tasas_implicitas():
    html = get_ecovalores_raw()
    if not html:
        return []
    try:
        import json
        m = re.search(r'var data00\s*=\s*(\[\[.*?\]\])\s*;', html, re.DOTALL)
        if not m:
            return []
        return json.loads(m.group(1))
    except Exception:
        return []


@st.cache_data(ttl=TTL, show_spinner=False)
def get_eco_bonos_ars():
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


@st.cache_data(ttl=TTL, show_spinner=False)
def get_eco_bonos_by_index(table_index: int):
    html = get_ecovalores_raw()
    if not html:
        return None
    try:
        from io import StringIO
        tables = pd.read_html(StringIO(html), flavor="lxml")
        if table_index >= len(tables):
            return None
        df = tables[table_index]
        if hasattr(df.columns, 'levels'):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).strip() for c in df.columns]
        return df.dropna(how="all").reset_index(drop=True)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  yfinance — índices globales
# ═══════════════════════════════════════════════════════════════════════════════

WORLD_TICKERS = {
    "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX",
    "DAX": "^GDAXI", "FTSE 100": "^FTSE", "NIKKEI": "^N225",
    "HANG SENG": "^HSI", "MERVAL": "^MERV", "BOVESPA": "^BVSP", "IPC MEX": "^MXX",
}

COMMODITY_TICKERS = {
    "GOLD": "GC=F", "SILVER": "SI=F", "WTI": "CL=F", "BRENT": "BZ=F",
    "NAT GAS": "NG=F", "COPPER": "HG=F", "SOJA": "ZS=F", "MAIZ": "ZC=F", "TRIGO": "ZW=F",
}

SECTOR_ETFS = {
    "Tech": "XLK", "Financials": "XLF", "Health": "XLV", "Energy": "XLE",
    "Industrials": "XLI", "ConsDisc": "XLY", "ConsStap": "XLP",
    "Materials": "XLB", "Utilities": "XLU", "RealEstate": "XLRE", "CommSvcs": "XLC",
}

FX_TICKERS = {
    "EUR/USD": "EURUSD=X", "USD/JPY": "JPY=X", "GBP/USD": "GBPUSD=X",
    "USD/BRL": "BRL=X", "USD/MXN": "MXN=X", "USD/CLP": "CLP=X", "DXY": "DX-Y.NYB",
}


def _prev_close_fallback(sym: str):
    try:
        fi = yf.Ticker(sym).fast_info
        return float(fi.get("previous_close") or fi.get("previousClose") or 0) or None
    except Exception:
        return None


@st.cache_data(ttl=TTL, show_spinner=False)
def get_yf_quotes(tickers_dict: dict):
    symbols = list(tickers_dict.values())
    names   = list(tickers_dict.keys())
    n = len(symbols)
    try:
        raw = yf.download(
            symbols, period="5d", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )
        result = {}
        for name, sym in zip(names, symbols):
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
                result[name] = {"price": price, "change_pct": round(chg, 2), "symbol": sym}
            except Exception:
                result[name] = {"price": None, "change_pct": 0.0, "symbol": sym}
        return result
    except Exception:
        return {name: {"price": None, "change_pct": 0.0} for name in names}


# ═══════════════════════════════════════════════════════════════════════════════
#  Formatters
# ═══════════════════════════════════════════════════════════════════════════════

def fmt_price(val, decimals=2):
    if val is None:
        return "—"
    try:
        val = float(val)
    except (ValueError, TypeError):
        return str(val)
    if val >= 10000:
        return f"{val:,.0f}"
    if val >= 1000:
        return f"{val:,.1f}"
    return f"{val:,.{decimals}f}"


def fmt_change(chg):
    if chg is None:
        return "—", "flat"
    try:
        chg = float(str(chg).replace("%", "").replace(",", "."))
    except (ValueError, TypeError):
        return str(chg), "flat"
    sign = "+" if chg >= 0 else ""
    css  = "up" if chg > 0.005 else ("down" if chg < -0.005 else "flat")
    return f"{sign}{chg:.2f}%", css


def safe_get(item: dict, field: str, default="—"):
    val = item.get(field)
    if val is None:
        return default
    return val


# ═══════════════════════════════════════════════════════════════════════════════
#  PPI — Letras con TNA real (portfoliopersonal.com via __NEXT_DATA__ SSR)
# ═══════════════════════════════════════════════════════════════════════════════

PPI_LETRAS_URL = "https://www.portfoliopersonal.com/Cotizaciones/Letras"

PPI_CURRENCY_MAP = {
    10000: "ARS",
    22013: "USD MEP",
    10001: "USD CCL",
}


def _tna_valida(tna):
    if tna is None or tna == 0 or tna < -50:
        return None
    return round(tna, 2)


@st.cache_data(ttl=TTL, show_spinner=False)
def get_letras_ppi():
    import json as _json_ppi
    try:
        r = requests.get(
            PPI_LETRAS_URL,
            headers={**HEADERS, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
            timeout=15
        )
        if r.status_code != 200 or len(r.text) < 10000:
            return []

        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            r.text, re.DOTALL
        )
        if not m:
            return []

        data = _json_ppi.loads(m.group(1))
        instruments = data.get("props", {}).get("pageProps", {}).get("instruments", [])

        result = []
        for inst in instruments:
            last = inst.get("lastPrice", 0)
            if last == 0:
                continue

            currency_id = inst.get("currency", {}).get("id", 10000)
            currency = PPI_CURRENCY_MAP.get(currency_id, "ARS")
            tna = _tna_valida(inst.get("tir", 0))
            expiry = inst.get("expirationDate", "")
            if expiry:
                expiry = expiry[:10]

            result.append({
                "ticker": inst.get("ticker", ""),
                "description": inst.get("description", ""),
                "last": last,
                "pct_change": inst.get("variation", 0),
                "volume": inst.get("volumen", 0),
                "expiration_date": expiry,
                "tna": tna,
                "currency": currency,
                "bid": inst.get("pricePurchase", 0),
                "ask": inst.get("priceSale", 0),
            })

        return result

    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  NEWS TICKER — RSS feeds from multiple sources
# ═══════════════════════════════════════════════════════════════════════════════

NEWS_TTL = 300


def _parse_feed(url, source_name, max_items=5):
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        results = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            if title:
                results.append({"title": title, "link": link, "source": source_name})
        return results
    except Exception:
        return []


@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_reuters():
    return _parse_feed("https://news.google.com/rss/search?q=site:reuters.com+finance+OR+markets&hl=en&gl=US&ceid=US:en", "REUTERS")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_cnbc():
    return _parse_feed("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "CNBC")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_investing():
    return _parse_feed("https://www.investing.com/rss/news.rss", "INVESTING")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_ft():
    return _parse_feed("https://news.google.com/rss/search?q=site:ft.com+markets+OR+finance&hl=en&gl=US&ceid=US:en", "FT")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_wsj():
    return _parse_feed("https://news.google.com/rss/search?q=site:wsj.com+markets+OR+economy&hl=en&gl=US&ceid=US:en", "WSJ")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_ambito():
    return _parse_feed("https://www.ambito.com/rss/economia.xml", "ÁMBITO")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_infobae():
    return _parse_feed("https://www.infobae.com/arc/outboundfeeds/rss/category/economia/", "INFOBAE")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_cronista():
    return _parse_feed("https://news.google.com/rss/search?q=site:cronista.com+mercados+OR+dolar&hl=es&gl=AR&ceid=AR:es", "CRONISTA")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_bloomberglinea():
    return _parse_feed("https://www.bloomberglinea.com/arc/outboundfeeds/rss/?outputType=xml", "BL LÍNEA")

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def _news_iprofesional():
    return _parse_feed("https://www.iprofesional.com/rss/finanzas", "iPROF")


def _interleave(*lists):
    result = []
    for batch in zip_longest(*lists):
        for item in batch:
            if item:
                result.append(item)
    return result


@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def get_news_international():
    return _interleave(_news_reuters(), _news_cnbc(), _news_ft(), _news_investing(), _news_wsj())

@st.cache_data(ttl=NEWS_TTL, show_spinner=False)
def get_news_argentina():
    return _interleave(_news_ambito(), _news_bloomberglinea(), _news_infobae(), _news_cronista(), _news_iprofesional())


# ═══════════════════════════════════════════════════════════════════════════════
#  ECONOMIC CALENDAR — Investing.com scraper
#  market: "US" (id=5) · "ARG" (id=29, confirmado del HTML de Investing)
#  Ventana lógica: AYER + HOY + MAÑANA (3 días corridos, no la semana Lun-Vie).
#  FIX pedido por Santi: el fetch a Investing.com a veces devuelve vacío para
#  el rango de semana completo a ciertas horas (o cae en un día sin releases),
#  y encima queda cacheado 1h. Con una ventana corta de ayer/hoy/mañana casi
#  siempre hay algo que mostrar (resultados reales de ayer/hoy + lo que viene).
#  TTL: 3600s — el calendario no cambia todo el tiempo durante la sesión.
# ═══════════════════════════════════════════════════════════════════════════════

_INVESTING_COUNTRY_CODES = {"US": ["5"], "ARG": ["29"]}

_CAL_MONTH_MAP = {
    "JAN": "Jan", "FEB": "Feb", "MAR": "Mar", "APR": "Apr",
    "MAY": "May", "JUN": "Jun", "JUL": "Jul", "AUG": "Aug",
    "SEP": "Sep", "OCT": "Oct", "NOV": "Nov", "DEC": "Dec",
}

_CAL_CATS_US = {
    "Nonfarm Payrolls":        ("LABOR",     3),
    "Unemployment Rate":       ("LABOR",     3),
    "ADP Nonfarm":             ("LABOR",     2),
    "Jobless Claims":          ("LABOR",     2),
    "JOLTS":                   ("LABOR",     2),
    "Average Hourly Earnings": ("LABOR",     2),
    "Participation Rate":      ("LABOR",     1),
    "Challenger Job Cuts":     ("LABOR",     1),
    "CPI":                     ("INFLATION", 3),
    "Core CPI":                ("INFLATION", 3),
    "PCE Price":               ("INFLATION", 3),
    "Core PCE":                ("INFLATION", 3),
    "PPI":                     ("INFLATION", 2),
    "Import Price":            ("INFLATION", 1),
    "GDP":                     ("GROWTH",    3),
    "Retail Sales":            ("GROWTH",    3),
    "Industrial Production":   ("GROWTH",    2),
    "Durable Goods":           ("GROWTH",    2),
    "ISM Manufacturing":       ("GROWTH",    2),
    "ISM Services":            ("GROWTH",    2),
    "ISM Non-Manufacturing":   ("GROWTH",    2),
    "PMI":                     ("GROWTH",    1),
    "Personal Income":         ("GROWTH",    2),
    "Personal Spending":       ("GROWTH",    2),
    "Consumer Confidence":     ("GROWTH",    2),
    "Michigan Consumer":       ("GROWTH",    2),
    "Trade Balance":           ("GROWTH",    2),
    "Housing Starts":          ("HOUSING",   2),
    "Building Permits":        ("HOUSING",   2),
    "Existing Home Sales":     ("HOUSING",   2),
    "New Home Sales":          ("HOUSING",   2),
    "Pending Home Sales":      ("HOUSING",   1),
    "Case-Shiller":            ("HOUSING",   1),
    "FOMC":                    ("FED",       3),
    "Fed Chair":               ("FED",       3),
    "Fed Minutes":             ("FED",       3),
    "Fed Interest Rate":       ("FED",       3),
    "Federal Reserve":         ("FED",       2),
    "Treasury":                ("RATES",     2),
    "Bond Auction":            ("RATES",     1),
}

_CAL_CATS_ARG = {
    "CPI":                  ("INFLACIÓN", 3),
    "Inflation":            ("INFLACIÓN", 3),
    "IPC":                  ("INFLACIÓN", 3),
    "INDEC CPI":            ("INFLACIÓN", 3),
    "Wholesale Price":      ("INFLACIÓN", 2),
    "GDP":                  ("ACTIVIDAD", 3),
    "Industrial Production":("ACTIVIDAD", 3),
    "EMAE":                 ("ACTIVIDAD", 3),
    "Manufacturing":        ("ACTIVIDAD", 2),
    "Retail Sales":         ("ACTIVIDAD", 2),
    "Construction":         ("ACTIVIDAD", 2),
    "Unemployment":         ("EMPLEO",    3),
    "Employment":           ("EMPLEO",    2),
    "Trade Balance":        ("COMERCIO",  3),
    "Exports":              ("COMERCIO",  2),
    "Imports":              ("COMERCIO",  2),
    "Current Account":      ("COMERCIO",  2),
    "Budget Balance":       ("FISCAL",    3),
    "Primary Surplus":      ("FISCAL",    3),
    "Tax Revenue":          ("FISCAL",    2),
    "Money Supply":         ("MONETARIO", 2),
    "Interest Rate":        ("MONETARIO", 3),
    "Central Bank":         ("MONETARIO", 3),
    "BCRA":                 ("MONETARIO", 3),
    "FX Reserves":          ("MONETARIO", 3),
    "Foreign Reserves":     ("MONETARIO", 3),
}


def _cal_week_range():
    """
    FIX: antes devolvía Lun-Vie de "la semana lógica" (si es finde, la que
    viene). Eso hacía que a ciertas horas / ciertos días sin releases el
    calendario se viera vacío, y como get_economic_calendar cachea 1h, esa
    foto vacía quedaba pegada un buen rato. Ahora es una ventana corrida de
    3 días (ayer, hoy, mañana) — siempre trae algo: lo ya publicado de
    ayer/hoy y lo que se viene mañana.
    """
    today     = _dt.today()
    date_from = today - _td(days=1)
    date_to   = today + _td(days=1)
    return date_from.strftime("%Y-%m-%d"), date_to.strftime("%Y-%m-%d")


def _cal_extract_period(name, release_date=""):
    skip = {"MOM","YOY","QOQ","YTD","ADJ","NSA","SA","PREL","FINAL",
            "FLASH","EST","REV","P","F","R","2ND EST","3RD EST"}
    paren = re.findall(r"\(([^)]+)\)", name)
    for p in reversed(paren):
        p_up = p.upper().strip()
        if p_up in skip:
            continue
        for mk in _CAL_MONTH_MAP:
            if mk in p_up:
                return p.strip()
        if re.search(r"Q[1-4]", p_up):
            return p.strip()
        if re.search(r"WK|WEEK|" + "|".join(_CAL_MONTH_MAP.keys()), p_up):
            return p.strip()
    q = re.search(r"\bQ([1-4])\b", name, re.I)
    if q:
        return f"Q{q.group(1)}"
    for mk, mv in _CAL_MONTH_MAP.items():
        if re.search(rf"\b{mk}\b", name.upper()):
            return mv
    if release_date:
        try:
            rd = pd.Timestamp(str(release_date)[:10])
            if "jobless" in name.lower() or "claims" in name.lower():
                wk = rd - _td(days=7)
                return f"Wk {wk.strftime('%b %-d')}"
            return (rd - pd.DateOffset(months=1)).strftime("%b %Y")
        except Exception:
            pass
    return ""


def _cal_classify(name, market):
    cats = _CAL_CATS_US if market == "US" else _CAL_CATS_ARG
    nu   = name.upper()
    for kw in sorted(cats.keys(), key=len, reverse=True):
        if kw.upper() in nu:
            return cats[kw]
    return ("OTHER", 1)


def _cal_parse_importance(row_tag, imp_td):
    if imp_td:
        dk = imp_td.get("data-img_key", "")
        if dk.startswith("bull") and dk[4:].isdigit():
            return min(int(dk[4:]), 3)
    for attr in ["data-importance", "importance"]:
        val = row_tag.get(attr, "")
        if val and str(val).isdigit():
            return min(int(val), 3)
    if imp_td:
        active = sum(
            1 for i in imp_td.find_all("i")
            if "Empty" not in " ".join(i.get("class", []))
        )
        if active:
            return min(active, 3)
    return 1


def _cal_parse_html(html_content, market):
    soup     = BeautifulSoup(html_content, "lxml")
    events   = []
    cur_date = None

    for row in soup.find_all("tr"):
        row_id  = row.get("id", "")
        row_cls = " ".join(row.get("class", []))

        if "theDay" in row_id or row.find("td", {"class": "theDay"}):
            td = row.find("td")
            if td:
                raw = td.get_text(strip=True)
                try:
                    cur_date = pd.Timestamp(raw).strftime("%Y-%m-%d")
                except Exception:
                    try:
                        from dateutil import parser as _dp
                        cur_date = _dp.parse(raw).strftime("%Y-%m-%d")
                    except Exception:
                        cur_date = raw
            continue

        if "js-event-item" not in row_cls:
            continue

        try:
            time_td  = row.find("td", {"class": re.compile(r"\btime\b")})
            evt_time = time_td.get_text(strip=True) if time_td else ""

            imp_td     = row.find("td", {"class": "sentiment"})
            importance = _cal_parse_importance(row, imp_td)

            evt_td   = row.find("td", {"class": re.compile(r"\bevent\b")})
            evt_name = ""
            if evt_td:
                a        = evt_td.find("a")
                evt_name = (a or evt_td).get_text(strip=True)
                evt_name = re.sub(r"\s+", " ", evt_name).strip()
            if not evt_name:
                continue

            act_td  = row.find("td", {"id": re.compile(r"eventActual")})
            fc_td   = row.find("td", {"id": re.compile(r"eventForecast")})
            prev_td = row.find("td", {"id": re.compile(r"eventPrevious")})

            actual   = act_td.get_text(strip=True)  if act_td  else ""
            forecast = fc_td.get_text(strip=True)   if fc_td   else ""
            previous = prev_td.get_text(strip=True) if prev_td else ""

            rel_dt  = row.get("data-event-datetime", "")
            period  = _cal_extract_period(evt_name, rel_dt or cur_date or "")
            cat, ic = _cal_classify(evt_name, market)

            events.append({
                "date":       cur_date or "",
                "time_et":    evt_time,
                "importance": importance,
                "imp_final":  importance if importance > 0 else ic,
                "category":   cat,
                "event":      evt_name,
                "period":     period,
                "forecast":   forecast,
                "previous":   previous,
                "actual":     actual,
                "release_dt": rel_dt,
            })
        except Exception:
            continue

    return events


_INVESTING_BROWSER_HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="126", "Not.A/Brand";v="24", "Google Chrome";v="126"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_economic_calendar(market: str = "US"):
    """
    Scraper del calendario económico de Investing.com.
    market: "US" | "ARG"
    Devuelve list[dict] o {"error": str} si falla.

    NOTA sobre HTTP 403: a diferencia del HTTP 400 (rango de fechas sin
    resultados, ya resuelto con la ventana ayer/hoy/mañana), un 403 es
    Investing.com directamente rechazando la request — típicamente su
    sistema anti-bot (Cloudflare/PerimeterX) bloqueando la IP del servidor
    en el que corre Streamlit Cloud, no un problema de la fecha pedida. Se
    reintenta 2 veces con headers más "de navegador real" y sesión nueva
    cada vez, pero si el bloqueo es por IP/fingerprint del datacenter, un
    cambio de headers no alcanza — es una limitación del lado de Investing,
    no del código.
    """
    date_from, date_to = _cal_week_range()

    last_error = "unknown"
    for attempt in range(2):
        try:
            session = requests.Session()
            session.headers.update(_INVESTING_BROWSER_HEADERS)
            session.get("https://www.investing.com", timeout=12)
            _time.sleep(1.5)
            session.get("https://www.investing.com/economic-calendar/", timeout=12)
            _time.sleep(1.2)

            r = session.post(
                "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData",
                data={
                    "country[]":     _INVESTING_COUNTRY_CODES.get(market, ["5"]),
                    "importance[]":  ["1", "2", "3"],
                    "dateFrom":      date_from,
                    "dateTo":        date_to,
                    "timeZone":      "8",
                    "timeFilter":    "timeRemain",
                    "currentTab":    "custom",
                    "submitFilters": "1",
                    "limit_from":    "0",
                },
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer":          "https://www.investing.com/economic-calendar/",
                    "Origin":           "https://www.investing.com",
                    "Content-Type":     "application/x-www-form-urlencoded",
                },
                timeout=20,
            )

            if r.status_code != 200:
                last_error = f"HTTP {r.status_code}"
                if r.status_code == 403 and attempt == 0:
                    _time.sleep(2.0)
                    continue
                return {"error": last_error}

            try:
                html = _json.loads(r.text).get("data", "")
            except Exception:
                html = r.text

            if not html:
                last_error = "Respuesta vacía"
                if attempt == 0:
                    _time.sleep(2.0)
                    continue
                return {"error": last_error}

            return _cal_parse_html(html, market)

        except Exception as e:
            last_error = str(e)
            continue

    return {"error": last_error}
