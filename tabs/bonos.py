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


def _fit_curve(durations, yields, x_range, color, name, fig):
    """Add a fitted polynomial curve trace."""
    if len(durations) < 2:
        return
    try:
        dur_arr = np.array(durations)
        yld_arr = np.array(yields)
        deg = min(2, len(durations) - 1)
        coeffs = np.polyfit(dur_arr, yld_arr, deg)
        poly = np.poly1d(coeffs)
        x_smooth = np.linspace(x_range[0], x_range[1], 80)
        y_smooth = poly(x_smooth)
        fig.add_trace(go.Scatter(
            x=x_smooth, y=y_smooth,
            mode="lines",
            line=dict(color=color, width=1.5, dash="dot"),
            name=f"Curva {name}",
            hoverinfo="skip",
            showlegend=False,
        ))
    except Exception:
        pass


def _resolve_text_positions(points):
    """Assign text positions to avoid overlap between nearby points."""
    n = len(points)
    positions = ["top center"] * n
    if n < 2:
        return positions

    dur_range = max(p["duration"] for p in points) - min(p["duration"] for p in points)
    yld_range = max(p["yield"] for p in points) - min(p["yield"] for p in points)
    if dur_range == 0: dur_range = 1
    if yld_range == 0: yld_range = 1

    options = ["top center", "bottom center", "top right", "bottom right",
               "top left", "bottom left", "middle right", "middle left"]

    for i in range(n):
        for j in range(i + 1, n):
            dx = abs(points[i]["duration"] - points[j]["duration"]) / dur_range
            dy = abs(points[i]["yield"] - points[j]["yield"]) / yld_range
            if dx < 0.12 and dy < 0.18:
                used = {positions[k] for k in range(j)}
                for opt in options:
                    if opt not in used:
                        positions[j] = opt
                        break
                else:
                    positions[j] = "bottom center"
    return positions


