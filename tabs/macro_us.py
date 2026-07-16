"""
tabs/macro_us.py — MACRO US
Subtabs: GDP · LABOR · INFLATION · RATES
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
#  NAV — breadcrumb (nuevo)
# ═══════════════════════════════════════════════════════════════════════════════
def _breadcrumb(section):
    st.markdown(
        f'<div style="font-family:\'Courier New\',monospace;font-size:12px;'
        f'letter-spacing:1.5px;margin-bottom:12px;color:#666;">'
        f'MACRO US <span style="color:#444">&rsaquo;</span> '
        f'<span style="color:{ORANGE};font-weight:bold">{section}</span></div>',
        unsafe_allow_html=True
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  CHART CONFIG — modebar habilitado + selector de rango (nuevo)
# ═══════════════════════════════════════════════════════════════════════════════
PLOTLY_CFG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
        "hoverCompareCartesian", "hoverClosestCartesian",
    ],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}

def _rangeselector():
    return dict(
        buttons=list([
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(count=3, label="3M", step="month", stepmode="backward"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=2, label="2Y", step="year", stepmode="backward"),
            dict(step="all", label="MAX"),
        ]),
        font=dict(size=10, color=MUTED, family="'Courier New',monospace"),
        bgcolor="#0a0a0a",
        activecolor="rgba(255,102,0,0.18)",
        bordercolor="#222",
        borderwidth=1,
        # Anclado a la IZQUIERDA a propósito: la modebar de Plotly (cámara,
        # zoom, home, etc.) vive siempre arriba a la derecha del área del
        # gráfico y no es reposicionable — si el selector de rango también
        # se ancla a la derecha, se pisan. Poniéndolo a la izquierda nunca
        # compiten por el mismo espacio, sea cual sea el ancho del chart.
        x=0, xanchor="left", y=1.22, yanchor="top",
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT — BBG style
# ═══════════════════════════════════════════════════════════════════════════════
def _layout(height=360):
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG2,
        font=dict(family="'Courier New', monospace", color=TEXT, size=11),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, showgrid=False,
                   tickfont=dict(size=11, color='#aaaaaa')),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=True,
                   zerolinecolor="#333",
                   tickfont=dict(size=11, color='#aaaaaa')),
        hovermode="x unified",
        barmode="relative",
        height=height,
        margin=dict(l=55, r=20, t=30, b=36),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11, family="Courier New"),
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
    )

def _layout_sub(height=340):
    """Layout for make_subplots figures."""
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG2,
        font=dict(family="'Courier New', monospace", color=TEXT, size=11),
        hovermode="x unified",
        height=height,
        margin=dict(l=55, r=20, t=30, b=36),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11, family="Courier New"),
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        ),
    )

def _style_sub_axes(fig, secondary=True):
    """Apply BBG grid style to all axes of a subplot figure."""
    ax_style = dict(gridcolor=GRID, linecolor=GRID, zeroline=False,
                    tickfont=dict(size=11, color='#aaaaaa'), title_text=None,
                    showgrid=True)
    fig.update_xaxes(**ax_style)
    fig.update_yaxes(**ax_style)

# Recuadro ("card") alrededor de cada sección — separa visualmente los bloques.
# Se abre un st.container(border=True) por sección y se cierra automáticamente
# al abrir la siguiente (o explícitamente en los puntos donde el flujo sale de
# un `with` — ver _close_box() en cada uno de esos puntos). Usamos enter/exit
# manuales (en vez de "with") para no tener que reindentar todo el archivo.
_open_box = [None]

def _close_box():
    if _open_box[0] is not None:
        try:
            _open_box[0].__exit__(None, None, None)
        except Exception:
            pass
        _open_box[0] = None

def _sec(text, box=True):
    _close_box()
    if box:
        c = st.container(border=True)
        c.__enter__()
        _open_box[0] = c
    st.markdown(
        f'<div style="color:{ORANGE};font-size:11px;font-weight:bold;letter-spacing:2px;'
        f'text-transform:uppercase;border-bottom:1px solid #333;padding-bottom:3px;'
        f'margin:6px 0 6px 0;font-family:\'Courier New\',monospace">{text}</div>',
        unsafe_allow_html=True
    )

def _kpi_strip(kpis):
    """
    Cada kpi es una tupla (val, label, sub, color) o, opcionalmente,
    (val, label, sub, color, prefix_html) donde prefix_html es una flecha
    generada por _delta_arrow() — 100% retro-compatible con las llamadas
    de 4 elementos ya existentes.
    """
    items = ""
    for kpi in kpis:
        val, label, sub, color = kpi[:4]
        prefix = kpi[4] if len(kpi) > 4 else ""
        items += (
            f'<div class="kpi-item">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="color:{color}">{val}</div>'
            f'<div class="kpi-sub" style="color:{MUTED}">{prefix}{sub}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="kpi-strip">{items}</div>', unsafe_allow_html=True)

def _delta_arrow(cur, prev, invert=False):
    """
    Flecha de tendencia real (solo cuando hay un valor previo genuino con el
    que comparar — no se infiere de clasificaciones por umbral como _ic()).
    invert=True → un aumento se considera negativo (ej: desempleo, inflación).
    Reusa las clases globales .up/.down/.flat ya definidas en app.py.
    """
    if cur is None or prev is None:
        return ""
    if cur == prev:
        return '<span class="flat">&#8212;</span>&nbsp;'
    up   = cur > prev
    good = (not up) if invert else up
    cls  = "up" if good else "down"
    arrow = "&#9650;" if up else "&#9660;"
    return f'<span class="{cls}">{arrow}</span>&nbsp;'

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
#  DATA — BLS  (FIX: batches de 10 series, timeout 20s por batch)
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
    """
    FIX v2: divide las series en batches de 10 con timeout de 20s cada uno.
    Si un batch falla (timeout u otro error de red), se omite y continúa.
    Esto evita el HTTPSConnectionPool timeout que bloqueaba toda la sección LABOR.
    """
    all_ids = list(series_dict.values())
    BATCH   = 10   # BLS free tier: max 25 por request; 10 es más seguro
    TIMEOUT = 20   # segundos por batch — fail fast, no colgar la UI
    rows    = []
    for i in range(0, len(all_ids), BATCH):
        batch = all_ids[i:i + BATCH]
        payload = dict(
            seriesid=batch,
            startyear=str(start_year),
            endyear=str(_dt.now().year),
            registrationkey=BLS_KEY,
            annualaverage=False,
        )
        try:
            resp = requests.post(
                "https://api.bls.gov/publicAPI/v2/timeseries/data/",
                data=json.dumps(payload),
                headers={"Content-type": "application/json"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            for series in resp.json().get("Results", {}).get("series", []):
                sid = series["seriesID"]
                for obs in series.get("data", []):
                    period = obs.get("period", "")
                    if not period.startswith("M") or period == "M13":
                        continue
                    try:
                        month = int(period[1:])
                        year  = int(obs["year"])
                        val   = float(obs["value"])
                        rows.append({
                            "series_id": sid,
                            "date": pd.Timestamp(f"{year}-{month:02d}-01"),
                            "value": val,
                        })
                    except:
                        continue
        except Exception:
            # Un batch fallido no rompe el resto
            continue
    if not rows:
        raise RuntimeError("BLS API no devolvió datos — todos los batches fallaron")
    return pd.DataFrame(rows).sort_values(["series_id", "date"]).reset_index(drop=True)

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
    _breadcrumb("GDP")
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
    _sec("CONTRIBUTIONS TO REAL GDP GROWTH")
    fig = go.Figure()
    for name, key, color in [
        ("Consumption", cons, GDP_COLORS["consumption"]),
        ("Investment",  inv,  GDP_COLORS["investment"]),
        ("Government",  gov,  GDP_COLORS["government"]),
        ("Net Exports", nx,   GDP_COLORS["net_exports"]),
    ]:
        vals = key.reindex(common).fillna(0).values
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
    lay_gdp = _layout(520)
    lay_gdp["margin"] = dict(l=55, r=20, t=56, b=36)
    lay_gdp["legend"]["y"] = 1.0
    lay_gdp["legend"]["yanchor"] = "bottom"
    fig.update_layout(**lay_gdp)
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)
    _sec("DRILL-DOWN")
    dtabs = st.tabs(["Consumption", "Investment", "Government", "Net Exports", "Final Sales"])
    def _sub(text):
        st.markdown(
            f'<div style="font-family:Courier New,monospace;font-size:11px;'
            f'color:#777;margin:4px 0 0 0;padding:0;line-height:1.4">{text}</div>',
            unsafe_allow_html=True
        )
    def _drill_layout():
        lay = _layout(340)
        lay["margin"] = dict(l=55, r=20, t=36, b=36)
        lay["legend"] = dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11, family="Courier New"),
            orientation="h",
            yanchor="bottom", y=1.0,
            xanchor="left", x=0,
        )
        return lay
    with dtabs[0]:
        _sub("Durables &nbsp;&middot;&nbsp; Nondurables &nbsp;&middot;&nbsp; Services &nbsp;&nbsp; ◆ = Total PCE contribution")
        fig = _stacked_fig([
            ("Durables",    _gs(df,GDP_CODES["durables"]),    GDP_COLORS["durables"]),
            ("Nondurables", _gs(df,GDP_CODES["nondurables"]), GDP_COLORS["nondurables"]),
            ("Services",    _gs(df,GDP_CODES["services"]),    GDP_COLORS["services"]),
        ], common, quarters)
        _add_diamond(fig, cons, common, quarters, "Total PCE")
        fig.update_layout(**_drill_layout())
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)
    with dtabs[1]:
        _sub("Residential &nbsp;&middot;&nbsp; Nonresidential &nbsp;&middot;&nbsp; Inventories &nbsp;&nbsp; ◆ = Total Investment")
        fig = _stacked_fig([
            ("Residential",    _gs(df,GDP_CODES["residential"]),    GDP_COLORS["residential"]),
            ("Nonresidential", _gs(df,GDP_CODES["nonresidential"]), GDP_COLORS["nonresidential"]),
            ("Inventories",    _gs(df,GDP_CODES["inventories"]),    GDP_COLORS["inventories"]),
        ], common, quarters)
        _add_diamond(fig, inv, common, quarters, "Total Investment")
        fig.update_layout(**_drill_layout())
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)
    with dtabs[2]:
        _sub("Federal &nbsp;&middot;&nbsp; State & Local &nbsp;&nbsp; ◆ = Total Government")
        fig = _stacked_fig([
            ("Federal",       _gs(df,GDP_CODES["federal"]),     GDP_COLORS["federal"]),
            ("State & Local", _gs(df,GDP_CODES["state_local"]), GDP_COLORS["state_local"]),
        ], common, quarters)
        _add_diamond(fig, gov, common, quarters, "Total Government")
        fig.update_layout(**_drill_layout())
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)
    with dtabs[3]:
        _sub("Exports &nbsp;&middot;&nbsp; Imports &nbsp;&nbsp; ◆ = Net Exports")
        fig = _stacked_fig([
            ("Exports", _gs(df,GDP_CODES["exports"]), GDP_COLORS["exports"]),
            ("Imports", _gs(df,GDP_CODES["imports"]), GDP_COLORS["imports"]),
        ], common, quarters)
        _add_diamond(fig, nx, common, quarters, "Net Exports")
        fig.update_layout(**_drill_layout())
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)
    with dtabs[4]:
        inv_ch = _gs(df,GDP_CODES["inventories"]).reindex(common).fillna(0)
        fs     = gdp.reindex(common).fillna(0) - inv_ch
        _sub("Final Sales &nbsp;&middot;&nbsp; Inventory Change &nbsp;&nbsp; ◆ = Total GDP")
        fig = _stacked_fig([
            ("Final Sales",      fs,     GDP_COLORS["final_sales"]),
            ("Inventory Change", inv_ch, GDP_COLORS["inv_change"]),
        ], common, quarters)
        _add_diamond(fig, gdp.reindex(common), common, quarters, "Total GDP")
        fig.update_layout(**_drill_layout())
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CFG)
    _sec("LAST 8 QUARTERS — CONTRIBUTIONS (pp)")
    last8 = common[-8:]
    ql8   = [_qlabel(d) for d in last8]
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
    TH = f"padding:4px 10px;{T}font-size:11px;font-weight:bold;letter-spacing:1px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;white-space:nowrap;"
    TH0= f"padding:4px 12px;{T}font-size:11px;font-weight:bold;letter-spacing:1px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;min-width:150px;"
    hdr = f'<tr><th style="{TH0}">SERIES</th>' + "".join(f'<th style="{TH}">{q}</th>' for q in ql8) + "</tr>"
    rows_html = ""
    for i,(label, s, indented) in enumerate(series_map_ordered):
        vals     = s.reindex(last8).fillna(0).values
        is_top   = not indented
        top_bdr  = "border-top:1px solid #2a2a2a;" if is_top and i > 0 else ""
        fw       = "font-weight:bold;" if is_top else "font-weight:normal;"
        ind_px   = "padding-left:22px;" if indented else "padding-left:12px;"
        name_td  = f"padding:3px 10px;{T}font-size:12px;{fw}{ind_px}color:#ccc;background:#000;border-right:1px solid #333;{top_bdr}white-space:nowrap;"
        rows_html += f'<tr><td style="{name_td}">{label.strip()}</td>'
        for v in vals:
            bg, fg = _cell_bg_fg(v)
            sign   = "+" if v >= 0 else ""
            td     = f"padding:3px 10px;{T}font-size:12px;font-weight:bold;text-align:right;background:{bg};color:{fg};border-right:1px solid #111;{top_bdr}white-space:nowrap;"
            rows_html += f'<td style="{td}">{sign}{v:.2f}</td>'
        rows_html += "</tr>"
    st.markdown(f"""
    <div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:4px;">
      <table style="border-collapse:collapse;width:100%;">
        <thead>{hdr}</thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <div style="color:#444;font-size:11px;{T}margin-bottom:10px;">
      BEA NIPA Table 1.1.2 &nbsp;·&nbsp; Quarterly annualized rates &nbsp;·&nbsp; Contributions in pp
    </div>""", unsafe_allow_html=True)
    _close_box()

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: LABOR  —  2Y fixed
# ═══════════════════════════════════════════════════════════════════════════════
def _render_labor():
    _breadcrumb("LABOR")
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
        (f"{l_pay:+,.0f}K" if l_pay else "—",   "NFP MOM",      f"prev {p_pay:+,.0f}K" if p_pay else "", _cv(l_pay),
         _delta_arrow(l_pay, p_pay)),
        (f"{l_u:.1f}%"     if l_u   else "—",   "UNEMPLOYMENT", f"prev {p_u:.1f}%" if p_u else "",       _cv(l_u, invert=True),
         _delta_arrow(l_u, p_u, invert=True)),
        (f"{_lat(u6):.1f}%" if _lat(u6) else "—","U-6 BROAD",   "underemployment",                        _cv(_lat(u6), invert=True)),
        (f"{l_part:.1f}%"  if l_part else "—",  "LFPR",         "labor force part.",                      BLUE),
        (f"{l_wages:.1f}%" if l_wages else "—", "WAGES YoY",    "avg hourly earnings",                    _ic(l_wages) if l_wages else MUTED),
        (f"{_lat(fs('jolts_openings'))/1000:.1f}M" if _lat(fs('jolts_openings')) else "—", "JOLTS OPEN", "job openings", CYAN),
    ])
    _sec("NONFARM PAYROLLS — MONTHLY CHANGE (000s)")
    ma3 = pay_ch_t.rolling(3).mean()
    view_tabs = st.tabs(["Total", "Private vs Government"])
    with view_tabs[0]:
        fig1 = go.Figure()
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
        fig1.add_hline(y=0, line_color="#333", line_width=1)
        lay1 = _layout(440)
        lay1["xaxis"]["rangeselector"] = _rangeselector()
        lay1["margin"] = dict(l=55, r=20, t=92, b=36)
        fig1.update_layout(**lay1)
        st.plotly_chart(fig1, use_container_width=True, config=PLOTLY_CFG)
    with view_tabs[1]:
        fig1b = go.Figure()
        fig1b.add_trace(go.Bar(
            name="Private", x=pay_priv_ch_t.index, y=pay_priv_ch_t.values,
            marker_color=BLUE, opacity=0.85,
            hovertemplate="<b>Private</b>: %{y:+,.0f}K<extra></extra>",
        ))
        fig1b.add_trace(go.Bar(
            name="Government", x=pay_govt_ch_t.index, y=pay_govt_ch_t.values,
            marker_color=AMBER, opacity=0.85,
            hovertemplate="<b>Government</b>: %{y:+,.0f}K<extra></extra>",
        ))
        fig1b.add_hline(y=0, line_color="#333", line_width=1)
        lay1b = _layout(440)
        lay1b["xaxis"]["rangeselector"] = _rangeselector()
        lay1b["margin"] = dict(l=55, r=20, t=92, b=36)
        fig1b.update_layout(**lay1b)
        st.plotly_chart(fig1b, use_container_width=True, config=PLOTLY_CFG)
    _sec("NONFARM PAYROLLS — SECTOR BREAKDOWN")
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
    # Menos series visibles por defecto (antes: 11 + Total NFP de una) — el resto
    # se puede activar haciendo click en la leyenda (comportamiento nativo de Plotly).
    SECTORS_HIDDEN_BY_DEFAULT = {
        "Goods Producing", "Construction", "Manufacturing", "Information",
        "Financial", "Other Services",
    }
    SECTOR_CUT = -30
    sector_series = {}
    for label, sid, color, group in SECTOR_CFG:
        if bls_df.empty: continue
        s = _bls_s(bls_df, sid).diff()
        sector_series[label] = (s, color)
    fig_sec = go.Figure()
    total_nfp = pay_ch
    for label, (s, color) in sector_series.items():
        t = _trim(s.dropna(), SECTOR_CUT)
        if len(t):
            fig_sec.add_trace(go.Bar(
                name=label, x=t.index, y=t.values,
                marker_color=color, marker_line_width=0,
                visible="legendonly" if label in SECTORS_HIDDEN_BY_DEFAULT else True,
                hovertemplate=f"<b>{label}</b>: %{{y:+.0f}}K<extra></extra>",
            ))
    tot_t = _trim(total_nfp.dropna(), SECTOR_CUT)
    if len(tot_t):
        fig_sec.add_trace(go.Scatter(
            name="Total NFP", x=tot_t.index, y=tot_t.values,
            line=dict(color=WHITE, width=2),
            mode="lines",
            hovertemplate="<b>Total NFP</b>: %{y:+.0f}K<extra></extra>",
        ))
    fig_sec.add_hline(y=0, line_color="#333", line_width=1)
    lay_sec = _layout(480)
    lay_sec["barmode"] = "relative"
    lay_sec["margin"] = dict(l=55, r=20, t=110, b=36)
    lay_sec["legend"] = dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=11, family="Courier New"),
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        tracegroupgap=6,
        entrywidth=145,
        entrywidthmode="pixels",
    )
    fig_sec.update_layout(**lay_sec)
    st.plotly_chart(fig_sec, use_container_width=True, config=PLOTLY_CFG)
    st.markdown(
        f'<div style="color:{MUTED};font-size:11px;margin:-8px 0 8px 0;font-family:\'Courier New\',monospace">'
        f'6 sectores menores empiezan ocultos — clic en la leyenda para mostrarlos.</div>',
        unsafe_allow_html=True
    )
    N_MONTHS = 8
    heat_data = {}
    for label, (s, color) in sector_series.items():
        ch = s.dropna()
        if len(ch) >= N_MONTHS:
            heat_data[label] = {"series": ch, "color": color}
    if heat_data:
        all_idx = sorted(set.intersection(*[set(v["series"].index) for v in heat_data.values()]))
        col_dates = sorted(all_idx)[-N_MONTHS:]
        col_labels = [d.strftime("%b-%y") for d in col_dates]
        def _td_style(val):
            if   val >  80: bg,fg = "#0a3d1f","#4ade80"
            elif val >  30: bg,fg = "#062910","#34d399"
            elif val >   0: bg,fg = "#041a0a","#6ee7b7"
            elif val > -30: bg,fg = "#1a0505","#fca5a5"
            elif val > -80: bg,fg = "#2a0606","#f87171"
            else:           bg,fg = "#3d0808","#ef4444"
            return bg, fg
        T2 = "font-family:'Courier New',monospace;"
        TH2  = f"padding:4px 10px;{T2}font-size:11px;font-weight:bold;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;white-space:nowrap;"
        TH2a = f"padding:4px 12px;{T2}font-size:11px;font-weight:bold;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;min-width:160px;"
        hdr2 = f'<tr><th style="{TH2a}">SERIES</th>'
        for cl in col_labels:
            hdr2 += f'<th style="{TH2}">{cl}</th>'
        hdr2 += "</tr>"
        body2 = ""
        for label, info in heat_data.items():
            color = info["color"]
            vals  = [info["series"].get(d, float("nan")) for d in col_dates]
            name_td = f"padding:3px 12px;{T2}font-size:12px;font-weight:bold;color:{color};background:#000;border-right:1px solid #333;white-space:nowrap;"
            body2 += f'<tr><td style="{name_td}">{label}</td>'
            for v in vals:
                if pd.isna(v):
                    body2 += f'<td style="padding:3px 10px;{T2}font-size:12px;text-align:right;background:#0a0a0a;color:#333;border-right:1px solid #111;">—</td>'
                else:
                    bg, fg = _td_style(v)
                    sign   = "+" if v >= 0 else ""
                    td2    = f"padding:3px 10px;{T2}font-size:12px;font-weight:bold;text-align:right;background:{bg};color:{fg};border-right:1px solid #111;white-space:nowrap;"
                    body2 += f'<td style="{td2}">{sign}{v:.0f}K</td>'
            body2 += "</tr>"
        st.markdown(f"""
        <div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:4px;">
          <table style="border-collapse:collapse;width:100%;">
            <thead>{hdr2}</thead>
            <tbody>{body2}</tbody>
          </table>
        </div>
        <div style="color:#444;font-size:11px;{T2}margin-bottom:10px;">
          BLS CES &nbsp;·&nbsp; Monthly net change in thousands &nbsp;·&nbsp; Seasonally adjusted
        </div>""", unsafe_allow_html=True)
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
    fig3.update_layout(**_layout_sub(380))
    _style_sub_axes(fig3)
    st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CFG)
    _sec("AVERAGE HOURLY EARNINGS — YoY %")
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        name="AHE YoY%", x=wages_yoy_t.index, y=wages_yoy_t.values,
        line=dict(color=AMBER, width=2.5),
        hovertemplate="<b>Wages YoY</b>: %{y:.2f}%<extra></extra>",
    ))
    lay4 = _layout(280)
    lay4['yaxis']['autorange'] = True
    lay4['yaxis']['rangemode'] = 'normal'
    fig4.update_layout(**lay4)
    st.plotly_chart(fig4, use_container_width=True, config=PLOTLY_CFG)
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
                                              tickfont=dict(color=MUTED,size=10))),
                    hovertemplate="<b>%{customdata}</b><br>U: %{x:.1f}%<br>Openings: %{y:.2f}M<extra></extra>",
                    customdata=[d.strftime("%b %Y") for d in common_idx],
                ))
                fig_b.add_trace(go.Scatter(
                    name="Latest", x=[un_bev.iloc[-1]], y=[op_bev.iloc[-1]/1000],
                    mode="markers", marker=dict(symbol="star",size=14,color=CYAN),
                    hovertemplate=f"<b>Latest</b>: {common_idx[-1].strftime('%b %Y')}<extra></extra>",
                ))
                lb = _layout(440)
                lb["hovermode"] = "closest"
                lb["showlegend"] = False
                fig_b.update_layout(**lb)
                st.plotly_chart(fig_b, use_container_width=True, config=PLOTLY_CFG)
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
            fig_fl.update_layout(**_layout(380))
            st.plotly_chart(fig_fl, use_container_width=True, config=PLOTLY_CFG)
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
            fig_ov.update_layout(**_layout_sub(360))
            _style_sub_axes(fig_ov)
            st.plotly_chart(fig_ov, use_container_width=True, config=PLOTLY_CFG)
    st.markdown(f'<div style="color:{MUTED};font-size:11px;margin-top:6px;font-family:\'Courier New\',monospace">Sources: BLS CES (payrolls, wages) · BLS CPS (unemployment, participation) · FRED JOLTS</div>', unsafe_allow_html=True)
    _close_box()

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
    _breadcrumb("INFLATION")
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
    p_cpi = _prv(cpi_all_yoy); p_pce = _prv(pce_yoy)
    latest_date = cpi_all_yoy.dropna().index[-1].strftime("%b %Y") if len(cpi_all_yoy.dropna()) else ""
    _kpi_strip([
        (f"{l_cpi:.1f}%"      if l_cpi      else "—", "CPI HEADLINE",  f"prev {p_cpi:.1f}%" if p_cpi else "", _ic(l_cpi),
         _delta_arrow(l_cpi, p_cpi, invert=True)),
        (f"{l_core:.1f}%"     if l_core     else "—", "CORE CPI",      "ex Food & Energy",   _ic(l_core)),
        (f"{l_pce:.1f}%"      if l_pce      else "—", "PCE HEADLINE",  f"prev {p_pce:.1f}%" if p_pce else "",  _ic(l_pce),
         _delta_arrow(l_pce, p_pce, invert=True)),
        (f"{l_pce_core:.1f}%" if l_pce_core else "—", "CORE PCE",      "PCE preferred gauge",   _ic(l_pce_core)),
        (f"{l_be5:.2f}%"      if l_be5      else "—", "5Y BREAKEVEN",  "TIPS market",        CYAN),
        (f"{l_mich:.1f}%"     if l_mich     else "—", "MICH 1Y EXPEC", "consumer survey",    VIOLET),
    ])
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
    lay1 = _layout(420)
    lay1["xaxis"]["rangeselector"] = _rangeselector()
    lay1["margin"] = dict(l=55, r=20, t=92, b=36)
    fig1.update_layout(**lay1)
    st.plotly_chart(fig1, use_container_width=True, config=PLOTLY_CFG)
    _sec("CPI COMPONENT CONTRIBUTIONS")
    mode_tabs = st.tabs(["YoY %", "MoM %"])
    for mode, mode_tab in zip(["YoY %", "MoM %"], mode_tabs):
      with mode_tab:
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
                # FIX: legendgroup en ambos traces — antes, al ocultar una serie
                # desde la leyenda, solo se ocultaba la parte positiva; la parte
                # negativa (showlegend=False) quedaba "pegada" visible porque no
                # estaba vinculada al mismo grupo de leyenda.
                if pos_vals.abs().sum() > 0:
                    fig2.add_trace(go.Bar(
                        name=label, x=common_idx, y=pos_vals.values,
                        base=pos_stack.values,
                        marker=dict(color=color, line=dict(width=0)),
                        legendgroup=label, showlegend=True,
                        hovertemplate=f"<b>{label}</b>: %{{y:+.3f}}pp<extra></extra>",
                    ))
                    pos_stack += pos_vals
                if neg_vals.abs().sum() > 0:
                    fig2.add_trace(go.Bar(
                        name=label, x=common_idx, y=neg_vals.values,
                        base=neg_stack.values,
                        marker=dict(color=color, line=dict(width=0)),
                        legendgroup=label, showlegend=False,
                        hovertemplate=f"<b>{label}</b>: %{{y:+.3f}}pp<extra></extra>",
                    ))
                    neg_stack += neg_vals
            fig2.add_trace(go.Scatter(
                name="CPI Total", x=common_idx, y=total.values,
                mode="lines", line=dict(color=WHITE, width=2),
                legendgroup="CPI Total",
                hovertemplate="<b>CPI Total</b>: %{y:.2f}%<extra></extra>",
            ))
            l2 = _layout(420)
            fig2.update_layout(**l2)
            st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CFG)
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
    fig3.update_layout(**_layout(340))
    st.plotly_chart(fig3, use_container_width=True, config=PLOTLY_CFG)
    _sec("INFLATION EXPECTATIONS — TIPS BREAKEVENS & MICHIGAN SURVEY")
    # FIX: breakevens y Michigan son series de FRED con frecuencia/gaps
    # distintos a CPI/BLS (breakevens son diarias, no mensuales) — "últimas 24
    # filas" les daba una ventana de fechas equivocada o desalineada entre
    # series. Acá se recorta por fecha real (2 años calendario), no por
    # cantidad de observaciones.
    exp_cutoff = (pd.Timestamp.today() - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    exp_tabs = st.tabs(["TIPS Breakevens", "Michigan Survey"])
    with exp_tabs[0]:
        fig4a = go.Figure()
        for name, key, color, dash in [
            ("5Y Breakeven",  "breakeven_5y",  CYAN,   "solid"),
            ("10Y Breakeven", "breakeven_10y", VIOLET, "dash"),
        ]:
            t = _rtrim(fi(key).dropna(), exp_cutoff)
            if len(t):
                fig4a.add_trace(go.Scatter(
                    name=name, x=t.index, y=t.values,
                    line=dict(color=color, width=2, dash=dash),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
                ))
        # Altura igualada a los otros charts con rangeselector (420): el selector
        # y la leyenda se posicionan en fracción del área del gráfico, así que un
        # chart más bajo (antes 340) comprime esa fracción y el espacio entre
        # ambos se ve más apretado aunque el margen en px sea el mismo.
        lay4a = _layout(420)
        lay4a["xaxis"]["rangeselector"] = _rangeselector()
        lay4a["margin"] = dict(l=55, r=20, t=92, b=36)
        fig4a.update_layout(**lay4a)
        st.plotly_chart(fig4a, use_container_width=True, config=PLOTLY_CFG)
    with exp_tabs[1]:
        fig4b = go.Figure()
        for name, key, color in [
            ("Michigan 1Y", "mich_1y", GOLD),
            ("Michigan 5Y", "mich_5y", BLUE),
        ]:
            t = _rtrim(fi(key).dropna(), exp_cutoff)
            if len(t):
                fig4b.add_trace(go.Scatter(
                    name=name, x=t.index, y=t.values,
                    line=dict(color=color, width=2),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>",
                ))
        fig4b.update_layout(**_layout(300))
        st.plotly_chart(fig4b, use_container_width=True, config=PLOTLY_CFG)
    st.markdown(f'<div style="color:{MUTED};font-size:11px;margin-top:8px;font-family:\'Courier New\',monospace">Sources: BLS (CPI CUUR series) · FRED (PCE, TIPS breakevens, Michigan Survey)</div>', unsafe_allow_html=True)
    _close_box()

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB: RATES  —  2Y fixed default
# ═══════════════════════════════════════════════════════════════════════════════
FRED_RATES = {
    "dgs1m":     "DGS1MO",
    "dgs3m":     "DGS3MO",
    "dgs6m":     "DGS6MO",
    "dgs1":      "DGS1",
    "dgs2":      "DGS2",
    "dgs5":      "DGS5",
    "dgs7":      "DGS7",
    "dgs10":     "DGS10",
    "dgs20":     "DGS20",
    "dgs30":     "DGS30",
    "t10y2y":    "T10Y2Y",
    "t10y3m":    "T10Y3M",
    "fedfunds":  "FEDFUNDS",
    "fed_lb":    "DFEDTARL",
    "fed_ub":    "DFEDTARU",
    "sofr":      "SOFR",
    "iorb":      "IORB",
    "onrrp":     "RRPONTSYAWARD",
    "tips5":     "DFII5",
    "tips10":    "DFII10",
    "tips30":    "DFII30",
    "bei5":      "T5YIE",
    "bei10":     "T10YIE",
    "ig_oas":    "BAMLC0A0CM",
    "hy_oas":    "BAMLH0A0HYM2",
    "bbb_oas":   "BAMLC0A4CBBB",
    "nfci":      "NFCI",
    "vix":       "VIXCLS",
    "mortgage30":"MORTGAGE30US",
    "dollar":    "DTWEXBGS",
}
TENORS      = ["1M","3M","6M","1Y","2Y","5Y","7Y","10Y","20Y","30Y"]
TENOR_KEYS  = ["dgs1m","dgs3m","dgs6m","dgs1","dgs2","dgs5","dgs7","dgs10","dgs20","dgs30"]
TEAL   = "#14b8a6"
PINK   = "#f472b6"

@st.cache_data(ttl=3600, show_spinner=False)
def _load_rates_fred(start="2000-01-01"):
    out = {}
    for name, sid in FRED_RATES.items():
        try:
            params = {"series_id": sid, "observation_start": start,
                      "api_key": FRED_KEY, "file_type": "json"}
            r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                             params=params, timeout=20)
            r.raise_for_status()
            rows = []
            for o in r.json()["observations"]:
                try: rows.append({"date": pd.Timestamp(o["date"]), "value": float(o["value"])})
                except: continue
            out[name] = pd.DataFrame(rows).set_index("date")["value"].sort_index() if rows else pd.Series(dtype=float)
        except:
            out[name] = pd.Series(dtype=float)
    return out

@st.cache_data(ttl=1800, show_spinner=False)
def _load_treasury_curve():
    try:
        import xml.etree.ElementTree as ET
        url    = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        params = {"data": "daily_treasury_yield_curve",
                  "field_tdr_date_value_month": _dt.now().strftime("%Y%m")}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        root    = ET.fromstring(r.text)
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        if not entries: return pd.Series(dtype=float)
        props   = entries[-1].find(".//{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties")
        tag_map = {"BC_1MONTH":"1M","BC_3MONTH":"3M","BC_6MONTH":"6M",
                   "BC_1YEAR":"1Y","BC_2YEAR":"2Y","BC_3YEAR":"3Y",
                   "BC_5YEAR":"5Y","BC_7YEAR":"7Y","BC_10YEAR":"10Y",
                   "BC_20YEAR":"20Y","BC_30YEAR":"30Y"}
        curve = {}
        for tag, label in tag_map.items():
            el = props.find(f"{{http://schemas.microsoft.com/ado/2007/08/dataservices}}{tag}")
            if el is not None and el.text:
                try: curve[label] = float(el.text)
                except: pass
        return pd.Series(curve)
    except:
        return pd.Series(dtype=float)

def _rlast(s):
    d = s.dropna()
    return float(d.iloc[-1]) if len(d) else float("nan")

def _rpctile(s, val):
    d = s.dropna()
    if not len(d): return float("nan")
    return (d <= val).mean() * 100

def _rtrim(s, start_date):
    if start_date is None or not len(s): return s
    if not isinstance(s.index, pd.DatetimeIndex): return s
    return s[s.index >= pd.Timestamp(start_date)]

def _spr_color(v):
    if pd.isna(v): return MUTED
    return GREEN if v > 0.5 else (RED if v < -0.2 else AMBER)

# ═══════════════════════════════════════════════════════════════════════════════
#  FEDWATCH — Implied Fed Funds path from ZQ futures (Barchart)
# ═══════════════════════════════════════════════════════════════════════════════
FOMC_MEETINGS = [
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
]
_MONTH_CODES = {1:"F",2:"G",3:"H",4:"J",5:"K",6:"M",
                7:"N",8:"Q",9:"U",10:"V",11:"X",12:"Z"}
_BC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
}

@st.cache_data(ttl=3600, show_spinner=False)
def _load_zq_barchart() -> dict:
    from urllib.parse import unquote
    import time as _time
    try:
        session = requests.Session()
        session.headers.update(_BC_HEADERS)
        session.get("https://www.barchart.com", timeout=10)
        _time.sleep(0.5)
        session.get("https://www.barchart.com/futures/quotes/ZQ*0/futures-prices", timeout=10)
        xsrf_raw = session.cookies.get("XSRF-TOKEN", "")
        if not xsrf_raw:
            return {}
        xsrf = unquote(xsrf_raw)
        today = _dt.today()
        contratos = []
        for yr_offset in range(3):
            yr = today.year + yr_offset
            y2 = str(yr)[-2:]
            for m in range(1, 13):
                if yr == today.year and m < today.month:
                    continue
                contratos.append(f"ZQ{_MONTH_CODES[m]}{y2}")
        symbols = ",".join(contratos[:20])
        api_url = (
            f"https://www.barchart.com/proxies/core-api/v1/quotes/get"
            f"?symbols={symbols}"
            f"&fields=symbol,contractName,lastPrice,priceChange,volume,openInterest"
            f"&raw=1"
        )
        resp = session.get(api_url, headers={
            "Accept": "application/json",
            "X-XSRF-TOKEN": xsrf,
            "Referer": "https://www.barchart.com/futures/quotes/ZQ*0/futures-prices",
        }, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        result = {}
        for q in data.get("data", []):
            raw   = q.get("raw", {})
            sym   = raw.get("symbol", "")
            price = raw.get("lastPrice")
            vol   = raw.get("volume", 0)
            oi    = raw.get("openInterest", 0)
            chg   = raw.get("priceChange", 0)
            name  = raw.get("contractName", "")
            if sym and price:
                result[sym] = {
                    "price": price,
                    "rate":  round(100.0 - price, 4),
                    "chg":   chg,
                    "vol":   vol,
                    "oi":    oi,
                    "name":  name,
                }
        return result
    except Exception:
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def _load_zq_historical() -> dict:
    try:
        import yfinance as yf
    except ImportError:
        return {}
    today = pd.Timestamp.today()
    contratos = []
    for yr_offset in range(3):
        yr = today.year + yr_offset
        y2 = str(yr)[-2:]
        for m in range(1, 13):
            if yr == today.year and m < today.month:
                continue
            contratos.append(f"ZQ{_MONTH_CODES[m]}{y2}")
    yf_map = {c: f"{c}.CBT" for c in contratos[:18]}
    start  = (today - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
    result = {}
    try:
        raw = yf.download(
            " ".join(yf_map.values()),
            start=start,
            auto_adjust=True,
            progress=False,
        )
        if raw.empty:
            return {}
        close = raw["Close"] if "Close" in raw.columns else raw.xs("Close", axis=1, level=0)
        if isinstance(close.columns, pd.MultiIndex):
            close.columns = close.columns.get_level_values(-1)
        for canon, yf_sym in yf_map.items():
            col = yf_sym if yf_sym in close.columns else (canon if canon in close.columns else None)
            if col is None:
                continue
            s = close[col].dropna()
            if len(s) < 5:
                continue
            result[canon] = (100.0 - s).rename(canon)
    except Exception:
        return {}
    return result

def _rate_for_meeting(meeting_dt: pd.Timestamp, zq_data: dict) -> float:
    year2 = str(meeting_dt.year)[-2:]
    mc    = _MONTH_CODES[meeting_dt.month]
    canon = f"ZQ{mc}{year2}"
    entry = zq_data.get(canon)
    if entry is None:
        return float("nan")
    return entry.get("rate", float("nan"))

def _build_fw_curve(zq_data: dict):
    today_ts = pd.Timestamp.today().normalize()
    meetings = [pd.Timestamp(m) for m in FOMC_MEETINGS
                if pd.Timestamp(m) >= today_ts - pd.Timedelta(days=5)]
    labels, rates, changes = [], [], []
    for m in meetings:
        r = _rate_for_meeting(m, zq_data)
        if not pd.isna(r):
            labels.append(m.strftime("%d %b %Y"))
            rates.append(r)
            year2 = str(m.year)[-2:]
            mc    = _MONTH_CODES[m.month]
            entry = zq_data.get(f"ZQ{mc}{year2}", {})
            changes.append(round(entry.get("chg", 0) * -100, 1))
    return labels, rates, changes

def _curve_at_date(zq_hist: dict, target: pd.Timestamp, tol_days: int = 5) -> tuple:
    labels, rates = [], []
    for m_str in FOMC_MEETINGS:
        meeting = pd.Timestamp(m_str)
        if meeting < target:
            continue
        y2    = str(meeting.year)[-2:]
        mc    = _MONTH_CODES[meeting.month]
        canon = f"ZQ{mc}{y2}"
        s     = zq_hist.get(canon)
        if s is None or len(s) == 0:
            continue
        diffs = [abs((idx - target).days) for idx in s.index]
        min_d = min(diffs)
        if min_d > tol_days:
            continue
        rate = float(s.iloc[diffs.index(min_d)])
        if pd.isna(rate) or rate <= 0 or rate > 10:
            continue
        labels.append(meeting.strftime("%d %b %Y"))
        rates.append(round(rate, 4))
    return labels, rates

def _render_fedwatch():
    _sec("FED FUNDS PATH IMPLÍCITO — ZQ Futures (CME/Barchart)")
    with st.spinner("Descargando contratos ZQ..."):
        zq_data = _load_zq_barchart()
    if not zq_data:
        st.warning("No se pudieron cargar contratos ZQ desde Barchart. Verificar conexión.")
        _close_box()
        return
    labels_now, rates_now, changes_now = _build_fw_curve(zq_data)
    if not rates_now:
        st.warning("No hay meetings futuros con datos disponibles.")
        _close_box()
        return
    front_rate   = rates_now[0]
    min_rate     = min(rates_now)
    total_cuts   = max(0.0, (front_rate - min_rate) * 100)
    terminal_lbl = labels_now[rates_now.index(min_rate)]
    n_meetings   = len(rates_now)
    _kpi_strip([
        (f"{front_rate:.2f}%",  "TASA PRÓX. MEETING",    labels_now[0],                  AMBER),
        (f"{min_rate:.2f}%",    "TASA TERMINAL",          f"mín ciclo · {terminal_lbl}",  CYAN),
        (f"{total_cuts:.0f}bp", "RECORTES IMPLÍCITOS",    "frente → piso",                GREEN if total_cuts > 0 else MUTED),
        (f"{n_meetings}",       "MEETINGS CON DATOS",     "vía Barchart · ZQ",            MUTED),
    ])
    fig_fw = go.Figure()
    fig_fw.add_trace(go.Scatter(
        x=labels_now + labels_now[::-1],
        y=[r + 0.25 for r in rates_now] + [r - 0.25 for r in rates_now[::-1]],
        fill="toself", fillcolor="rgba(255,102,0,0.05)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))
    fig_fw.add_trace(go.Scatter(
        name="Tasa implícita",
        x=labels_now, y=rates_now,
        mode="lines+markers+text",
        line=dict(color=ORANGE, width=2.5),
        marker=dict(size=8, color=ORANGE, line=dict(color=BG2, width=1.5)),
        text=[f"{r:.2f}%" for r in rates_now],
        textposition="top center",
        textfont=dict(size=10, color=GOLD, family="'Courier New',monospace"),
        hovertemplate="<b>%{x}</b><br>Tasa implícita: <b>%{y:.2f}%</b><extra></extra>",
    ))
    fig_fw.add_hline(
        y=front_rate, line_dash="dot", line_color=AMBER,
        annotation_text=f"Próx. meeting {front_rate:.2f}%",
        annotation_font=dict(size=10, color=AMBER, family="'Courier New',monospace"),
        annotation_position="bottom right",
    )
    lay_fw = _layout(360)
    lay_fw["margin"]             = dict(l=55, r=20, t=30, b=80)
    lay_fw["xaxis"]["tickangle"] = -40
    lay_fw["xaxis"]["showgrid"]  = True
    lay_fw["xaxis"]["gridcolor"] = GRID
    lay_fw["yaxis"]["tickformat"] = ".2f"
    lay_fw["yaxis"]["ticksuffix"] = "%"
    lay_fw["showlegend"] = False
    fig_fw.update_layout(**lay_fw)
    st.plotly_chart(fig_fw, use_container_width=True, config=PLOTLY_CFG)
    _sec("TABLA — CURVA IMPLÍCITA POR MEETING")
    T3     = "font-family:'Courier New',monospace;"
    TH_s   = f"padding:4px 10px;{T3}font-size:11px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;"
    TH0_s  = f"padding:4px 10px;{T3}font-size:11px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;"
    hdr    = (f'<tr>'
              f'<th style="{TH0_s}">MEETING</th>'
              f'<th style="{TH_s}">CONTRATO</th>'
              f'<th style="{TH_s}">TASA IMPL.</th>'
              f'<th style="{TH_s}">vs PRÓX.</th>'
              f'<th style="{TH_s}">CHG (bp)</th>'
              f'<th style="{TH_s}">VOL</th>'
              f'</tr>')
    body = ""
    for i, (lbl, rate, chg_bp) in enumerate(zip(labels_now, rates_now, changes_now)):
        m_ts  = pd.to_datetime(lbl, dayfirst=True)
        y2    = str(m_ts.year)[-2:]
        mc    = _MONTH_CODES[m_ts.month]
        sym   = f"ZQ{mc}{y2}"
        entry = zq_data.get(sym, {})
        vol   = entry.get("vol", 0)
        vol_s = f"{vol:,}" if vol else "—"
        delta   = rate - front_rate
        dcolor  = GREEN if delta < -0.005 else (RED if delta > 0.005 else MUTED)
        chg_col = GREEN if chg_bp < 0 else (RED if chg_bp > 0 else MUTED)
        rate_s  = f'<span style="color:{GOLD};font-weight:bold">{rate:.2f}%</span>'
        delta_s = f'<span style="color:{dcolor};font-weight:bold">{delta:+.2f}%</span>'
        chg_s   = f'<span style="color:{chg_col};font-weight:bold">{chg_bp:+.1f}</span>'
        bg_row  = "#000" if i % 2 == 0 else "#060606"
        body   += (f'<tr>'
                   f'<td style="padding:3px 10px;{T3}font-size:12px;color:#ccc;background:{bg_row};border-right:1px solid #1a1a1a;">{lbl}</td>'
                   f'<td style="padding:3px 10px;{T3}font-size:11px;color:{MUTED};background:{bg_row};border-right:1px solid #1a1a1a;text-align:center;">{sym}</td>'
                   f'<td style="padding:3px 10px;{T3}font-size:12px;text-align:right;background:{bg_row};border-right:1px solid #1a1a1a;">{rate_s}</td>'
                   f'<td style="padding:3px 10px;{T3}font-size:12px;text-align:right;background:{bg_row};border-right:1px solid #1a1a1a;">{delta_s}</td>'
                   f'<td style="padding:3px 10px;{T3}font-size:12px;text-align:right;background:{bg_row};border-right:1px solid #1a1a1a;">{chg_s}</td>'
                   f'<td style="padding:3px 10px;{T3}font-size:11px;color:{MUTED};text-align:right;background:{bg_row};">{vol_s}</td>'
                   f'</tr>')
    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:8px;">'
        f'<table style="border-collapse:collapse;width:100%;">'
        f'<thead>{hdr}</thead><tbody>{body}</tbody></table></div>',
        unsafe_allow_html=True,
    )
    _sec("DESPLAZAMIENTO DE LA CURVA — HOY vs T-30 · T-90 · T-365")
    with st.spinner("Cargando historia ZQ..."):
        zq_hist = _load_zq_historical()
    today_ts = pd.Timestamp.today().normalize()
    snapshots = [
        ("Hoy",   today_ts,                              ORANGE,    2.5, "solid",   True),
        ("−30d",  today_ts - pd.Timedelta(days=30),      CYAN,      1.8, "dot",     False),
        ("−90d",  today_ts - pd.Timedelta(days=90),      GREEN,     1.8, "dash",    False),
        ("−365d", today_ts - pd.Timedelta(days=365),     "#9b59b6", 1.5, "dashdot", False),
    ]
    fig_hist = go.Figure()
    kpi_rows = []
    has_data = False
    for label, snap_date, color, width, dash, is_today in snapshots:
        if is_today:
            lbl_c, rate_c = labels_now, rates_now
        else:
            if not zq_hist:
                continue
            lbl_c, rate_c = _curve_at_date(zq_hist, snap_date)
        if not rate_c:
            continue
        has_data   = True
        snap_min   = min(rate_c)
        snap_front = rate_c[0]
        snap_cuts  = max(0.0, (snap_front - snap_min) * 100)
        term_lbl   = lbl_c[rate_c.index(snap_min)]
        kpi_rows.append({
            "label": label, "color": color,
            "front": snap_front, "terminal": snap_min,
            "cuts_bp": snap_cuts, "term_lbl": term_lbl,
        })
        fig_hist.add_trace(go.Scatter(
            name=label,
            x=lbl_c, y=rate_c,
            mode="lines+markers" + ("+text" if is_today else ""),
            line=dict(color=color, width=width, dash=dash),
            marker=dict(size=7 if is_today else 5, color=color,
                        line=dict(color=BG2, width=1)),
            text=[f"{r:.2f}%" for r in rate_c] if is_today else None,
            textposition="top center" if is_today else None,
            textfont=dict(size=10, color=GOLD, family="'Courier New',monospace"),
            hovertemplate=(
                f"<b>{label}</b> · %{{x}}<br>"
                f"Tasa: <b>%{{y:.2f}}%</b><extra></extra>"
            ),
        ))
    if has_data:
        lay_h = _layout(360)
        lay_h["margin"]              = dict(l=55, r=20, t=30, b=80)
        lay_h["xaxis"]["tickangle"]  = -40
        lay_h["xaxis"]["showgrid"]   = True
        lay_h["xaxis"]["gridcolor"]  = GRID
        lay_h["yaxis"]["tickformat"] = ".2f"
        lay_h["yaxis"]["ticksuffix"] = "%"
        lay_h["showlegend"]          = True
        lay_h["legend"] = dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, size=11, family="'Courier New',monospace"),
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        )
        fig_hist.update_layout(**lay_h)
        st.plotly_chart(fig_hist, use_container_width=True, config=PLOTLY_CFG)
    if len(kpi_rows) >= 2:
        T3    = "font-family:'Courier New',monospace;"
        TH_s  = f"padding:4px 12px;{T3}font-size:11px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;"
        TH0_s = f"padding:4px 12px;{T3}font-size:11px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;"
        hdr_hist = (
            f'<tr>'
            f'<th style="{TH0_s}">SNAPSHOT</th>'
            f'<th style="{TH_s}">TASA FRENTE</th>'
            f'<th style="{TH_s}">TASA TERMINAL</th>'
            f'<th style="{TH_s}">RECORTES IMPL.</th>'
            f'<th style="{TH_s}">MEETING TERMINAL</th>'
            f'<th style="{TH_s}">Δ FRENTE vs HOY</th>'
            f'<th style="{TH_s}">Δ TERMINAL vs HOY</th>'
            f'</tr>'
        )
        t_front   = kpi_rows[0]["front"]
        t_term    = kpi_rows[0]["terminal"]
        body_hist = ""
        for i, row in enumerate(kpi_rows):
            bg  = "#000" if i % 2 == 0 else "#060606"
            c   = row["color"]
            df_ = row["front"]    - t_front
            dt_ = row["terminal"] - t_term
            dc_f = MUTED if i == 0 else (GREEN if df_ < -0.005 else (RED if df_ > 0.005 else MUTED))
            dc_t = MUTED if i == 0 else (GREEN if dt_ < -0.005 else (RED if dt_ > 0.005 else MUTED))
            df_s = "—" if i == 0 else f'<span style="color:{dc_f};font-weight:bold">{df_*100:+.1f}bp</span>'
            dt_s = "—" if i == 0 else f'<span style="color:{dc_t};font-weight:bold">{dt_*100:+.1f}bp</span>'
            td   = f"padding:4px 12px;{T3}font-size:12px;background:{bg};border-right:1px solid #1a1a1a;"
            body_hist += (
                f'<tr>'
                f'<td style="{td}color:{c};font-weight:bold">{row["label"]}</td>'
                f'<td style="{td}text-align:right;color:{GOLD};font-weight:bold">{row["front"]:.2f}%</td>'
                f'<td style="{td}text-align:right;color:{CYAN};font-weight:bold">{row["terminal"]:.2f}%</td>'
                f'<td style="{td}text-align:right;color:{"#00ff41" if row["cuts_bp"]>0 else MUTED};font-weight:bold">{row["cuts_bp"]:.0f}bp</td>'
                f'<td style="{td}text-align:center;color:#aaa">{row["term_lbl"]}</td>'
                f'<td style="{td}text-align:right">{df_s}</td>'
                f'<td style="{td}text-align:right">{dt_s}</td>'
                f'</tr>'
            )
        st.markdown(
            f'<div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:8px;">'
            f'<table style="border-collapse:collapse;width:100%;">'
            f'<thead>{hdr_hist}</thead><tbody>{body_hist}</tbody></table></div>',
            unsafe_allow_html=True,
        )
    elif not has_data:
        st.info("No hay datos históricos ZQ disponibles desde Yahoo Finance en este momento.")
    st.markdown(
        f'<div style="color:{MUTED};font-size:11px;font-family:\'Courier New\',monospace;margin-top:4px;">'
        f'Fuente: CME 30-Day Fed Funds Futures (ZQ) vía Barchart.com (actual) · Yahoo Finance CBT (historia) &nbsp;·&nbsp; '
        f'Metodología: tasa implícita = 100 − precio settle &nbsp;·&nbsp; Cache: 60 min</div>',
        unsafe_allow_html=True,
    )
    _close_box()

def _render_rates():
    _breadcrumb("RATES")
    CUT = "2Y"
    with st.spinner("Loading FRED rates data..."):
        try:
            today = pd.Timestamp.today()
            fetch_start = (today - pd.DateOffset(years=4)).strftime("%Y-%m-%d")
            D   = _load_rates_fred(fetch_start)
            tcv = _load_treasury_curve()
        except Exception as e:
            st.error(f"Rates data error: {e}"); return
    cut_date = (pd.Timestamp.today() - pd.DateOffset(years=2)).strftime("%Y-%m-%d")
    def tr(s): return _rtrim(s, cut_date)
    l_ff    = _rlast(D["fedfunds"])
    l_2     = _rlast(D["dgs2"])
    l_10    = _rlast(D["dgs10"])
    l_30    = _rlast(D["dgs30"])
    l_3m    = _rlast(D["dgs3m"])
    l_spr   = _rlast(D["t10y2y"])
    l_t10t3m= _rlast(D["t10y3m"])
    l_real  = _rlast(D["tips10"])
    l_bei10 = _rlast(D["bei10"])
    l_sofr  = _rlast(D["sofr"])
    l_hy_bp = _rlast(D["hy_oas"])  * 100
    l_ig_bp = _rlast(D["ig_oas"])  * 100
    l_nfci  = _rlast(D["nfci"])
    l_mort  = _rlast(D["mortgage30"])
    l_dxy   = _rlast(D["dollar"])
    _kpi_strip([
        (f"{l_ff:.2f}%"      if not pd.isna(l_ff)    else "—", "FED FUNDS",   f"SOFR: {l_sofr:.2f}%",       AMBER),
        (f"{l_2:.2f}%"       if not pd.isna(l_2)     else "—", "2Y TREASURY", f"3M: {l_3m:.2f}%",           BLUE),
        (f"{l_10:.2f}%"      if not pd.isna(l_10)    else "—", "10Y TREASURY",f"30Y: {l_30:.2f}%",          CYAN),
        (f"{l_spr:+.2f}%"    if not pd.isna(l_spr)   else "—", "2s10s SPREAD",f"10Y-3M: {l_t10t3m:+.2f}%", _spr_color(l_spr)),
        (f"{l_real:.2f}%"    if not pd.isna(l_real)  else "—", "10Y REAL",    f"BEI: {l_bei10:.2f}%",       TEAL),
        (f"{l_hy_bp:.0f}bp"  if not pd.isna(l_hy_bp) else "—", "HY OAS",      f"IG: {l_ig_bp:.0f}bp",       GREEN if l_hy_bp < 350 else (AMBER if l_hy_bp < 600 else RED)),
    ])
    rtabs = st.tabs(["YIELD CURVE", "FED CORRIDOR", "CREDIT & CONDITIONS", "FEDWATCH", "RATE SNAPSHOT"])
    with rtabs[0]:
        ytabs = st.tabs(["Snapshot", "History", "Spreads"])
        with ytabs[0]:
            _sec("YIELD CURVE — CURRENT vs 3M AGO vs 1Y AGO")
            def _curve_pts(days_ago=0):
                pts = {}
                for label, key in zip(TENORS, TENOR_KEYS):
                    s = D[key].dropna()
                    if not len(s): continue
                    idx = -1 - days_ago
                    if abs(idx) <= len(s):
                        pts[label] = float(s.iloc[idx])
                return pts
            today_c = dict(tcv) if len(tcv) else _curve_pts(0)
            m3ago_c = _curve_pts(63)
            y1ago_c = _curve_pts(252)
            tenor_ord = ["1M","3M","6M","1Y","2Y","3Y","5Y","7Y","10Y","20Y","30Y"]
            def _ordered(d):
                return [(t, d[t]) for t in tenor_ord if t in d]
            fig_yc = go.Figure()
            for label, pts, color, dash, width in [
                ("Today",    today_c, CYAN,  "solid", 2.5),
                ("3M ago",   m3ago_c, AMBER, "dot",   1.5),
                ("1Y ago",   y1ago_c, MUTED, "dash",  1.5),
            ]:
                ordered = _ordered(pts)
                if ordered:
                    xs, ys = zip(*ordered)
                    fig_yc.add_trace(go.Scatter(
                        name=label, x=list(xs), y=list(ys),
                        mode="lines+markers",
                        line=dict(color=color, width=width, dash=dash),
                        marker=dict(size=5, color=color),
                        hovertemplate=f"<b>{label}</b> %{{x}}: %{{y:.2f}}%<extra></extra>",
                    ))
            lay_yc = _layout(380)
            lay_yc["margin"] = dict(l=55, r=20, t=36, b=36)
            lay_yc["xaxis"]["showgrid"] = True
            lay_yc["xaxis"]["gridcolor"] = GRID
            fig_yc.update_layout(**lay_yc)
            st.plotly_chart(fig_yc, use_container_width=True, config=PLOTLY_CFG)
            _sec("TENOR SNAPSHOT")
            T = "font-family:'Courier New',monospace;"
            th_s = f"padding:4px 12px;{T}font-size:11px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;white-space:nowrap;"
            th0  = f"padding:4px 12px;{T}font-size:11px;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;min-width:80px;"
            hdr_yc = f'<tr><th style="{th0}">TENOR</th>'
            for col in ["CURRENT","3M AGO","1Y AGO","CHG 3M","CHG 1Y"]:
                hdr_yc += f'<th style="{th_s}">{col}</th>'
            hdr_yc += "</tr>"
            body_yc = ""
            for tenor in tenor_ord:
                cur = today_c.get(tenor); m3 = m3ago_c.get(tenor); y1 = y1ago_c.get(tenor)
                if cur is None: continue
                chg3 = cur - m3 if m3 else float("nan")
                chgy = cur - y1 if y1 else float("nan")
                def _td_chg(v):
                    if pd.isna(v): return f'<td style="padding:3px 10px;{T}font-size:12px;text-align:right;background:#0a0a0a;color:#444;border-right:1px solid #111;">—</td>'
                    bg = "#062910" if v < -0.1 else ("#2a0606" if v > 0.1 else "#0a0a0a")
                    fg = "#34d399" if v < -0.1 else ("#f87171" if v > 0.1 else "#888")
                    return f'<td style="padding:3px 10px;{T}font-size:12px;font-weight:bold;text-align:right;background:{bg};color:{fg};border-right:1px solid #111;">{v:+.2f}%</td>'
                nm = f'<td style="padding:3px 12px;{T}font-size:12px;font-weight:bold;color:{CYAN};background:#000;border-right:1px solid #333;">{tenor}</td>'
                vc = f'<td style="padding:3px 10px;{T}font-size:12px;font-weight:bold;text-align:right;background:#0a0a0a;color:{GOLD};border-right:1px solid #111;">{cur:.2f}%</td>'
                v3 = f'<td style="padding:3px 10px;{T}font-size:12px;text-align:right;background:#000;color:#aaa;border-right:1px solid #111;">{m3:.2f}%</td>' if m3 else f'<td style="padding:3px 10px;{T}font-size:12px;text-align:right;background:#000;color:#444;border-right:1px solid #111;">—</td>'
                v1 = f'<td style="padding:3px 10px;{T}font-size:12px;text-align:right;background:#000;color:#888;border-right:1px solid #111;">{y1:.2f}%</td>' if y1 else f'<td style="padding:3px 10px;{T}font-size:12px;text-align:right;background:#000;color:#444;border-right:1px solid #111;">—</td>'
                body_yc += f"<tr>{nm}{vc}{v3}{v1}{_td_chg(chg3)}{_td_chg(chgy)}</tr>"
            st.markdown(f"""
            <div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:8px;">
              <table style="border-collapse:collapse;width:100%;">
                <thead>{hdr_yc}</thead><tbody>{body_yc}</tbody>
              </table>
            </div>""", unsafe_allow_html=True)
            _close_box()
        with ytabs[1]:
            _sec("10Y · 2Y · 3M — HISTORICAL")
            fig_yh = go.Figure()
            for name, key, color, dash in [
                ("10Y", "dgs10", CYAN,  "solid"),
                ("2Y",  "dgs2",  BLUE,  "solid"),
                ("3M",  "dgs3m", AMBER, "dot"),
                ("30Y", "dgs30", MUTED, "dash"),
            ]:
                s = tr(D[key].dropna())
                if len(s):
                    fig_yh.add_trace(go.Scatter(name=name, x=s.index, y=s.values,
                        line=dict(color=color, width=2, dash=dash),
                        hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>"))
            lay_yh = _layout(420); lay_yh["margin"] = dict(l=55, r=20, t=92, b=36)
            lay_yh["xaxis"]["rangeselector"] = _rangeselector()
            fig_yh.update_layout(**lay_yh)
            st.plotly_chart(fig_yh, use_container_width=True, config=PLOTLY_CFG)
            _close_box()
        with ytabs[2]:
            _sec("2s10s & 10Y-3M SPREADS")
            fig_sp = go.Figure()
            fig_sp.add_hline(y=0, line_color="#333", line_width=1)
            for name, key, color in [
                ("2s10s",   "t10y2y", CYAN),
                ("10Y-3M",  "t10y3m", AMBER),
            ]:
                s = tr(D[key].dropna())
                if len(s):
                    fig_sp.add_trace(go.Scatter(name=name, x=s.index, y=s.values,
                        line=dict(color=color, width=2),
                        fill="tozeroy", fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.06)",
                        hovertemplate=f"<b>{name}</b>: %{{y:+.2f}}%<extra></extra>"))
            lay_sp = _layout(320); lay_sp["margin"] = dict(l=55, r=20, t=36, b=36)
            fig_sp.update_layout(**lay_sp)
            st.plotly_chart(fig_sp, use_container_width=True, config=PLOTLY_CFG)
            _close_box()
    with rtabs[1]:
        _sec("FED CORRIDOR — FED FUNDS · SOFR · IORB · ON RRP")
        fig_corr = make_subplots(specs=[[{"secondary_y": True}]])
        lb = tr(D["fed_lb"].dropna()); ub = tr(D["fed_ub"].dropna())
        ci = lb.index.intersection(ub.index)
        if len(ci):
            fig_corr.add_trace(go.Scatter(
                name="Target Range",
                x=list(ci) + list(ci[::-1]),
                y=list(ub.reindex(ci).values) + list(lb.reindex(ci).values[::-1]),
                fill="toself", fillcolor="rgba(245,158,11,0.08)",
                line=dict(color="rgba(0,0,0,0)"), showlegend=True, hoverinfo="skip",
            ), secondary_y=False)
        for name, key, color, width, dash in [
            ("Fed Funds",    "fedfunds", AMBER,  2.5, "solid"),
            ("SOFR",         "sofr",     CYAN,   2.0, "solid"),
            ("IORB (ceil.)", "iorb",     PINK,   1.5, "dot"),
            ("ON RRP (fl.)", "onrrp",    VIOLET, 1.5, "dash"),
        ]:
            s = tr(D[key].dropna())
            if len(s):
                fig_corr.add_trace(go.Scatter(name=name, x=s.index, y=s.values,
                    line=dict(color=color, width=width, dash=dash),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>"),
                    secondary_y=False)
        lay_c = _layout_sub(420)
        lay_c["margin"] = dict(l=55, r=20, t=36, b=36)
        fig_corr.update_layout(**lay_c)
        _style_sub_axes(fig_corr)
        st.plotly_chart(fig_corr, use_container_width=True, config=PLOTLY_CFG)
        _sec("REAL RATE · TIPS · BREAKEVENS")
        fig_rr = go.Figure()
        for name, key, color, dash in [
            ("10Y Real (TIPS)", "tips10", TEAL,   "solid"),
            ("5Y Real",         "tips5",  CYAN,   "dot"),
            ("BEI 10Y",         "bei10",  PINK,   "solid"),
            ("BEI 5Y",          "bei5",   VIOLET, "dot"),
        ]:
            s = tr(D[key].dropna())
            if len(s):
                fig_rr.add_trace(go.Scatter(name=name, x=s.index, y=s.values,
                    line=dict(color=color, width=2, dash=dash),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}%<extra></extra>"))
        fig_rr.add_hline(y=0, line_color="#333", line_width=1)
        lay_rr = _layout(320); lay_rr["margin"] = dict(l=55, r=20, t=36, b=36)
        fig_rr.update_layout(**lay_rr)
        st.plotly_chart(fig_rr, use_container_width=True, config=PLOTLY_CFG)
        _sec("MORTGAGE 30Y vs FED FUNDS · USD INDEX")
        fig_tr = make_subplots(specs=[[{"secondary_y": True}]])
        for name, key, color, dash, sec_y in [
            ("Mortgage 30Y", "mortgage30", PINK,  "solid", False),
            ("Fed Funds",    "fedfunds",   AMBER, "dot",   False),
            ("USD Index",    "dollar",     CYAN,  "solid", True),
        ]:
            s = tr(D[key].dropna())
            if len(s):
                fig_tr.add_trace(go.Scatter(name=name, x=s.index, y=s.values,
                    line=dict(color=color, width=2, dash=dash),
                    hovertemplate=f"<b>{name}</b>: %{{y:.2f}}<extra></extra>"),
                    secondary_y=sec_y)
        lay_tr = _layout_sub(340); lay_tr["margin"] = dict(l=55, r=55, t=36, b=36)
        fig_tr.update_layout(**lay_tr)
        _style_sub_axes(fig_tr)
        st.plotly_chart(fig_tr, use_container_width=True, config=PLOTLY_CFG)
        _close_box()
    with rtabs[2]:
        _sec("CREDIT SPREADS — OAS (basis points)")
        ig_bp  = D["ig_oas"]  * 100
        hy_bp  = D["hy_oas"]  * 100
        bbb_bp = D["bbb_oas"] * 100
        ig_pct  = _rpctile(ig_bp,  l_ig_bp)
        hy_pct  = _rpctile(hy_bp,  l_hy_bp)
        def _oas_c(p): return GREEN if p < 30 else (AMBER if p < 60 else RED)
        _kpi_strip([
            (f"{l_ig_bp:.0f}bp",           "IG OAS",    f"pctile {ig_pct:.0f}%",  _oas_c(ig_pct)),
            (f"{_rlast(bbb_bp):.0f}bp",    "BBB OAS",   "BAML C0A4",              AMBER),
            (f"{l_hy_bp:.0f}bp",           "HY OAS",    f"pctile {hy_pct:.0f}%",  _oas_c(hy_pct)),
            (f"{l_hy_bp - l_ig_bp:.0f}bp", "HY-IG DIFF","fallen angel proxy",     AMBER),
        ])
        fig_cr = go.Figure()
        for name, s, color, dash in [
            ("HY OAS",  tr(hy_bp.dropna()),  RED,   "solid"),
            ("BBB OAS", tr(bbb_bp.dropna()), AMBER, "dot"),
            ("IG OAS",  tr(ig_bp.dropna()),  GREEN, "dash"),
        ]:
            if len(s):
                fig_cr.add_trace(go.Scatter(name=name, x=s.index, y=s.values,
                    line=dict(color=color, width=2, dash=dash),
                    hovertemplate=f"<b>{name}</b>: %{{y:.0f}}bp<extra></extra>"))
        lay_cr = _layout(380); lay_cr["margin"] = dict(l=55, r=20, t=36, b=36)
        fig_cr.update_layout(**lay_cr)
        st.plotly_chart(fig_cr, use_container_width=True, config=PLOTLY_CFG)
        _sec("FINANCIAL CONDITIONS — NFCI · VIX")
        nfci_t = tr(D["nfci"].dropna())
        vix_t  = tr(D["vix"].dropna())
        fig_nf = make_subplots(specs=[[{"secondary_y": True}]])
        if len(nfci_t):
            nfci_pos = nfci_t.clip(lower=0)
            nfci_neg = nfci_t.clip(upper=0)
            fig_nf.add_trace(go.Bar(name="NFCI tight (>0)", x=nfci_pos.index, y=nfci_pos.values,
                marker_color=RED, opacity=0.7,
                hovertemplate="<b>NFCI</b>: %{y:+.3f}<extra></extra>"), secondary_y=False)
            fig_nf.add_trace(go.Bar(name="NFCI loose (<0)", x=nfci_neg.index, y=nfci_neg.values,
                marker_color=GREEN, opacity=0.7,
                hovertemplate="<b>NFCI</b>: %{y:+.3f}<extra></extra>"), secondary_y=False)
            ma52 = nfci_t.rolling(52).mean()
            fig_nf.add_trace(go.Scatter(name="52W MA", x=ma52.index, y=ma52.values,
                line=dict(color=WHITE, width=2),
                hovertemplate="<b>52W MA</b>: %{y:+.3f}<extra></extra>"), secondary_y=False)
        if len(vix_t):
            fig_nf.add_trace(go.Scatter(name="VIX", x=vix_t.index, y=vix_t.values,
                line=dict(color=CYAN, width=1.5, dash="dot"),
                hovertemplate="<b>VIX</b>: %{y:.1f}<extra></extra>"), secondary_y=True)
        lay_nf = _layout_sub(340)
        lay_nf["barmode"] = "overlay"
        lay_nf["margin"]  = dict(l=55, r=55, t=36, b=36)
        fig_nf.update_layout(**lay_nf)
        _style_sub_axes(fig_nf)
        st.plotly_chart(fig_nf, use_container_width=True, config=PLOTLY_CFG)
        _close_box()
    with rtabs[3]:
        _render_fedwatch()
    with rtabs[4]:
        _sec("RATE SNAPSHOT — LEVELS & DELTAS")
        snap_map = [
            ("Fed Funds",       "fedfunds",   "rate"),
            ("SOFR",            "sofr",       "rate"),
            ("IORB",            "iorb",       "rate"),
            ("ON RRP",          "onrrp",      "rate"),
            ("3M T-Bill",       "dgs3m",      "rate"),
            ("2Y Treasury",     "dgs2",       "rate"),
            ("5Y Treasury",     "dgs5",       "rate"),
            ("10Y Treasury",    "dgs10",      "rate"),
            ("30Y Treasury",    "dgs30",      "rate"),
            ("2s10s Spread",    "t10y2y",     "spread"),
            ("10Y-3M Spread",   "t10y3m",     "spread"),
            ("10Y Real (TIPS)", "tips10",     "rate"),
            ("BEI 10Y",         "bei10",      "rate"),
            ("IG OAS (bp)",     "ig_oas",     "oas"),
            ("HY OAS (bp)",     "hy_oas",     "oas"),
            ("VIX",             "vix",        "vix"),
            ("NFCI",            "nfci",       "nfci"),
            ("Mortgage 30Y",    "mortgage30", "rate"),
            ("USD Index",       "dollar",     "idx"),
        ]
        T2 = "font-family:'Courier New',monospace;"
        TH  = f"padding:4px 10px;{T2}font-size:11px;font-weight:bold;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #1a1a1a;text-align:center;white-space:nowrap;"
        TH0 = f"padding:4px 12px;{T2}font-size:11px;font-weight:bold;color:#666;background:#0d0d0d;border-bottom:1px solid #333;border-right:1px solid #333;text-align:left;min-width:160px;"
        hdr_s = f'<tr><th style="{TH0}">INSTRUMENT</th>'
        for col in ["CURRENT","1W Δ","1M Δ","3M Δ","1Y Δ"]:
            hdr_s += f'<th style="{TH}">{col}</th>'
        hdr_s += "</tr>"
        def _snap_fmtc(kind, v):
            if pd.isna(v): return "—"
            if kind == "oas":  return f"{v*100:.0f}"
            if kind == "nfci": return f"{v:+.3f}"
            if kind in ("vix","idx"): return f"{v:.1f}"
            return f"{v:.2f}%"
        def _snap_fmtd(kind, v):
            if pd.isna(v): return "—"
            if kind == "oas":  return f"{v*100:+.0f}"
            if kind == "nfci": return f"{v:+.3f}"
            if kind in ("vix","idx"): return f"{v:+.1f}"
            return f"{v:+.2f}%"
        def _snap_delta_style(v, kind):
            if pd.isna(v): return f"padding:3px 10px;{T2}font-size:12px;text-align:right;background:#0a0a0a;color:#333;border-right:1px solid #111;white-space:nowrap;"
            raw = v * 100 if kind == "oas" else v
            thr = 0.5 if kind not in ("vix","idx","nfci") else (3 if kind=="vix" else 1)
            if raw > thr:    bg,fg = "#2a0606","#f87171"
            elif raw > 0.05: bg,fg = "#1a0505","#fca5a5"
            elif raw < -thr: bg,fg = "#062910","#34d399"
            elif raw < -0.05:bg,fg = "#041a0a","#6ee7b7"
            else:             bg,fg = "#0a0a0a","#666"
            return f"padding:3px 10px;{T2}font-size:12px;font-weight:bold;text-align:right;background:{bg};color:{fg};border-right:1px solid #111;white-space:nowrap;"
        body_s = ""
        for label, key, kind in snap_map:
            s = D[key].dropna()
            cur = float(s.iloc[-1]) if len(s) else float("nan")
            deltas = []
            for days in [5, 22, 63, 252]:
                deltas.append(float(s.iloc[-1] - s.iloc[-days]) if len(s) > days else float("nan"))
            nm_td = f'<td style="padding:3px 12px;{T2}font-size:12px;font-weight:bold;color:#ccc;background:#000;border-right:1px solid #333;white-space:nowrap;">{label}</td>'
            cv_td = f'<td style="padding:3px 10px;{T2}font-size:12px;font-weight:bold;text-align:right;background:#0a0a0a;color:{GOLD};border-right:1px solid #111;white-space:nowrap;">{_snap_fmtc(kind, cur)}</td>'
            d_tds = "".join(f'<td style="{_snap_delta_style(d, kind)}">{_snap_fmtd(kind, d)}</td>' for d in deltas)
            body_s += f"<tr>{nm_td}{cv_td}{d_tds}</tr>"
        st.markdown(f"""
        <div style="overflow-x:auto;border:1px solid #2a2a2a;background:#000;margin-bottom:4px;">
          <table style="border-collapse:collapse;width:100%;">
            <thead>{hdr_s}</thead><tbody>{body_s}</tbody>
          </table>
        </div>
        <div style="color:#444;font-size:11px;{T2}margin-bottom:10px;">
          FRED &nbsp;·&nbsp; US Treasury &nbsp;·&nbsp; OAS in basis points (BAML ×100) &nbsp;·&nbsp; Red = rising rate / Green = falling
        </div>""", unsafe_allow_html=True)
        _close_box()

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def render():
    # _close_box() extra de seguridad: si algún _render_* corta antes de
    # llegar a su _close_box() (excepción no prevista), esto evita que un
    # recuadro quede "abierto" y arrastre contenido de las demás sub-tabs.
    subtabs = st.tabs(["GDP", "LABOR", "INFLATION", "RATES"])
    with subtabs[0]:
        try: _render_gdp()
        finally: _close_box()
    with subtabs[1]:
        try: _render_labor()
        finally: _close_box()
    with subtabs[2]:
        try: _render_inflation()
        finally: _close_box()
    with subtabs[3]:
        try: _render_rates()
        finally: _close_box()
