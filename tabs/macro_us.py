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
from datetime import datetime as _dt

# ═══════════════════════════════════════════════════════════════════════════════
#  PALETTE — BBG Argy
# ═══════════════════════════════════════════════════════════════════════════════
BBG_BG      = "#000000"
BBG_BG2     = "#0a0a0a"
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
#  API KEYS
# ═══════════════════════════════════════════════════════════════════════════════
FRED_API_KEY    = "3e448a2c51c7a8837aaf72757836a7b7"
BEA_API_KEY_VAL = "081DA2FC-1900-47A0-A40B-49C31925E395"
BLS_API_KEY_VAL = "94e0e0f57c5e4d5397ba3898198927ae"

# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _bbg_layout(height=340):
    return dict(
        paper_bgcolor=BBG_BG,
        plot_bgcolor=BBG_BG2,
        font=dict(family="'Courier New', monospace", color=BBG_TEXT, size=11),
        xaxis=dict(
            gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
            tickfont=dict(size=9, color=BBG_MUTED),
            title=None,
        ),
        yaxis=dict(
            gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
            zeroline=True, zerolinecolor="#333",
            tickfont=dict(size=9, color=BBG_MUTED),
            title=None,
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
        margin=dict(l=50, r=20, t=40, b=40),
        title=None,
    )

def _sec_header(text):
    st.markdown(
        f'<div style="color:{BBG_ORANGE};font-size:9px;font-weight:bold;'
        f'letter-spacing:2px;text-transform:uppercase;'
        f'border-bottom:1px solid #333;padding-bottom:3px;margin:10px 0 6px 0;'
        f'font-family:\'Courier New\',monospace">{text}</div>',
        unsafe_allow_html=True
    )

def _kpi_strip(kpis):
    items_html = ""
    for val, label, sub, color in kpis:
        items_html += f"""
        <div class="kpi-item">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{val}</div>
            <div class="kpi-sub" style="color:{BBG_MUTED}">{sub}</div>
        </div>"""
    st.markdown(f'<div class="kpi-strip">{items_html}</div>', unsafe_allow_html=True)

def _color_val(val, invert=False):
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
    try:
        v = float(val)
        if v > 3.5:   return BBG_RED
        elif v > 2.5: return BBG_GOLD
        else:          return BBG_GREEN
    except:
        return BBG_MUTED

def _trim(s, cut):
    if cut == 0:
        return s
    return s.iloc[cut:]

def _latest(s):
    d = s.dropna()
    return d.iloc[-1] if len(d) else None

def _prev(s):
    d = s.dropna()
    return d.iloc[-2] if len(d) >= 2 else None


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def _fred(series_id: str, start="2010-01-01") -> pd.Series:
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&observation_start={start}"
        f"&api_key={FRED_API_KEY}&file_type=json"
    )
    try:
        r = requests.get(url, timeout=15)
        obs = r.json().get("observations", [])
        data = {o["date"]: (float(o["value"]) if o["value"] != "." else None) for o in obs}
        s = pd.Series(data)
        s.index = pd.to_datetime(s.index)
        return s.dropna().sort_index()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600, show_spinner=False)
def _bea_nipa(table="T10102", freq="Q"):
    url = (
        f"https://apps.bea.gov/api/data?UserID={BEA_API_KEY_VAL}"
        f"&method=GetData&DataSetName=NIPA"
        f"&TableName={table}&Frequency={freq}&Year=ALL&ResultFormat=JSON"
    )
    try:
        r = requests.get(url, timeout=20)
        data = r.json().get("BEAAPI", {}).get("Results", {}).get("Data", [])
        rows = []
        for d in data:
            try:
                rows.append({
                    "SeriesCode": d.get("SeriesCode", ""),
                    "TimePeriod": d.get("TimePeriod", ""),
                    "DataValue":  float(d.get("DataValue", "0").replace(",", "")),
                })
            except Exception:
                pass
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def _bea_series(df, code):
    sub = df[df["SeriesCode"] == code].copy()
    sub["date"] = pd.to_datetime(
        sub["TimePeriod"]
        .str.replace("Q1", "-01-01")
        .str.replace("Q2", "-04-01")
        .str.replace("Q3", "-07-01")
        .str.replace("Q4", "-10-01")
    )
    return sub.set_index("date")["DataValue"].sort_index()


