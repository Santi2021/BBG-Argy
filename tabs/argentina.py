import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import (get_acciones, get_cedears, get_dolar, get_mep, get_ccl, 
                  get_adrs, get_debug_fields, fmt_change, fmt_price, safe_get)


def _change_html(val):
    """Returns styled HTML for a percentage change value."""
    if val is None or val == "—":
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


def _fmt_num(val):
    """Format a numeric value for display."""
    if val is None or val == "—":
        return "—"
    try:
        f = float(str(val).replace(",", "."))
        if f >= 10000:
            return f"{f:,.0f}"
        elif f >= 100:
            return f"{f:,.1f}"
        elif f >= 1:
            return f"{f:,.2f}"
        else:
            return f"{f:,.4f}"
    except (ValueError, TypeError):
        return str(val)


def _render_table(data: list, fields: list, headers: list, max_rows=None):
    """Render a Bloomberg-style dense table."""
    if not data:
        st.markdown('<p style="color:#444;font-size:10px;padding:8px">Sin datos disponibles</p>', 
                    unsafe_allow_html=True)
        return

    display_data = data[:max_rows] if max_rows else data

    rows = ""
    for item in display_data:
        if not isinstance(item, dict):
            continue
        row_cells = ""
        for i, f in enumerate(fields):
            val = item.get(f, "—")
            if val is None:
                val = "—"

            if i == 0:
                # Ticker column
                row_cells += f'<td style="text-align:left;color:#f5a623;font-weight:500">{val}</td>'
            elif "pct" in f.lower() or "change" in f.lower() or "var" in f.lower():
                row_cells += f'<td>{_change_html(val)}</td>'
            else:
                row_cells += f'<td>{_fmt_num(val)}</td>'
        rows += f"<tr>{row_cells}</tr>"

    ths = ""
    for i, h in enumerate(headers):
        align = 'text-align:left' if i == 0 else 'text-align:right'
        ths += f'<th style="{align}">{h}</th>'

    html = f"""
    <div style="overflow-x:auto">
    <table class="bbg-table">
      <thead><tr>{ths}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)


def render():
    subtabs = st.tabs(["TIPOS DE CAMBIO", "ACCIONES", "CEDEARS", "ADRs", "🔧 DEBUG"])

    # ── Tipos de cambio ──────────────────────────────────────────────────────
    with subtabs[0]:
        dol = get_dolar()
        mep_data = get_mep()
        ccl_data = get_ccl()

        # Check for API errors
        if isinstance(dol, dict) and "error" in dol:
            st.markdown(f'<p style="color:#ff3d3d;font-size:10px">dolarapi error: {dol["error"]}</p>', 
                        unsafe_allow_html=True)

        # ── FX Table ──
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
            
            # Spread
            if compra and venta:
                spread = venta - compra
                spread_pct = (spread / venta * 100) if venta else 0
                sp_str = f'<span style="color:#555;font-size:9px">{spread:,.1f} ({spread_pct:.1f}%)</span>'
            else:
                sp_str = ""
            
            fx_rows += f"""
            <tr>
              <td style="text-align:left;color:#f5a623;font-weight:500">{label}</td>
              <td>{c_str}</td>
              <td>{v_str}</td>
              <td>{sp_str}</td>
            </tr>"""

        st.markdown(f"""
        <div class="sec-header">TIPOS DE CAMBIO · DOLARAPI</div>
        <div style="overflow-x:auto">
        <table class="bbg-table">
          <thead><tr>
            <th style="text-align:left">TIPO</th>
            <th>COMPRA</th><th>VENTA</th><th>SPREAD</th>
          </tr></thead>
          <tbody>{fx_rows}</tbody>
        </table>
        </div>""", unsafe_allow_html=True)

        # ── MEP + CCL side by side ──
        col_mep, col_ccl = st.columns(2)

        with col_mep:
            if mep_data:
                st.markdown(f'<div class="sec-header">MEP IMPLÍCITO · {len(mep_data)} BONOS</div>', 
                            unsafe_allow_html=True)
                _render_table(
                    mep_data,
                    ["ticker", "bid", "ask", "mark", "pct_change"],
                    ["TICKER", "BID", "ASK", "MARK", "% DÍA"],
                    max_rows=25,
                )
            else:
                st.markdown('<div class="sec-header">MEP IMPLÍCITO</div>', unsafe_allow_html=True)
                st.markdown('<p style="color:#333;font-size:10px">Sin datos MEP</p>', unsafe_allow_html=True)

        with col_ccl:
            if ccl_data:
                st.markdown(f'<div class="sec-header">CCL IMPLÍCITO · {len(ccl_data)} BONOS</div>', 
                            unsafe_allow_html=True)
                _render_table(
                    ccl_data,
                    ["ticker", "bid", "ask", "mark", "pct_change"],
                    ["TICKER", "BID", "ASK", "MARK", "% DÍA"],
                    max_rows=25,
                )
            else:
                st.markdown('<div class="sec-header">CCL IMPLÍCITO</div>', unsafe_allow_html=True)
                st.markdown('<p style="color:#333;font-size:10px">Sin datos CCL</p>', unsafe_allow_html=True)

    # ── Acciones ─────────────────────────────────────────────────────────────
    with subtabs[1]:
        with st.spinner(""):
            acc = get_acciones()
        
        n = len(acc) if acc else 0
        st.markdown(f'<div class="sec-header">ACCIONES ARG · DATA912 — {n} INSTRUMENTOS</div>', 
                    unsafe_allow_html=True)
        
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["TICKER", "PRECIO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(acc, fields, hdrs)

    # ── CEDEARs ──────────────────────────────────────────────────────────────
    with subtabs[2]:
        with st.spinner(""):
            ced = get_cedears()
        
        n = len(ced) if ced else 0
        st.markdown(f'<div class="sec-header">CEDEARS — {n} INSTRUMENTOS</div>', 
                    unsafe_allow_html=True)
        
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["TICKER", "PRECIO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(ced, fields, hdrs)

    # ── ADRs ─────────────────────────────────────────────────────────────────
    with subtabs[3]:
        with st.spinner(""):
            adrs = get_adrs()
        
        n = len(adrs) if adrs else 0
        st.markdown(f'<div class="sec-header">ADRs ARGENTINOS EN USA — {n} INSTRUMENTOS</div>', 
                    unsafe_allow_html=True)
        
        fields = ["ticker", "last", "bid", "ask", "pct_change", "volume"]
        hdrs   = ["TICKER", "PRECIO", "BID", "ASK", "% DÍA", "VOL"]
        _render_table(adrs, fields, hdrs)

    # ── DEBUG ────────────────────────────────────────────────────────────────
    with subtabs[4]:
        st.markdown('<div class="sec-header">🔧 API FIELD DEBUG</div>', unsafe_allow_html=True)
        st.markdown("""
        <p style="color:#666;font-size:10px;margin-bottom:12px">
        Este panel muestra los campos reales que devuelve cada API.<br>
        Si ves que los campos no coinciden con los esperados (ticker, last, bid, ask, pct_change, volume),
        hay que ajustar el FIELD_ALIASES en data.py.
        </p>""", unsafe_allow_html=True)
        
        debug = get_debug_fields()
        
        if not debug:
            st.markdown('<p style="color:#444;font-size:10px">Cargá algún tab primero para ver los campos.</p>', 
                        unsafe_allow_html=True)
        
        for endpoint, info in debug.items():
            st.markdown(f'<div style="color:#f5a623;font-size:11px;margin-top:12px;font-weight:600">{endpoint}</div>', 
                        unsafe_allow_html=True)
            st.markdown(f'<div style="color:#888;font-size:10px">Keys: {info["keys"]}</div>', 
                        unsafe_allow_html=True)
            st.code(str(info["sample"]), language="python")
        
        # Also show raw sample from each source
        st.markdown('<div class="sec-header" style="margin-top:16px">RAW SAMPLES (FIRST ITEM)</div>', 
                    unsafe_allow_html=True)
        
        if st.button("🔄 Fetch & Show Raw Data", key="debug_fetch"):
            import json
            
            sources = {
                "arg_stocks": get_acciones,
                "arg_cedears": get_cedears,
                "mep": get_mep,
                "ccl": get_ccl,
                "usa_adrs": get_adrs,
            }
            
            for name, fn in sources.items():
                data = fn()
                st.markdown(f'<div style="color:#f5a623;font-size:11px;margin-top:8px">{name} ({len(data)} items)</div>', 
                            unsafe_allow_html=True)
                if data and isinstance(data, list) and len(data) > 0:
                    st.code(json.dumps(data[0], indent=2, ensure_ascii=False, default=str), language="json")
                else:
                    st.markdown(f'<span style="color:#ff3d3d;font-size:10px">Empty or error: {type(data)}</span>', 
                                unsafe_allow_html=True)
