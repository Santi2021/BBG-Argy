import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import (get_acciones, get_cedears, get_dolar, get_mep, get_ccl, 
                  get_adrs, get_debug_fields, fmt_change, fmt_price, safe_get)


def _chg_html(val):
    if val is None or val == "—":
        return '<span style="color:#555">—</span>'
    try:
        s = str(val).replace("%", "").replace(",", ".").strip()
        f = float(s)
        if f > 0:
            return f'<span style="color:#00ff41;font-weight:bold">+{f:.2f}%</span>'
        elif f < 0:
            return f'<span style="color:#ff3b3b;font-weight:bold">{f:.2f}%</span>'
        else:
            return f'<span style="color:#555">0.00%</span>'
    except:
        return f'<span style="color:#555">{val}</span>'


def _fmt_num(val):
    if val is None or val == "—": return "—"
    try:
        f = float(str(val).replace(",", "."))
        if f >= 10000: return f"{f:,.0f}"
        elif f >= 100: return f"{f:,.1f}"
        elif f >= 1: return f"{f:,.2f}"
        else: return f"{f:,.4f}"
    except: return str(val)


def _render_table(data, fields, headers, max_rows=None):
    if not data:
        st.markdown('<p style="color:#333;font-size:10px;padding:4px">Sin datos</p>', unsafe_allow_html=True)
        return
    display_data = data[:max_rows] if max_rows else data
    rows = ""
    for item in display_data:
        if not isinstance(item, dict): continue
        cells = ""
        for i, f in enumerate(fields):
            val = item.get(f, "—")
            if val is None: val = "—"
            if i == 0:
                cells += f'<td>{val}</td>'
            elif "pct" in f.lower() or "change" in f.lower():
                cells += f'<td>{_chg_html(val)}</td>'
            else:
                cells += f'<td style="color:#ffcc00">{_fmt_num(val)}</td>'
        rows += f"<tr>{cells}</tr>"
    
    ths = "".join(f'<th>{h}</th>' for h in headers)
    st.markdown(f"""<table class="t">
    <thead><tr>{ths}</tr></thead>
    <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)


def render():
    subtabs = st.tabs(["TIPOS DE CAMBIO", "ACCIONES", "CEDEARS", "ADRs", "🔧 DEBUG"])

    with subtabs[0]:
        dol = get_dolar()
        mep_data = get_mep()
        ccl_data = get_ccl()

        fx_items = [
            ("oficial", "OFICIAL"), ("blue", "BLUE"), ("bolsa", "MEP / BOLSA"),
            ("contadoconliqui", "CCL"), ("mayorista", "MAYORISTA"),
            ("cripto", "CRIPTO"), ("tarjeta", "TARJETA"),
        ]
        
        fx_rows = ""
        for key, label in fx_items:
            d = dol.get(key, {})
            c = d.get("compra")
            v = d.get("venta")
            c_s = f"{c:,.2f}" if c else "—"
            v_s = f"{v:,.2f}" if v else "—"
            sp = ""
            if c and v:
                spread = v - c
                sp_pct = spread / v * 100
                sp = f'{spread:,.1f} ({sp_pct:.1f}%)'
            fx_rows += f"""<tr>
                <td>{label}</td>
                <td style="color:#ffcc00">{c_s}</td>
                <td style="color:#ffcc00">{v_s}</td>
                <td style="color:#555">{sp}</td>
            </tr>"""

        st.markdown(f"""
        <div class="sh">TIPOS DE CAMBIO · DOLARAPI</div>
        <table class="t">
          <thead><tr><th>TIPO</th><th>COMPRA</th><th>VENTA</th><th>SPREAD</th></tr></thead>
          <tbody>{fx_rows}</tbody>
        </table>""", unsafe_allow_html=True)

        col_m, col_c = st.columns(2)
        with col_m:
            if mep_data:
                st.markdown(f'<div class="sh">MEP IMPLÍCITO · {len(mep_data)} BONOS</div>', unsafe_allow_html=True)
                _render_table(mep_data, ["ticker","bid","ask","mark","pct_change"], 
                             ["TICKER","BID","ASK","MARK","% DIA"], max_rows=25)
        with col_c:
            if ccl_data:
                st.markdown(f'<div class="sh">CCL IMPLÍCITO · {len(ccl_data)} BONOS</div>', unsafe_allow_html=True)
                _render_table(ccl_data, ["ticker","bid","ask","mark","pct_change"],
                             ["TICKER","BID","ASK","MARK","% DIA"], max_rows=25)

    with subtabs[1]:
        with st.spinner(""):
            acc = get_acciones()
        st.markdown(f'<div class="sh">ACCIONES ARG · DATA912 — {len(acc) if acc else 0} INSTRUMENTOS</div>', unsafe_allow_html=True)
        _render_table(acc, ["ticker","last","bid","ask","pct_change","volume"],
                     ["TICKER","PRECIO","BID","ASK","% DIA","VOL"])

    with subtabs[2]:
        with st.spinner(""):
            ced = get_cedears()
        st.markdown(f'<div class="sh">CEDEARS — {len(ced) if ced else 0} INSTRUMENTOS</div>', unsafe_allow_html=True)
        _render_table(ced, ["ticker","last","bid","ask","pct_change","volume"],
                     ["TICKER","PRECIO","BID","ASK","% DIA","VOL"])

    with subtabs[3]:
        with st.spinner(""):
            adrs = get_adrs()
        st.markdown(f'<div class="sh">ADRs ARGENTINOS — {len(adrs) if adrs else 0} INSTRUMENTOS</div>', unsafe_allow_html=True)
        _render_table(adrs, ["ticker","last","bid","ask","pct_change","volume"],
                     ["TICKER","PRECIO","BID","ASK","% DIA","VOL"])

    with subtabs[4]:
        st.markdown('<div class="sh">🔧 API FIELD DEBUG</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#555;font-size:10px">Muestra los campos reales de cada API para diagnosticar mapeo.</p>', unsafe_allow_html=True)
        
        debug = get_debug_fields()
        if not debug:
            st.markdown('<p style="color:#333;font-size:10px">Cargá otro tab primero.</p>', unsafe_allow_html=True)
        for ep, info in debug.items():
            st.markdown(f'<div style="color:#ff6600;font-size:11px;font-weight:bold;margin-top:8px">{ep}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:#666;font-size:9px">Keys: {info["keys"]}</div>', unsafe_allow_html=True)
            st.code(str(info["sample"]), language="python")
        
        if st.button("🔄 FETCH RAW DATA"):
            import json
            for name, fn in {"arg_stocks": get_acciones, "arg_cedears": get_cedears, "mep": get_mep, "ccl": get_ccl, "usa_adrs": get_adrs}.items():
                data = fn()
                st.markdown(f'<div style="color:#ff6600;font-size:10px;font-weight:bold;margin-top:6px">{name} ({len(data)} items)</div>', unsafe_allow_html=True)
                if data and isinstance(data, list) and len(data) > 0:
                    st.code(json.dumps(data[0], indent=2, ensure_ascii=False, default=str), language="json")
                else:
                    st.markdown(f'<span style="color:#ff3b3b;font-size:9px">Empty: {type(data)}</span>', unsafe_allow_html=True)
