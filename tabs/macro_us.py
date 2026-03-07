"""
tabs/macro_us.py — MACRO US
Subtabs: GDP · LABOR · INFLATION
Sources: BEA (GDP) · BLS (Payrolls, CPI) · FRED (everything else)
Style: BBG Argy — #000 bg · #ff6600 orange · Courier New
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import os

# ═══════════════════════════════════════════════════════════════════════════════
#  PALETTE — BBG Argy
# ═══════════════════════════════════════════════════════════════════════════════
BBG_BG      = "#000000"
BBG_BG2     = "#0a0a0a"
BBG_BG3     = "#111111"
BBG_BORDER  = "#333333"
BBG_ORANGE  = "#ff6600"
BBG_GOLD    = "#ffcc00"
BBG_GREEN   = "#00ff41"
BBG_RED     = "#ff3b3b"
BBG_MUTED   = "#555555"
BBG_TEXT    = "#cccccc"
BBG_WHITE   = "#ffffff"
BBG_BLUE    = "#60a5fa"
BBG_CYAN    = "#00d4ff"
BBG_VIOLET  = "#a78bfa"

FED_TARGET  = 2.0

# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _bbg_layout(height=340, title=""):
    return dict(
        paper_bgcolor=BBG_BG,
        plot_bgcolor=BBG_BG2,
        font=dict(family="'Courier New', monospace", color=BBG_TEXT, size=11),
        xaxis=dict(
            gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
            tickfont=dict(size=9, color=BBG_MUTED),
        ),
        yaxis=dict(
            gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
            zeroline=True, zerolinecolor="#333",
            tickfont=dict(size=9, color=BBG_MUTED),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=BBG_TEXT, size=9, family="Courier New"),
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
        ),
        hovermode="x unified",
        barmode="relative",
        height=height,
        margin=dict(l=50, r=20, t=50, b=40),
        title=dict(
            text=title,
            font=dict(color=BBG_ORANGE, size=10, family="Courier New"),
            x=0.01, xanchor="left",
        ) if title else None,
    )

def _sec_header(text):
    """BBG section header — orange, uppercase, border-bottom"""
    st.markdown(
        f'<div style="color:{BBG_ORANGE};font-size:9px;font-weight:bold;'
        f'letter-spacing:2px;text-transform:uppercase;'
        f'border-bottom:1px solid #333;padding-bottom:3px;margin:10px 0 6px 0;'
        f'font-family:\'Courier New\',monospace">{text}</div>',
        unsafe_allow_html=True
    )

def _kpi_strip(kpis):
    """
    kpis: list of (value, label, sub, color)
    Renders the BBG-style kpi-strip
    """
    items_html = ""
    for val, label, sub, color in kpis:
        items_html += f"""
        <div class="kpi-item">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{val}</div>
            <div class="kpi-sub" style="color:{BBG_MUTED}">{sub}</div>
        </div>"""
    st.markdown(
        f'<div class="kpi-strip">{items_html}</div>',
        unsafe_allow_html=True
    )

def _color_val(val, invert=False):
    """Green if positive (or inverted), red if negative"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return BBG_MUTED
    try:
        v = float(val)
        if invert:
            return BBG_GREEN if v < 0 else BBG_RED
        return BBG_GREEN if v > 0 else (BBG_RED if v < 0 else BBG_MUTED)
    except:
        return BBG_MUTED

def _infl_color(val):
    """Color for inflation values — red = hot, amber = warm, green = on target"""
    try:
        v = float(val)
        if v > 3.5:  return BBG_RED
        elif v > 2.5: return BBG_GOLD
        else:          return BBG_GREEN
    except:
        return BBG_MUTED


# ═══════════════════════════════════════════════════════════════════════════════
#  FRED HELPER
# ═══════════════════════════════════════════════════════════════════════════════

FRED_API_KEY = "3e448a2c51c7a8837aaf72757836a7b7"
BEA_API_KEY_VAL  = "081DA2FC-1900-47A0-A40B-49C31925E395"
BLS_API_KEY_VAL  = "94e0e0f57c5e4d5397ba3898198927ae"

@st.cache_data(ttl=3600, show_spinner=False)
def _fred(series_id: str, start="2010-01-01") -> pd.Series:
    api_key = FRED_API_KEY
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&observation_start={start}"
        f"&api_key={api_key}&file_type=json"
    )
    r = requests.get(url, timeout=15)
    obs = r.json().get("observations", [])
    data = {o["date"]: (float(o["value"]) if o["value"] != "." else None) for o in obs}
    s = pd.Series(data)
    s.index = pd.to_datetime(s.index)
    return s.dropna().sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
#  BEA HELPER
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def _bea_nipa(table="T10102", freq="Q"):
    api_key = BEA_API_KEY_VAL
    url = (
        f"https://apps.bea.gov/api/data?UserID={api_key}"
        f"&method=GetData&DataSetName=NIPA"
        f"&TableName={table}&Frequency={freq}&Year=ALL&ResultFormat=JSON"
    )
    r = requests.get(url, timeout=20)
    data = r.json().get("BEAAPI", {}).get("Results", {}).get("Data", [])
    rows = []
    for d in data:
        try:
            rows.append({
                "SeriesCode": d.get("SeriesCode", ""),
                "TimePeriod": d.get("TimePeriod", ""),
                "DataValue":  float(d.get("DataValue", "0").replace(",", "")),
                "LineDescription": d.get("LineDescription", ""),
            })
        except Exception:
            pass
    return pd.DataFrame(rows)


