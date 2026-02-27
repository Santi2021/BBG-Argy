import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import (get_yf_quotes, get_dolar, get_riesgo_pais,
                  fmt_price, fmt_change,
                  WORLD_TICKERS, COMMODITY_TICKERS, FX_TICKERS)


def _ticker_cards(quotes: dict, cols_per_row=6):
    items = list(quotes.items())
    for i in range(0, len(items), cols_per_row):
        chunk = items[i:i+cols_per_row]
        cols  = st.columns(len(chunk))
        for col, (name, q) in zip(cols, chunk):
            price  = q.get("price")
            chg    = q.get("change_pct", 0)
            chg_str, css = fmt_change(chg)
            with col:
                st.markdown(f"""
                <div class="ticker-card">
                  <div class="t-symbol">{name}</div>
                  <div class="t-price">{fmt_price(price)}</div>
                  <div class="t-change {css}">{chg_str}</div>
                </div>""", unsafe_allow_html=True)


def render():
    # ── Riesgo País KPI ──
    rp = get_riesgo_pais()
    dol = get_dolar()

    bps     = rp.get("bps", "—")
    d1d     = rp.get("delta_1d", 0)
    d1d_str = f"+{d1d}" if d1d and d1d >= 0 else str(d1d)
    d1d_css = "up" if d1d and d1d > 0 else "down"

    oficial = dol.get("oficial", {})
    mep     = dol.get("bolsa", {})
    blue    = dol.get("blue", {})
    ccl     = dol.get("contadoconliqui", {})

    def dv(d, k="venta"):
        v = d.get(k)
        return f"{v:,.2f}" if v else "—"

    st.markdown(f"""
    <div class="kpi-strip">
      <div class="kpi-item">
        <div class="kpi-label">RIESGO PAÍS</div>
        <div class="kpi-value">{bps}<span style="font-size:11px;color:#555"> bps</span></div>
        <div class="kpi-sub {d1d_css}">{d1d_str} hoy</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">USD OFICIAL</div>
        <div class="kpi-value">{dv(oficial)}</div>
        <div class="kpi-sub flat">ARS</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">USD MEP</div>
        <div class="kpi-value">{dv(mep)}</div>
        <div class="kpi-sub flat">ARS</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">USD CCL</div>
        <div class="kpi-value">{dv(ccl)}</div>
        <div class="kpi-sub flat">ARS</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">USD BLUE</div>
        <div class="kpi-value">{dv(blue)}</div>
        <div class="kpi-sub flat">ARS</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Indices globales ──
    st.markdown('<div class="sec-header">ÍNDICES GLOBALES</div>', unsafe_allow_html=True)
    with st.spinner(""):
        world = get_yf_quotes(WORLD_TICKERS)
    _ticker_cards(world, cols_per_row=6)

    # ── Commodities ──
    st.markdown('<div class="sec-header">COMMODITIES</div>', unsafe_allow_html=True)
    with st.spinner(""):
        comm = get_yf_quotes(COMMODITY_TICKERS)
    _ticker_cards(comm, cols_per_row=6)

    # ── FX ──
    st.markdown('<div class="sec-header">DIVISAS</div>', unsafe_allow_html=True)
    with st.spinner(""):
        fx = get_yf_quotes(FX_TICKERS)
    _ticker_cards(fx, cols_per_row=7)