def _yield_curve_chart(bonds, title="", height=340):
    """Bloomberg-style Yield vs Duration scatter with fitted curves per group."""
    if not bonds:
        return

    points = []
    for b in bonds:
        y = b.get("yield")
        d = b.get("modDuration")
        tk = b.get("ticker") or b.get("localTicker", "")
        if y is not None and d is not None and d > 0:
            points.append({
                "ticker": tk, "yield": float(y), "duration": float(d),
                "price": b.get("price"), "change1D": b.get("change1D"),
                "law": b.get("_law", ""),
            })

    if len(points) < 2:
        return

    fig = go.Figure()

    laws = sorted(set(p.get("law", "") for p in points))
    has_groups = len(laws) > 1

    palette = {
        "LEY NY": "#ff6600",
        "LEY AR": "#00ff41",
    }
    fallback = ["#00ff41", "#ff6600", "#ffcc00", "#00bfff", "#cc66ff"]

    if has_groups:
        for idx, law_name in enumerate(laws):
            law_pts = sorted(
                [p for p in points if p.get("law", "") == law_name],
                key=lambda p: p["duration"]
            )
            if not law_pts:
                continue

            col = palette.get(law_name, fallback[idx % len(fallback)])
            durations = [p["duration"] for p in law_pts]
            yields = [p["yield"] for p in law_pts]
            tickers = [p["ticker"] for p in law_pts]

            # Separate fitted curve per law
            if len(law_pts) >= 2:
                d_min = min(durations) * 0.85
                d_max = max(durations) * 1.08
                _fit_curve(durations, yields, (d_min, d_max), col, law_name, fig)

            text_pos = _resolve_text_positions(law_pts)

            fig.add_trace(go.Scatter(
                x=durations, y=yields,
                mode="markers+text",
                marker=dict(color=col, size=8, line=dict(color="#222", width=0.8)),
                text=tickers,
                textposition=text_pos,
                textfont=dict(size=7, color=col, family="Courier New"),
                name=law_name,
                hovertemplate="<b>%{text}</b><br>Dur: %{x:.2f}<br>Yield: %{y:.2f}%<extra>" + law_name + "</extra>",
            ))
    else:
        points.sort(key=lambda p: p["duration"])
        durations = [p["duration"] for p in points]
        yields = [p["yield"] for p in points]
        tickers = [p["ticker"] for p in points]

        _fit_curve(durations, yields,
                   (min(durations) * 0.85, max(durations) * 1.08),
                   "#ff6600", "", fig)

        text_pos = _resolve_text_positions(points)

        fig.add_trace(go.Scatter(
            x=durations, y=yields,
            mode="markers+text",
            marker=dict(color="#00ff41", size=8, line=dict(color="#222", width=0.8)),
            text=tickers,
            textposition=text_pos,
            textfont=dict(size=7, color="#00ff41", family="Courier New"),
            name="Bonos",
            hovertemplate="<b>%{text}</b><br>Dur: %{x:.2f}<br>Yield: %{y:.2f}%<extra></extra>",
        ))

    all_yields = [p["yield"] for p in points]
    all_durs = [p["duration"] for p in points]
    y_pad = (max(all_yields) - min(all_yields)) * 0.2 if max(all_yields) != min(all_yields) else 1
    x_pad = (max(all_durs) - min(all_durs)) * 0.08 if max(all_durs) != min(all_durs) else 0.5

    fig.update_layout(
        paper_bgcolor="#000",
        plot_bgcolor="#000",
        font=dict(family="Courier New", size=9, color="#555"),
        margin=dict(l=45, r=15, t=35, b=40),
        height=height,
        title=dict(
            text=title,
            font=dict(family="Courier New", size=10, color="#ff6600"),
            x=0.01, xanchor="left",
        ) if title else None,
        xaxis=dict(
            title=dict(text="DURATION", font=dict(size=8, color="#ff6600")),
            gridcolor="#111", linecolor="#333", zerolinecolor="#333",
            tickfont=dict(size=8, color="#555", family="Courier New"),
            showgrid=True,
            range=[min(all_durs) - x_pad, max(all_durs) + x_pad],
        ),
        yaxis=dict(
            title=dict(text="YIELD %", font=dict(size=8, color="#ff6600")),
            gridcolor="#111", linecolor="#333", zerolinecolor="#333",
            tickfont=dict(size=8, color="#555", family="Courier New"),
            ticksuffix="%", showgrid=True,
            range=[min(all_yields) - y_pad, max(all_yields) + y_pad],
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0.7)", bordercolor="#333", borderwidth=1,
            font=dict(size=9, color="#ccc", family="Courier New"),
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        ),
        hoverlabel=dict(
            bgcolor="#111", bordercolor="#ff6600",
            font=dict(family="Courier New", size=9, color="#fff"),
        ),
        showlegend=has_groups,
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
        all_sov_bonds = []
        for sec in sov.get("sections",[]):
            st.markdown(f'<div class="sh">{sec.get("label","")} · LEY {sec.get("law","")}</div>', unsafe_allow_html=True)
            _bonds(sec.get("bonds",[]))
            law_label = f'LEY {sec.get("law", "")}' if sec.get("law") else sec.get("label", "")
            for b in sec.get("bonds", []):
                b_copy = dict(b)
                b_copy["_law"] = law_label
                all_sov_bonds.append(b_copy)
        
        _yield_curve_chart(all_sov_bonds, title="YIELD vs DURATION · SOBERANOS", height=340)

    with subtabs[1]:
        corp_bonds = corp.get("bonds", [])
        _bonds(corp_bonds)
        _yield_curve_chart(corp_bonds, title="YIELD vs DURATION · CORPORATIVOS", height=340)

    with subtabs[2]:
        prov_bonds = prov.get("bonds", [])
        _bonds(prov_bonds)
        _yield_curve_chart(prov_bonds, title="YIELD vs DURATION · PROVINCIALES", height=340)
