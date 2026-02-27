import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_acciones, get_cedears, get_dolar, get_mep, get_ccl, get_adrs, fmt_change
import pandas as pd


def _change_html(val):
    """Returns just the inner HTML for a change value (no <td> wrapper)."""
    if val is None:
        return '<span style="color:#555">—</span>'
    try:
        s = str(val).replace("%", "").replace(",", ".").strip()
        f = float(s)
        if f > 0:
            return f'<span style="color:#00c853">+{f:.2f}%</span>'
        elif f < 0:
            return f'<span style="color:#ff3d3d">{f:.2f}%</span>'
        else:
            return f'<span style="color:#555">0.00%</span>'
    except Exception:
        s = str(val)
        if "+" in s:
            return f'<span style="color:#00c853">{s}</span>'
        elif "-" in s:
            return f'<span style="color:#ff3d3d">{s}</span>'
        return f'<span style="color:#555">{s}</span>'


def _render_table(data: list, fields: list, headers: list):
    if not data:
        st.markdown('<p style="color:#444;font-size:11px;padding:16px">Sin datos</p>', unsafe_allow_html=True)
        return

    rows = ""
    for item in data:
        row_cells = ""
        for i, f in enumerate(fields):
            val = item.get(f, "—")
            if val is None:
                val = "—"

            if i == 0:
                # First column: ticker/symbol style
                row_cells += f'<td style="text-align:left;color:#f5a623;font-weight:500">{val}</td>'
            elif "pct" in f.lower() or "change" in f.lower() or "var" in f.lower():
                row_cells += f'<td>{_change_html(val)}</td>'
            else:
                row_cells += f'<td>{val}</td>'
        rows += f"<tr>{row_cells}</tr>"

    ths = ""
    for i, h in enumerate(headers):
        if i == 0:
            ths += f'<th style="text-align:left">{h}</th>'
        else:
            ths += f'<th>{h}</th>'

    html = f"""
    <div style="overflow-x:auto">
    <table class="bbg-table">
      <thead><tr>{ths}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)


def _render_table_compact(data: list, fields: list, headers: list, max_rows=None):
    """Compact table for side-by-side BBG layout."""
    if not data:
        st.markdown('<p style="color:#444;font-size:10px;padding:8px">Sin datos</p>', unsafe_allow_html=True)
        return

    display_data = data[:max_rows] if max_rows else data

    rows = ""
    for item in display_data:
        row_cells = ""
        for i, f in enumerate(fields):
            val = item.get(f, "—")
            if val is None:
                val = "—"

            if i == 0:
                row_cells += f'<td style="text-align:left;color:#f5a623;font-weight:500;font-size:10px">{val}</td>'
            elif "pct" in f.lower() or "change" in f.lower() or "var" in f.lower():
                row_cells += f'<td style="font-size:10px">{_change_html(val)}</td>'
            else:
                row_cells += f'<td style="font-size:10px">{val}</td>'
        rows += f"<tr>{row_cells}</tr>"

    ths = ""
    for i, h in enumerate(headers):
        if i == 0:
            ths += f'<th style="text-align:left">{h}</th>'
        else:
            ths += f'<th>{h}</th>'

    html = f"""
    <div style="overflow-x:auto">
    <table class="bbg-table">
      <thead><tr>{ths}</tr></thead>
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

        # ── FX Table (compact, like BBG reference) ──
        fx_items = [
            ("oficial",          "OFICIAL"),
            ("blue",             "BLUE"),
            ("bolsa",            "MEP / BOLSA"),
            ("contadoconliqui",  "CCL"),
            ("mayorista",        "MAYORISTA"),
            ("cripto",           "CRIPTO"),
            ("tarjeta",          "TARJETA"),
        ]

        fx_rows = ""
        for key, label in fx_items:
            d = dol.get(key, {})
            compra = d.get("compra")
            venta  = d.get("venta")
            c_str  = f"{compra:,.2f}" if compra else "—"
            v_str  = f"{venta:,.2f}"  if venta  else "—"
            fx_rows += f"""
            <tr>
              <td style="text-align:left;color:#f5a623;font-weight:500">{label}</td>
              <td>{c_str}</td>
              <td>{v_str}</td>
            </tr>"""

        st.markdown(f"""
        <div class="sec-header">TIPOS DE CAMBIO</div>
        <div style="overflow-x:auto">
        <table class="bbg-table">
          <thead><tr>
            <th style="text-align:left">TIPO</th>
            <th>COMPRA</th><th>VENTA</th>
          </tr></thead>
          <tbody>{fx_rows}</tbody>
        </table>
        </div>""", unsafe_allow_html=True)

        # ── MEP + CCL side by side ──
        col_mep, col_ccl = st.columns(2)

        with col_mep:
            if mep_data:
                st.markdown('<div class="sec-header">MEP IMPLÍCITO (data912)</div>', unsafe_allow_html=True)
                _render_table_compact(
                    mep_data[:20],
                    ["ticker", "bid", "ask", "mark", "pct_change"],
                    ["TICKER", "BID MEP", "ASK MEP", "MARK", "% DÍA"],
                )

        with col_ccl:
            if ccl_data:
                st.markdown('<div class="sec-header">CCL IMPLÍCITO (data912)</div>', unsafe_allow_html=True)
                _render_table_compact(
                    ccl_data[:20],
                    ["ticker", "bid", "ask", "mark", "pct_change"],
                    ["TICKER", "BID CCL", "ASK CCL", "MARK", "% DÍA"],
                )

    # ── Acciones ─────────────────────────────────────────────────────────────
    with subtabs[1]:
        with st.spinner(""):
            acc = get_acciones()
        st.markdown(f'<div class="sec-header">ACCIONES ARG (data912) — {len(acc)} instrumentos</div>', unsafe_allow_html=True)
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["TICKER", "PRECIO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(acc, fields, hdrs)

    # ── CEDEARs ──────────────────────────────────────────────────────────────
    with subtabs[2]:
        with st.spinner(""):
            ced = get_cedears()

        # Show top CEDEARs first, then full list
        st.markdown(f'<div class="sec-header">CEDEARS — {len(ced)} instrumentos</div>', unsafe_allow_html=True)
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["TICKER", "PRECIO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(ced, fields, hdrs)

    # ── ADRs ─────────────────────────────────────────────────────────────────
    with subtabs[3]:
        with st.spinner(""):
            adrs = get_adrs()
        st.markdown(f'<div class="sec-header">ADRs ARGENTINOS EN USA — {len(adrs)} instrumentos</div>', unsafe_allow_html=True)
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["TICKER", "PRECIO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(adrs, fields, hdrs)
