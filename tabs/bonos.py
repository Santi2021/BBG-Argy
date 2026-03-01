import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_bondterminal_bootstrap, get_riesgo_pais


def _chg(val):
    if val is None: return '<td style="color:#555">—</td>'
    try:
        f = float(val)
        c = "#00ff41" if f > 0 else ("#ff3b3b" if f < 0 else "#555")
        s = "+" if f > 0 else ""
        return f'<td style="color:{c};font-weight:bold">{s}{f:.2f}</td>'
    except: return f'<td style="color:#555">{val}</td>'


def _bonds(bonds):
    if not bonds:
        st.markdown('<p style="color:#333;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        return
    rows = ""
    for b in bonds:
        tk = b.get("ticker") or b.get("localTicker", "")
        nm = b.get("name", b.get("displayName", ""))
        p = b.get("price")
        ch = b.get("change1D")
        y = b.get("yield")
        d = b.get("modDuration")
        gs = b.get("gSpread")
        gc = b.get("gSpreadChange")
        rows += f"""<tr>
            <td>{tk}</td>
            <td style="color:#555;font-size:9px">{nm[:20]}</td>
            <td style="color:#ffcc00">{f'{p:.2f}' if p else '—'}</td>
            {_chg(ch)}
            <td>{f'{y:.1f}%' if y else '—'}</td>
            <td style="color:#555">{f'{d:.2f}' if d else '—'}</td>
            <td style="color:#555">{gs or '—'}</td>
            {_chg(gc)}
        </tr>"""
    st.markdown(f"""<table class="t">
    <thead><tr><th>TICKER</th><th>NOMBRE</th><th>PRECIO</th><th>Δ DIA</th><th>YIELD</th><th>DUR</th><th>G-SPR</th><th>Δ SPR</th></tr></thead>
    <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)


def _yield_curve_chart(bonds, title="", height=320):
    """
    Bloomberg-style Yield vs Duration scatter with fitted curve.
    bonds: list of dicts with 'ticker', 'yield', 'modDuration', optionally 'law' or section info.
    """
    if not bonds:
        return

    # Extract data points
    points = []
    for b in bonds:
        y = b.get("yield")
        d = b.get("modDuration")
        tk = b.get("ticker") or b.get("localTicker", "")
        if y is not None and d is not None and d > 0:
            points.append({"ticker": tk, "yield": float(y), "duration": float(d),
                           "price": b.get("price"), "change1D": b.get("change1D"),
                           "law": b.get("_law", "")})

    if len(points) < 2:
        return

    # Sort by duration for curve fitting
    points.sort(key=lambda p: p["duration"])
    durations = [p["duration"] for p in points]
    yields = [p["yield"] for p in points]
    tickers = [p["ticker"] for p in points]
    laws = [p.get("law", "") for p in points]

    fig = go.Figure()

    # ── Fitted curve (polynomial) ──
    try:
        dur_arr = np.array(durations)
        yld_arr = np.array(yields)
        # Degree 2 or 3 depending on number of points
        deg = min(3, len(points) - 1)
        coeffs = np.polyfit(dur_arr, yld_arr, deg)
        poly = np.poly1d(coeffs)
        x_smooth = np.linspace(min(durations) * 0.9, max(durations) * 1.05, 100)
        y_smooth = poly(x_smooth)

        fig.add_trace(go.Scatter(
            x=x_smooth, y=y_smooth,
            mode="lines",
            line=dict(color="#ff6600", width=1.5, dash="dot"),
            name="Curva",
            hoverinfo="skip",
            showlegend=False,
        ))
    except Exception:
        pass

    # ── Determine colors by law if available ──
    unique_laws = list(set(laws))
    if len(unique_laws) > 1:
        color_map = {}
        palette = ["#00ff41", "#ff6600", "#ffcc00", "#00bfff", "#ff3b3b", "#cc66ff"]
        for i, law in enumerate(sorted(unique_laws)):
            color_map[law] = palette[i % len(palette)]

        for law_name in sorted(unique_laws):
            law_pts = [p for p in points if p.get("law", "") == law_name]
            if not law_pts:
                continue
            col = color_map[law_name]
            fig.add_trace(go.Scatter(
                x=[p["duration"] for p in law_pts],
                y=[p["yield"] for p in law_pts],
                mode="markers+text",
                marker=dict(color=col, size=8, line=dict(color="#fff", width=0.5)),
                text=[p["ticker"] for p in law_pts],
                textposition="top center",
                textfont=dict(size=8, color=col, family="Courier New"),
                name=law_name if law_name else "—",
                hovertemplate="<b>%{text}</b><br>Duration: %{x:.2f}<br>Yield: %{y:.2f}%<br><extra>" + law_name + "</extra>",
            ))
    else:
        # Single color
        fig.add_trace(go.Scatter(
            x=durations, y=yields,
            mode="markers+text",
            marker=dict(color="#00ff41", size=8, line=dict(color="#fff", width=0.5)),
            text=tickers,
            textposition="top center",
            textfont=dict(size=8, color="#00ff41", family="Courier New"),
            name="Bonos",
            hovertemplate="<b>%{text}</b><br>Duration: %{x:.2f}<br>Yield: %{y:.2f}%<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="#000",
        plot_bgcolor="#000",
        font=dict(family="Courier New", size=9, color="#555"),
        margin=dict(l=45, r=15, t=30, b=35),
        height=height,
        title=dict(
            text=title,
            font=dict(family="Courier New", size=10, color="#ff6600"),
            x=0.01, xanchor="left",
        ) if title else None,
        xaxis=dict(
            title=dict(text="DURATION", font=dict(size=8, color="#ff6600")),
            gridcolor="#111",
            linecolor="#333",
            zerolinecolor="#333",
            tickfont=dict(size=8, color="#555", family="Courier New"),
            showgrid=True,
            gridwidth=1,
        ),
        yaxis=dict(
            title=dict(text="YIELD %", font=dict(size=8, color="#ff6600")),
            gridcolor="#111",
            linecolor="#333",
            zerolinecolor="#333",
            tickfont=dict(size=8, color="#555", family="Courier New"),
            ticksuffix="%",
            showgrid=True,
            gridwidth=1,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#333",
            borderwidth=1,
            font=dict(size=8, color="#ccc", family="Courier New"),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        hoverlabel=dict(
            bgcolor="#111",
            bordercolor="#ff6600",
            font=dict(family="Courier New", size=9, color="#fff"),
        ),
        showlegend=len(unique_laws) > 1 if 'unique_laws' in dir() else False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render():
    rp = get_riesgo_pais()
    boot = get_bondterminal_bootstrap()

    if isinstance(rp, dict) and "error" in rp:
        rp = {"bps":"ERR","delta_1d":0,"delta_1w":0,"delta_1m":0,"bps_ambito":"—","data_quality":""}
    
    bps = rp.get("bps","—")
    d1d = rp.get("delta_1d",0)
    d1w = rp.get("delta_1w",0)
    d1m = rp.get("delta_1m",0)

    def _d(v,l):
        if not v: return ""
        c = "#00ff41" if v>0 else "#ff3b3b"
        s = "+" if v>0 else ""
        return f'<span style="color:{c};font-weight:bold">{s}{v:.0f} {l}</span> '

    st.markdown(f"""
    <div style="border:1px solid #333;padding:6px 12px;margin-bottom:6px;display:flex;align-items:center;gap:20px">
      <div><span style="color:#ffcc00;font-size:24px;font-weight:bold">{bps}</span><span style="color:#555;font-size:10px"> bps EMBI</span></div>
      <div style="font-size:10px">{_d(d1d,"hoy")}{_d(d1w,"7d")}{_d(d1m,"30d")}</div>
      <div style="margin-left:auto;color:#555;font-size:9px">Ámbito: {rp.get("bps_ambito","—")} bps</div>
    </div>""", unsafe_allow_html=True)

    if isinstance(boot, dict) and "error" in boot:
        st.markdown(f'<p style="color:#ff3b3b;font-size:10px">Error: {boot["error"]}</p>', unsafe_allow_html=True)
        return

    subtabs = st.tabs(["SOBERANOS", "CORPORATIVOS", "PROVINCIALES"])
    sov = boot.get("sovereignSnapshot",{})
    corp = boot.get("corporateSnapshot",{})
    prov = boot.get("provincialSnapshot",{})

    with subtabs[0]:
        # Tables
        all_sov_bonds = []
        for sec in sov.get("sections",[]):
            st.markdown(f'<div class="sh">{sec.get("label","")} · LEY {sec.get("law","")}</div>', unsafe_allow_html=True)
            _bonds(sec.get("bonds",[]))
            # Collect bonds with law tag for chart
            law_label = f'LEY {sec.get("law", "")}' if sec.get("law") else sec.get("label", "")
            for b in sec.get("bonds", []):
                b_copy = dict(b)
                b_copy["_law"] = law_label
                all_sov_bonds.append(b_copy)
        
        # Yield vs Duration chart
        st.markdown('<div style="margin-top:12px"></div>', unsafe_allow_html=True)
        _yield_curve_chart(all_sov_bonds, title="YIELD vs DURATION · SOBERANOS", height=340)

    with subtabs[1]:
        corp_bonds = corp.get("bonds", [])
        _bonds(corp_bonds)
        st.markdown('<div style="margin-top:12px"></div>', unsafe_allow_html=True)
        _yield_curve_chart(corp_bonds, title="YIELD vs DURATION · CORPORATIVOS", height=340)

    with subtabs[2]:
        prov_bonds = prov.get("bonds", [])
        _bonds(prov_bonds)
        st.markdown('<div style="margin-top:12px"></div>', unsafe_allow_html=True)
        _yield_curve_chart(prov_bonds, title="YIELD vs DURATION · PROVINCIALES", height=340)
