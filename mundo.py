import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import (get_yf_quotes, fmt_price, fmt_change,
                  WORLD_TICKERS, COMMODITY_TICKERS, SECTOR_ETFS, FX_TICKERS)


PLOT_BASE = dict(
    paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a",
    font=dict(family="IBM Plex Mono", size=9, color="#555"),
    margin=dict(l=10, r=10, t=30, b=10),
    hoverlabel=dict(bgcolor="#111", bordercolor="#333",
                    font=dict(family="IBM Plex Mono", size=10, color="#e8e0d0")),
)


def _bar_chart(data: dict, title: str, color_by_sign=True):
    names  = list(data.keys())
    values = [v.get("change_pct", 0) or 0 for v in data.values()]
    colors = []
    for v in values:
        if color_by_sign:
            colors.append("#00c853" if v >= 0 else "#ff3d3d")
        else:
            colors.append("#f5a623")

    fig = go.Figure(go.Bar(
        x=names, y=values,
        marker_color=colors,
        text=[f"{'+' if v>=0 else ''}{v:.2f}%" for v in values],
        textposition="outside",
        textfont=dict(size=9, family="IBM Plex Mono"),
        hovertemplate="<b>%{x}</b><br>%{y:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        **PLOT_BASE,
        title=dict(text=title, font=dict(size=9, color="#444"), x=0.01),
        yaxis=dict(gridcolor="#141414", linecolor="#1e1e1e", zerolinecolor="#222",
                   ticksuffix="%", tickfont=dict(size=8)),
        xaxis=dict(linecolor="#1e1e1e", tickfont=dict(size=8)),
        showlegend=False,
        height=260,
    )
    return fig


def render():
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="sec-header">ÍNDICES GLOBALES</div>', unsafe_allow_html=True)
        with st.spinner(""):
            world = get_yf_quotes(WORLD_TICKERS)

        rows = ""
        for name, q in world.items():
            price = q.get("price")
            chg   = q.get("change_pct", 0)
            chg_str, css = fmt_change(chg)
            rows += f"""
            <tr>
              <td style="text-align:left;color:#f5a623;font-weight:500">{name}</td>
              <td>{fmt_price(price)}</td>
              <td class="{css}">{chg_str}</td>
            </tr>"""

        st.markdown(f"""
        <table class="bbg-table">
          <thead><tr>
            <th style="text-align:left">ÍNDICE</th>
            <th>VALOR</th><th>% DÍA</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>""", unsafe_allow_html=True)

        st.markdown('<div class="sec-header" style="margin-top:16px">DIVISAS</div>', unsafe_allow_html=True)
        with st.spinner(""):
            fx = get_yf_quotes(FX_TICKERS)

        rows_fx = ""
        for name, q in fx.items():
            price = q.get("price")
            chg   = q.get("change_pct", 0)
            chg_str, css = fmt_change(chg)
            rows_fx += f"""
            <tr>
              <td style="text-align:left;color:#f5a623;font-weight:500">{name}</td>
              <td>{fmt_price(price, 4)}</td>
              <td class="{css}">{chg_str}</td>
            </tr>"""

        st.markdown(f"""
        <table class="bbg-table">
          <thead><tr>
            <th style="text-align:left">PAR</th>
            <th>VALOR</th><th>% DÍA</th>
          </tr></thead>
          <tbody>{rows_fx}</tbody>
        </table>""", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="sec-header">COMMODITIES</div>', unsafe_allow_html=True)
        with st.spinner(""):
            comm = get_yf_quotes(COMMODITY_TICKERS)

        rows_c = ""
        for name, q in comm.items():
            price = q.get("price")
            chg   = q.get("change_pct", 0)
            chg_str, css = fmt_change(chg)
            rows_c += f"""
            <tr>
              <td style="text-align:left;color:#f5a623;font-weight:500">{name}</td>
              <td>{fmt_price(price, 2)}</td>
              <td class="{css}">{chg_str}</td>
            </tr>"""

        st.markdown(f"""
        <table class="bbg-table">
          <thead><tr>
            <th style="text-align:left">COMMODITY</th>
            <th>PRECIO</th><th>% DÍA</th>
          </tr></thead>
          <tbody>{rows_c}</tbody>
        </table>""", unsafe_allow_html=True)

    # ── Sectores US (barchart) ──
    st.markdown('<div class="sec-header">SECTORES S&P 500 · % DÍA</div>', unsafe_allow_html=True)
    with st.spinner(""):
        sectors = get_yf_quotes(SECTOR_ETFS)
    fig_sec = _bar_chart(sectors, "")
    st.plotly_chart(fig_sec, use_container_width=True)

    # ── Commodities barchart ──
    st.markdown('<div class="sec-header">COMMODITIES · % DÍA</div>', unsafe_allow_html=True)
    fig_comm = _bar_chart(comm, "")
    st.plotly_chart(fig_comm, use_container_width=True)