def _bea_series(df, code):
    sub = df[df["SeriesCode"] == code].copy()
    sub["date"] = pd.to_datetime(sub["TimePeriod"].str.replace("Q1","-01-01")
                                                    .str.replace("Q2","-04-01")
                                                    .str.replace("Q3","-07-01")
                                                    .str.replace("Q4","-10-01"))
    return sub.set_index("date")["DataValue"].sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
#  BLS HELPER
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def _bls(series_ids: list, start_year=2010):
    from datetime import datetime as _dt
    api_key = BLS_API_KEY_VAL
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear":   str(_dt.now().year),
        "catalog":   False,
        "calculations": False,
        "annualaverage": False,
        "registrationkey": api_key,
    }
    r = requests.post(url, json=payload, timeout=20)
    result = {}
    for s in r.json().get("Results", {}).get("series", []):
        sid = s["seriesID"]
        rows = []
        for d in s.get("data", []):
            try:
                month = int(d["period"].replace("M",""))
                year  = int(d["year"])
                val   = float(d["value"])
                rows.append((pd.Timestamp(year=year, month=month, day=1), val))
            except Exception:
                pass
        if rows:
            idx, vals = zip(*sorted(rows))
            result[sid] = pd.Series(list(vals), index=list(idx)).sort_index()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  TRIM HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _trim(s, cut):
    if cut == 0:
        return s
    return s.iloc[cut:]


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: GDP
# ═══════════════════════════════════════════════════════════════════════════════