@st.cache_data(ttl=3600, show_spinner=False)
def _bls(series_ids: list, start_year=2010):
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    payload = {
        "seriesid":       series_ids,
        "startyear":      str(start_year),
        "endyear":        str(_dt.now().year),
        "catalog":        False,
        "calculations":   False,
        "annualaverage":  False,
        "registrationkey": BLS_API_KEY_VAL,
    }
    try:
        r = requests.post(url, json=payload, timeout=25)
        result = {}
        for s in r.json().get("Results", {}).get("series", []):
            sid = s["seriesID"]
            rows = []
            for d in s.get("data", []):
                try:
                    month = int(d["period"].replace("M", ""))
                    year  = int(d["year"])
                    val   = float(d["value"])
                    rows.append((pd.Timestamp(year=year, month=month, day=1), val))
                except Exception:
                    pass
            if rows:
                idx, vals = zip(*sorted(rows))
                result[sid] = pd.Series(list(vals), index=list(idx)).sort_index()
        return result
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: GDP  —  fixed range: 5Y (last 20 quarters)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_gdp():
    CUT = -20   # 5 years of quarterly data

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
    }
    COMP_COLORS = {
        "consumption": BBG_BLUE,
        "investment":  BBG_GREEN,
        "government":  BBG_GOLD,
        "net_exports": BBG_RED,
        "inventories": BBG_VIOLET,
    }

    with st.spinner("Loading BEA data..."):
        try:
            bea_df = _bea_nipa("T10102", "Q")
        except Exception as e:
            st.error(f"BEA fetch error: {e}")
            return

    try:
        gdp_level = _fred("GDP")
    except Exception:
        gdp_level = pd.Series(dtype=float)

    def gs(code):
        try:
            return _bea_series(bea_df, code)
        except Exception:
            return pd.Series(dtype=float)

    gdp_q         = gs(CODES["gdp"])
    consumption_q = gs(CODES["consumption"])
    investment_q  = gs(CODES["investment"])
    government_q  = gs(CODES["government"])
    net_exports_q = gs(CODES["net_exports"])
    inventories_q = gs(CODES["inventories"])
    durables_q    = gs(CODES["durables"])
    nondurables_q = gs(CODES["nondurables"])
    services_q    = gs(CODES["services"])
    nonres_q      = gs(CODES["nonresidential"])
    residential_q = gs(CODES["residential"])

    l_gdp       = _latest(gdp_q)
    l_cons      = _latest(consumption_q)
    l_inv       = _latest(investment_q)
    l_gov       = _latest(government_q)
    l_nx        = _latest(net_exports_q)
    l_gdp_level = _latest(gdp_level) if len(gdp_level) else None

    kpis = [
        (f"{l_gdp:.1f}%"       if l_gdp       else "—", "GDP QoQ",     "annualized",          _color_val(l_gdp)),
        (f"{l_cons:.1f}%"      if l_cons      else "—", "CONSUMPTION", "PCE contribution",    _color_val(l_cons)),
        (f"{l_inv:.1f}%"       if l_inv       else "—", "INVESTMENT",  "gross private",       _color_val(l_inv)),
        (f"{l_gov:.1f}%"       if l_gov       else "—", "GOVERNMENT",  "federal + state",     _color_val(l_gov)),
        (f"{l_nx:.1f}%"        if l_nx        else "—", "NET EXPORTS", "exports - imports",   _color_val(l_nx)),
        (f"${l_gdp_level/1000:.1f}T" if l_gdp_level else "—", "NOMINAL GDP", "USD trillion", BBG_GOLD),
    ]
    _kpi_strip(kpis)

    # Chart 1: GDP Growth QoQ
    _sec_header("GDP GROWTH QoQ (Annualized) — BEA NIPA")

    fig1 = go.Figure()
    if len(gdp_q.dropna()):
        gdp_t = _trim(gdp_q.dropna(), CUT)
        fig1.add_trace(go.Bar(
            name="GDP", x=gdp_t.index, y=gdp_t.values,
            marker_color=[BBG_GREEN if v >= 0 else BBG_RED for v in gdp_t.values],
            opacity=0.85,
            hovertemplate="<b>GDP</b>: %{y:.1f}%<extra></extra>",
        ))
        ma4   = gdp_q.dropna().rolling(4).mean()
        ma4_t = _trim(ma4.dropna(), CUT)
        fig1.add_trace(go.Scatter(
            name="4Q Avg", x=ma4_t.index, y=ma4_t.values,
            line=dict(color=BBG_GOLD, width=2),
            hovertemplate="<b>4Q Avg</b>: %{y:.1f}%<extra></extra>",
        ))
    fig1.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig1.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # Chart 2: Components Contribution
    _sec_header("GDP COMPONENTS — CONTRIBUTION TO GROWTH")

    fig2 = go.Figure()
    for name, s, color in [
        ("Consumption", consumption_q, COMP_COLORS["consumption"]),
        ("Investment",  investment_q,  COMP_COLORS["investment"]),
        ("Government",  government_q,  COMP_COLORS["government"]),
        ("Net Exports", net_exports_q, COMP_COLORS["net_exports"]),
        ("Inventories", inventories_q, COMP_COLORS["inventories"]),
    ]:
        t = _trim(s.dropna(), CUT)
        if len(t):
            fig2.add_trace(go.Bar(
                name=name, x=t.index, y=t.values,
                marker_color=color, opacity=0.8,
                hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
            ))
    if len(gdp_q.dropna()):
        gdp_t2 = _trim(gdp_q.dropna(), CUT)
        fig2.add_trace(go.Scatter(
            name="GDP Total", x=gdp_t2.index, y=gdp_t2.values,
            line=dict(color=BBG_WHITE, width=2),
            mode="lines+markers", marker=dict(size=4),
            hovertemplate="<b>GDP</b>: %{y:.1f}%<extra></extra>",
        ))
    fig2.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig2.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Chart 3: Consumption Breakdown
    _sec_header("CONSUMPTION BREAKDOWN — DURABLES · NON-DURABLES · SERVICES")

    fig3 = go.Figure()
    for name, s, color in [
        ("Durables",     durables_q,    BBG_BLUE),
        ("Non-Durables", nondurables_q, BBG_CYAN),
        ("Services",     services_q,    BBG_VIOLET),
    ]:
        t = _trim(s.dropna(), CUT)
        if len(t):
            fig3.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(width=2),
                hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
            ))
    fig3.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig3.update_layout(**_bbg_layout(280))
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # Chart 4: Investment
    _sec_header("INVESTMENT — RESIDENTIAL vs NON-RESIDENTIAL")

    fig4 = go.Figure()
    for name, s, color, dash in [
        ("Non-Residential", nonres_q,     BBG_GREEN, "solid"),
        ("Residential",     residential_q, BBG_CYAN,  "dot"),
    ]:
        t = _trim(s.dropna(), CUT)
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
        f'Sources: BEA NIPA Table 1.1.2 · FRED · Quarterly annualized rates</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: LABOR  —  fixed range: 2Y
