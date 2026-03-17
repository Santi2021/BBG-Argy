"""
OVERVIEW — Markets Terminal 3x3 Grid
9 equal panels (KPI strip moved to app.py as news ticker):
  Row 1: Cauciones | Futuros Dólar | Letras ARS
  Row 2: Bonos Soberanos | Corporativos | US Rates
  Row 3: Acciones ARG | ADRs ARG | Commodities & Crypto
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import (
    get_yf_quotes, get_dolar, get_riesgo_pais, get_acciones,
    get_bondterminal_bootstrap, get_futuros_dolar, get_adrs,
    get_letras, get_bonos_ars, get_us_rates, get_letras_ppi,
    fmt_price, fmt_change,
    COMMODITY_TICKERS,
)


def _pct_html(val):
    if val is None or val == "—":
        return '<span style="color:#555">—</span>'
    try:
        v = float(str(val).replace("%","").replace(",",".").strip())
        c = "#00ff41" if v > 0 else ("#ff3b3b" if v < 0 else "#555")
        s = "+" if v >= 0 else ""
        return f'<span style="color:{c};font-weight:bold">{s}{v:.2f}%</span>'
    except:
        return f'<span style="color:#555">{val}</span>'


def _chg_html(val):
    if val is None or val == "—":
        return '<span style="color:#555">—</span>'
    try:
        v = float(str(val).replace("%","").replace(",",".").strip())
        c = "#00ff41" if v > 0 else ("#ff3b3b" if v < 0 else "#555")
        s = "+" if v >= 0 else ""
        a = "▲" if v >= 0 else "▼"
        return f'<span style="color:{c};font-weight:bold">{a} {s}{v:.2f}</span>'
    except:
        return f'<span style="color:#555">{val}</span>'


def _panel_html(title, headers, rows_html, max_height=320):
    ths = "".join(f"<th>{h}</th>" for h in headers)
    return f"""<div style="border:1px solid #333;background:#000;height:{max_height}px;display:flex;flex-direction:column;overflow:hidden">
  <div style="background:#111;color:#ff6600;font-size:9px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;padding:3px 8px;border-bottom:1px solid #ff6600;flex-shrink:0">{title}</div>
  <div style="overflow-y:auto;flex:1">
    <table class="t" style="border-collapse:collapse;width:100%">
      <thead><tr style="position:sticky;top:0;z-index:2;background:#111">{ths}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>"""


def _build_acciones():
    acc = get_acciones()
    MERVAL = [
        "ALUA", "BBAR", "BMA", "BYMA", "CEPU", "COME", "CRES", "EDN",
        "GGAL", "LOMA", "METR", "PAMP", "SUPV", "TECO2", "TGNO4",
        "TGSU2", "TRAN", "TXAR", "VALO", "YPFD",
    ]
    by_ticker = {}
    for item in (acc or []):
        tk = item.get("ticker", "")
        if tk in MERVAL:
            by_ticker[tk] = item
    rows = ""
    for tk in MERVAL:
        item = by_ticker.get(tk)
        if item:
            p = item.get("last")
            chg = item.get("pct_change")
            p_s = fmt_price(p) if p else "—"
            rows += f'<tr><td>{tk}</td><td class="mkt">BYMA</td><td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td></tr>'
        else:
            rows += f'<tr><td>{tk}</td><td class="mkt">BYMA</td><td style="color:#555">—</td><td style="color:#555">—</td></tr>'
    return rows


def _build_adrs():
    adrs = get_adrs()
    ARG_ADRS = [
        "YPF", "GGAL", "BBAR", "BMA", "SUPV", "PAM",
        "LOMA", "CEPU", "TEO", "TGS", "EDN", "CRESY", "IRS",
    ]
    by_ticker = {}
    for item in (adrs or []):
        tk = item.get("ticker", "")
        if tk in ARG_ADRS:
            by_ticker[tk] = item
    rows = ""
    for tk in ARG_ADRS:
        item = by_ticker.get(tk)
        if item:
            p = item.get("last")
            chg = item.get("pct_change")
            p_s = fmt_price(p, 2) if p else "—"
            rows += f'<tr><td>{tk}</td><td class="mkt">NYSE</td><td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td></tr>'
        else:
            rows += f'<tr><td>{tk}</td><td class="mkt">NYSE</td><td style="color:#555">—</td><td style="color:#555">—</td></tr>'
    return rows


def _build_commodities():
    comm = get_yf_quotes(COMMODITY_TICKERS)
    rows = ""
    for name, q in comm.items():
        p = q.get("price")
        chg = q.get("change_pct", 0)
        rows += f'<tr><td>{name}</td><td class="mkt">CMX</td><td style="color:#ffcc00">{fmt_price(p, 2)}</td><td>{_chg_html(chg)}</td><td>{_pct_html(chg)}</td></tr>'
    rows += '<tr><td colspan="5" style="border-bottom:1px solid #333;padding:1px"></td></tr>'
    crypto_map = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD"}
    crypto = get_yf_quotes(crypto_map)
    for name, q in crypto.items():
        p = q.get("price")
        chg = q.get("change_pct", 0)
        rows += f'<tr><td>{name}</td><td class="mkt">CRYPTO</td><td style="color:#ffcc00">{fmt_price(p, 2)}</td><td>{_chg_html(chg)}</td><td>{_pct_html(chg)}</td></tr>'
    return rows


def _build_corporativos():
    boot = get_bondterminal_bootstrap()
    rows = ""
    if isinstance(boot, dict) and "error" not in boot:
        corp = boot.get("corporateSnapshot", {})
        bonds = corp.get("bonds", [])
        bonds_sorted = sorted(bonds, key=lambda b: b.get("modDuration") or 999)
        for b in bonds_sorted:
            tk = b.get("ticker") or b.get("localTicker", "")
            p = b.get("price")
            ch = b.get("change1D")
            y = b.get("yield")
            d = b.get("modDuration")
            rows += f'<tr><td>{tk}</td><td style="color:#ffcc00">{f"{p:.2f}" if p else "—"}</td><td>{_chg_html(ch)}</td><td>{f"{y:.1f}%" if y else "—"}</td><td style="color:#555">{f"{d:.1f}" if d else "—"}</td></tr>'
    return rows


def _build_us_rates():
    rates = get_us_rates()
    rows = ""

    def _rate_html(key, color="#00ff41", decimals=2):
        data = rates.get(key, {})
        rate = data.get("rate")
        if rate is not None:
            return f'<span style="color:{color};font-weight:bold">{rate:.{decimals}f}%</span>'
        return '<span style="color:#555">—</span>'

    def _chg_bps_html(key):
        """Convierte change absoluto de yield a bps con color."""
        data = rates.get(key, {})
        chg = data.get("change")
        if chg is None:
            return '<span style="color:#555">—</span>'
        try:
            v = float(str(chg).replace(",", ".").strip())
            bps = round(v * 100)
            c = "#00ff41" if v < 0 else ("#ff3b3b" if v > 0 else "#555")
            s = "+" if bps >= 0 else ""
            return f'<span style="color:{c};font-weight:bold">{s}{bps}bps</span>'
        except Exception:
            return f'<span style="color:#555">{chg}</span>'

    # ── SOFR / EFFR / OBFR ──────────────────────────────────────────────────
    for label, key in [("SOFR", "SOFR"), ("EFFR", "EFFR"), ("OBFR", "OBFR")]:
        data = rates.get(key, {})
        target_from = data.get("target_from")
        target_to   = data.get("target_to")
        target_s    = f'{target_from:.2f}-{target_to:.2f}%' if target_from and target_to else ""
        rows += f'<tr><td>{label}</td><td>{_rate_html(key)}</td><td></td><td style="color:#555;font-size:9px">{target_s}</td></tr>'

    rows += '<tr><td colspan="4" style="border-bottom:1px solid #333;padding:1px"></td></tr>'

    # ── Treasury yields ──────────────────────────────────────────────────────
    for label, key in [
        ("UST 1M",  "UST_1M"),  ("UST 3M",  "UST_3M"),
        ("UST 6M",  "UST_6M"),  ("UST 1Y",  "UST_1Y"),
        ("UST 2Y",  "UST_2Y"),  ("UST 5Y",  "UST_5Y"),
        ("UST 10Y", "UST_10Y"), ("UST 30Y", "UST_30Y"),
    ]:
        rows += f'<tr><td>{label}</td><td>{_rate_html(key, "#ffcc00")}</td><td>{_chg_bps_html(key)}</td><td></td></tr>'

    # ── 10Y-2Y Spread ────────────────────────────────────────────────────────
    ust10 = rates.get("UST_10Y", {}).get("rate")
    ust2  = rates.get("UST_2Y",  {}).get("rate")
    if ust10 is not None and ust2 is not None:
        spread    = round((ust10 - ust2) * 100)
        spr_color = "#00ff41" if spread > 0 else "#ff3b3b"
        spr_s     = f'<span style="color:{spr_color};font-weight:bold">{spread:+d} bps</span>'
    else:
        spr_s = '<span style="color:#555">—</span>'
    rows += f'<tr><td>10Y-2Y SPR</td><td>{spr_s}</td><td></td><td></td></tr>'

    rows += '<tr><td colspan="4" style="border-bottom:1px solid #333;padding:1px"></td></tr>'

    # ── TIPS y BEI ───────────────────────────────────────────────────────────
    rows += f'<tr><td>TIPS 5Y</td><td>{_rate_html("TIPS_5Y",  "#ff6600")}</td><td></td><td></td></tr>'
    rows += f'<tr><td>TIPS 10Y</td><td>{_rate_html("TIPS_10Y", "#ff6600")}</td><td></td><td></td></tr>'
    rows += f'<tr><td>BEI 5Y</td><td>{_rate_html("BEI_5Y",   "#ff6600")}</td><td></td><td style="color:#555;font-size:9px">breakeven</td></tr>'
    rows += f'<tr><td>BEI 10Y</td><td>{_rate_html("BEI_10Y",  "#ff6600")}</td><td></td><td style="color:#555;font-size:9px">breakeven</td></tr>'

    return rows


def _build_bonos():
    boot = get_bondterminal_bootstrap()
    rows = ""
    if isinstance(boot, dict) and "error" not in boot:
        sov = boot.get("sovereignSnapshot", {})
        for sec in sov.get("sections",[]):
            for b in sec.get("bonds", []):
                tk = b.get("ticker", "")
                p = b.get("price")
                ch = b.get("change1D")
                y = b.get("yield")
                d = b.get("modDuration")
                rows += f'<tr><td>{tk}</td><td style="color:#ffcc00">{f"{p:.2f}" if p else "—"}</td><td>{_chg_html(ch)}</td><td>{f"{y:.1f}%" if y else "—"}</td><td style="color:#555">{f"{d:.1f}" if d else "—"}</td></tr>'
    return rows


def _build_letras():
    """
    Letras ARS — una letra representativa por mes de vencimiento.
    Seleccion automatica: mayor volumen por mes, solo ARS con TNA valida.
    Ordenadas por fecha para construir curva de rendimientos.
    Columnas: TICKER | PRECIO | % DIA | TNA | VTO
    """
    from datetime import date

    ppi = get_letras_ppi()
    candidatos = [
        item for item in (ppi or [])
        if item.get("currency") == "ARS"
        and item.get("tna") is not None
        and item.get("tna") > 0          # excluir CER, TAMAR, dollar-linked
        and item.get("expiration_date")
        and item.get("last", 0) > 0
        and item.get("last", 0) < 10000  # excluir dollar-linked (precio ~140k)
        and str(item.get("ticker", ""))[0] in ("S", "T")  # solo capitalizables tasa fija
    ]

    # Una letra por mes: la de mayor volumen operado
    by_month = {}
    for item in candidatos:
        mes = item["expiration_date"][:7]  # "YYYY-MM"
        vol = item.get("volume", 0) or 0
        if mes not in by_month or vol > (by_month[mes].get("volume") or 0):
            by_month[mes] = item

    # Ordenar por vencimiento y filtrar vencidas
    hoy = date.today().isoformat()
    curva = sorted(
        [x for x in by_month.values() if x["expiration_date"] >= hoy],
        key=lambda x: x["expiration_date"]
    )

    rows = ""
    for item in curva:
        tk = item["ticker"]
        p = item["last"]
        chg = item.get("pct_change", 0)
        tna = item["tna"]
        vto = item["expiration_date"]

        p_s = fmt_price(p) if p else "—"
        tna_s = f'<span style="color:#ff6600;font-weight:bold">{tna:.1f}%</span>'
        vto_s = f'<span style="color:#555;font-size:9px">{vto[5:7]}/{vto[2:4]}</span>'

        rows += f'<tr><td>{tk}</td><td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td><td>{tna_s}</td><td>{vto_s}</td></tr>'

    if not rows:
        rows = '<tr><td colspan="5" style="color:#555">Sin datos PPI</td></tr>'

    # ── Dollar-linked ──
    dl_candidatos = [
        item for item in (ppi or [])
        if item.get("tna") is not None
        and item.get("tna") > 0
        and item.get("expiration_date")
        and item.get("last", 0) > 0
        and str(item.get("ticker", ""))[0] == "D"
    ]
    dl_by_month = {}
    for item in dl_candidatos:
        mes = item["expiration_date"][:7]
        vol = item.get("volume", 0) or 0
        if mes not in dl_by_month or vol > (dl_by_month[mes].get("volume") or 0):
            dl_by_month[mes] = item

    dl_curva = sorted(
        [x for x in dl_by_month.values() if x["expiration_date"] >= hoy],
        key=lambda x: x["expiration_date"]
    )

    if dl_curva:
        rows += '<tr><td colspan="5" style="border-top:1px solid #333;padding:2px 6px;color:#00bfff;font-size:8px;font-weight:bold;letter-spacing:1px">DOLLAR LINKED</td></tr>'
        for item in dl_curva:
            tk = item["ticker"]
            p = item["last"]
            chg = item.get("pct_change", 0)
            tna = item["tna"]
            vto = item["expiration_date"]

            p_s = fmt_price(p) if p else "—"
            tna_s = f'<span style="color:#00bfff;font-weight:bold">{tna:.1f}%</span>'
            vto_s = f'<span style="color:#555;font-size:9px">{vto[5:7]}/{vto[2:4]}</span>'

            rows += f'<tr><td>{tk}</td><td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td><td>{tna_s}</td><td>{vto_s}</td></tr>'

    return rows


def _build_cauciones():
    from data import get_cauciones_resumen
    cauc = get_cauciones_resumen()
    rows = ""
    if cauc:
        for d in cauc:
            plazo = d.get("plazo", "—")
            tasa = d.get("tasa", 0)
            monto = d.get("monto_contado", "—")
            if tasa and tasa > 0:
                tasa_s = f'<span style="color:#00ff41;font-weight:bold">{tasa:.2f}%</span>'
            else:
                tasa_s = '<span style="color:#555">—</span>'
            rows += f'<tr><td>{plazo} DÍAS</td><td>{tasa_s}</td><td style="color:#555;font-size:9px">{monto}</td></tr>'
    else:
        for plazo in ["1","3","7","14","30","60","90"]:
            rows += f'<tr><td>{plazo} DÍAS</td><td style="color:#555">—</td><td style="color:#555">—</td></tr>'
    return rows


def _build_futuros():
    df = get_futuros_dolar()
    rows = ""
    if not df.empty:
        for _, r in df.iterrows():
            esp = r.iloc[0] if len(r) > 0 else "—"
            ult = r.iloc[1] if len(r) > 1 else "—"
            tna = r.iloc[3] if len(r) > 3 else "—"
            try:
                tna_f = float(str(tna).replace(",",".").replace("%",""))
                tna_s = f'<span style="color:#ff6600;font-weight:bold">{tna_f:.1f}%</span>'
            except:
                tna_s = f'<span style="color:#555">{tna}</span>'
            rows += f'<tr><td>{esp}</td><td style="color:#ffcc00">{ult}</td><td>{tna_s}</td></tr>'
    return rows


def render():
    with st.spinner(""):
        r_acc = _build_acciones()
        r_adr = _build_adrs()
        r_com = _build_commodities()
        r_bon = _build_bonos()
        r_corp = _build_corporativos()
        r_usr = _build_us_rates()
        r_let = _build_letras()
        r_cau = _build_cauciones()
        r_fut = _build_futuros()

    PH = 340

    p1 = _panel_html("CAUCIONES", ["PLAZO","TNA","VOLUMEN"], r_cau, PH)
    p2 = _panel_html("FUTUROS DÓLAR", ["CONTRATO","ÚLTIMO","TNA"], r_fut, PH)
    p3 = _panel_html("LETRAS EN ARS · PPI", ["TICKER","PRECIO","% DIA","TNA","VTO"], r_let, PH)

    p4 = _panel_html("BONOS SOBERANOS", ["BONO","PRECIO","Δ DIA","YIELD","DUR"], r_bon, PH)
    p5 = _panel_html("CORPORATIVOS", ["BONO","PRECIO","Δ DIA","YIELD","DUR"], r_corp, PH)
    p6 = _panel_html("US RATES · SOFR · TREASURY", ["RATE", "VALOR", "CHG", "TARGET"], r_usr, PH)

    p7 = _panel_html("ACCIONES ARG", ["TICKER","MKT","PRECIO","% DIA"], r_acc, PH)
    p8 = _panel_html("ADRs ARGENTINOS", ["ADR","MKT","PRECIO","% DIA"], r_adr, PH)
    p9 = _panel_html("COMMODITIES & CRYPTO", ["NOMBRE","MKT","PRECIO","CAMBIO","% DIA"], r_com, PH)

    grid_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:auto auto auto;gap:4px;margin-top:4px">
      <div>{p1}</div><div>{p2}</div><div>{p3}</div>
      <div>{p4}</div><div>{p5}</div><div>{p6}</div>
      <div>{p7}</div><div>{p8}</div><div>{p9}</div>
    </div>"""

    st.markdown(grid_html, unsafe_allow_html=True)
