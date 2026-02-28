"""
Centralized data fetching — all sources, cached at 60s.
Sources:
  - data912 (Milton)  → acciones, CEDEARs, MEP/CCL, bonos ARS
  - BondTerminal      → bonos USD soberanos/corp/prov, riesgo país
  - Ecovalores        → futuros dólar, curva rendimientos, bonos ARS
  - dolarapi.com      → tipos de cambio (blue, oficial, tarjeta…)
  - yfinance          → índices globales, commodities, sectores US
  - IOL               → cauciones (scraping)
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


# ═══════════════════════════════════════════════════════════════════════════════
#  FIELD NORMALIZATION — data912 returns varying field names
# ═══════════════════════════════════════════════════════════════════════════════

# Mapping of canonical field names → possible source field names
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
    """Normalize a data912 item to canonical field names."""
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
    
    # Keep any extra fields not yet mapped
    for k, v in item.items():
        if k not in used_keys:
            normalized[k] = v
    
    return normalized


def _normalize_list(data: list) -> list:
    """Normalize a list of data912 items."""
    if not data or not isinstance(data, list):
        return data
    return [_normalize_item(item) for item in data]


# ═══════════════════════════════════════════════════════════════════════════════
#  DEBUG: log field names from first API response
# ═══════════════════════════════════════════════════════════════════════════════

def _log_fields(endpoint: str, data):
    """Store the raw field names for debugging."""
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


# ═══════════════════════════════════════════════════════════════════════════════
#  data912
# ═══════════════════════════════════════════════════════════════════════════════

BASE912 = "https://data912.com/live"

@st.cache_data(ttl=TTL, show_spinner=False)
def get_912_raw(endpoint: str):
    """Get raw data from data912 (before normalization)."""
    try:
        r = requests.get(f"{BASE912}/{endpoint}", headers=HEADERS, timeout=10)
        data = r.json()
        _log_fields(endpoint, data)
        return data
    except Exception as e:
        return []


def get_912(endpoint: str):
    """Get normalized data from data912."""
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
    """Return debug info about API field names."""
    return st.session_state.get('_debug_fields', {})


# ═══════════════════════════════════════════════════════════════════════════════
#  IOL — Cauciones (scraping HTML)
# ═══════════════════════════════════════════════════════════════════════════════

IOL_CAUCIONES_URL = "https://iol.invertironline.com/mercado/cotizaciones/argentina/cauciones/todas"

@st.cache_data(ttl=TTL, show_spinner=False)
def get_cauciones():
    """
    Scrape cauciones from IOL.
    Returns list of dicts: {plazo, moneda, monto_contado, tasa, fecha}
    """
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
        
        # No role="row" — just plain <tr> inside tbody
        rows = tbody.find_all("tr")
        result = []
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            
            # Cell 0: Plazo (plain text number like "3", "7", "14")
            plazo = cells[0].get_text(strip=True)
            
            # Cell 1: Moneda ("PESOS" / "DOLARES")
            moneda = cells[1].get_text(strip=True)
            
            # Cell 2: Monto Contado
            monto_contado = cells[2].get_text(strip=True)
            
            # Cell 3: Monto Futuro
            monto_futuro = cells[3].get_text(strip=True)
            
            # Cell 4: Fecha Vencimiento (usually empty)
            
            # Cell 5: Tasa Tomadora — use data-order attribute (comma as decimal: "10,00")
            tasa_cell = cells[5]
            tasa_raw = tasa_cell.get("data-order") or tasa_cell.get_text(strip=True)
            tasa_str = str(tasa_raw).replace("%", "").replace(",", ".").replace(" ", "").strip()
            try:
                tasa = float(tasa_str)
            except (ValueError, TypeError):
                tasa = 0.0
            
            # Cell 6: Fecha/Hora
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
    """
    Returns summarized cauciones: one row per plazo for PESOS,
    showing the latest (highest) tasa tomadora.
    Returns list of dicts: {plazo, tasa, volumen}
    """
    data = get_cauciones()
    if not data:
        return []
    
    # Group by plazo, only PESOS
    pesos = [d for d in data if "PESOS" in d.get("moneda", "").upper()]
    
    # For each plazo, get the row with highest tasa
    by_plazo = {}
    for d in pesos:
        p = d["plazo"]
        if p not in by_plazo or d["tasa"] > by_plazo[p]["tasa"]:
            by_plazo[p] = d
    
    # Sort by plazo numerically
    def plazo_sort(item):
        try:
            return int(re.sub(r'\D', '', item["plazo"]))
        except:
            return 999
    
    result = sorted(by_plazo.values(), key=plazo_sort)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  US Rates — NY Fed (SOFR, EFFR, OBFR) + Treasury Yields (yfinance)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=TTL, show_spinner=False)
def get_us_rates():
    """
    Returns dict with SOFR, EFFR, OBFR from NY Fed + Treasury yields + TIPS + BEI from FRED.
    """
    result = {}
    
    # NY Fed rates
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
    
    # FRED CSV — Treasury yields, TIPS, Breakeven Inflation
    # No API key needed for CSV endpoint
    fred_series = {
        "UST_1M":   "DGS1MO",
        "UST_3M":   "DGS3MO",
        "UST_6M":   "DGS6MO",
        "UST_1Y":   "DGS1",
        "UST_2Y":   "DGS2",
        "UST_5Y":   "DGS5",
        "UST_10Y":  "DGS10",
        "UST_30Y":  "DGS30",
        "TIPS_5Y":  "DFII5",
        "TIPS_10Y": "DFII10",
        "BEI_5Y":   "T5YIE",
        "BEI_10Y":  "T10YIE",
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
            # Skip MultiIndex tables — we want flat columns
            if isinstance(df.columns, pd.MultiIndex):
                continue
            
            cols_lower = [str(c).lower() for c in df.columns]
            flat = " ".join(cols_lower)
            
            # Must have TNA and Pase columns (the futuros dólar table)
            if "tna" not in flat or "pase" not in flat:
                continue
            
            # Must have Especie column
            if not any("especie" in c for c in cols_lower):
                continue
            
            # Should contain FEB/MAR/ABR style contract names
            df_clean = df.dropna(how="all")
            if len(df_clean) < 3:
                continue
            
            first_col = df_clean.iloc[:, 0].astype(str)
            has_contracts = first_col.str.match(r"[A-Z]{3}\d{2}", na=False).any()
            if not has_contracts:
                continue
            
            # Prefer the smallest matching table (most specific)
            if best is None or len(df_clean) < len(best):
                best = df_clean.copy()
        
        if best is None:
            return pd.DataFrame()
        
        # Filter to only contract rows (FEB26, MAR26, etc.)
        best = best[best.iloc[:, 0].astype(str).str.match(r"[A-Z]{3}\d{2}", na=False)]
        
        # Normalize column names
        best.columns = ["Especie", "Último", "Var.Día", "TNA%", "Pase%"][:len(best.columns)]
        
        # TNA comes as "217" meaning 21.7%, convert
        def fix_tna(val):
            try:
                v = float(str(val).replace(",", ".").replace("-", "").strip())
                if v > 100:  # values like 217 mean 21.7%
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


# ═══════════════════════════════════════════════════════════════════════════════
#  yfinance — índices globales
# ═══════════════════════════════════════════════════════════════════════════════

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
    """Batch download current quotes."""
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
    """Safely get a field value, returning default if None or missing."""
    val = item.get(field)
    if val is None:
        return default
    return val