# ═══════════════════════════════════════════════════════════════════════════════

def _render_labor():
    CUT = -24   # 2 years of monthly data

    BLS_SERIES = {
        "nfp_total":    "CES0000000001",
        "nfp_private":  "CES0500000001",
        "nfp_mfg":      "CES3000000001",
        "nfp_construct":"CES2000000001",
        "nfp_retail":   "CES4200000001",
        "nfp_fin":      "CES5500000001",
        "nfp_gov":      "CES9000000001",
        "nfp_leisure":  "CES7000000001",
        "nfp_health":   "CES6500000001",
        "u3":           "LNS14000000",
        "u6":           "LNS13327709",
        "lfpr":         "LNS11300000",
        "avg_earn":     "CES0500000003",
        "avg_earn_yoy": "CES0500000008",
    }
    FRED_LABOR = {
        "jolts_open": "JTSJOL",
        "jolts_hire": "JTSHIL",
        "jolts_quit": "JTSQUL",
        "jolts_lay":  "JTSLAL",
        "init_claims":"ICSA",
    }

    with st.spinner("Loading BLS + FRED labor data..."):
        try:
            bls_raw = _bls(list(BLS_SERIES.values()), start_year=2015)
            bls = {k: bls_raw.get(v, pd.Series(dtype=float)) for k, v in BLS_SERIES.items()}
        except Exception as e:
            st.error(f"BLS fetch error: {e}")
            bls = {k: pd.Series(dtype=float) for k in BLS_SERIES}
        fred_labor = {}
        for k, v in FRED_LABOR.items():
            try:
                fred_labor[k] = _fred(v)
            except Exception:
                fred_labor[k] = pd.Series(dtype=float)

    nfp     = bls["nfp_total"]
    nfp_mom = nfp.diff()

    l_nfp   = _latest(nfp_mom)
    l_u3    = _latest(bls["u3"])
    l_u6    = _latest(bls["u6"])
    l_lfpr  = _latest(bls["lfpr"])
    l_wages = _latest(bls["avg_earn_yoy"])
    l_jolts = _latest(fred_labor["jolts_open"])

    kpis = [
        (f"{l_nfp:+,.0f}K"       if l_nfp   else "—", "NFP MOM",      "non-farm payrolls",        _color_val(l_nfp)),
        (f"{l_u3:.1f}%"          if l_u3    else "—", "UNEMPLOYMENT", "U-3 rate",                 _color_val(l_u3, invert=True)),
        (f"{l_u6:.1f}%"          if l_u6    else "—", "U-6 BROAD",    "underemployment",          _color_val(l_u6, invert=True)),
        (f"{l_lfpr:.1f}%"        if l_lfpr  else "—", "LFPR",         "labor force part.",        BBG_BLUE),
        (f"{l_wages:.1f}%"       if l_wages else "—", "WAGES YoY",    "avg hourly earnings",      _infl_color(l_wages) if l_wages else BBG_MUTED),
        (f"{l_jolts/1000:.1f}M"  if l_jolts else "—", "JOLTS OPEN",   "job openings",             BBG_CYAN),
    ]
    _kpi_strip(kpis)

    # Chart 1: NFP MoM
    _sec_header("NON-FARM PAYROLLS — MONTHLY CHANGE (000s)")

    fig1 = go.Figure()
    nfp_t = _trim(nfp_mom.dropna(), CUT)
    if len(nfp_t):
        fig1.add_trace(go.Bar(
            name="NFP MoM", x=nfp_t.index, y=nfp_t.values / 1000,
            marker_color=[BBG_GREEN if v >= 0 else BBG_RED for v in nfp_t.values],
            opacity=0.85,
            hovertemplate="<b>NFP</b>: %{y:+.0f}K<extra></extra>",
        ))
        ma3   = (nfp_mom / 1000).rolling(3).mean()
        ma3_t = _trim(ma3.dropna(), CUT)
        if len(ma3_t):
            fig1.add_trace(go.Scatter(
                name="3M Avg", x=ma3_t.index, y=ma3_t.values,
                line=dict(color=BBG_GOLD, width=2),
                hovertemplate="<b>3M Avg</b>: %{y:+.0f}K<extra></extra>",
            ))
    fig1.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig1.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # Chart 2: U3 + U6 + LFPR
    _sec_header("UNEMPLOYMENT RATES — U-3 · U-6 · LABOR FORCE PARTICIPATION")

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    for name, key, color, secondary in [
        ("U-3 Rate",  "u3",   BBG_RED,    False),
        ("U-6 Broad", "u6",   BBG_ORANGE, False),
        ("LFPR",      "lfpr", BBG_GREEN,  True),
    ]:
        t = _trim(bls[key].dropna(), CUT)
        if len(t):
            fig2.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(color=color, width=2),
                hovertemplate=f"<b>{name}</b>: %{{y:.1f}}%<extra></extra>",
            ), secondary_y=secondary)
    layout2 = _bbg_layout(280)
    fig2.update_layout(**layout2)
    fig2.update_yaxes(gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
                      tickfont=dict(size=9, color=BBG_MUTED),
                      title_text=None, secondary_y=False)
    fig2.update_yaxes(gridcolor=BBG_BORDER, linecolor=BBG_BORDER,
                      tickfont=dict(size=9, color=BBG_MUTED),
                      title_text=None, secondary_y=True)
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Chart 3: Sector table
    _sec_header("PAYROLLS BY SECTOR — MOM CHANGE")

    sector_rows = ""
    for name, key, color in [
        ("Private",   "nfp_private",   BBG_BLUE),
        ("Mfg",       "nfp_mfg",       BBG_GREEN),
        ("Construct", "nfp_construct", BBG_CYAN),
        ("Retail",    "nfp_retail",    BBG_VIOLET),
        ("Financial", "nfp_fin",       BBG_GOLD),
        ("Gov",       "nfp_gov",       BBG_RED),
        ("Leisure",   "nfp_leisure",   "#f97316"),
        ("Health",    "nfp_health",    "#14b8a6"),
    ]:
        s  = bls[key].diff()
        lv = _latest(s)
        pv = _prev(s)
        if lv is not None:
            chg     = lv - pv if pv is not None else 0
            cv      = BBG_GREEN if lv >= 0 else BBG_RED
            arrow   = "▲" if lv >= 0 else "▼"
            cv_chg  = BBG_GREEN if chg >= 0 else BBG_RED
            sector_rows += (
                f'<tr>'
                f'<td style="color:{color};font-weight:bold">{name}</td>'
                f'<td style="color:{BBG_GOLD};text-align:right">{lv/1000:+.0f}K</td>'
                f'<td style="color:{cv_chg};text-align:right">{arrow} {chg/1000:+.0f}K</td>'
                f'</tr>'
            )

    st.markdown(f"""
    <table class="t" style="margin-bottom:10px;max-width:500px">
      <thead><tr><th>SECTOR</th><th style="text-align:right">LAST MOM</th><th style="text-align:right">VS PREV</th></tr></thead>
      <tbody>{sector_rows}</tbody>
    </table>""", unsafe_allow_html=True)

    # Chart 4: JOLTS
    _sec_header("JOLTS — JOB OPENINGS · QUITS · LAYOFFS (Millions)")

    fig4 = go.Figure()
    for name, key, color, dash in [
        ("Job Openings", "jolts_open", BBG_CYAN,  "solid"),
        ("Hires",        "jolts_hire", BBG_GREEN, "dash"),
        ("Quits",        "jolts_quit", BBG_GOLD,  "dot"),
        ("Layoffs",      "jolts_lay",  BBG_RED,   "dot"),
    ]:
        s = fred_labor[key]
        t = _trim(s.dropna(), CUT)
        if len(t):
            fig4.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values / 1000,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}M<extra></extra>",
            ))
    fig4.update_layout(**_bbg_layout(300))
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    # Chart 5: Wages + Initial Claims — dual axis
    _sec_header("WAGES YoY & INITIAL CLAIMS")

    wages_s  = bls["avg_earn_yoy"].dropna()
    claims_s = fred_labor["init_claims"].dropna()
    wages_t  = _trim(wages_s, CUT)
    claims_t = _trim(claims_s, CUT)

    if len(wages_t) or len(claims_t):
        fig5 = make_subplots(specs=[[{"secondary_y": True}]])
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
        layout5 = _bbg_layout(260)
        fig5.update_layout(**layout5)
        fig5.update_yaxes(gridcolor=BBG_BORDER, zeroline=False,
                          tickfont=dict(size=9, color=BBG_MUTED),
                          title_text=None, secondary_y=False)
        fig5.update_yaxes(gridcolor=BBG_BORDER, zeroline=False,
                          tickfont=dict(size=9, color=BBG_MUTED),
                          title_text=None, secondary_y=True)
        st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f'<div style="color:{BBG_MUTED};font-size:9px;margin-top:6px;font-family:\'Courier New\',monospace">'
        f'Sources: BLS (CES payrolls, LNS unemployment, LFPR, wages) · FRED (JOLTS, Claims)</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: INFLATION  —  fixed range: 2Y