def _render_gdp():
    CODES = {
        "gdp":            "A191RL",
        "consumption":    "DPCERY",
        "durables":       "DDURRY",
        "nondurables":    "DNDGRY",
        "services":       "DSERRY",
        "investment":     "A006RY",
        "nonresidential": "A008RY",
        "residential":    "A011RY",
        "inventories":    "A014RY",
        "net_exports":    "A019RY",
        "exports":        "A020RY",
        "imports":        "A021RY",
        "government":     "A822RY",
        "federal":        "A823RY",
        "state_local":    "A829RY",
    }
    FRED_GDP = {
        "gdp_level":     "GDP",
        "real_gdp":      "GDPC1",
        "gdp_per_cap":   "A939RC0Q052SBEA",
        "gdp_now":       "GDPNOW",  # Atlanta Fed GDPNow (if available)
        "pce_real":      "PCECC96",
        "gdi":           "GDI",
    }
    COLORS = {
        "consumption":   BBG_BLUE,
        "investment":    BBG_GREEN,
        "government":    BBG_GOLD,
        "net_exports":   BBG_RED,
        "inventories":   BBG_VIOLET,
    }

    col_r, _ = st.columns([3, 7])
    with col_r:
        rng = st.radio("Range", ["5Y", "10Y", "20Y", "All"],
                       index=1, horizontal=True, label_visibility="collapsed", key="gdp_range")
    cuts = {"5Y": -20, "10Y": -40, "20Y": -80, "All": 0}
    cut = cuts[rng]

    with st.spinner("Loading BEA data..."):
        try:
            bea_df = _bea_nipa("T10102", "Q")
        except Exception as e:
            st.error(f"BEA fetch error: {e}")
            return

    # Pull FRED supplementary
    try:
        gdp_level   = _fred("GDP")
        real_gdp    = _fred("GDPC1")
        gdp_per_cap = _fred("A939RC0Q052SBEA")
    except Exception:
        gdp_level = real_gdp = gdp_per_cap = pd.Series(dtype=float)

    # Series from BEA
    def gs(code):
        try:
            return _bea_series(bea_df, code)
        except Exception:
            return pd.Series(dtype=float)

    gdp_q          = gs(CODES["gdp"])
    consumption_q  = gs(CODES["consumption"])
    investment_q   = gs(CODES["investment"])
    government_q   = gs(CODES["government"])
    net_exports_q  = gs(CODES["net_exports"])
    inventories_q  = gs(CODES["inventories"])
    durables_q     = gs(CODES["durables"])
    nondurables_q  = gs(CODES["nondurables"])
    services_q     = gs(CODES["services"])
    nonres_q       = gs(CODES["nonresidential"])
    residential_q  = gs(CODES["residential"])
    exports_q      = gs(CODES["exports"])
    imports_q      = gs(CODES["imports"])
    federal_q      = gs(CODES["federal"])
    statelocal_q   = gs(CODES["state_local"])

    def latest(s):
        d = s.dropna()
        return d.iloc[-1] if len(d) else None
    def prev(s):
        d = s.dropna()
        return d.iloc[-2] if len(d) >= 2 else None
    def ldelta(s):
        l, p = latest(s), prev(s)
        return l - p if l is not None and p is not None else None

    l_gdp       = latest(gdp_q)
    l_cons      = latest(consumption_q)
    l_inv       = latest(investment_q)
    l_gov       = latest(government_q)
    l_nx        = latest(net_exports_q)
    l_gdp_level = latest(gdp_level) if len(gdp_level) else None
    l_real_gdp  = latest(real_gdp)  if len(real_gdp)  else None

    # KPI STRIP
    kpis = [
        (f"{l_gdp:.1f}%" if l_gdp else "—",         "GDP QoQ",       "annualized",           _color_val(l_gdp)),
        (f"{l_cons:.1f}%" if l_cons else "—",        "CONSUMPTION",   "PCE contribution",     _color_val(l_cons)),
        (f"{l_inv:.1f}%" if l_inv else "—",          "INVESTMENT",    "gross private",        _color_val(l_inv)),
        (f"{l_gov:.1f}%" if l_gov else "—",          "GOVERNMENT",    "federal + state",      _color_val(l_gov)),
        (f"{l_nx:.1f}%" if l_nx else "—",            "NET EXPORTS",   "exports - imports",    _color_val(l_nx)),
        (f"${l_gdp_level/1000:.1f}T" if l_gdp_level else "—", "NOMINAL GDP", "current USD trillion", BBG_GOLD),
    ]
    _kpi_strip(kpis)

    # ── Chart 1: GDP Growth + Components Waterfall ──────────────────────────
    _sec_header("GDP GROWTH QoQ (Annualized) — BEA NIPA T10102")

    fig1 = go.Figure()
    if len(gdp_q.dropna()) > 0:
        gdp_t = _trim(gdp_q.dropna(), cut)
        fig1.add_trace(go.Bar(
            name="GDP", x=gdp_t.index, y=gdp_t.values,
            marker_color=[BBG_GREEN if v >= 0 else BBG_RED for v in gdp_t.values],
            opacity=0.85,
            hovertemplate="<b>GDP</b>: %{y:.1f}%<extra></extra>",
        ))
        # MA4
        ma4 = gdp_q.dropna().rolling(4).mean()
        ma4_t = _trim(ma4.dropna(), cut)
        fig1.add_trace(go.Scatter(
            name="4Q Avg", x=ma4_t.index, y=ma4_t.values,
            line=dict(color=BBG_GOLD, width=2),
            hovertemplate="<b>4Q Avg</b>: %{y:.1f}%<extra></extra>",
        ))
    fig1.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig1.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 2: Components Contribution ────────────────────────────────────
    _sec_header("GDP COMPONENTS — CONTRIBUTION TO GROWTH")

    fig2 = go.Figure()
    comp_data = [
        ("Consumption",  consumption_q, COLORS["consumption"]),
        ("Investment",   investment_q,  COLORS["investment"]),
        ("Government",   government_q,  COLORS["government"]),
        ("Net Exports",  net_exports_q, COLORS["net_exports"]),
        ("Inventories",  inventories_q, COLORS["inventories"]),
    ]
    for name, s, color in comp_data:
        t = _trim(s.dropna(), cut)
        if len(t):
            fig2.add_trace(go.Bar(
                name=name, x=t.index, y=t.values,
                marker_color=color, opacity=0.8,
                hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
            ))
    if len(gdp_q.dropna()) > 0:
        gdp_t2 = _trim(gdp_q.dropna(), cut)
        fig2.add_trace(go.Scatter(
            name="GDP Total", x=gdp_t2.index, y=gdp_t2.values,
            line=dict(color=BBG_WHITE, width=2),
            mode="lines+markers", marker=dict(size=4),
            hovertemplate="<b>GDP</b>: %{y:.1f}%<extra></extra>",
        ))
    fig2.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig2.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 3: Consumption Breakdown ──────────────────────────────────────
    _sec_header("CONSUMPTION BREAKDOWN — DURABLES · NON-DURABLES · SERVICES")

    fig3 = go.Figure()
    for name, s, color in [
        ("Durables",     durables_q,    BBG_BLUE),
        ("Non-Durables", nondurables_q, BBG_CYAN),
        ("Services",     services_q,    BBG_VIOLET),
    ]:
        t = _trim(s.dropna(), cut)
        if len(t):
            fig3.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(width=2),
                fill="none" if name != "Services" else "none",
                hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
            ))
    fig3.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig3.update_layout(**_bbg_layout(280))
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 4: Investment — Residential vs Non-Residential ────────────────
    _sec_header("INVESTMENT — RESIDENTIAL vs NON-RESIDENTIAL")

    fig4 = make_subplots(specs=[[{"secondary_y": False}]])
    for name, s, color, dash in [
        ("Non-Residential", nonres_q,    BBG_GREEN, "solid"),
        ("Residential",     residential_q, BBG_CYAN,  "dot"),
    ]:
        t = _trim(s.dropna(), cut)
        if len(t):
            fig4.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
            ))
    fig4.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig4.update_layout(**_bbg_layout(260))
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f'<div style="color:{BBG_MUTED};font-size:9px;margin-top:6px;font-family:\'Courier New\',monospace">'
        f'Sources: BEA NIPA Table 1.1.2 (contributions, %) · FRED (GDP levels) · Quarterly, annualized rates</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: LABOR
# ═══════════════════════════════════════════════════════════════════════════════

