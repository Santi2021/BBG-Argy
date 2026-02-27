import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_acciones, get_cedears, get_dolar, get_mep, get_ccl, get_adrs, fmt_change
import pandas as pd


def _change_html(val):
    if val is None:
        return '<span class="neutral">—</span>'
    try:
        f = float(str(val).replace("%","").replace(",","."))
        css = "up" if f > 0 else ("down" if f < 0 else "neutral")
        sign = "+" if f > 0 else ""
        return f'<span class="{css}">{sign}{f:.2f}%</span>'
    except Exception:
        s = str(val)
        css = "up" if "+" in s else ("down" if "-" in s else "neutral")
        return f'<span class="{css}">{s}</span>'


def _render_table(data: list, fields: list, headers: list):
    if not data:
        st.markdown('<p style="color:#444;font-size:11px;padding:16px">Sin datos</p>', unsafe_allow_html=True)
        return

    rows = ""
    for item in data:
        cells = ""
        for i, f in enumerate(fields):
            val = item.get(f, "—")
            if "pct" in f.lower() or "change" in f.lower() or "var" in f.lower():
                cell = _change_html(val)
            elif i == 0:
                cell = f'<td style="text-align:left;color:#f5a623;font-weight:500">{val}</td>'
                rows += f"<tr>{cell}"
                continue
            else:
                cell = f"<td>{val if val is not None else '—'}</td>"
            cells += cell
        rows += cells + "</tr>"

    ths = "".join(f"<th>{ h }</th>" for h in headers[1:])
    html = f"""
    <div style="overflow-x:auto">
    <table class="bbg-table">
      <thead><tr><th style="text-align:left">{headers[0]}</th>{ths}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)


def render():
    subtabs = st.tabs(["TIPOS DE CAMBIO", "ACCIONES", "CEDEARS", "ADRs"])

    # ── Tipos de cambio ──────────────────────────────────────────────────────
    with subtabs[0]:
        dol = get_dolar()
        mep_data = get_mep()
        ccl_data = get_ccl()

        # Main FX grid
        fx_items = [
            ("oficial",          "Oficial"),
            ("blue",             "Blue"),
            ("bolsa",            "MEP (AL30)"),
            ("contadoconliqui",  "CCL"),
            ("tarjeta",          "Tarjeta"),
            ("mayorista",        "Mayorista"),
            ("cripto",           "Cripto"),
        ]

        cards_html = '<div class="ticker-grid" style="grid-template-columns:repeat(auto-fill,minmax(180px,1fr))">'
        for key, label in fx_items:
            d = dol.get(key, {})
            compra = d.get("compra")
            venta  = d.get("venta")
            c_str  = f"{compra:,.2f}" if compra else "—"
            v_str  = f"{venta:,.2f}"  if venta  else "—"

            if compra and venta:
                spread = venta - compra
                spread_str = f"spread {spread:,.2f}"
            else:
                spread_str = ""

            cards_html += f"""
            <div class="ticker-card">
              <div class="t-symbol">{label}</div>
              <div class="t-price">{v_str}</div>
              <div class="t-name" style="color:#555;font-size:9px">
                compra {c_str} &nbsp;·&nbsp; {spread_str}
              </div>
            </div>"""
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        # MEP por bono
        if mep_data:
            st.markdown('<div class="sec-header">MEP IMPLÍCITO POR BONO</div>', unsafe_allow_html=True)
            cols_mep = ["ticker", "bid", "ask", "mark", "pct_change"]
            hdrs_mep = ["BONO", "BID", "ASK", "MARK", "% DÍA"]
            _render_table(mep_data[:15], cols_mep, hdrs_mep)

        # CCL por bono
        if ccl_data:
            st.markdown('<div class="sec-header">CCL IMPLÍCITO POR BONO</div>', unsafe_allow_html=True)
            _render_table(ccl_data[:15], cols_mep, hdrs_mep)

    # ── Acciones ─────────────────────────────────────────────────────────────
    with subtabs[1]:
        with st.spinner(""):
            acc = get_acciones()
        st.markdown(f'<div class="sec-header">PANEL MERVAL — {len(acc)} instrumentos</div>', unsafe_allow_html=True)
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["ESPECIE", "ÚLTIMO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(acc, fields, hdrs)

    # ── CEDEARs ──────────────────────────────────────────────────────────────
    with subtabs[2]:
        with st.spinner(""):
            ced = get_cedears()
        st.markdown(f'<div class="sec-header">CEDEARS — {len(ced)} instrumentos</div>', unsafe_allow_html=True)
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["ESPECIE", "ÚLTIMO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(ced, fields, hdrs)

    # ── ADRs ─────────────────────────────────────────────────────────────────
    with subtabs[3]:
        with st.spinner(""):
            adrs = get_adrs()
        st.markdown(f'<div class="sec-header">ADRs ARGENTINOS EN USA — {len(adrs)} instrumentos</div>', unsafe_allow_html=True)
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["ESPECIE", "ÚLTIMO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(adrs, fields, hdrs)
