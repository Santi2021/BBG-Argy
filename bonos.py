import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_bondterminal_bootstrap, get_riesgo_pais, get_live_prices_bt


def _chg_html(val):
    if val is None:
        return '<span style="color:#444">—</span>'
    try:
        f = float(val)
        css = "#00c853" if f > 0 else ("#ff3d3d" if f < 0 else "#444")
        sign = "+" if f > 0 else ""
        return f'<span style="color:{css}">{sign}{f:.2f}</span>'
    except Exception:
        return f'<span style="color:#555">{val}</span>'


def _render_bonds(bonds: list):
    if not bonds:
        st.markdown('<p style="color:#444;font-size:11px;padding:8px">Sin datos</p>', unsafe_allow_html=True)
        return

    rows = ""
    for b in bonds:
        ticker   = b.get("ticker") or b.get("localTicker", "")
        name     = b.get("name", b.get("displayName", ""))
        price    = b.get("price")
        chg1d    = b.get("change1D")
        yld      = b.get("yield")
        dur      = b.get("modDuration")
        gspread  = b.get("gSpread")
        gspd_chg = b.get("gSpreadChange")

        p_str = f"{price:.2f}" if price else "—"
        y_str = f"{yld:.1f}%" if yld else "—"
        d_str = f"{dur:.2f}" if dur else "—"
        g_str = f"{gspread}" if gspread else "—"

        rows += f"""
        <tr>
          <td style="text-align:left;color:#f5a623;font-weight:500">{ticker}</td>
          <td style="color:#888;font-size:10px">{name}</td>
          <td>{p_str}</td>
          <td>{_chg_html(chg1d)}</td>
          <td style="color:#aaa">{y_str}</td>
          <td style="color:#aaa">{d_str}</td>
          <td style="color:#666">{g_str}</td>
          <td>{_chg_html(gspd_chg)}</td>
        </tr>"""

    html = f"""
    <div style="overflow-x:auto">
    <table class="bbg-table">
      <thead><tr>
        <th style="text-align:left">TICKER</th>
        <th style="text-align:left">NOMBRE</th>
        <th>PRECIO</th><th>Δ DÍA</th>
        <th>YIELD</th><th>DUR.</th>
        <th>G-SPREAD</th><th>Δ G-SPR</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)


def render():
    rp   = get_riesgo_pais()
    boot = get_bondterminal_bootstrap()

    # ── Riesgo País Banner ──
    bps     = rp.get("bps", "—")
    d1d     = rp.get("delta_1d", 0)
    d1w     = rp.get("delta_1w", 0)
    d1m     = rp.get("delta_1m", 0)
    ambito  = rp.get("bps_ambito", "—")
    quality = rp.get("data_quality", "")

    def delta_html(v, label):
        if v is None:
            return ""
        css = "#00c853" if v > 0 else ("#ff3d3d" if v < 0 else "#555")
        sign = "+" if v > 0 else ""
        return f'<span style="color:{css};font-size:10px">{sign}{v:.0f} {label}</span>'

    st.markdown(f"""
    <div style="background:#0d0d0d;border:1px solid #1e1e1e;padding:14px 20px;margin-bottom:12px;
                display:flex;align-items:center;gap:32px">
      <div>
        <div style="font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#444;margin-bottom:2px">
          RIESGO PAÍS · EMBI ARG
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:32px;font-weight:600;
                    color:#f5a623;line-height:1">
          {bps}<span style="font-size:14px;color:#555;margin-left:4px">bps</span>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px">
        {delta_html(d1d, "hoy")}
        {delta_html(d1w, "7d")}
        {delta_html(d1m, "30d")}
      </div>
      <div style="margin-left:auto;text-align:right">
        <div style="font-size:9px;color:#333;text-transform:uppercase;letter-spacing:.1em">Ámbito</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:16px;color:#666">{ambito} bps</div>
        <div style="font-size:9px;color:#2a2a2a;margin-top:2px">{quality}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    subtabs = st.tabs(["SOBERANOS NY/AR", "CORPORATIVOS", "PROVINCIALES"])

    sov  = boot.get("sovereignSnapshot", {})
    corp = boot.get("corporateSnapshot", {})
    prov = boot.get("provincialSnapshot", {})

    with subtabs[0]:
        sections = sov.get("sections", [])
        for section in sections:
            label = section.get("label", "")
            law   = section.get("law", "")
            bonds = section.get("bonds", [])
            weighted = section.get("weighted", {})

            st.markdown(f'<div class="sec-header">{label} · LEY {law}</div>', unsafe_allow_html=True)
            _render_bonds(bonds)

            # Weighted summary
            if weighted:
                wp  = weighted.get("price", 0)
                wy  = weighted.get("yield", 0)
                wc  = weighted.get("change1D", 0)
                css = "#00c853" if wc and wc > 0 else "#ff3d3d"
                sign = "+" if wc and wc > 0 else ""
                st.markdown(f"""
                <div style="text-align:right;font-size:9px;color:#333;
                            letter-spacing:.08em;margin-top:4px;margin-bottom:8px">
                  PONDERADO &nbsp;·&nbsp; precio {wp:.2f} &nbsp;·&nbsp;
                  yield {wy:.1f}% &nbsp;·&nbsp;
                  <span style="color:{css}">{sign}{wc:.2f} hoy</span>
                </div>""", unsafe_allow_html=True)

    with subtabs[1]:
        _render_bonds(corp.get("bonds", []))

    with subtabs[2]:
        _render_bonds(prov.get("bonds", []))