def _render_labor():
    # BLS Series IDs
    BLS_SERIES = {
        "nfp_total":    "CES0000000001",   # Total Nonfarm Payrolls
        "nfp_private":  "CES0500000001",   # Private
        "nfp_mfg":      "CES3000000001",   # Manufacturing
        "nfp_construct":"CES2000000001",   # Construction
        "nfp_retail":   "CES4200000001",   # Retail Trade
        "nfp_fin":      "CES5500000001",   # Financial
        "nfp_gov":      "CES9000000001",   # Government
        "nfp_leisure":  "CES7000000001",   # Leisure & Hospitality
        "nfp_health":   "CES6500000001",   # Health & Education
        "u3":           "LNS14000000",     # Unemployment rate U-3
        "u6":           "LNS13327709",     # U-6 (broad)
        "lfpr":         "LNS11300000",     # Labor Force Participation Rate
        "avg_hours":    "CES0500000007",   # Avg weekly hours private
        "avg_earn":     "CES0500000003",   # Avg hourly earnings private (level)
        "avg_earn_yoy": "CES0500000008",   # Avg hourly earnings YoY %
    }
    # FRED for JOLTS
    FRED_LABOR = {
        "jolts_open":  "JTSJOL",   # Job Openings
        "jolts_hire":  "JTSHIL",   # Hires
        "jolts_quit":  "JTSQUL",   # Quits
        "jolts_lay":   "JTSLAL",   # Layoffs
        "jolts_rate":  "JTSJOR",   # Job Openings Rate
        "sahm":        "SAHMREALTIME",  # Sahm Rule
        "init_claims": "ICSA",     # Initial Claims
        "cont_claims": "CCSA",     # Continued Claims
    }

    col_r, _ = st.columns([3, 7])
    with col_r:
        rng = st.radio("Range", ["2Y", "5Y", "10Y", "All"],
                       index=1, horizontal=True, label_visibility="collapsed", key="labor_range")
    cuts = {"2Y": -24, "5Y": -60, "10Y": -120, "All": 0}
    cut = cuts[rng]

    with st.spinner("Loading BLS + FRED labor data..."):
        try:
            bls_data = _bls(list(BLS_SERIES.values()), start_year=2010)
            # Map back to friendly names
            bls = {k: bls_data.get(v, pd.Series(dtype=float))
                   for k, v in BLS_SERIES.items()}
        except Exception as e:
            st.error(f"BLS fetch error: {e}")
            bls = {k: pd.Series(dtype=float) for k in BLS_SERIES}
        try:
            fred_labor = {k: _fred(v) for k, v in FRED_LABOR.items()}
        except Exception as e:
            st.warning(f"FRED labor partial error: {e}")
            fred_labor = {k: pd.Series(dtype=float) for k in FRED_LABOR}

    def latest(s):
        d = s.dropna()
        return d.iloc[-1] if len(d) else None
    def prev(s):
        d = s.dropna()
        return d.iloc[-2] if len(d) >= 2 else None

    # Calculate MoM payrolls change
    nfp = bls["nfp_total"]
    nfp_mom = nfp.diff()

    l_nfp   = latest(nfp_mom)
    l_u3    = latest(bls["u3"])
    l_u6    = latest(bls["u6"])
    l_lfpr  = latest(bls["lfpr"])
    l_wages = latest(bls["avg_earn_yoy"])
    l_jolts = latest(fred_labor["jolts_open"])

    # KPI STRIP
    kpis = [
        (f"{l_nfp:+,.0f}K" if l_nfp else "—",     "NFP MOM",      "non-farm payrolls",       _color_val(l_nfp)),
        (f"{l_u3:.1f}%" if l_u3 else "—",          "UNEMPLOYMENT", "U-3 rate",                _color_val(l_u3, invert=True)),
        (f"{l_u6:.1f}%" if l_u6 else "—",          "U-6 BROAD",    "underemployment",         _color_val(l_u6, invert=True)),
        (f"{l_lfpr:.1f}%" if l_lfpr else "—",      "LFPR",         "labor force participation", BBG_BLUE),
        (f"{l_wages:.1f}%" if l_wages else "—",    "WAGES YoY",    "avg hourly earnings",     _infl_color(l_wages) if l_wages else BBG_MUTED),
        (f"{l_jolts/1000:.1f}M" if l_jolts else "—","JOLTS OPEN",  "job openings",            BBG_CYAN),
    ]
    _kpi_strip(kpis)

    # ── Chart 1: NFP Monthly Change ──────────────────────────────────────────
    _sec_header("NON-FARM PAYROLLS — MONTHLY CHANGE (000s)")

    fig1 = go.Figure()
    nfp_t = _trim(nfp_mom.dropna(), cut)
    if len(nfp_t):
        fig1.add_trace(go.Bar(
            name="NFP MoM", x=nfp_t.index, y=nfp_t.values / 1000,
            marker_color=[BBG_GREEN if v >= 0 else BBG_RED for v in nfp_t.values],
            opacity=0.85,
            hovertemplate="<b>NFP</b>: %{y:+.0f}K<extra></extra>",
        ))
        ma3 = (nfp_mom / 1000).rolling(3).mean()
        ma3_t = _trim(ma3.dropna(), cut)
        fig1.add_trace(go.Scatter(
            name="3M Avg", x=ma3_t.index, y=ma3_t.values,
            line=dict(color=BBG_GOLD, width=2),
            hovertemplate="<b>3M Avg</b>: %{y:+.0f}K<extra></extra>",
        ))
    fig1.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig1.update_layout(**_bbg_layout(300, "THOUSANDS"))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 2: Unemployment U3 + U6 + LFPR ────────────────────────────────
    _sec_header("UNEMPLOYMENT RATES — U-3 · U-6 · LABOR FORCE PARTICIPATION")

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    for name, key, color, secondary in [
        ("U-3 Rate",  "u3",   BBG_RED,    False),
        ("U-6 Broad", "u6",   BBG_ORANGE, False),
        ("LFPR",      "lfpr", BBG_GREEN,  True),
    ]:
        t = _trim(bls[key].dropna(), cut)
        if len(t):
            fig2.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(color=color, width=2),
                hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
            ), secondary_y=secondary)

    fig2.update_layout(**_bbg_layout(280))
    fig2.update_layout(paper_bgcolor=BBG_BG, plot_bgcolor=BBG_BG2)
    fig2.update_yaxes(gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
                      tickfont=dict(size=9, color=BBG_MUTED),
                      title_text="Rate (%)", secondary_y=False)
    fig2.update_yaxes(gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
                      tickfont=dict(size=9, color=BBG_MUTED),
                      title_text="LFPR (%)", secondary_y=True)
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 3: Sector Payrolls Breakdown ──────────────────────────────────
    _sec_header("PAYROLLS BY SECTOR — MOM CHANGE")

    sectors = [
        ("Private",   "nfp_private",  BBG_BLUE),
        ("Mfg",       "nfp_mfg",      BBG_GREEN),
        ("Construct", "nfp_construct",BBG_CYAN),
        ("Retail",    "nfp_retail",   BBG_VIOLET),
        ("Financial", "nfp_fin",      BBG_GOLD),
        ("Gov",       "nfp_gov",      BBG_RED),
        ("Leisure",   "nfp_leisure",  "#f97316"),
        ("Health",    "nfp_health",   "#14b8a6"),
    ]

    sector_rows = ""
    for name, key, color in sectors:
        s = bls[key].diff()
        l = latest(s)
        p = prev(s)
        if l is not None:
            chg = l - p if p is not None else 0
            color_v = BBG_GREEN if l >= 0 else BBG_RED
            arrow = "▲" if l >= 0 else "▼"
            sector_rows += (
                f'<tr>'
                f'<td style="color:{color};font-weight:bold">{name}</td>'
                f'<td style="color:{BBG_GOLD}">{l/1000:+.0f}K</td>'
                f'<td style="color:{color_v}">{arrow} {chg/1000:+.0f}K</td>'
                f'</tr>'
            )

    st.markdown(f"""
    <table class="t" style="margin-bottom:10px">
      <thead><tr>
        <th>SECTOR</th><th>LAST MOM</th><th>VS PREV</th>
      </tr></thead>
      <tbody>{sector_rows}</tbody>
    </table>""", unsafe_allow_html=True)

    # ── Chart 4: JOLTS — Openings & Quits ───────────────────────────────────
    _sec_header("JOLTS — JOB OPENINGS · QUITS · LAYOFFS (Millions)")

    fig4 = go.Figure()
    jolts_series = [
        ("Job Openings", "jolts_open", BBG_CYAN,  "solid"),
        ("Hires",        "jolts_hire", BBG_GREEN, "dash"),
        ("Quits",        "jolts_quit", BBG_GOLD,  "dot"),
        ("Layoffs",      "jolts_lay",  BBG_RED,   "dot"),
    ]
    for name, key, color, dash in jolts_series:
        s = fred_labor[key]
        t = _trim(s.dropna(), cut)
        if len(t):
            fig4.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values / 1000,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}M<extra></extra>",
            ))
    fig4.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 5: Wages YoY + Initial Claims ─────────────────────────────────
    _sec_header("WAGES YoY & INITIAL CLAIMS")

    fig5 = make_subplots(specs=[[{"secondary_y": True}]])
    wages_t = _trim(bls["avg_earn_yoy"].dropna(), cut)
    claims_t = _trim(fred_labor["init_claims"].dropna(), cut)
    if len(wages_t):
        fig5.add_trace(go.Scatter(
            name="Wages YoY %", x=wages_t.index, y=wages_t.values,
            line=dict(color=BBG_GOLD, width=2),
            hovertemplate="<b>Wages YoY</b>: %{y:.2f}%<extra></extra>",
        ), secondary_y=False)
    if len(claims_t):
        fig5.add_trace(go.Scatter(
            name="Init Claims (000s)", x=claims_t.index, y=claims_t.values / 1000,
            line=dict(color=BBG_RED, width=1.5, dash="dot"),
            hovertemplate="<b>Init Claims</b>: %{y:.0f}K<extra></extra>",
        ), secondary_y=True)
    fig5.update_layout(**_bbg_layout(260))
    fig5.update_layout(paper_bgcolor=BBG_BG, plot_bgcolor=BBG_BG2)
    fig5.update_yaxes(gridcolor=BBG_BORDER, zeroline=False, tickfont=dict(size=9, color=BBG_MUTED),
                      title_text="Wages YoY %", secondary_y=False)
    fig5.update_yaxes(gridcolor=BBG_BORDER, zeroline=False, tickfont=dict(size=9, color=BBG_MUTED),
                      title_text="Init Claims (000s)", secondary_y=True)
    st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})

    # ── Sahm Rule ────────────────────────────────────────────────────────────
    sahm_t = _trim(fred_labor["sahm"].dropna(), cut)
    if len(sahm_t):
        l_sahm = sahm_t.iloc[-1]
        sahm_color = BBG_RED if l_sahm >= 0.5 else (BBG_GOLD if l_sahm >= 0.3 else BBG_GREEN)
        _sec_header("SAHM RULE — RECESSION INDICATOR")
        st.markdown(
            f'<div style="font-family:\'Courier New\',monospace;font-size:10px;color:{BBG_MUTED};'
            f'padding:8px;border:1px solid #222;background:{BBG_BG2};margin-bottom:8px">'
            f'Current: <span style="color:{sahm_color};font-weight:bold">{l_sahm:.2f}</span>'
            f' &nbsp;·&nbsp; Trigger: <span style="color:{BBG_RED}">≥ 0.50</span>'
            f' &nbsp;·&nbsp; {"⚠️ TRIGGERED" if l_sahm >= 0.5 else "✓ Below threshold"}'
            f'</div>',
            unsafe_allow_html=True
        )
        fig_sahm = go.Figure()
        fig_sahm.add_hrect(y0=0.5, y1=max(sahm_t.max(), 0.6),
                           fillcolor=BBG_RED, opacity=0.1, line_width=0)
        fig_sahm.add_hline(y=0.5, line_color=BBG_RED, line_width=1, line_dash="dot",
                           annotation_text="0.50 trigger",
                           annotation_font=dict(color=BBG_RED, size=9))
        fig_sahm.add_trace(go.Scatter(
            name="Sahm Rule", x=sahm_t.index, y=sahm_t.values,
            line=dict(color=BBG_GOLD, width=2),
            fill="tozeroy", fillcolor="rgba(255,102,0,0.08)",
            hovertemplate="<b>Sahm</b>: %{y:.2f}<extra></extra>",
        ))
        fig_sahm.update_layout(**_bbg_layout(220))
        st.plotly_chart(fig_sahm, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f'<div style="color:{BBG_MUTED};font-size:9px;margin-top:6px;font-family:\'Courier New\',monospace">'
        f'Sources: BLS (CES payrolls, LNS unemployment, LFPR, wages) · FRED (JOLTS, Sahm Rule, Claims)</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: INFLATION
# ═══════════════════════════════════════════════════════════════════════════════

def _render_inflation():
    BLS_CPI = {
        "cpi_all":       "CUUR0000SA0",
        "cpi_core":      "CUUR0000SA0L1E",
        "cpi_shelter":   "CUUR0000SAH1",
        "cpi_food_home": "CUUR0000SAF1",
        "cpi_food_out":  "CUUR0000SEFV",
        "cpi_energy":    "CUUR0000SA0E",
        "cpi_gasoline":  "CUUR0000SETB01",
        "cpi_medical":   "CUUR0000SAM",
        "cpi_apparel":   "CUUR0000SAA",
        "cpi_new_cars":  "CUUR0000SAT1",
        "cpi_used_cars": "CUUR0000SETA02",
        "cpi_recreation":"CUUR0000SAR",
        "cpi_transp":    "CUUR0000SAT",
    }
    FRED_INFL = {
        "pce":          "PCEPI",
        "pce_core":     "PCEPILFE",
        "breakeven_5y": "T5YIE",
        "breakeven_10y":"T10YIE",
        "mich_1y":      "MICH",
        "mich_5y":      "EXPINF5YR",
        "ppi_final":    "PPIFIS",
        "ppi_core":     "PPICOR",
        "supercore":    "CPILFESL",   # CPI less Food, Energy, Shelter proxy via FRED
    }

    COMPONENTS = {
        "cpi_shelter":   ("Shelter",             0.3620, BBG_BLUE),
        "cpi_food_home": ("Food at Home",        0.0850, BBG_GREEN),
        "cpi_food_out":  ("Food Away",           0.0540, "#34d399"),
        "cpi_medical":   ("Medical Care",        0.0640, BBG_VIOLET),
        "cpi_energy":    ("Energy",              0.0640, BBG_GOLD),
        "cpi_new_cars":  ("New Vehicles",        0.0340, BBG_MUTED),
        "cpi_used_cars": ("Used Vehicles",       0.0230, "#64748b"),
        "cpi_apparel":   ("Apparel",             0.0240, "#f97316"),
        "cpi_recreation":("Recreation",          0.0570, BBG_CYAN),
        "cpi_gasoline":  ("Gasoline",            0.0320, "#fb923c"),
    }

    col_r, _ = st.columns([3, 7])
    with col_r:
        rng = st.radio("Range", ["2Y", "5Y", "10Y", "All"],
                       index=1, horizontal=True, label_visibility="collapsed", key="infl_range")
    cuts = {"2Y": -24, "5Y": -60, "10Y": -120, "All": 0}
    cut = cuts[rng]

    with st.spinner("Loading BLS + FRED inflation data..."):
        try:
            cpi_data = _bls(list(BLS_CPI.values()), start_year=2010)
            cpi = {k: cpi_data.get(v, pd.Series(dtype=float)) for k, v in BLS_CPI.items()}
        except Exception as e:
            st.error(f"BLS CPI error: {e}")
            cpi = {k: pd.Series(dtype=float) for k in BLS_CPI}
        try:
            fred_infl = {k: _fred(v) for k, v in FRED_INFL.items()}
        except Exception as e:
            st.warning(f"FRED inflation partial error: {e}")
            fred_infl = {k: pd.Series(dtype=float) for k in FRED_INFL}

    def yoy(s):
        """Compute YoY % from level series"""
        return s.pct_change(12) * 100

    def mom(s):
        """MoM % change"""
        return s.pct_change(1) * 100

    def latest(s):
        d = s.dropna()
        return d.iloc[-1] if len(d) else None
    def prev(s):
        d = s.dropna()
        return d.iloc[-2] if len(d) >= 2 else None

    cpi_all_yoy  = yoy(cpi["cpi_all"])
    cpi_core_yoy = yoy(cpi["cpi_core"])
    pce_yoy      = yoy(fred_infl["pce"])
    pce_core_yoy = yoy(fred_infl["pce_core"])
    be5          = fred_infl["breakeven_5y"]
    be10         = fred_infl["breakeven_10y"]
    mich_1y      = fred_infl["mich_1y"]

    l_cpi      = latest(cpi_all_yoy)
    l_core     = latest(cpi_core_yoy)
    l_pce      = latest(pce_yoy)
    l_pce_core = latest(pce_core_yoy)
    l_be5      = latest(be5)
    l_mich     = latest(mich_1y)

    latest_date = cpi_all_yoy.dropna().index[-1].strftime("%b %Y") if len(cpi_all_yoy.dropna()) else ""

    # KPI STRIP
    kpis = [
        (f"{l_cpi:.1f}%"      if l_cpi      else "—", "CPI HEADLINE",  f"prev {prev(cpi_all_yoy):.1f}%" if prev(cpi_all_yoy) else "",    _infl_color(l_cpi)),
        (f"{l_core:.1f}%"     if l_core     else "—", "CORE CPI",      "ex Food & Energy",   _infl_color(l_core)),
        (f"{l_pce:.1f}%"      if l_pce      else "—", "PCE HEADLINE",  f"prev {prev(pce_yoy):.1f}%" if prev(pce_yoy) else "",             _infl_color(l_pce)),
        (f"{l_pce_core:.1f}%" if l_pce_core else "—", "CORE PCE",      "Fed target: 2.0%",   _infl_color(l_pce_core)),
        (f"{l_be5:.2f}%"      if l_be5      else "—", "5Y BREAKEVEN",  "TIPS market",        BBG_CYAN),
        (f"{l_mich:.1f}%"     if l_mich     else "—", "MICH 1Y EXPEC", "consumer survey",    BBG_VIOLET),
    ]
    _kpi_strip(kpis)

    # ── Chart 1: CPI vs PCE vs Core ──────────────────────────────────────────
    _sec_header(f"CPI · PCE · CORE — YoY% · LATEST: {latest_date}")

    fig1 = go.Figure()
    fig1.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot",
                   annotation_text="Fed 2%",
                   annotation_font=dict(color=BBG_GREEN, size=9))
    for name, s, color, dash in [
        ("CPI Headline",  cpi_all_yoy,  BBG_ORANGE, "solid"),
        ("Core CPI",      cpi_core_yoy, BBG_GOLD,   "dash"),
        ("PCE Headline",  pce_yoy,      BBG_BLUE,   "solid"),
        ("Core PCE",      pce_core_yoy, BBG_CYAN,   "dot"),
    ]:
        t = _trim(s.dropna(), cut)
        if len(t):
            fig1.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig1.update_layout(**_bbg_layout(320))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 2: CPI Components Contribution ─────────────────────────────────
    _sec_header("CPI COMPONENTS — YoY % BY CATEGORY")

    fig2 = go.Figure()
    for key, (label, weight, color) in COMPONENTS.items():
        s = yoy(cpi[key])
        t = _trim(s.dropna(), cut)
        if len(t):
            fig2.add_trace(go.Scatter(
                name=label, x=t.index, y=t.values,
                line=dict(color=color, width=1.5),
                hovertemplate=f"<b>{label}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig2.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot")
    fig2.update_layout(**_bbg_layout(320))
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 3: Shelter vs Core ex-Shelter ─────────────────────────────────
    _sec_header("SHELTER vs CORE EX-SHELTER — YoY %")

    shelter_yoy = yoy(cpi["cpi_shelter"])
    core_yoy    = cpi_core_yoy
    SHELTER_W   = 0.36
    core_ex_shelter = (core_yoy - SHELTER_W * shelter_yoy) / (1 - SHELTER_W)

    fig3 = go.Figure()
    fig3.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot",
                   annotation_text="2%", annotation_font=dict(color=BBG_GREEN, size=9))
    for name, s, color, dash in [
        ("Shelter",          shelter_yoy,   BBG_BLUE,   "solid"),
        ("Core CPI",         core_yoy,      BBG_GOLD,   "dot"),
        ("Core ex-Shelter*", core_ex_shelter, BBG_CYAN, "solid"),
    ]:
        t = _trim(s.dropna(), cut)
        if len(t):
            fig3.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig3.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        f'<div style="color:{BBG_MUTED};font-size:9px;font-family:\'Courier New\',monospace;'
        f'margin-top:-8px">* Core ex-Shelter approx. with 36% shelter weight in Core CPI</div>',
        unsafe_allow_html=True
    )

    # ── Chart 4: MoM CPI ────────────────────────────────────────────────────
    _sec_header("CPI MOM % — HEADLINE vs CORE")

    fig4 = go.Figure()
    for name, s, color in [
        ("CPI MoM",      mom(cpi["cpi_all"]),  BBG_ORANGE),
        ("Core CPI MoM", mom(cpi["cpi_core"]), BBG_GOLD),
    ]:
        t = _trim(s.dropna(), cut)
        if len(t):
            fig4.add_trace(go.Bar(
                name=name, x=t.index, y=t.values,
                marker_color=color, opacity=0.7,
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig4.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig4.update_layout(**_bbg_layout(260))
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    # ── Chart 5: Inflation Expectations ─────────────────────────────────────
    _sec_header("INFLATION EXPECTATIONS — TIPS BREAKEVENS & MICHIGAN SURVEY")

    exp_tabs = st.tabs(["TIPS BREAKEVENS", "MICHIGAN SURVEY"])

    with exp_tabs[0]:
        fig5a = go.Figure()
        fig5a.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot",
                        annotation_text="2%", annotation_font=dict(color=BBG_GREEN, size=9))
        for name, key, color, dash in [
            ("5Y Breakeven",  "breakeven_5y",  BBG_CYAN,   "solid"),
            ("10Y Breakeven", "breakeven_10y", BBG_VIOLET, "dash"),
        ]:
            t = _trim(fred_infl[key].dropna(), cut)
            if len(t):
                fig5a.add_trace(go.Scatter(
                    name=name, x=t.index, y=t.values,
                    line=dict(color=color, width=2, dash=dash),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
                ))
        fig5a.update_layout(**_bbg_layout(260))
        st.plotly_chart(fig5a, use_container_width=True, config={"displayModeBar": False})

    with exp_tabs[1]:
        fig5b = go.Figure()
        fig5b.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot")
        for name, key, color in [
            ("Michigan 1Y",  "mich_1y", BBG_GOLD),
            ("Michigan 5Y",  "mich_5y", BBG_BLUE),
        ]:
            t = _trim(fred_infl[key].dropna(), cut)
            if len(t):
                fig5b.add_trace(go.Scatter(
                    name=name, x=t.index, y=t.values,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
                ))
        fig5b.update_layout(**_bbg_layout(260))
        st.plotly_chart(fig5b, use_container_width=True, config={"displayModeBar": False})

    # ── Snapshot Table ───────────────────────────────────────────────────────
    _sec_header("SNAPSHOT — LATEST VALUES")

    snap = [
        ("CPI Headline",      latest(cpi_all_yoy),  _infl_color(latest(cpi_all_yoy))),
        ("Core CPI",          latest(cpi_core_yoy), _infl_color(latest(cpi_core_yoy))),
        ("PCE Headline",      latest(pce_yoy),       _infl_color(latest(pce_yoy))),
        ("Core PCE",          latest(pce_core_yoy),  _infl_color(latest(pce_core_yoy))),
        ("Shelter YoY",       latest(yoy(cpi["cpi_shelter"])), BBG_BLUE),
        ("Energy YoY",        latest(yoy(cpi["cpi_energy"])),  BBG_GOLD),
        ("Food at Home YoY",  latest(yoy(cpi["cpi_food_home"])), BBG_GREEN),
        ("5Y Breakeven",      latest(be5),  BBG_CYAN),
        ("10Y Breakeven",     latest(be10), BBG_VIOLET),
        ("Michigan 1Y",       latest(mich_1y), BBG_GOLD),
    ]

    rows_html = ""
    for label, val, color in snap:
        v_str = f"{val:.2f}%" if val is not None else "—"
        rows_html += f'<tr><td>{label}</td><td style="color:{color};font-weight:bold">{v_str}</td></tr>'

    st.markdown(f"""
    <table class="t" style="max-width:400px">
      <thead><tr><th>INDICATOR</th><th>LATEST YoY%</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)

    st.markdown(
        f'<div style="color:{BBG_MUTED};font-size:9px;margin-top:8px;font-family:\'Courier New\',monospace">'
        f'Sources: BLS (CPI series CUUR) · FRED (PCE, TIPS breakevens, Michigan Survey, PPI) · '
        f'All YoY% calculations from monthly levels</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    subtabs = st.tabs(["📊 GDP", "👷 LABOR", "📈 INFLATION"])

    with subtabs[0]:
        _render_gdp()

    with subtabs[1]:
        _render_labor()

    with subtabs[2]:
        _render_inflation()
