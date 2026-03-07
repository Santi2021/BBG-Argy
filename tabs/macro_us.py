"""
tabs/macro_us.py — MACRO US
Subtabs: GDP · LABOR · INFLATION
Lógica 1:1 con MacroTerminal — solo estilos BBG Argy
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime as _dt

# ═══════════════════════════════════════════════════════════════════════════════
#  PALETTE BBG Argy
# ═══════════════════════════════════════════════════════════════════════════════
BG      = "#000000"
BG2     = "#0a0a0a"
GRID    = "#222222"
TEXT    = "#cccccc"
MUTED   = "#555555"
ORANGE  = "#ff6600"
GOLD    = "#ffcc00"
GREEN   = "#00ff41"
RED     = "#ff3b3b"
BLUE    = "#60a5fa"
CYAN    = "#00d4ff"
VIOLET  = "#a78bfa"
AMBER   = "#f59e0b"
WHITE   = "#ffffff"


# ═══════════════════════════════════════════════════════════════════════════════
#  API KEYS
# ═══════════════════════════════════════════════════════════════════════════════
FRED_KEY = "3e448a2c51c7a8837aaf72757836a7b7"
BEA_KEY  = "081DA2FC-1900-47A0-A40B-49C31925E395"
BLS_KEY  = "94e0e0f57c5e4d5397ba3898198927ae"

# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT — BBG style, NO title field (causes "undefined")
# ═══════════════════════════════════════════════════════════════════════════════

def _layout(height=360):
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG2,
        font=dict(family="'Courier New', monospace", color=TEXT, size=11),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, showgrid=False,
                   tickfont=dict(size=9, color='#aaaaaa')),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=True,
                   zerolinecolor="#333",
                   tickfont=dict(size=9, color='#aaaaaa')),
        hovermode="x unified",
        barmode="relative",
        height=height,
        margin=dict(l=55, r=20, t=30, b=36),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=9, family="Courier New"),
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
    )

def _layout_sub(height=340):
    """Layout for make_subplots figures — no xaxis/yaxis keys (causes 'undefined')."""
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG2,
        font=dict(family="'Courier New', monospace", color=TEXT, size=11),
        hovermode="x unified",
        height=height,
        margin=dict(l=55, r=20, t=30, b=36),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=9, family="Courier New"),
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
    )

def _style_sub_axes(fig, secondary=True):
    """Apply BBG grid style to all axes of a subplot figure."""
    ax_style = dict(gridcolor=GRID, linecolor=GRID, zeroline=False,
                    tickfont=dict(size=9, color='#aaaaaa'), title_text=None,
                    showgrid=True)
    fig.update_xaxes(**ax_style)
    fig.update_yaxes(**ax_style)

def _sec(text):
    st.markdown(
        f'<div style="color:{ORANGE};font-size:9px;font-weight:bold;letter-spacing:2px;'
        f'text-transform:uppercase;border-bottom:1px solid #333;padding-bottom:3px;'
        f'margin:18px 0 6px 0;font-family:\'Courier New\',monospace">{text}</div>',
        unsafe_allow_html=True
    )

def _kpi_strip(kpis):
    items = ""
    for val, label, sub, color in kpis:
        items += (
            f'<div class="kpi-item">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color}">{val}</div>'
            f'<div class="kpi-sub" style="color:{MUTED}">{sub}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="kpi-strip">{items}</div>', unsafe_allow_html=True)

def _cv(val, invert=False):
    if val is None: return MUTED
    try:
        v = float(val)
        if invert: return GREEN if v < 0 else RED
        return GREEN if v > 0 else (RED if v < 0 else MUTED)
    except: return MUTED

def _ic(val):
    try:
        v = float(val)
        if v > 3.5: return RED
        if v > 2.5: return GOLD
        return GREEN
    except: return MUTED

def _lat(s):
    d = s.dropna()
    return float(d.iloc[-1]) if len(d) else None

def _prv(s):
    d = s.dropna()
    return float(d.iloc[-2]) if len(d) >= 2 else None

def _trim(s, cut):
    return s.iloc[cut:] if cut != 0 else s


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA — BEA
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def _load_bea():
    params = dict(
        UserID=BEA_KEY, method="GetData", DataSetName="NIPA",
        TableName="T10102", Frequency="Q", Year="ALL", ResultFormat="JSON"
    )
    resp = requests.get("https://apps.bea.gov/api/data", params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()["BEAAPI"]["Results"]["Data"]
    df = pd.DataFrame(rows)
    df["DataValue"] = (df["DataValue"].astype(str)
                       .str.replace(",","",regex=False)
                       .pipe(pd.to_numeric, errors="coerce").fillna(0))
    def parse_q(p):
        p = str(p).strip()
        if "Q" in p:
            yr, q = p.split("Q")
            return pd.Timestamp(f"{yr}-{int(q)*3-2:02d}-01")
        return pd.NaT
    df["Date"] = df["TimePeriod"].apply(parse_q)
    return df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

def _gs(df, code):
    return df[df["SeriesCode"]==code].set_index("Date")["DataValue"].sort_index()

def _qlabel(ts):
    return f"{ts.year} Q{(ts.month-1)//3+1}"


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA — BLS
# ═══════════════════════════════════════════════════════════════════════════════

BLS_IDS = {
    "payrolls_total":   "CES0000000001",
    "payrolls_private": "CES0500000001",
    "payrolls_govt":    "CES9000000001",
    "unemployment":     "LNS14000000",
    "u6":               "LNS13327709",
    "participation":    "LNS11300000",
    "wages_ahe":        "CES0500000003",
    # sectors
    "sec_mining":       "CES1000000001",
    "sec_construction": "CES2000000001",
    "sec_manufacturing":"CES3000000001",
    "sec_trade_trans":  "CES4000000001",
    "sec_information":  "CES5000000001",
    "sec_financial":    "CES5500000001",
    "sec_prof_biz":     "CES6000000001",
    "sec_edu_health":   "CES6500000001",
    "sec_leisure":      "CES7000000001",
    "sec_other":        "CES8000000001",
    "sec_govt_federal": "CES9091000001",
    "sec_govt_state":   "CES9092000001",
    "sec_govt_local":   "CES9093000001",
}

BLS_CPI_IDS = {
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

@st.cache_data(ttl=3600, show_spinner=False)
def _load_bls(series_dict: dict, start_year=2015):
    payload = dict(
        seriesid=list(series_dict.values()),
        startyear=str(start_year),
        endyear=str(_dt.now().year),
        registrationkey=BLS_KEY,
        annualaverage=False,
    )
    resp = requests.post(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=json.dumps(payload),
        headers={"Content-type": "application/json"},
        timeout=45
    )
    resp.raise_for_status()
    rows = []
    for series in resp.json().get("Results", {}).get("series", []):
        sid = series["seriesID"]
        for obs in series.get("data", []):
            period = obs.get("period","")
            if not period.startswith("M") or period == "M13":
                continue
            try:
                month = int(period[1:])
                year  = int(obs["year"])
                val   = float(obs["value"])
                rows.append({"series_id": sid, "date": pd.Timestamp(f"{year}-{month:02d}-01"), "value": val})
            except: continue
    return pd.DataFrame(rows).sort_values(["series_id","date"]).reset_index(drop=True)

def _bls_s(df, sid):
    return df[df["series_id"]==sid].set_index("date")["value"].sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA — FRED
# ═══════════════════════════════════════════════════════════════════════════════

FRED_LABOR = {"jolts_openings":"JTSJOL","jolts_hires":"JTSHIL","jolts_quits":"JTSQUL","jolts_layoffs":"JTSLDL"}
FRED_INFL  = {"pce":"PCEPI","pce_core":"PCEPILFE","breakeven_5y":"T5YIE","breakeven_10y":"T10YIE","mich_1y":"MICH","mich_5y":"EXPINF5YR"}

@st.cache_data(ttl=3600, show_spinner=False)
def _load_fred(series_dict: dict, start="2010-01-01"):
    rows = []
    for name, sid in series_dict.items():
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = dict(series_id=sid, observation_start=start, api_key=FRED_KEY, file_type="json")
            resp = requests.get(url, params=params, timeout=20)
            for obs in resp.json().get("observations",[]):
                try:
                    rows.append({"series_id": name, "date": pd.Timestamp(obs["date"]), "value": float(obs["value"])})
                except: continue
        except: continue
    return pd.DataFrame(rows).sort_values(["series_id","date"]).reset_index(drop=True)

def _fred_s(df, name):
    return df[df["series_id"]==name].set_index("date")["value"].sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: GDP  —  5Y fixed
# ═══════════════════════════════════════════════════════════════════════════════

GDP_CODES = {
    "gdp":"A191RL","consumption":"DPCERY","durables":"DDURRY","nondurables":"DNDGRY",
    "services":"DSERRY","investment":"A006RY","nonresidential":"A008RY","residential":"A011RY",
    "inventories":"A014RY","net_exports":"A019RY","exports":"A020RY","imports":"A021RY",
    "government":"A822RY","federal":"A823RY","state_local":"A829RY",
}
GDP_COLORS = {
    "consumption":"#3b82f6","investment":"#00ff41","government":GOLD,"net_exports":RED,
    "durables":"#f59e0b","nondurables":"#f97316","services":"#3b82f6",
    "residential":"#34d399","nonresidential":"#f59e0b","inventories":"#a78bfa",
    "federal":"#fbbf24","state_local":"#92400e","exports":"#4ade80","imports":"#f87171",
    "final_sales":VIOLET,"inv_change":"#7c3aed",
}

def _stacked_fig(series_list, common, quarters):
    fig = go.Figure()
    for name, s, color in series_list:
        vals = s.reindex(common).fillna(0).values
        fig.add_trace(go.Bar(
            name=name, x=quarters, y=vals,
            marker_color=color, marker_line_color=BG2, marker_line_width=0.8,
            hovertemplate=f"<b>{name}</b>: %{{y:+.2f}} pp<extra></extra>",
        ))
    return fig

def _add_diamond(fig, total_s, common, quarters, label):
    vals = total_s.reindex(common).fillna(0).values
    fig.add_trace(go.Scatter(
        name=label, x=quarters, y=vals, mode="markers",
        marker=dict(symbol="diamond", size=7, color=WHITE),
        hovertemplate=f"<b>{label}</b>: %{{y:+.2f}} pp<extra></extra>",
    ))

def _render_gdp():
    CUT = -20   # 5Y quarterly

    with st.spinner("Loading BEA data..."):
        try:
            df = _load_bea()
        except Exception as e:
            st.error(f"BEA error: {e}"); return

    if df.empty:
        st.error("BEA returned no data."); return

    gdp  = _gs(df, GDP_CODES["gdp"])
    cons = _gs(df, GDP_CODES["consumption"])
    inv  = _gs(df, GDP_CODES["investment"])
    gov  = _gs(df, GDP_CODES["government"])
    nx   = _gs(df, GDP_CODES["net_exports"])

    common = gdp.index
    for s in [cons, inv, gov, nx]:
        if len(s): common = common.intersection(s.index)
    common   = common.sort_values()
    common   = common[CUT:] if CUT != 0 else common
    quarters = [_qlabel(d) for d in common]

    l_gdp  = _lat(gdp)
    l_cons = _lat(cons)
    l_inv  = _lat(inv)
    l_gov  = _lat(gov)
    l_nx   = _lat(nx)

    _kpi_strip([
        (f"{l_gdp:.1f}%"  if l_gdp  else "—", "GDP QoQ",     "annualized",        _cv(l_gdp)),
        (f"{l_cons:.1f}%" if l_cons else "—", "CONSUMPTION", "PCE contribution",  _cv(l_cons)),
        (f"{l_inv:.1f}%"  if l_inv  else "—", "INVESTMENT",  "gross private",     _cv(l_inv)),
        (f"{l_gov:.1f}%"  if l_gov  else "—", "GOVERNMENT",  "federal + state",   _cv(l_gov)),
        (f"{l_nx:.1f}%"   if l_nx   else "—", "NET EXPORTS", "exports - imports", _cv(l_nx)),
    ])

    # Main chart: stacked bars + diamond total (igual al original)
    _sec("CONTRIBUTIONS TO REAL GDP GROWTH")
    fig = go.Figure()
    for name, key, color in [
        ("Consumption", cons, GDP_COLORS["consumption"]),
        ("Investment",  inv,  GDP_COLORS["investment"]),
        ("Government",  gov,  GDP_COLORS["government"]),
        ("Net Exports", nx,   GDP_COLORS["net_exports"]),
    ]:
        vals = name.replace("","") and s.reindex(common).fillna(0).values if False else key.reindex(common).fillna(0).values
        fig.add_trace(go.Bar(
            name=name, x=quarters, y=vals,
            marker_color=color, marker_line_color=BG2, marker_line_width=0.8,
            hovertemplate=f"<b>{name}</b>: %{{y:+.2f}} pp<extra></extra>",
        ))
    gdp_vals = gdp.reindex(common).fillna(0).values
    fig.add_trace(go.Scatter(
        name="Total GDP", x=quarters, y=gdp_vals, mode="markers",
        marker=dict(symbol="diamond", size=7, color=WHITE),
        hovertemplate="<b>Total GDP</b>: %{y:+.2f}%<extra></extra>",
    ))
    fig.update_layout(**_layout(400))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Drill-downs (igual al original)
    _sec("DRILL-DOWN")
    dtabs = st.tabs(["Consumption", "Investment", "Government", "Net Exports", "Final Sales"])

    def _drill_layout(subtitle):
        """Layout for drill-down charts — legend below subtitle, no overlap."""
        lay = _layout(320)
        lay["margin"] = dict(l=55, r=20, t=62, b=36)
        lay["legend"]["y"] = 1.0
        lay["legend"]["yanchor"] = "bottom"
        lay["annotations"] = [dict(
            text=subtitle, xref="paper", yref="paper",
            x=0, y=1.0, xanchor="left", yanchor="bottom",
            font=dict(family="'Courier New',monospace", size=9, color="#888"),
            showarrow=False,
        )]
        return lay

    with dtabs[0]:
        fig = _stacked_fig([
            ("Durables",    _gs(df,GDP_CODES["durables"]),    GDP_COLORS["durables"]),
            ("Nondurables", _gs(df,GDP_CODES["nondurables"]), GDP_COLORS["nondurables"]),
            ("Services",    _gs(df,GDP_CODES["services"]),    GDP_COLORS["services"]),
        ], common, quarters)
        _add_diamond(fig, cons, common, quarters, "Total PCE")
        fig.update_layout(**_drill_layout("Durables · Nondurables · Services   ◆ = Total PCE contribution"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with dtabs[1]:
        fig = _stacked_fig([
            ("Residential",    _gs(df,GDP_CODES["residential"]),    GDP_COLORS["residential"]),
            ("Nonresidential", _gs(df,GDP_CODES["nonresidential"]), GDP_COLORS["nonresidential"]),
            ("Inventories",    _gs(df,GDP_CODES["inventories"]),    GDP_COLORS["inventories"]),
        ], common, quarters)
        _add_diamond(fig, inv, common, quarters, "Total Investment")
        fig.update_layout(**_drill_layout("Residential · Nonresidential · Inventories   ◆ = Total Investment"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with dtabs[2]:
        fig = _stacked_fig([
            ("Federal",       _gs(df,GDP_CODES["federal"]),     GDP_COLORS["federal"]),
            ("State & Local", _gs(df,GDP_CODES["state_local"]), GDP_COLORS["state_local"]),
        ], common, quarters)
        _add_diamond(fig, gov, common, quarters, "Total Government")
        fig.update_layout(**_drill_layout("Federal · State & Local   ◆ = Total Government"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with dtabs[3]:
        fig = _stacked_fig([
            ("Exports", _gs(df,GDP_CODES["exports"]), GDP_COLORS["exports"]),
            ("Imports", _gs(df,GDP_CODES["imports"]), GDP_COLORS["imports"]),
        ], common, quarters)
        _add_diamond(fig, nx, common, quarters, "Net Exports")
        fig.update_layout(**_drill_layout("Exports · Imports   ◆ = Net Exports"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with dtabs[4]:
        inv_ch = _gs(df,GDP_CODES["inventories"]).reindex(common).fillna(0)
        fs     = gdp.reindex(common).fillna(0) - inv_ch
        fig = _stacked_fig([
            ("Final Sales",      fs,     GDP_COLORS["final_sales"]),
            ("Inventory Change", inv_ch, GDP_COLORS["inv_change"]),
        ], common, quarters)
        _add_diamond(fig, gdp.reindex(common), common, quarters, "Total GDP")
        fig.update_layout(**_drill_layout("Final Sales · Inventory Change   ◆ = Total GDP"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Heatmap table — last 8 quarters — pure HTML Bloomberg style
    _sec("LAST 8 QUARTERS — CONTRIBUTIONS (pp)")
    last8 = common[-8:]
    ql8   = [_qlabel(d) for d in last8]

    # ordered series with indent markers
    series_map_ordered = [
        ("GDP",             gdp,                                    False),
        ("Consumption",     cons,                                   False),
        ("  Durables",      _gs(df,GDP_CODES["durables"]),          True),
        ("  Nondurables",   _gs(df,GDP_CODES["nondurables"]),       True),
        ("  Services",      _gs(df,GDP_CODES["services"]),          True),
        ("Investment",      inv,                                    False),
        ("  Residential",   _gs(df,GDP_CODES["residential"]),       True),
        ("  Nonresidential",_gs(df,GDP_CODES["nonresidential"]),    True),
        ("  Inventories",   _gs(df,GDP_CODES["inventories"]),       True),
        ("Government",      gov,                                    False),
        ("Net Exports",     nx,                                     False),
    ]

    def _cell_bg_fg(v):
        if   v >  2.0: return "#0a3d1f","#4ade80"
        elif v >  0.5: return "#062910","#34d399"
        elif v >  0.0: return "#041a0a","#6ee7b7"
        elif v > -0.5: return "#1a0505","#fca5a5"
        elif v > -2.0: return "#2a0606","#f87171"
        else:          return "#3d0808","#ef4444"

    T  = "font-family:'Courier New',monospace;"
    TH = f"padding:4px 10px;{T}font-size:9px;font-weight:bold;letter-spacing:1px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;white-space:nowrap;"
    TH0= f"padding:4px 12px;{T}font-size:9px;font-weight:bold;letter-spacing:1px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;min-width:150px;"

    hdr = f'<tr><th style="{TH0}">SERIES</th>' + "".join(f'<th style="{TH}">{q}</th>' for q in ql8) + "</tr>"

    rows_html = ""
    for i,(label, s, indented) in enumerate(series_map_ordered):
        vals     = s.reindex(last8).fillna(0).values
        is_top   = not indented
        top_bdr  = "border-top:1px solid #2a2a2a;" if is_top and i > 0 else ""
        fw       = "font-weight:bold;" if is_top else "font-weight:normal;"
        ind_px   = "padding-left:22px;" if indented else "padding-left:12px;"
        name_td  = f"padding:3px 10px;{T}font-size:10px;{fw}{ind_px}color:#ccc;background:#000;border-right:1px solid #333;{top_bdr}white-space:nowrap;"
        rows_html += f'<tr><td style="{name_td}">{label.strip()}</td>'
        for v in vals:
            bg, fg = _cell_bg_fg(v)
            sign   = "+" if v >= 0 else ""
            td     = f"padding:3px 10px;{T}font-size:10px;font-weight:bold;text-align:right;background:{bg};color:{fg};border-right:1px solid #111;{top_bdr}white-space:nowrap;"
            rows_html += f'<td style="{td}">{sign}{v:.2f}</td>'
        rows_html += "</tr>"

    st.markdown(f"""
    <div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:4px;">
      <table style="border-collapse:collapse;width:100%;">
        <thead>{hdr}</thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <div style="color:#444;font-size:9px;{T}margin-bottom:10px;">
      BEA NIPA Table 1.1.2 &nbsp;·&nbsp; Quarterly annualized rates &nbsp;·&nbsp; Contributions in pp
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: LABOR  —  2Y fixed
# ═══════════════════════════════════════════════════════════════════════════════

