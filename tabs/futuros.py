import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_futuros_dolar


def render():
    with st.spinner(""):
        df = get_futuros_dolar()

    if df.empty:
        st.markdown('<p style="color:#333;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        return

    # ── Table ──
    rows = ""
    contracts = []
    tna_vals = []

    for _, r in df.iterrows():
        esp = r.iloc[0] if len(r) > 0 else "—"
        ult = r.iloc[1] if len(r) > 1 else "—"
        var = r.iloc[2] if len(r) > 2 else "—"
        tna = r.iloc[3] if len(r) > 3 else "—"
        pase = r.iloc[4] if len(r) > 4 else "—"

        try:
            v = float(str(var).replace(",", "."))
            vc = f'<span style="color:{"#00ff41" if v > 0 else "#ff3b3b"};font-weight:bold">{var}</span>'
        except:
            vc = f'<span style="color:#555">{var}</span>'

        try:
            t = float(str(tna).replace(",", ".").replace("%", ""))
            tc = f'<span style="color:#ff6600;font-weight:bold">{t:.1f}%</span>'
        except:
            t = None
            tc = f'<span style="color:#555">{tna}</span>'

        rows += f"<tr><td>{esp}</td><td style='color:#ffcc00'>{ult}</td><td>{vc}</td><td>{tc}</td><td style='color:#555'>{pase}</td></tr>"

        if t is not None and t > 0:
            contracts.append(str(esp))
            tna_vals.append(t)

    st.markdown(f"""<table class="t">
    <thead><tr><th>CONTRATO</th><th>ÚLTIMO</th><th>VAR DIA</th><th>TNA</th><th>PASE</th></tr></thead>
    <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

    # ── TNA Bar Chart ──
    if contracts and tna_vals:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=contracts,
            y=tna_vals,
            marker_color="#ff6600",
            text=[f"{v:.1f}%" for v in tna_vals],
            textposition="outside",
            textfont=dict(size=8, family="Courier New", color="#ff6600"),
            hovertemplate="<b>%{x}</b><br>TNA: %{y:.1f}%<extra></extra>",
        ))

        y_max = max(tna_vals) * 1.15
        y_min = min(tna_vals) * 0.85

        fig.update_layout(
            paper_bgcolor="#000",
            plot_bgcolor="#000",
            font=dict(family="Courier New", size=9, color="#555"),
            margin=dict(l=45, r=10, t=30, b=35),
            height=300,
            showlegend=False,
            title=dict(
                text="TNA IMPLÍCITA POR VENCIMIENTO",
                font=dict(family="Courier New", size=10, color="#ff6600"),
                x=0.01, xanchor="left",
            ),
            xaxis=dict(
                gridcolor="#111", linecolor="#333",
                tickfont=dict(size=9, color="#ccc", family="Courier New"),
                categoryorder="array", categoryarray=contracts,
            ),
            yaxis=dict(
                gridcolor="#111", linecolor="#333",
                tickfont=dict(size=8, color="#555", family="Courier New"),
                ticksuffix="%",
                range=[y_min, y_max],
            ),
            hoverlabel=dict(
                bgcolor="#111", bordercolor="#ff6600",
                font=dict(family="Courier New", size=9, color="#fff"),
            ),
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