# ═══════════════════════════════════════════════════════════════════════════════

def _render_inflation():
    CUT = -24   # 2 years of monthly data

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
    }
    FRED_INFL = {
        "pce":          "PCEPI",
        "pce_core":     "PCEPILFE",
        "breakeven_5y": "T5YIE",
        "breakeven_10y":"T10YIE",
        "mich_1y":      "MICH",
        "mich_5y":      "EXPINF5YR",
    }
    COMPONENTS = {
        "cpi_shelter":   ("Shelter",        BBG_BLUE),
        "cpi_food_home": ("Food at Home",   BBG_GREEN),
        "cpi_food_out":  ("Food Away",      "#34d399"),
        "cpi_medical":   ("Medical Care",   BBG_VIOLET),
        "cpi_energy":    ("Energy",         BBG_GOLD),
        "cpi_new_cars":  ("New Vehicles",   BBG_MUTED),
        "cpi_used_cars": ("Used Vehicles",  "#64748b"),
        "cpi_apparel":   ("Apparel",        "#f97316"),
        "cpi_recreation":("Recreation",     BBG_CYAN),
        "cpi_gasoline":  ("Gasoline",       "#fb923c"),
    }

    with st.spinner("Loading BLS + FRED inflation data..."):
        try:
            cpi_raw = _bls(list(BLS_CPI.values()), start_year=2015)
            cpi = {k: cpi_raw.get(v, pd.Series(dtype=float)) for k, v in BLS_CPI.items()}
        except Exception as e:
            st.error(f"BLS CPI error: {e}")
            cpi = {k: pd.Series(dtype=float) for k in BLS_CPI}
        fred_infl = {}
        for k, v in FRED_INFL.items():
            try:
                fred_infl[k] = _fred(v)
            except Exception:
                fred_infl[k] = pd.Series(dtype=float)

    def yoy(s):
        return s.pct_change(12) * 100

    def mom(s):
        return s.pct_change(1) * 100

    cpi_all_yoy  = yoy(cpi["cpi_all"])
    cpi_core_yoy = yoy(cpi["cpi_core"])
    pce_yoy      = yoy(fred_infl["pce"])
    pce_core_yoy = yoy(fred_infl["pce_core"])
    be5          = fred_infl["breakeven_5y"]
    be10         = fred_infl["breakeven_10y"]
    mich_1y      = fred_infl["mich_1y"]

    l_cpi      = _latest(cpi_all_yoy)
    l_core     = _latest(cpi_core_yoy)
    l_pce      = _latest(pce_yoy)
    l_pce_core = _latest(pce_core_yoy)
    l_be5      = _latest(be5)
    l_mich     = _latest(mich_1y)

    latest_date = cpi_all_yoy.dropna().index[-1].strftime("%b %Y") if len(cpi_all_yoy.dropna()) else ""

    kpis = [
        (f"{l_cpi:.1f}%"      if l_cpi      else "—", "CPI HEADLINE",  f"prev {_prev(cpi_all_yoy):.1f}%" if _prev(cpi_all_yoy) else "", _infl_color(l_cpi)),
        (f"{l_core:.1f}%"     if l_core     else "—", "CORE CPI",      "ex Food & Energy",   _infl_color(l_core)),
        (f"{l_pce:.1f}%"      if l_pce      else "—", "PCE HEADLINE",  f"prev {_prev(pce_yoy):.1f}%" if _prev(pce_yoy) else "",         _infl_color(l_pce)),
        (f"{l_pce_core:.1f}%" if l_pce_core else "—", "CORE PCE",      "Fed target: 2.0%",   _infl_color(l_pce_core)),
        (f"{l_be5:.2f}%"      if l_be5      else "—", "5Y BREAKEVEN",  "TIPS market",        BBG_CYAN),
        (f"{l_mich:.1f}%"     if l_mich     else "—", "MICH 1Y EXPEC", "consumer survey",    BBG_VIOLET),
    ]
    _kpi_strip(kpis)

    # Chart 1: CPI vs PCE vs Core
    _sec_header(f"CPI · PCE · CORE — YoY%  ·  LATEST: {latest_date}")

    fig1 = go.Figure()
    fig1.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot",
                   annotation_text="Fed 2%",
                   annotation_font=dict(color=BBG_GREEN, size=9))
    for name, s, color, dash in [
        ("CPI Headline", cpi_all_yoy,  BBG_ORANGE, "solid"),
        ("Core CPI",     cpi_core_yoy, BBG_GOLD,   "dash"),
        ("PCE Headline", pce_yoy,      BBG_BLUE,   "solid"),
        ("Core PCE",     pce_core_yoy, BBG_CYAN,   "dot"),
    ]:
        t = _trim(s.dropna(), CUT)
        if len(t):
            fig1.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig1.update_layout(**_bbg_layout(320))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # Chart 2: Components YoY
    _sec_header("CPI COMPONENTS — YoY % BY CATEGORY")

    fig2 = go.Figure()
    for key, (label, color) in COMPONENTS.items():
        s = yoy(cpi[key])
        t = _trim(s.dropna(), CUT)
        if len(t):
            fig2.add_trace(go.Scatter(
                name=label, x=t.index, y=t.values,
                line=dict(color=color, width=1.5),
                hovertemplate=f"<b>{label}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig2.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot")
    fig2.update_layout(**_bbg_layout(320))
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Chart 3: Shelter vs Core ex-Shelter
    _sec_header("SHELTER vs CORE EX-SHELTER — YoY %")

    shelter_yoy     = yoy(cpi["cpi_shelter"])
    core_yoy        = cpi_core_yoy
    SHELTER_W       = 0.36
    core_ex_shelter = (core_yoy - SHELTER_W * shelter_yoy) / (1 - SHELTER_W)

    fig3 = go.Figure()
    fig3.add_hline(y=FED_TARGET, line_color=BBG_GREEN, line_width=1, line_dash="dot",
                   annotation_text="2%", annotation_font=dict(color=BBG_GREEN, size=9))
    for name, s, color, dash in [
        ("Shelter",           shelter_yoy,     BBG_BLUE,   "solid"),
        ("Core CPI",          core_yoy,        BBG_GOLD,   "dot"),
        ("Core ex-Shelter*",  core_ex_shelter, BBG_CYAN,   "solid"),
    ]:
        t = _trim(s.dropna(), CUT)
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
        f'margin-top:-8px">* Core ex-Shelter approx. con shelter weight 36%</div>',
        unsafe_allow_html=True
    )

    # Chart 4: MoM CPI
    _sec_header("CPI MOM % — HEADLINE vs CORE")

    fig4 = go.Figure()
    for name, s, color in [
        ("CPI MoM",      mom(cpi["cpi_all"]),  BBG_ORANGE),
        ("Core CPI MoM", mom(cpi["cpi_core"]), BBG_GOLD),
    ]:
        t = _trim(s.dropna(), CUT)
        if len(t):
            fig4.add_trace(go.Bar(
                name=name, x=t.index, y=t.values,
                marker_color=color, opacity=0.7,
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig4.add_hline(y=0, line_color=BBG_BORDER, line_width=1)
    fig4.update_layout(**_bbg_layout(260))
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    # Chart 5: Expectations
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
            t = _trim(fred_infl[key].dropna(), CUT)
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
            ("Michigan 1Y", "mich_1y", BBG_GOLD),
            ("Michigan 5Y", "mich_5y", BBG_BLUE),
        ]:
            t = _trim(fred_infl[key].dropna(), CUT)
            if len(t):
                fig5b.add_trace(go.Scatter(
                    name=name, x=t.index, y=t.values,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
                ))
        fig5b.update_layout(**_bbg_layout(260))
        st.plotly_chart(fig5b, use_container_width=True, config={"displayModeBar": False})

    # Snapshot table
    _sec_header("SNAPSHOT — LATEST VALUES")

    snap = [
        ("CPI Headline",     _latest(cpi_all_yoy),                _infl_color(_latest(cpi_all_yoy))),
        ("Core CPI",         _latest(cpi_core_yoy),               _infl_color(_latest(cpi_core_yoy))),
        ("PCE Headline",     _latest(pce_yoy),                    _infl_color(_latest(pce_yoy))),
        ("Core PCE",         _latest(pce_core_yoy),               _infl_color(_latest(pce_core_yoy))),
        ("Shelter YoY",      _latest(yoy(cpi["cpi_shelter"])),    BBG_BLUE),
        ("Energy YoY",       _latest(yoy(cpi["cpi_energy"])),     BBG_GOLD),
        ("Food at Home YoY", _latest(yoy(cpi["cpi_food_home"])),  BBG_GREEN),
        ("5Y Breakeven",     _latest(be5),                        BBG_CYAN),
        ("10Y Breakeven",    _latest(be10),                       BBG_VIOLET),
        ("Michigan 1Y",      _latest(mich_1y),                    BBG_GOLD),
    ]

    rows_html = ""
    for label, val, color in snap:
        v_str = f"{val:.2f}%" if val is not None else "—"
        rows_html += f'<tr><td>{label}</td><td style="color:{color};font-weight:bold;text-align:right">{v_str}</td></tr>'

    st.markdown(f"""
    <table class="t" style="max-width:400px">
      <thead><tr><th>INDICATOR</th><th style="text-align:right">LATEST YoY%</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)

    st.markdown(
        f'<div style="color:{BBG_MUTED};font-size:9px;margin-top:8px;font-family:\'Courier New\',monospace">'
        f'Sources: BLS (CPI CUUR series) · FRED (PCE, TIPS breakevens, Michigan Survey)</div>',
        unsafe_allow_html=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    subtabs = st.tabs(["GDP", "LABOR", "INFLATION"])

    with subtabs[0]:
        _render_gdp()

    with subtabs[1]:
        _render_labor()

    with subtabs[2]:
        _render_inflation()
