import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_bondterminal_bootstrap, get_riesgo_pais


def _chg(val):
    if val is None: return '<td style="color:#555">—</td>'
    try:
        f = float(val)
        c = "#00ff41" if f > 0 else ("#ff3b3b" if f < 0 else "#555")
        s = "+" if f > 0 else ""
        return f'<td style="color:{c};font-weight:bold">{s}{f:.2f}</td>'
    except: return f'<td style="color:#555">{val}</td>'


def _bonds(bonds):
    if not bonds:
        st.markdown('<p style="color:#333;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        return
    rows = ""
    for b in bonds:
        tk = b.get("ticker") or b.get("localTicker", "")
        nm = b.get("name", b.get("displayName", ""))
        p = b.get("price")
        ch = b.get("change1D")
        y = b.get("yield")
        d = b.get("modDuration")
        gs = b.get("gSpread")
        gc = b.get("gSpreadChange")
        rows += f"""<tr>
            <td>{tk}</td>
            <td style="color:#555;font-size:9px">{nm[:20]}</td>
            <td style="color:#ffcc00">{f'{p:.2f}' if p else '—'}</td>
            {_chg(ch)}
            <td>{f'{y:.1f}%' if y else '—'}</td>
            <td style="color:#555">{f'{d:.2f}' if d else '—'}</td>
            <td style="color:#555">{gs or '—'}</td>
            {_chg(gc)}
        </tr>"""
    st.markdown(f"""<table class="t">
    <thead><tr><th>TICKER</th><th>NOMBRE</th><th>PRECIO</th><th>Δ DIA</th><th>YIELD</th><th>DUR</th><th>G-SPR</th><th>Δ SPR</th></tr></thead>
    <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)


def render():
    rp = get_riesgo_pais()
    boot = get_bondterminal_bootstrap()

    if isinstance(rp, dict) and "error" in rp:
        rp = {"bps":"ERR","delta_1d":0,"delta_1w":0,"delta_1m":0,"bps_ambito":"—","data_quality":""}
    
    bps = rp.get("bps","—")
    d1d = rp.get("delta_1d",0)
    d1w = rp.get("delta_1w",0)
    d1m = rp.get("delta_1m",0)

    def _d(v,l):
        if not v: return ""
        c = "#00ff41" if v>0 else "#ff3b3b"
        s = "+" if v>0 else ""
        return f'<span style="color:{c};font-weight:bold">{s}{v:.0f} {l}</span> '

    st.markdown(f"""
    <div style="border:1px solid #333;padding:6px 12px;margin-bottom:6px;display:flex;align-items:center;gap:20px">
      <div><span style="color:#ffcc00;font-size:24px;font-weight:bold">{bps}</span><span style="color:#555;font-size:10px"> bps EMBI</span></div>
      <div style="font-size:10px">{_d(d1d,"hoy")}{_d(d1w,"7d")}{_d(d1m,"30d")}</div>
      <div style="margin-left:auto;color:#555;font-size:9px">Ámbito: {rp.get("bps_ambito","—")} bps</div>
    </div>""", unsafe_allow_html=True)

    if isinstance(boot, dict) and "error" in boot:
        st.markdown(f'<p style="color:#ff3b3b;font-size:10px">Error: {boot["error"]}</p>', unsafe_allow_html=True)
        return

    subtabs = st.tabs(["SOBERANOS", "CORPORATIVOS", "PROVINCIALES"])
    sov = boot.get("sovereignSnapshot",{})
    corp = boot.get("corporateSnapshot",{})
    prov = boot.get("provincialSnapshot",{})

    with subtabs[0]:
        for sec in sov.get("sections",[]):
            st.markdown(f'<div class="sh">{sec.get("label","")} · LEY {sec.get("law","")}</div>', unsafe_allow_html=True)
            _bonds(sec.get("bonds",[]))
    with subtabs[1]:
        _bonds(corp.get("bonds",[]))
    with subtabs[2]:
        _bonds(prov.get("bonds",[]))
