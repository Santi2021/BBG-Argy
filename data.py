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
"""

import streamlit as st
import requests
import yfinance as yf
import pandas as pd
import re
import feedparser
from itertools import zip_longest
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html,*/*",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

TTL = 60  # seconds


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
#  DEBUG: log field names from first API response
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
#  US Rates — NY Fed (SOFR, EFFR, OBFR) + Treasury Yields + TIPS + BEI
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL, show_spinner=False)
def get_us_rates():
    result = {}
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
                        "rate": rates[0].get("percentRate"),
                        "date": rates[0].get("effectiveDate", ""),
                        "target_from": rates[0].get("targetRateFrom"),
                        "target_to": rates[0].get("targetRateTo"),
                    }
        except Exception:
            pass

    fred_series = {
        "UST_1M": "DGS1MO", "UST_3M": "DGS3MO", "UST_6M": "DGS6MO",
        "UST_1Y": "DGS1", "UST_2Y": "DGS2", "UST_5Y": "DGS5",
        "UST_10Y": "DGS10", "UST_30Y": "DGS30",
        "TIPS_5Y": "DFII5", "TIPS_10Y": "DFII10",
        "BEI_5Y": "T5YIE", "BEI_10Y": "T10YIE",
    }
    for key, series_id in fred_series.items():
        try:
            r = requests.get(
                f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2025-01-01",
                headers=HEADERS, timeout=8
            )
            if r.status_code == 200:
                lines = r.text.strip().split("\n")
                if len(lines) > 1:
                    last_line = lines[-1]
                    parts = last_line.split(",")
                    if len(parts) >= 2 and parts[1].strip() != ".":
                        try:
                            result[key] = {"rate": float(parts[1].strip())}
                        except ValueError:
                            pass
        except Exception:
            pass
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
    """
    Devuelve DataFrame de Ecovalores por índice de tabla (confirmados empíricamente):
      8  → CER  (CUAP, DICP, DIP0, PAP0, PARP, TX26, TX28, TZX26, TZX27, TZX28)
      13 → Tasa Fija (TO26)
      16 → BOPREAL (BPOA7, BPOB7, BPOC7)
      19 → Soberanos USD en ARS (AE38, AL29, AL30, AL35, AL41, GD29, GD30...)
      22 → Soberanos USD en USD (AE38D, AL30D, GD30D...)
      25 → Dollar Linked (TZV26)
    """
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


@st.cache_data(ttl=TTL, show_spinner=False)
def get_yf_quotes(tickers_dict: dict):
    symbols = list(tickers_dict.values())
    names   = list(tickers_dict.keys())
    try:
        raw = yf.download(
            symbols, period="2d", interval="1d", group_by="ticker",
            auto_adjust=True, progress=False, threads=True,
        )
        result = {}
        for name, sym in zip(names, symbols):
            try:
                if len(symbols) == 1:
                    closes = raw["Close"]
                else:
                    try:
                        closes = raw[sym]["Close"]
                    except (KeyError, TypeError):
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
    except Exception:
        return {n: {"price": None, "change_pct": 0.0} for n in names}


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
    import json as _json
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

        data = _json.loads(m.group(1))
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
