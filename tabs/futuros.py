import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_futuros_dolar, get_tasas_implicitas, get_curva_rendimientos

PL = dict(
    paper_bgcolor="#000", plot_bgcolor="#000",
    font=dict(family="Courier New", size=9, color="#555"),
    margin=dict(l=40, r=10, t=25, b=30),
    xaxis=dict(gridcolor="#111", linecolor="#333", zerolinecolor="#333", tickfont=dict(size=8, color="#555")),
    yaxis=dict(gridcolor="#111", linecolor="#333", zerolinecolor="#333", tickfont=dict(size=8, color="#555")),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=8, color="#666")),
    hoverlabel=dict(bgcolor="#111", bordercolor="#333", font=dict(family="Courier New", size=9, color="#fff")),
)

def render():
    subtabs = st.tabs(["FUTUROS DÓLAR", "TASAS TNA", "CURVA TIR"])

    with subtabs[0]:
        with st.spinner(""):
            df = get_futuros_dolar()
        if df.empty:
            st.markdown('<p style="color:#333;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        else:
            rows = ""
            for _, r in df.iterrows():
                esp = r.iloc[0]; ult = r.iloc[1] if len(r)>1 else "—"
                var = r.iloc[2] if len(r)>2 else "—"; tna = r.iloc[3] if len(r)>3 else "—"
                pase = r.iloc[4] if len(r)>4 else "—"
                try:
                    v = float(str(var).replace(",","."))
                    vc = f'<span style="color:{"#00ff41" if v>0 else "#ff3b3b"};font-weight:bold">{var}</span>'
                except: vc = f'<span style="color:#555">{var}</span>'
                try:
                    t = float(str(tna).replace(",",".").replace("%",""))
                    tc = f'<span style="color:#ff6600;font-weight:bold">{t:.1f}%</span>'
                except: tc = f'<span style="color:#555">{tna}</span>'
                rows += f"<tr><td>{esp}</td><td style='color:#ffcc00'>{ult}</td><td>{vc}</td><td>{tc}</td><td style='color:#555'>{pase}</td></tr>"
            st.markdown(f"""<table class="t">
            <thead><tr><th>CONTRATO</th><th>ÚLTIMO</th><th>VAR DIA</th><th>TNA</th><th>PASE</th></tr></thead>
            <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

    with subtabs[1]:
        with st.spinner(""):
            tna_data = get_tasas_implicitas()
        if not tna_data:
            st.markdown('<p style="color:#333;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[p[0] for p in tna_data], y=[p[1] for p in tna_data],
                mode="lines+markers", line=dict(color="#ff6600",width=1.5),
                marker=dict(color="#ff6600",size=5), text=[p[2] for p in tna_data],
                hovertemplate="<b>%{text}</b><br>Días: %{x}<br>TNA: %{y:.2f}%<extra></extra>"))
            layout = dict(PL); layout["yaxis"] = dict(**PL["yaxis"], ticksuffix="%")
            fig.update_layout(**layout, height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with subtabs[2]:
        with st.spinner(""):
            cer, usd = get_curva_rendimientos()
        if not cer and not usd:
            st.markdown('<p style="color:#333;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        else:
            fig = go.Figure()
            if cer:
                fig.add_trace(go.Scatter(x=[p[0] for p in cer], y=[p[1] for p in cer],
                    mode="markers+text", marker=dict(color="#00ff41",size=7),
                    text=[p[2] for p in cer], textposition="top center",
                    textfont=dict(size=7,color="#00ff41"), name="CER",
                    hovertemplate="<b>%{text}</b><br>Dur:%{x:.2f}<br>TIR:%{y:.2f}%<extra></extra>"))
            if usd:
                fig.add_trace(go.Scatter(x=[p[0] for p in usd], y=[p[1] for p in usd],
                    mode="markers+text", marker=dict(color="#ff6600",size=7,symbol="diamond"),
                    text=[p[2] for p in usd], textposition="top center",
                    textfont=dict(size=7,color="#ff6600"), name="USD",
                    hovertemplate="<b>%{text}</b><br>Dur:%{x:.2f}<br>TIR:%{y:.2f}%<extra></extra>"))
            layout = dict(PL); layout["yaxis"] = dict(**PL["yaxis"], ticksuffix="%")
            fig.update_layout(**layout, height=380)
            st.plotly_chart(fig, use_container_width=True)
