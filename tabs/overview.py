"""
OVERVIEW — Bloomberg Launchpad style
Everything on one screen: FX, Riesgo País, Indices, Commodities, 
Top Acciones, Bonos, Futuros, Crypto
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import (
    get_yf_quotes, get_dolar, get_riesgo_pais, get_acciones, get_cedears,
    get_bondterminal_bootstrap, get_futuros_dolar, get_adrs,
    fmt_price, fmt_change,
    WORLD_TICKERS, COMMODITY_TICKERS, FX_TICKERS,
)


def _arrow(chg):
    """Return ▲/▼ arrow based on sign."""
    if chg is None: return ""
    try:
        v = float(str(chg).replace("%","").replace(",","."))
        return "▲" if v >= 0 else "▼"
    except: return ""


def _clr(val):
    """Return color string for a numeric value."""
    if val is None: return "#555"
    try:
        v = float(str(val).replace("%","").replace(",","."))
        return "#00ff41" if v >= 0 else "#ff3b3b"
    except: return "#555"


def _chg_td(val):
    """Format a change value as colored <td>."""
    if val is None:
        return '<td style="color:#555">—</td>'
    try:
        v = float(str(val).replace("%","").replace(",","."))
        c = "#00ff41" if v >= 0 else "#ff3b3b"
        s = "+" if v >= 0 else ""
        arrow = "▲" if v >= 0 else "▼"
        return f'<td style="color:{c};font-weight:bold">{arrow} {s}{v:.2f}</td>'
    except:
        return f'<td style="color:#555">{val}</td>'


def _chg_pct_td(val):
    """Format a %change as colored <td>."""
    if val is None:
        return '<td style="color:#555">—</td>'
    try:
        v = float(str(val).replace("%","").replace(",","."))
        c = "#00ff41" if v >= 0 else "#ff3b3b"
        s = "+" if v >= 0 else ""
        return f'<td style="color:{c};font-weight:bold">{s}{v:.2f}%</td>'
    except:
        return f'<td style="color:#555">{val}</td>'


def _panel(title, content):
    """Wrap content in a Bloomberg panel box."""
    return f"""<div class="panel">
    <div class="panel-title">{title}</div>
    <div style="padding:2px 0">{content}</div>
    </div>"""


def render():
    # ══════════════════════════════════════════════════════════════════════
    # FETCH ALL DATA
    # ══════════════════════════════════════════════════════════════════════
    rp = get_riesgo_pais()
    dol = get_dolar()
    
    if isinstance(rp, dict) and "error" in rp:
        rp = {"bps": "ERR", "delta_1d": 0, "delta_1w": 0, "delta_1m": 0}
    if isinstance(dol, dict) and "error" in dol:
        dol = {}

    # ══════════════════════════════════════════════════════════════════════
    # ROW 1: KPI STRIP — Riesgo País + FX rates
    # ══════════════════════════════════════════════════════════════════════
    bps = rp.get("bps", "—")
    d1d = rp.get("delta_1d", 0)
    d1d_c = "#00ff41" if d1d and d1d > 0 else ("#ff3b3b" if d1d and d1d < 0 else "#555")
    d1d_s = f"+{d1d}" if d1d and d1d >= 0 else str(d1d or 0)

    def _fxv(key):
        d = dol.get(key, {})
        v = d.get("venta")
        return f"{v:,.2f}" if v else "—"
    
    def _fxc(key):
        d = dol.get(key, {})
        v = d.get("compra")
        return f"{v:,.2f}" if v else "—"

    # Brecha blue vs oficial
    of_v = dol.get("oficial", {}).get("venta")
    bl_v = dol.get("blue", {}).get("venta")
    brecha = ""
    if of_v and bl_v:
        b_pct = (bl_v - of_v) / of_v * 100
        brecha = f'<span style="color:#ff6600;font-size:8px">brecha {b_pct:.1f}%</span>'

    st.markdown(f"""
    <div class="kpi-strip">
      <div class="kpi-item">
        <div class="kpi-label">RIESGO PAÍS</div>
        <div class="kpi-value">{bps} <span style="font-size:9px;color:#555">bps</span></div>
        <div class="kpi-sub" style="color:{d1d_c}">{d1d_s} hoy</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">OFICIAL</div>
        <div class="kpi-value">{_fxv("oficial")}</div>
        <div class="kpi-sub flat">C {_fxc("oficial")}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">BLUE</div>
        <div class="kpi-value">{_fxv("blue")}</div>
        <div class="kpi-sub">{brecha}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">MEP</div>
        <div class="kpi-value">{_fxv("bolsa")}</div>
        <div class="kpi-sub flat">C {_fxc("bolsa")}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">CCL</div>
        <div class="kpi-value">{_fxv("contadoconliqui")}</div>
        <div class="kpi-sub flat">C {_fxc("contadoconliqui")}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">MAYORISTA</div>
        <div class="kpi-value">{_fxv("mayorista")}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">TARJETA</div>
        <div class="kpi-value">{_fxv("tarjeta")}</div>
      </div>
      <div class="kpi-item">
        <div class="kpi-label">CRIPTO</div>
        <div class="kpi-value">{_fxv("cripto")}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 2: 3-column grid — Indices | Acciones TOP | Commodities+Crypto
    # ══════════════════════════════════════════════════════════════════════
    c1, c2, c3 = st.columns([1, 1, 1])

    # ── COL 1: Indices Globales ──
    with c1:
        with st.spinner(""):
            world = get_yf_quotes(WORLD_TICKERS)
        
        rows = ""
        for name, q in world.items():
            p = q.get("price")
            chg = q.get("change_pct", 0)
            p_str = fmt_price(p)
            rows += f"""<tr>
                <td>{name}</td>
                <td class="mkt">{'USA' if 'S&P' in name or 'DOW' in name or 'NASDAQ' in name or 'VIX' in name else 'INT'}</td>
                <td style="color:#ffcc00">{p_str}</td>
                {_chg_td(chg)}
                {_chg_pct_td(chg)}
            </tr>"""
        
        html = f"""<table class="t">
        <thead><tr><th>NOMBRE</th><th>MKT</th><th>PRECIO</th><th>CAMBIO</th><th>% DIA</th></tr></thead>
        <tbody>{rows}</tbody></table>"""
        st.markdown(_panel("INDICES GLOBALES", html), unsafe_allow_html=True)

    # ── COL 2: Top Acciones ARG + ADRs ──
    with c2:
        with st.spinner(""):
            acc = get_acciones()
        
        # Top 10 by absolute change
        top_acc = []
        if acc:
            for item in acc[:15]:
                t = item.get("ticker", "—")
                p = item.get("last")
                chg = item.get("pct_change")
                if t != "—":
                    top_acc.append((t, p, chg))
        
        rows = ""
        for t, p, chg in top_acc[:12]:
            p_str = fmt_price(p) if p else "—"
            rows += f"""<tr>
                <td>{t}</td>
                <td class="mkt">BYMA</td>
                <td style="color:#ffcc00">{p_str}</td>
                {_chg_pct_td(chg)}
            </tr>"""
        
        html = f"""<table class="t">
        <thead><tr><th>TICKER</th><th>MKT</th><th>PRECIO</th><th>% DIA</th></tr></thead>
        <tbody>{rows}</tbody></table>"""
        st.markdown(_panel(f"ACCIONES ARG · TOP {len(top_acc[:12])}", html), unsafe_allow_html=True)

        # ADRs mini
        with st.spinner(""):
            adrs = get_adrs()
        
        rows_adr = ""
        for item in (adrs or [])[:8]:
            t = item.get("ticker", "—")
            p = item.get("last")
            chg = item.get("pct_change")
            p_str = fmt_price(p) if p else "—"
            rows_adr += f"""<tr>
                <td>{t}</td>
                <td class="mkt">NYSE</td>
                <td style="color:#ffcc00">{p_str}</td>
                {_chg_pct_td(chg)}
            </tr>"""
        
        if rows_adr:
            html_adr = f"""<table class="t">
            <thead><tr><th>ADR</th><th>MKT</th><th>PRECIO</th><th>% DIA</th></tr></thead>
            <tbody>{rows_adr}</tbody></table>"""
            st.markdown(_panel("ADRs ARGENTINOS", html_adr), unsafe_allow_html=True)

    # ── COL 3: Commodities + Crypto + FX ──
    with c3:
        with st.spinner(""):
            comm = get_yf_quotes(COMMODITY_TICKERS)
        
        rows_c = ""
        for name, q in comm.items():
            p = q.get("price")
            chg = q.get("change_pct", 0)
            p_str = fmt_price(p, 2)
            rows_c += f"""<tr>
                <td>{name}</td>
                <td class="mkt">CMX</td>
                <td style="color:#ffcc00">{p_str}</td>
                {_chg_td(chg)}
                {_chg_pct_td(chg)}
            </tr>"""
        
        html_c = f"""<table class="t">
        <thead><tr><th>NOMBRE</th><th>MKT</th><th>PRECIO</th><th>CAMBIO</th><th>% DIA</th></tr></thead>
        <tbody>{rows_c}</tbody></table>"""
        st.markdown(_panel("MATERIAS PRIMAS", html_c), unsafe_allow_html=True)

        # Crypto
        crypto_tickers = {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD"}
        with st.spinner(""):
            crypto = get_yf_quotes(crypto_tickers)
        
        rows_cr = ""
        for name, q in crypto.items():
            p = q.get("price")
            chg = q.get("change_pct", 0)
            p_str = fmt_price(p, 2)
            rows_cr += f"""<tr>
                <td>{name}</td>
                <td class="mkt">CRYPTO</td>
                <td style="color:#ffcc00">{p_str}</td>
                {_chg_td(chg)}
                {_chg_pct_td(chg)}
            </tr>"""
        
        html_cr = f"""<table class="t">
        <thead><tr><th>NOMBRE</th><th>MKT</th><th>PRECIO</th><th>CAMBIO</th><th>% DIA</th></tr></thead>
        <tbody>{rows_cr}</tbody></table>"""
        st.markdown(_panel("CRIPTOMONEDAS", html_cr), unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # ROW 3: 2-column — Divisas | Bonos Soberanos snapshot
    # ══════════════════════════════════════════════════════════════════════
    c4, c5 = st.columns([1, 1])

    with c4:
        with st.spinner(""):
            fx = get_yf_quotes(FX_TICKERS)
        
        rows_fx = ""
        for name, q in fx.items():
            p = q.get("price")
            chg = q.get("change_pct", 0)
            p_str = fmt_price(p, 4)
            rows_fx += f"""<tr>
                <td>{name}</td>
                <td style="color:#ffcc00">{p_str}</td>
                {_chg_pct_td(chg)}
            </tr>"""
        
        html_fx = f"""<table class="t">
        <thead><tr><th>PAR</th><th>VALOR</th><th>% DIA</th></tr></thead>
        <tbody>{rows_fx}</tbody></table>"""
        st.markdown(_panel("DIVISAS", html_fx), unsafe_allow_html=True)

        # Futuros Dolar mini
        with st.spinner(""):
            df_fut = get_futuros_dolar()
        
        if not df_fut.empty:
            rows_f = ""
            for _, row in df_fut.head(6).iterrows():
                esp = row.iloc[0] if len(row) > 0 else "—"
                ult = row.iloc[1] if len(row) > 1 else "—"
                tna = row.iloc[3] if len(row) > 3 else "—"
                try:
                    tna_f = float(str(tna).replace(",",".").replace("%",""))
                    tna_html = f'<td style="color:#ff6600;font-weight:bold">{tna_f:.1f}%</td>'
                except:
                    tna_html = f'<td style="color:#555">{tna}</td>'
                rows_f += f"<tr><td>{esp}</td><td style='color:#ffcc00'>{ult}</td>{tna_html}</tr>"
            
            html_f = f"""<table class="t">
            <thead><tr><th>CONTRATO</th><th>ÚLTIMO</th><th>TNA</th></tr></thead>
            <tbody>{rows_f}</tbody></table>"""
            st.markdown(_panel("FUTUROS DÓLAR", html_f), unsafe_allow_html=True)

    with c5:
        boot = get_bondterminal_bootstrap()
        if isinstance(boot, dict) and "error" not in boot:
            sov = boot.get("sovereignSnapshot", {})
            sections = sov.get("sections", [])
            
            rows_b = ""
            for section in sections:
                for b in section.get("bonds", [])[:6]:
                    ticker = b.get("ticker", "")
                    price = b.get("price")
                    chg = b.get("change1D")
                    yld = b.get("yield")
                    dur = b.get("modDuration")
                    
                    p_str = f"{price:.2f}" if price else "—"
                    y_str = f"{yld:.1f}%" if yld else "—"
                    d_str = f"{dur:.1f}" if dur else "—"
                    
                    rows_b += f"""<tr>
                        <td>{ticker}</td>
                        <td style="color:#ffcc00">{p_str}</td>
                        {_chg_td(chg)}
                        <td>{y_str}</td>
                        <td style="color:#555">{d_str}</td>
                    </tr>"""
            
            if rows_b:
                html_b = f"""<table class="t">
                <thead><tr><th>BONO</th><th>PRECIO</th><th>Δ DIA</th><th>YIELD</th><th>DUR</th></tr></thead>
                <tbody>{rows_b}</tbody></table>"""
                st.markdown(_panel("BONOS SOBERANOS", html_b), unsafe_allow_html=True)

        # Riesgo país detail
        d1w = rp.get("delta_1w", 0)
        d1m = rp.get("delta_1m", 0)
        ambito = rp.get("bps_ambito", "—")
        
        def _delta(v, label):
            if not v: return ""
            c = "#00ff41" if v > 0 else "#ff3b3b"
            s = "+" if v > 0 else ""
            return f'<span style="color:{c};font-weight:bold">{s}{v:.0f} {label}</span>'
        
        st.markdown(f"""
        <div class="panel">
          <div class="panel-title">RIESGO PAÍS DETALLE</div>
          <div style="padding:6px 8px;display:flex;gap:20px;align-items:center">
            <div>
              <span style="color:#ffcc00;font-size:24px;font-weight:bold">{bps}</span>
              <span style="color:#555;font-size:10px"> bps</span>
            </div>
            <div style="display:flex;flex-direction:column;gap:2px;font-size:10px">
              {_delta(d1d, "hoy")}
              {_delta(d1w, "7d")}
              {_delta(d1m, "30d")}
            </div>
            <div style="margin-left:auto;font-size:10px;color:#555">
              Ámbito: <span style="color:#ccc">{ambito} bps</span>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