def _render_labor():
    CUT = -24   # 2Y monthly

    with st.spinner("Loading BLS + FRED labor data..."):
        try:
            bls_df  = _load_bls(BLS_IDS, start_year=2015)
        except Exception as e:
            st.error(f"BLS error: {e}"); bls_df = pd.DataFrame()
        try:
            fred_df = _load_fred(FRED_LABOR)
        except Exception as e:
            st.warning(f"FRED JOLTS error: {e}"); fred_df = pd.DataFrame()

    def gs(sid):
        if bls_df.empty: return pd.Series(dtype=float)
        return _bls_s(bls_df, BLS_IDS.get(sid, sid))
    def fs(name):
        if fred_df.empty: return pd.Series(dtype=float)
        return _fred_s(fred_df, name)

    pay_tot  = gs("payrolls_total")
    pay_priv = gs("payrolls_private")
    pay_govt = gs("payrolls_govt")
    unemp    = gs("unemployment")
    u6       = gs("u6")
    part     = gs("participation")
    wages    = gs("wages_ahe")

    pay_ch      = pay_tot.diff()
    pay_priv_ch = pay_priv.diff()
    pay_govt_ch = pay_govt.diff()
    wages_yoy   = wages.pct_change(12) * 100

    def trim(s): return _trim(s, CUT)

    pay_ch_t      = trim(pay_ch)
    pay_priv_ch_t = trim(pay_priv_ch)
    pay_govt_ch_t = trim(pay_govt_ch)
    unemp_t       = trim(unemp)
    u6_t          = trim(u6)
    part_t        = trim(part)
    wages_yoy_t   = trim(wages_yoy)

    l_pay   = _lat(pay_ch)
    l_u     = _lat(unemp)
    l_part  = _lat(part)
    l_wages = _lat(wages_yoy)
    p_pay   = _prv(pay_ch)
    p_u     = _prv(unemp)

    _kpi_strip([
        (f"{l_pay:+,.0f}K" if l_pay else "—",   "NFP MOM",      f"prev {p_pay:+,.0f}K" if p_pay else "", _cv(l_pay)),
        (f"{l_u:.1f}%"     if l_u   else "—",   "UNEMPLOYMENT", f"prev {p_u:.1f}%" if p_u else "",       _cv(l_u, invert=True)),
        (f"{_lat(u6):.1f}%" if _lat(u6) else "—","U-6 BROAD",   "underemployment",                        _cv(_lat(u6), invert=True)),
        (f"{l_part:.1f}%"  if l_part else "—",  "LFPR",         "labor force part.",                      BLUE),
        (f"{l_wages:.1f}%" if l_wages else "—", "WAGES YoY",    "avg hourly earnings",                    _ic(l_wages) if l_wages else MUTED),
        (f"{_lat(fs('jolts_openings'))/1000:.1f}M" if _lat(fs('jolts_openings')) else "—", "JOLTS OPEN", "job openings", CYAN),
    ])

    # ── Section 1: Payrolls ──────────────────────────────────────────────────
    _sec("NONFARM PAYROLLS — MONTHLY CHANGE (000s)")

    view_opt = st.radio("View", ["Total", "Private vs Government"],
                        horizontal=True, label_visibility="collapsed", key="labor_view")

    ma3  = pay_ch_t.rolling(3).mean()
    fig1 = go.Figure()
    if view_opt == "Total":
        fig1.add_trace(go.Bar(
            name="Payrolls MoM", x=pay_ch_t.index, y=pay_ch_t.values,
            marker_color=[GREEN if v >= 0 else RED for v in pay_ch_t.values],
            hovertemplate="<b>%{x|%b %Y}</b>: %{y:+,.0f}K<extra></extra>",
        ))
        fig1.add_trace(go.Scatter(
            name="3M Avg", x=ma3.index, y=ma3.values,
            line=dict(color=CYAN, width=2, dash="dot"),
            hovertemplate="<b>3M Avg</b>: %{y:+,.0f}K<extra></extra>",
        ))
    else:
        fig1.add_trace(go.Bar(
            name="Private", x=pay_priv_ch_t.index, y=pay_priv_ch_t.values,
            marker_color=BLUE, opacity=0.85,
            hovertemplate="<b>Private</b>: %{y:+,.0f}K<extra></extra>",
        ))
        fig1.add_trace(go.Bar(
            name="Government", x=pay_govt_ch_t.index, y=pay_govt_ch_t.values,
            marker_color=AMBER, opacity=0.85,
            hovertemplate="<b>Government</b>: %{y:+,.0f}K<extra></extra>",
        ))
    fig1.add_hline(y=0, line_color="#333", line_width=1)
    fig1.update_layout(**_layout(340))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # ── Section 2: Payrolls by sector — BBG-style stacked chart + HTML data table
    _sec("NONFARM PAYROLLS — SECTOR BREAKDOWN")

    # Sector config: (label_short, BLS_ID, color, group)
    SECTOR_CFG = [
        ("Goods Producing",       BLS_IDS["sec_mining"],       "#f59e0b",  "goods"),
        ("Construction",          BLS_IDS["sec_construction"],  "#fbbf24",  "goods"),
        ("Manufacturing",         BLS_IDS["sec_manufacturing"], "#d97706",  "goods"),
        ("Trade & Transport",     BLS_IDS["sec_trade_trans"],   "#3b82f6",  "services"),
        ("Information",           BLS_IDS["sec_information"],   "#8b5cf6",  "services"),
        ("Financial",             BLS_IDS["sec_financial"],     "#06b6d4",  "services"),
        ("Prof & Business",       BLS_IDS["sec_prof_biz"],      "#10b981",  "services"),
        ("Education & Health",    BLS_IDS["sec_edu_health"],    "#34d399",  "services"),
        ("Leisure & Hospitality", BLS_IDS["sec_leisure"],       "#f97316",  "services"),
        ("Other Services",        BLS_IDS["sec_other"],         "#6b7280",  "services"),
        ("Government",            BLS_IDS["sec_govt_federal"],  "#a78bfa",  "govt"),
    ]
    # Wider history for the chart
    SECTOR_CUT = -30

    sector_series = {}
    for label, sid, color, group in SECTOR_CFG:
        if bls_df.empty: continue
        s = _bls_s(bls_df, sid).diff()
        sector_series[label] = (s, color)

    # ── Stacked bar chart (BBG-style: stacked contributions, total as white line)
    fig_sec = go.Figure()
    total_nfp = pay_ch  # already computed above

    for label, (s, color) in sector_series.items():
        t = _trim(s.dropna(), SECTOR_CUT)
        if len(t):
            fig_sec.add_trace(go.Bar(
                name=label, x=t.index, y=t.values,
                marker_color=color, marker_line_width=0,
                hovertemplate=f"<b>{label}</b>: %{{y:+.0f}}K<extra></extra>",
            ))
    # Total white line overlay
    tot_t = _trim(total_nfp.dropna(), SECTOR_CUT)
    if len(tot_t):
        fig_sec.add_trace(go.Scatter(
            name="Total NFP", x=tot_t.index, y=tot_t.values,
            line=dict(color=WHITE, width=2),
            mode="lines",
            hovertemplate="<b>Total NFP</b>: %{y:+.0f}K<extra></extra>",
        ))
    fig_sec.add_hline(y=0, line_color="#333", line_width=1)
    lay_sec = _layout(380)
    lay_sec["barmode"] = "relative"
    lay_sec["margin"] = dict(l=55, r=20, t=80, b=36)
    lay_sec["legend"] = dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=9, family="Courier New"),
        orientation="h",
        yanchor="bottom", y=1.0,
        xanchor="left", x=0,
        tracegroupgap=0,
    )
    fig_sec.update_layout(**lay_sec)
    st.plotly_chart(fig_sec, use_container_width=True, config={"displayModeBar": False})

    # ── Integrated data table below chart — pure HTML, Bloomberg style ──────

    # Build last N months columns
    N_MONTHS = 8
    heat_data = {}
    for label, (s, color) in sector_series.items():
        ch = s.dropna()
        if len(ch) >= N_MONTHS:
            heat_data[label] = {"series": ch, "color": color}

    if heat_data:
        # Get the common last N dates
        all_idx = sorted(set.intersection(*[set(v["series"].index) for v in heat_data.values()]))
        col_dates = sorted(all_idx)[-N_MONTHS:]
        col_labels = [d.strftime("%b-%y") for d in col_dates]

        def _td_style(val):
            """Return (bg, fg) for a payroll change value in thousands."""
            if   val >  80: bg,fg = "#0a3d1f","#4ade80"
            elif val >  30: bg,fg = "#062910","#34d399"
            elif val >   0: bg,fg = "#041a0a","#6ee7b7"
            elif val > -30: bg,fg = "#1a0505","#fca5a5"
            elif val > -80: bg,fg = "#2a0606","#f87171"
            else:           bg,fg = "#3d0808","#ef4444"
            return bg, fg

        T2 = "font-family:'Courier New',monospace;"
        TH2  = f"padding:4px 10px;{T2}font-size:9px;font-weight:bold;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;white-space:nowrap;"
        TH2a = f"padding:4px 12px;{T2}font-size:9px;font-weight:bold;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;min-width:160px;"

        hdr2 = f'<tr><th style="{TH2a}">SERIES</th>'
        for cl in col_labels:
            hdr2 += f'<th style="{TH2}">{cl}</th>'
        hdr2 += "</tr>"

        body2 = ""
        for label, info in heat_data.items():
            color = info["color"]
            vals  = [info["series"].get(d, float("nan")) for d in col_dates]
            name_td = f"padding:3px 12px;{T2}font-size:10px;font-weight:bold;color:{color};background:#000;border-right:1px solid #333;white-space:nowrap;"
            body2 += f'<tr><td style="{name_td}">{label}</td>'
            for v in vals:
                if pd.isna(v):
                    body2 += f'<td style="padding:3px 10px;{T2}font-size:10px;text-align:right;background:#0a0a0a;color:#333;border-right:1px solid #111;">—</td>'
                else:
                    bg, fg = _td_style(v)
                    sign   = "+" if v >= 0 else ""
                    td2    = f"padding:3px 10px;{T2}font-size:10px;font-weight:bold;text-align:right;background:{bg};color:{fg};border-right:1px solid #111;white-space:nowrap;"
                    body2 += f'<td style="{td2}">{sign}{v:.0f}K</td>'
            body2 += "</tr>"

        st.markdown(f"""
        <div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:4px;">
          <table style="border-collapse:collapse;width:100%;">
            <thead>{hdr2}</thead>
            <tbody>{body2}</tbody>
          </table>
        </div>
        <div style="color:#444;font-size:9px;{T2}margin-bottom:10px;">
          BLS CES &nbsp;·&nbsp; Monthly net change in thousands &nbsp;·&nbsp; Seasonally adjusted
        </div>""", unsafe_allow_html=True)

    # ── Section 3: Unemployment + LFPR ──────────────────────────────────────
    _sec("UNEMPLOYMENT & LABOR FORCE PARTICIPATION")

    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
    fig3.add_trace(go.Scatter(
        name="Unemployment U-3", x=unemp_t.index, y=unemp_t.values,
        line=dict(color=RED, width=2),
        hovertemplate="<b>U-3</b>: %{y:.1f}%<extra></extra>",
    ), secondary_y=False)
    fig3.add_trace(go.Scatter(
        name="U-6 Broad", x=u6_t.index, y=u6_t.values,
        line=dict(color=ORANGE, width=1.5, dash="dot"),
        hovertemplate="<b>U-6</b>: %{y:.1f}%<extra></extra>",
    ), secondary_y=False)
    fig3.add_trace(go.Scatter(
        name="Participation Rate", x=part_t.index, y=part_t.values,
        line=dict(color=CYAN, width=2),
        hovertemplate="<b>Participation</b>: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig3.update_layout(**_layout_sub(340))
    _style_sub_axes(fig3)
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # ── Section 4: Wages ────────────────────────────────────────────────────
    _sec("AVERAGE HOURLY EARNINGS — YoY %")

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        name="AHE YoY%", x=wages_yoy_t.index, y=wages_yoy_t.values,
        line=dict(color=AMBER, width=2.5),
        hovertemplate="<b>Wages YoY</b>: %{y:.2f}%<extra></extra>",
    ))
    lay4 = _layout(240)
    lay4['yaxis']['autorange'] = True
    lay4['yaxis']['rangemode'] = 'normal'
    fig4.update_layout(**lay4)
    st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})

    # ── Section 5: JOLTS ────────────────────────────────────────────────────
    _sec("JOLTS DEEP DIVE")

    if fred_df.empty:
        st.warning("FRED data unavailable.")
    else:
        openings = fs("jolts_openings")
        hires    = fs("jolts_hires")
        quits    = fs("jolts_quits")
        layoffs  = fs("jolts_layoffs")

        op_t  = trim(openings)
        hi_t  = trim(hires)
        qu_t  = trim(quits)
        lay_t = trim(layoffs)

        jtabs = st.tabs(["Beveridge Curve", "Flows (Hires/Quits/Layoffs)", "Openings vs Unemployment"])

        with jtabs[0]:
            common_idx = openings.index.intersection(unemp.index).sort_values()
            if len(common_idx) > 12:
                op_bev = openings.reindex(common_idx)
                un_bev = unemp.reindex(common_idx)
                n      = len(common_idx)
                fig_b  = go.Figure()
                fig_b.add_trace(go.Scatter(
                    name="Beveridge Curve",
                    x=un_bev.values, y=op_bev.values / 1000,
                    mode="lines+markers",
                    line=dict(color="#1e1e3a", width=1),
                    marker=dict(size=6, color=list(range(n)),
                                colorscale=[[0,"#1e3a5f"],[0.5,BLUE],[1,CYAN]],
                                showscale=True,
                                colorbar=dict(thickness=8, len=0.5,
                                              tickfont=dict(color=MUTED,size=8))),
                    hovertemplate="<b>%{customdata}</b><br>U: %{x:.1f}%<br>Openings: %{y:.2f}M<extra></extra>",
                    customdata=[d.strftime("%b %Y") for d in common_idx],
                ))
                fig_b.add_trace(go.Scatter(
                    name="Latest", x=[un_bev.iloc[-1]], y=[op_bev.iloc[-1]/1000],
                    mode="markers", marker=dict(symbol="star",size=14,color=CYAN),
                    hovertemplate=f"<b>Latest</b>: {common_idx[-1].strftime('%b %Y')}<extra></extra>",
                ))
                lb = _layout(400)
                lb["hovermode"] = "closest"
                lb["showlegend"] = False
                fig_b.update_layout(**lb)
                st.plotly_chart(fig_b, use_container_width=True, config={"displayModeBar": False})

        with jtabs[1]:
            fig_fl = go.Figure()
            for name, s, color in [
                ("Hires",   hi_t,  GREEN),
                ("Quits",   qu_t,  AMBER),
                ("Layoffs", lay_t, RED),
            ]:
                fig_fl.add_trace(go.Scatter(
                    name=name, x=s.index, y=s.values/1000,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}M<extra></extra>",
                ))
            fig_fl.update_layout(**_layout(340))
            st.plotly_chart(fig_fl, use_container_width=True, config={"displayModeBar": False})

        with jtabs[2]:
            common_idx2 = openings.index.intersection(unemp.index).sort_values()
            op2 = trim(openings.reindex(common_idx2))
            un2 = trim(unemp.reindex(common_idx2))
            fig_ov = make_subplots(specs=[[{"secondary_y": True}]])
            fig_ov.add_trace(go.Scatter(
                name="Job Openings (M)", x=op2.index, y=op2.values/1000,
                line=dict(color=CYAN, width=2),
                hovertemplate="<b>Openings</b>: %{y:.2f}M<extra></extra>",
            ), secondary_y=False)
            fig_ov.add_trace(go.Scatter(
                name="Unemployment %", x=un2.index, y=un2.values,
                line=dict(color=RED, width=2, dash="dot"),
                hovertemplate="<b>Unemployment</b>: %{y:.1f}%<extra></extra>",
            ), secondary_y=True)
            fig_ov.update_layout(**_layout_sub(320))
            _style_sub_axes(fig_ov)
            st.plotly_chart(fig_ov, use_container_width=True, config={"displayModeBar": False})

    st.markdown(f'<div style="color:{MUTED};font-size:9px;margin-top:6px;font-family:\'Courier New\',monospace">Sources: BLS CES (payrolls, wages) · BLS CPS (unemployment, participation) · FRED JOLTS</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: INFLATION  —  2Y fixed
# ═══════════════════════════════════════════════════════════════════════════════

CPI_COMP = {
    "cpi_shelter":   ("Shelter",        0.3620, BLUE),
    "cpi_food_home": ("Food at Home",   0.0850, GREEN),
    "cpi_food_out":  ("Food Away",      0.0540, "#34d399"),
    "cpi_medical":   ("Medical Care",   0.0640, VIOLET),
    "cpi_energy":    ("Energy",         0.0640, GOLD),
    "cpi_new_cars":  ("New Vehicles",   0.0340, MUTED),
    "cpi_used_cars": ("Used Vehicles",  0.0230, "#64748b"),
    "cpi_apparel":   ("Apparel",        0.0240, "#f97316"),
    "cpi_recreation":("Recreation",     0.0570, CYAN),
    "cpi_gasoline":  ("Gasoline",       0.0320, "#fb923c"),
}

def _render_inflation():
    CUT = -24   # 2Y monthly

    with st.spinner("Loading BLS + FRED inflation data..."):
        try:
            cpi_df = _load_bls(BLS_CPI_IDS, start_year=2015)
        except Exception as e:
            st.error(f"BLS CPI error: {e}"); cpi_df = pd.DataFrame()
        try:
            fred_df = _load_fred(FRED_INFL)
        except Exception as e:
            st.warning(f"FRED inflation error: {e}"); fred_df = pd.DataFrame()

    def cs(key):
        if cpi_df.empty: return pd.Series(dtype=float)
        return _bls_s(cpi_df, BLS_CPI_IDS[key])
    def fi(name):
        if fred_df.empty: return pd.Series(dtype=float)
        return _fred_s(fred_df, name)
    def yoy(s): return s.pct_change(12) * 100
    def mom(s): return s.pct_change(1) * 100
    def trim(s): return _trim(s, CUT)

    cpi_all_yoy  = yoy(cs("cpi_all"))
    cpi_core_yoy = yoy(cs("cpi_core"))
    pce_yoy      = yoy(fi("pce"))
    pce_core_yoy = yoy(fi("pce_core"))
    be5          = fi("breakeven_5y")
    be10         = fi("breakeven_10y")
    mich_1y      = fi("mich_1y")

    l_cpi = _lat(cpi_all_yoy); l_core = _lat(cpi_core_yoy)
    l_pce = _lat(pce_yoy); l_pce_core = _lat(pce_core_yoy)
    l_be5 = _lat(be5); l_mich = _lat(mich_1y)
    latest_date = cpi_all_yoy.dropna().index[-1].strftime("%b %Y") if len(cpi_all_yoy.dropna()) else ""

    _kpi_strip([
        (f"{l_cpi:.1f}%"      if l_cpi      else "—", "CPI HEADLINE",  f"prev {_prv(cpi_all_yoy):.1f}%" if _prv(cpi_all_yoy) else "", _ic(l_cpi)),
        (f"{l_core:.1f}%"     if l_core     else "—", "CORE CPI",      "ex Food & Energy",   _ic(l_core)),
        (f"{l_pce:.1f}%"      if l_pce      else "—", "PCE HEADLINE",  f"prev {_prv(pce_yoy):.1f}%" if _prv(pce_yoy) else "",         _ic(l_pce)),
        (f"{l_pce_core:.1f}%" if l_pce_core else "—", "CORE PCE",      "PCE preferred gauge",   _ic(l_pce_core)),
        (f"{l_be5:.2f}%"      if l_be5      else "—", "5Y BREAKEVEN",  "TIPS market",        CYAN),
        (f"{l_mich:.1f}%"     if l_mich     else "—", "MICH 1Y EXPEC", "consumer survey",    VIOLET),
    ])

    # ── Section 1: CPI + PCE overview ───────────────────────────────────────
    _sec(f"CPI · PCE · CORE — YoY%  ·  {latest_date}")

    fig1 = go.Figure()
    for name, s, color, dash in [
        ("CPI Headline", cpi_all_yoy,  ORANGE, "solid"),
        ("Core CPI",     cpi_core_yoy, GOLD,   "dash"),
        ("PCE Headline", pce_yoy,      BLUE,   "solid"),
        ("Core PCE",     pce_core_yoy, CYAN,   "dot"),
    ]:
        t = trim(s.dropna())
        if len(t):
            fig1.add_trace(go.Scatter(
                name=name, x=t.index, y=t.values,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig1.update_layout(**_layout(320))
    st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    # ── Section 2: Component Contributions (stacked bar — igual al original) ─
    _sec("CPI COMPONENT CONTRIBUTIONS")

    mode = st.radio("Mode", ["YoY %", "MoM %"], horizontal=True,
                    label_visibility="collapsed", key="infl_mode")

    contrib_data = {}
    for key, (label, weight, color) in CPI_COMP.items():
        s = cs(key)
        if s.empty: continue
        if mode == "YoY %":
            contrib = yoy(s) * weight
        else:
            contrib = mom(s) * weight
        contrib_data[label] = contrib

    if contrib_data:
        contrib_df = pd.DataFrame(contrib_data).dropna()
        contrib_df = trim(contrib_df)
        if mode == "YoY %":
            total = trim(cpi_all_yoy.dropna())
        else:
            total = trim(mom(cs("cpi_all")).dropna())
        common_idx = contrib_df.index.intersection(total.index)
        contrib_df = contrib_df.reindex(common_idx)
        total      = total.reindex(common_idx)

        fig2 = go.Figure()
        pos_stack = pd.Series(0.0, index=common_idx)
        neg_stack = pd.Series(0.0, index=common_idx)
        for key, (label, weight, color) in CPI_COMP.items():
            if label not in contrib_df.columns: continue
            vals     = contrib_df[label]
            pos_vals = vals.clip(lower=0)
            neg_vals = vals.clip(upper=0)
            if pos_vals.abs().sum() > 0:
                fig2.add_trace(go.Bar(
                    name=label, x=common_idx, y=pos_vals.values,
                    base=pos_stack.values,
                    marker=dict(color=color, line=dict(width=0)),
                    showlegend=True,
                    hovertemplate=f"<b>{label}</b>: %{{y:+.3f}}pp<extra></extra>",
                ))
                pos_stack += pos_vals
            if neg_vals.abs().sum() > 0:
                fig2.add_trace(go.Bar(
                    name=label, x=common_idx, y=neg_vals.values,
                    base=neg_stack.values,
                    marker=dict(color=color, line=dict(width=0)),
                    showlegend=False,
                    hovertemplate=f"<b>{label}</b>: %{{y:+.3f}}pp<extra></extra>",
                ))
                neg_stack += neg_vals
        fig2.add_trace(go.Scatter(
            name="CPI Total", x=common_idx, y=total.values,
            mode="lines", line=dict(color=WHITE, width=2),
            hovertemplate="<b>CPI Total</b>: %{y:.2f}%<extra></extra>",
        ))
        l2 = _layout(380)
        fig2.update_layout(**l2)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Section 3: Shelter vs Core ex-Shelter ───────────────────────────────
    _sec("SHELTER vs CORE EX-SHELTER — YoY %")

    shelter_yoy     = yoy(cs("cpi_shelter"))
    SHELTER_W       = 0.36
    core_ex_shelter = (cpi_core_yoy - SHELTER_W * shelter_yoy) / (1 - SHELTER_W)

    fig3 = go.Figure()
    for name, s, color, dash in [
        ("Shelter",          trim(shelter_yoy.dropna()),     BLUE,   "solid"),
        ("Core CPI",         trim(cpi_core_yoy.dropna()),    GOLD,   "dot"),
        ("Core ex-Shelter*", trim(core_ex_shelter.dropna()), CYAN,   "solid"),
    ]:
        if len(s):
            fig3.add_trace(go.Scatter(
                name=name, x=s.index, y=s.values,
                line=dict(color=color, width=2, dash=dash),
                hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
            ))
    fig3.update_layout(**_layout(300))
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # ── Section 4: Inflation Expectations ───────────────────────────────────
    _sec("INFLATION EXPECTATIONS — TIPS BREAKEVENS & MICHIGAN SURVEY")

    exp_tabs = st.tabs(["TIPS Breakevens", "Michigan Survey"])
    with exp_tabs[0]:
        fig4a = go.Figure()
        for name, key, color, dash in [
            ("5Y Breakeven",  "breakeven_5y",  CYAN,   "solid"),
            ("10Y Breakeven", "breakeven_10y", VIOLET, "dash"),
        ]:
            t = trim(fi(key).dropna())
            if len(t):
                fig4a.add_trace(go.Scatter(
                    name=name, x=t.index, y=t.values,
                    line=dict(color=color, width=2, dash=dash),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
                ))
        fig4a.update_layout(**_layout(260))
        st.plotly_chart(fig4a, use_container_width=True, config={"displayModeBar": False})

    with exp_tabs[1]:
        fig4b = go.Figure()
        for name, key, color in [
            ("Michigan 1Y", "mich_1y", GOLD),
            ("Michigan 5Y", "mich_5y", BLUE),
        ]:
            t = trim(fi(key).dropna())
            if len(t):
                fig4b.add_trace(go.Scatter(
                    name=name, x=t.index, y=t.values,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
                ))
        fig4b.update_layout(**_layout(260))
        st.plotly_chart(fig4b, use_container_width=True, config={"displayModeBar": False})

    st.markdown(f'<div style="color:{MUTED};font-size:9px;margin-top:8px;font-family:\'Courier New\',monospace">Sources: BLS (CPI CUUR series) · FRED (PCE, TIPS breakevens, Michigan Survey)</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    subtabs = st.tabs(["GDP", "LABOR", "INFLATION"])
    with subtabs[0]: _render_gdp()
    with subtabs[1]: _render_labor()
    with subtabs[2]: _render_inflation()
