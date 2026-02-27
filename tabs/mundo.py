import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import (get_yf_quotes, fmt_price, fmt_change,
                  WORLD_TICKERS, COMMODITY_TICKERS, SECTOR_ETFS, FX_TICKERS)


def _pct_td(chg):
    if chg is None: return '<td style="color:#555">—</td>'
    try:
        v = float(str(chg).replace("%","").replace(",","."))
        c = "#00ff41" if v >= 0 else "#ff3b3b"
        s = "+" if v >= 0 else ""
        a = "▲" if v >= 0 else "▼"
        return f'<td style="color:{c};font-weight:bold">{a} {s}{v:.2f}%</td>'
    except: return f'<td style="color:#555">{chg}</td>'


def _quotes_table(data, title, cols=("NOMBRE","PRECIO","% DIA")):
    rows = ""
    for name, q in data.items():
        p = q.get("price")
        chg = q.get("change_pct", 0)
        rows += f"<tr><td>{name}</td><td style='color:#ffcc00'>{fmt_price(p)}</td>{_pct_td(chg)}</tr>"
    st.markdown(f"""<div class="sh">{title}</div>
    <table class="t"><thead><tr>{''.join(f'<th>{c}</th>' for c in cols)}</tr></thead>
    <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)


def render():
    c1, c2 = st.columns([3, 2])
    with c1:
        with st.spinner(""):
            world = get_yf_quotes(WORLD_TICKERS)
        _quotes_table(world, "INDICES GLOBALES", ("ÍNDICE","VALOR","% DIA"))
        with st.spinner(""):
            fx = get_yf_quotes(FX_TICKERS)
        _quotes_table(fx, "DIVISAS", ("PAR","VALOR","% DIA"))
    with c2:
        with st.spinner(""):
            comm = get_yf_quotes(COMMODITY_TICKERS)
        _quotes_table(comm, "COMMODITIES", ("COMMODITY","PRECIO","% DIA"))

    st.markdown('<div class="sh">SECTORES S&P 500</div>', unsafe_allow_html=True)
    with st.spinner(""):
        sec = get_yf_quotes(SECTOR_ETFS)
    names = list(sec.keys())
    vals = [v.get("change_pct",0) or 0 for v in sec.values()]
    fig = go.Figure(go.Bar(x=names, y=vals,
        marker_color=["#00ff41" if v>=0 else "#ff3b3b" for v in vals],
        text=[f"{'+'if v>=0 else''}{v:.2f}%" for v in vals],
        textposition="outside", textfont=dict(size=8, family="Courier New"),
        hovertemplate="<b>%{x}</b><br>%{y:.2f}%<extra></extra>"))
    fig.update_layout(paper_bgcolor="#000", plot_bgcolor="#000",
        font=dict(family="Courier New",size=8,color="#555"),
        margin=dict(l=8,r=8,t=8,b=8), showlegend=False, height=200,
        yaxis=dict(gridcolor="#111",ticksuffix="%",tickfont=dict(size=7)),
        xaxis=dict(tickfont=dict(size=7)))
    st.plotly_chart(fig, use_container_width=True)
