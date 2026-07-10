"""
ARGENTINA — Equity por Sectores
  Tab 1: 9 paneles simétricos por sector (grilla 3x3)
  Tab 2: Heatmap treemap (tamaño = volumen, color = variación diaria)
"""
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _price_fmt(val):
    """Precio sin decimales, propio de este tab (no toca fmt_price compartido)."""
    if val is None:
        return "—"
    try:
        return f"{float(val):,.0f}"
    except (ValueError, TypeError):
        return str(val)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTOR DEFINITIONS — tickers BYMA en ARS
# ═══════════════════════════════════════════════════════════════════════════════

SECTORS = {
    "BANCOS & FINANCIERAS": {
        "tickers": ["GGAL", "BBAR", "BMA", "SUPV", "BYMA", "VALO", "BPAT", "BHIP"],
        "color": "#00bfff",
    },
    "ENERGÍA": {
        "tickers": ["YPFD", "PAMP", "CAPX", "VIST"],
        "color": "#ff6600",
    },
    "UTILITIES": {
        "tickers": ["CEPU", "EDN", "TGNO4", "TGSU2", "METR", "TRAN",
                     "CECO2", "CGPA2", "DGCU2", "GBAN", "AUSO", "OEST", "ECOG"],
        "color": "#ffcc00",
    },
    "MATERIALES": {
        "tickers": ["ALUA", "TXAR", "LOMA", "HARG", "CELU"],
        "color": "#cc66ff",
    },
    "AGRO & ALIMENTOS": {
        "tickers": ["CRES", "AGRO", "MOLA", "MOLI", "SEMI", "SAMI",
                     "LEDE", "MORI", "INAG", "PATA"],
        "color": "#00ff41",
    },
    "TELECOM & MEDIOS": {
        "tickers": ["TECO2", "CVH", "GCLA", "HSAT"],
        "color": "#60a5fa",
    },
    "REAL ESTATE": {
        "tickers": ["IRSA", "CTIO", "CADO", "INVJ", "IEB", "RAGH"],
        "color": "#f59e0b",
    },
    "INDUSTRIA & CONSUMO": {
        "tickers": ["MIRG", "FERR", "GRIM", "LONG", "RICH", "RIGO",
                     "HAVA", "DOME", "ROSE"],
        "color": "#ec4899",
    },
    "OTROS": {
        "tickers": ["A3", "BOLT", "CARC", "FIPL", "GAMI", "GARO",
                     "GCDI", "INTR", "MERA", "POLL", "COME"],
        "color": "#555",
    },
}

ALL_TICKERS = []
for sec in SECTORS.values():
    for t in sec["tickers"]:
        if t not in ALL_TICKERS:
            ALL_TICKERS.append(t)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA FETCHING — yfinance batch, compatible con 0.2.58+
# ═══════════════════════════════════════════════════════════════════════════════

def _prev_close_fallback(sym: str) -> float | None:
    """Obtiene previousClose via fast_info — fallback cuando download devuelve < 2 filas."""
    try:
        fi = yf.Ticker(sym).fast_info
        return float(fi.get("previous_close") or fi.get("previousClose") or 0) or None
    except Exception:
        return None


def _radar_cache_bucket():
    """Determina la 'ventana' de cache según el horario de Buenos Aires:

    - 10:00–18:00 (mercado operando): bucket cambia cada 5 minutos, mismo
      comportamiento de refresco que antes.
    - 18:00–10:00 del día siguiente (mercado cerrado): el bucket queda FIJO
      con la fecha de cierre correspondiente — es la "foto" del cierre, no
      se vuelve a pedir nada a Yahoo hasta que abra de nuevo. Esto evita
      pisar el dato bueno con ceros/NaN de la ventana de consolidación
      post-cierre (~17:00–18:30), que es cuando Yahoo todavía no terminó
      de fijar el precio/volumen final del día.
    """
    from zoneinfo import ZoneInfo
    import datetime as _dt

    tz = ZoneInfo("America/Argentina/Buenos_Aires")
    now = _dt.datetime.now(tz)

    if _dt.time(10, 0) <= now.time() < _dt.time(18, 0):
        bucket_5min = (now.hour * 60 + now.minute) // 5
        return f"live_{now.date()}_{bucket_5min}"
    else:
        # Si todavía no son las 18:00, la "foto" pendiente es la de AYER
        # (recién cerrada); si ya pasaron las 18:00, es la de HOY.
        close_date = now.date() if now.time() >= _dt.time(18, 0) else now.date() - _dt.timedelta(days=1)
        return f"frozen_{close_date}"


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_arg_equity(_cache_bucket=None):
    """Fetch all Argentine equity data via yfinance .BA tickers.

    Baja ~1 año de historial para poder calcular, además del monto operado
    promedio de 21 ruedas: máximos/mínimos de 52 semanas y retorno YTD.
    El argumento _cache_bucket (ver _radar_cache_bucket) es lo que realmente
    controla cuándo se refresca — el ttl=600 es solo un piso de seguridad.
    """
    import pandas as pd
    from concurrent.futures import ThreadPoolExecutor, as_completed

    yf_symbols = [f"{t}.BA" for t in ALL_TICKERS]
    result = {}

    empty_record = {
        "price": None, "change_pct": 0, "volume": 0, "monto": 0,
        "avg_monto_21": None, "monto_ratio": None, "trend_ratio": None,
        "trend_base_avg": None, "high_52w": None, "low_52w": None,
        "is_new_high": False, "is_new_low": False,
        "pct_from_high": None, "pct_from_low": None,
        "returns": {"1S": None, "1M": None, "3M": None, "YTD": None, "12M": None},
    }

    def _fetch_one(yf_sym):
        """Descarga UN ticker por separado (no batch) — evita el bug de yfinance
        donde un batch grande de símbolos devuelve datos incompletos para un
        subconjunto sin avisar. Reintenta una vez si viene vacío.

        Además recorta del final cualquier rueda "fantasma" (feriado/día sin
        operatoria): Yahoo a veces repite el cierre anterior con volumen 0 en
        vez de simplemente omitir el día. Sin este recorte, un feriado se
        mostraba como si fuera "hoy" con % DIA en 0 y Monto vacío — no era un
        dato roto, era un feriado mal interpretado como sesión real."""
        for attempt in range(2):
            try:
                hist = yf.Ticker(yf_sym).history(period="1y", interval="1d", auto_adjust=True)
                if hist is None or len(hist) == 0:
                    continue
                vol = hist["Volume"]
                while len(hist) > 0 and (pd.isna(vol.iloc[-1]) or vol.iloc[-1] == 0):
                    hist = hist.iloc[:-1]
                    vol = hist["Volume"]
                if len(hist) > 0:
                    return hist["Close"].dropna(), hist["Volume"].dropna()
            except Exception:
                pass
        return pd.Series(dtype=float), pd.Series(dtype=float)

    hist_by_ticker = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_one, sym): ticker for ticker, sym in zip(ALL_TICKERS, yf_symbols)}
        for fut in as_completed(futures):
            hist_by_ticker[futures[fut]] = fut.result()

    try:
        for ticker, yf_sym in zip(ALL_TICKERS, yf_symbols):
            try:
                closes, volumes = hist_by_ticker.get(ticker, (pd.Series(dtype=float), pd.Series(dtype=float)))

                if len(closes) >= 2:
                    price = float(closes.iloc[-1])
                    prev  = float(closes.iloc[-2])
                    chg   = (price - prev) / prev * 100 if prev != 0 else 0
                elif len(closes) == 1:
                    price = float(closes.iloc[-1])
                    prev  = _prev_close_fallback(yf_sym)
                    chg   = (price - prev) / prev * 100 if prev else 0
                else:
                    price = None
                    chg   = 0

                vol   = int(volumes.iloc[-1]) if len(volumes) > 0 else 0
                monto = vol * price if (vol and price) else 0

                # Serie diaria de monto operado (precio × volumen), alineada por fecha
                monto_series = (closes * volumes).dropna()

                avg_monto_21   = None
                monto_ratio    = None
                trend_ratio    = None
                trend_base_avg = None
                if len(monto_series) >= 3:
                    # Todas las ruedas previas a hoy, últimas 21 disponibles
                    hist = monto_series.iloc[:-1].tail(21)
                    if len(hist) >= 3:
                        avg_val = float(hist.mean())
                        if avg_val > 0:
                            avg_monto_21 = avg_val
                            monto_ratio  = monto / avg_val if monto else 0.0

                    # Tendencia: mediana de últimas 5 ruedas (incl. hoy) vs media de las 16 previas.
                    window21 = monto_series.tail(21)
                    if len(window21) >= 10:
                        recent_5 = window21.tail(5)
                        base_n   = window21.iloc[:-5]
                        if len(base_n) >= 3:
                            base_avg = float(base_n.mean())
                            if base_avg > 0:
                                trend_ratio    = float(recent_5.median()) / base_avg
                                trend_base_avg = base_avg

                # 52 semanas: ¿esta semana (últimas 5 ruedas) rompió el máximo/mínimo de
                # todo lo anterior? Más útil que exigir que sea justo HOY el extremo —
                # una acción puede haber hecho el pico el lunes y hoy, jueves, estar
                # apenas por debajo, y sigue siendo relevante que rompió esta semana.
                high_52w      = None
                low_52w       = None
                is_new_high   = False
                is_new_low    = False
                pct_from_high = None
                pct_from_low  = None
                if price is not None and len(closes) >= 10:
                    week_closes  = closes.tail(5)
                    prior_closes = closes.iloc[:-5]
                    if len(prior_closes) >= 5:
                        prior_high = float(prior_closes.max())
                        prior_low  = float(prior_closes.min())
                        week_high  = float(week_closes.max())
                        week_low   = float(week_closes.min())

                        high_52w = max(prior_high, week_high)
                        low_52w  = min(prior_low, week_low)

                        if prior_high > 0:
                            is_new_high   = week_high >= prior_high * 0.999
                            pct_from_high = (price / prior_high - 1) * 100
                        if prior_low > 0:
                            is_new_low    = week_low <= prior_low * 1.001
                            pct_from_low  = (price / prior_low - 1) * 100

                # Ancla robusta: mediana de una pequeña ventana de días alrededor del
                # punto de referencia, en vez de un solo cierre puntual. Esto evita que
                # un día anómalo (ej. el debut ilíquido de un ticker recién listado, con
                # precio de descubrimiento poco representativo) contamine todo el retorno
                # — mismo principio que la mediana usada en Acumulación de Volumen.
                def _robust_base(idx_from_end):
                    idx = len(closes) - 1 - idx_from_end
                    if idx < 0:
                        return None
                    lo, hi = max(0, idx - 2), min(len(closes), idx + 3)
                    window = closes.iloc[lo:hi]
                    if len(window) == 0:
                        return None
                    val = float(window.median())
                    return val if val > 0 else None

                # YTD: mediana de un puñado de días del año calendario en curso, saltando
                # las primeras ~10 ruedas si hay suficiente historia — un ticker recién
                # salido de un spin-off o debut puede tener semanas de precio distorsionado
                # al principio, no solo el primer día.
                ytd_return = None
                if price is not None and len(closes) >= 2:
                    last_year = closes.index[-1].year
                    ytd_series = closes[closes.index.year == last_year]
                    if len(ytd_series) >= 2:
                        settle = 10 if len(ytd_series) >= 20 else 0
                        start_price = float(ytd_series.iloc[settle:settle + 5].median())
                        if start_price > 0:
                            ytd_return = (price / start_price - 1) * 100

                # Retornos por ventana fija (en ruedas hábiles), para el selector de período.
                # Para 12M no exigimos un número exacto de ruedas (yfinance con period="1y"
                # no siempre devuelve el mismo conteo por feriados/días sin operar) — usamos
                # la mediana de los primeros días disponibles de la ventana de ~1 año, con
                # el mismo colchón de asentamiento que YTD.
                def _ret_lookback(n):
                    if price is None or len(closes) <= n:
                        return None
                    base = _robust_base(n)
                    return (price / base - 1) * 100 if base else None

                ret_12m = None
                if price is not None and len(closes) >= 180:  # ~9 meses mínimo para llamarlo "12M"
                    settle = 10 if len(closes) >= 200 else 0
                    base = float(closes.iloc[settle:settle + 5].median())
                    if base > 0:
                        ret_12m = (price / base - 1) * 100

                returns_by_period = {
                    "1S":  _ret_lookback(5),
                    "1M":  _ret_lookback(21),
                    "3M":  _ret_lookback(63),
                    "YTD": ytd_return,
                    "12M": ret_12m,
                }

                result[ticker] = {
                    "price":          price,
                    "change_pct":     round(chg, 2),
                    "volume":         vol,
                    "monto":          round(monto),
                    "avg_monto_21":   round(avg_monto_21) if avg_monto_21 else None,
                    "monto_ratio":    round(monto_ratio, 2) if monto_ratio is not None else None,
                    "trend_ratio":    round(trend_ratio, 2) if trend_ratio is not None else None,
                    "trend_base_avg": round(trend_base_avg) if trend_base_avg else None,
                    "high_52w":       high_52w,
                    "low_52w":        low_52w,
                    "is_new_high":    is_new_high,
                    "is_new_low":     is_new_low,
                    "pct_from_high":  round(pct_from_high, 2) if pct_from_high is not None else None,
                    "pct_from_low":   round(pct_from_low, 2) if pct_from_low is not None else None,
                    "returns":        {k: (round(v, 2) if v is not None else None)
                                        for k, v in returns_by_period.items()},
                }
            except Exception:
                result[ticker] = dict(empty_record)

    except Exception:
        for t in ALL_TICKERS:
            result[t] = dict(empty_record)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _pct_html(val):
    if val is None or val == 0:
        return '<span style="color:#555">0.00%</span>'
    try:
        v = float(val)
        c = "#00ff41" if v > 0 else ("#ff3b3b" if v < 0 else "#555")
        s = "+" if v >= 0 else ""
        return f'<span style="color:{c};font-weight:bold">{s}{v:.2f}%</span>'
    except:
        return f'<span style="color:#555">{val}</span>'


def _vol_fmt(v):
    if not v or v == 0:
        return "—"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.0f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.0f}M"
    if v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(v)


def _panel_html(title, headers, rows_html, accent_color="#ff6600", max_height=260):
    ths = "".join(f"<th>{h}</th>" for h in headers)
    return f"""<div style="border:1px solid #333;background:#000;height:{max_height}px;display:flex;flex-direction:column;overflow:hidden">
  <div style="background:#111;color:{accent_color};font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;padding:4px 8px;border-bottom:1px solid {accent_color};flex-shrink:0">{title}</div>
  <div style="overflow-y:auto;flex:1">
    <table class="t" style="border-collapse:collapse;width:100%">
      <thead><tr style="position:sticky;top:0;z-index:2;background:#111">{ths}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>"""


def _build_sector_panel(sector_name, tickers, quotes, accent_color):
    items = []
    total_monto = 0
    total_avg21 = 0
    for t in tickers:
        q = quotes.get(t, {})
        monto = q.get("monto", 0) or 0
        items.append((t, q, monto))
        total_monto += monto
        total_avg21 += q.get("avg_monto_21") or 0
    items.sort(key=lambda x: x[2], reverse=True)

    rows = ""
    for t, q, monto in items:
        p         = q.get("price")
        chg       = q.get("change_pct", 0)
        avg21     = q.get("avg_monto_21")
        ratio     = q.get("monto_ratio")
        p_s       = _price_fmt(p) if p else "—"
        m_s       = _vol_fmt(monto)
        avg_s     = _vol_fmt(avg21) if avg21 else "—"
        # Resalta el monto de hoy si opera muy por encima de su propio promedio 21d
        monto_color = "#00ff41" if (ratio is not None and ratio >= 1.5) else "#999"
        rows += (
            f'<tr><td>{t}</td><td style="color:#ffcc00">{p_s}</td>'
            f'<td>{_pct_html(chg)}</td>'
            f'<td style="color:{monto_color};font-weight:{"bold" if monto_color=="#00ff41" else "normal"}">{m_s}</td>'
            f'<td style="color:#666">{avg_s}</td></tr>'
        )

    count = len(tickers)
    vol_s = _vol_fmt(total_monto)
    avg_total_s = _vol_fmt(total_avg21) if total_avg21 else "—"
    title = f"{sector_name} · {count} · MONTO {vol_s} · PROM {avg_total_s}"
    return _panel_html(title, ["TICKER", "PRECIO", "% DIA", "MONTO", "PROM 21D"], rows, accent_color)


# ═══════════════════════════════════════════════════════════════════════════════
#  HEATMAP — Plotly Treemap
# ═══════════════════════════════════════════════════════════════════════════════

def _build_heatmap(quotes):
    import math

    labels = []
    parents = []
    values = []
    colors = []
    text_lines = []
    hover_texts = []

    sector_data = {}
    all_leaf_changes = []

    for sector_name, sector_info in SECTORS.items():
        children = []
        sector_monto = 0
        sector_chg_w = 0
        for t in sector_info["tickers"]:
            q = quotes.get(t, {})
            monto = q.get("monto", 0) or 0
            chg = q.get("change_pct", 0) or 0
            price = q.get("price")
            if monto > 0 and price is not None:
                children.append((t, price, chg, monto))
                sector_monto += monto
                sector_chg_w += chg * monto
                all_leaf_changes.append(chg)
        if sector_monto > 0:
            avg_chg = sector_chg_w / sector_monto
            sector_data[sector_name] = {
                "children": children,
                "total_monto": sector_monto,
                "avg_chg": avg_chg,
                "color": sector_info["color"],
            }

    if not sector_data:
        return None

    if all_leaf_changes:
        actual_max = max(abs(c) for c in all_leaf_changes)
        max_abs = max(2.0, min(actual_max, 15.0))
    else:
        max_abs = 5.0

    def _compress(v):
        return math.sqrt(max(v, 0))

    sector_compressed_vals = {}
    for sector_name, sdata in sector_data.items():
        sector_compressed_vals[sector_name] = sum(_compress(m) for _, _, _, m in sdata["children"])

    root_val = sum(sector_compressed_vals.values())
    total_market_monto = sum(s["total_monto"] for s in sector_data.values())

    labels.append("EQUITY ARG")
    parents.append("")
    values.append(root_val)
    colors.append(0)
    text_lines.append("")
    hover_texts.append(f"Monto total: {_vol_fmt(total_market_monto)}")

    for sector_name, sdata in sector_data.items():
        labels.append(sector_name)
        parents.append("EQUITY ARG")
        values.append(sector_compressed_vals[sector_name])
        colors.append(sdata["avg_chg"])
        text_lines.append(f"<b>{sector_name}</b><br>{sdata['avg_chg']:+.2f}%")
        hover_texts.append(
            f"<b>{sector_name}</b><br>"
            f"Variación promedio: {sdata['avg_chg']:+.2f}%<br>"
            f"Monto: {_vol_fmt(sdata['total_monto'])}<br>"
            f"Empresas: {len(sdata['children'])}"
        )

        for t, price, chg, monto in sdata["children"]:
            p_str = f"${price:,.0f}" if price >= 100 else f"${price:,.2f}"
            labels.append(t)
            parents.append(sector_name)
            values.append(_compress(monto))
            colors.append(chg)
            text_lines.append(f"<b>{t}</b><br>{chg:+.2f}%")
            hover_texts.append(
                f"<b>{t}</b><br>"
                f"Sector: {sector_name}<br>"
                f"Precio: {p_str}<br>"
                f"Variación: {chg:+.2f}%<br>"
                f"Monto: {_vol_fmt(monto)}"
            )

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        marker=dict(
            colors=colors,
            colorscale=[
                [0.0,  "#8b0000"],
                [0.15, "#cc2222"],
                [0.35, "#551515"],
                [0.5,  "#222222"],
                [0.65, "#155515"],
                [0.85, "#22cc22"],
                [1.0,  "#006400"],
            ],
            cmid=0,
            cmin=-max_abs,
            cmax=max_abs,
            line=dict(color="#000", width=2),
            cornerradius=3,
            colorbar=dict(
                title=dict(text="% DIA", font=dict(size=9, color="#ff6600", family="Courier New")),
                tickfont=dict(size=8, color="#ccc", family="Courier New"),
                ticksuffix="%",
                bgcolor="rgba(0,0,0,0)",
                bordercolor="#333",
                borderwidth=1,
                len=0.5,
                thickness=12,
                x=1.01,
                tickvals=[-max_abs, -max_abs/2, 0, max_abs/2, max_abs],
                ticktext=[
                    f"{-max_abs:.1f}%",
                    f"{-max_abs/2:.1f}%",
                    "0%",
                    f"+{max_abs/2:.1f}%",
                    f"+{max_abs:.1f}%",
                ],
            ),
        ),
        text=text_lines,
        textinfo="text",
        hovertext=hover_texts,
        hoverinfo="text",
        textfont=dict(family="Courier New", size=12, color="#fff"),
        tiling=dict(packing="squarify", pad=3),
        pathbar=dict(
            visible=True,
            textfont=dict(family="Courier New", size=10, color="#ff6600"),
            thickness=20,
            edgeshape=">",
            side="top",
        ),
        maxdepth=3,
    ))

    fig.update_layout(
        paper_bgcolor="#000",
        plot_bgcolor="#000",
        font=dict(family="Courier New", size=10, color="#ccc"),
        margin=dict(l=4, r=4, t=35, b=4),
        height=720,
        title=dict(
            text=f"EQUITY ARG · HEATMAP POR SECTOR — TAMAÑO = MONTO OPERADO · COLOR = VARIACIÓN DIA · ESCALA ±{max_abs:.1f}%",
            font=dict(family="Courier New", size=10, color="#ff6600"),
            x=0.01, xanchor="left",
        ),
        hoverlabel=dict(
            bgcolor="#111",
            bordercolor="#ff6600",
            font=dict(family="Courier New", size=10, color="#fff"),
        ),
    )

    return fig


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER
# ═══════════════════════════════════════════════════════════════════════════════

def _market_kpi_html(quotes):
    total_monto = sum((quotes.get(t, {}).get("monto") or 0) for t in ALL_TICKERS)
    total_avg21 = sum((quotes.get(t, {}).get("avg_monto_21") or 0) for t in ALL_TICKERS)
    ratio = (total_monto / total_avg21) if total_avg21 else None

    ratio_color = "#00ff41" if (ratio is not None and ratio >= 1.2) else (
                  "#ff3b3b" if (ratio is not None and ratio <= 0.8) else "#ccc")
    ratio_s = f"{ratio:.2f}x" if ratio is not None else "—"

    def _kpi(label, value, color="#fff"):
        return (
            '<div style="border:1px solid #333;background:#000;padding:6px 14px;flex:1">'
            f'<div style="color:#666;font-size:9px;letter-spacing:2px;text-transform:uppercase">{label}</div>'
            f'<div style="color:{color};font-size:18px;font-weight:bold;font-family:\'Courier New\',monospace">{value}</div>'
            '</div>'
        )

    return (
        '<div style="display:flex;gap:4px;margin-bottom:6px">'
        + _kpi("MONTO TOTAL HOY", _vol_fmt(total_monto), "#ffcc00")
        + _kpi("PROMEDIO 21D", _vol_fmt(total_avg21), "#999")
        + _kpi("RATIO HOY/PROM", ratio_s, ratio_color)
        + '</div>'
    )


def _ticker_sector_map():
    m = {}
    for sector_name, info in SECTORS.items():
        for t in info["tickers"]:
            m[t] = sector_name
    return m


def _fmt_ratio_x(v):
    return f"{v:.2f}x", "#00ff41", True


def _fmt_pct_signed(v):
    color = "#00ff41" if v >= 0 else "#ff3b3b"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%", color, True


def _radar_table(title, rows, value_label, value_fmt=_fmt_ratio_x):
    if not rows:
        return f'''<div style="border:1px solid #333;background:#000;padding:10px">
  <div style="color:#ff6600;font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px">{title}</div>
  <div style="color:#555;font-size:12px">Sin señales por encima del umbral hoy.</div>
</div>'''
    trs = ""
    for t, sector, price, chg, value in rows:
        p_s = _price_fmt(price) if price else "—"
        v_s, v_color, v_bold = value_fmt(value)
        weight = "bold" if v_bold else "normal"
        trs += (
            f'<tr><td>{t}</td><td style="color:#999;font-size:11px">{sector}</td>'
            f'<td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td>'
            f'<td style="color:{v_color};font-weight:{weight}">{v_s}</td></tr>'
        )
    return f'''<div style="border:1px solid #333;background:#000">
  <div style="background:#111;color:#ff6600;font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;padding:4px 8px;border-bottom:1px solid #ff6600">{title}</div>
  <table class="t" style="border-collapse:collapse;width:100%">
    <thead><tr><th>TICKER</th><th>SECTOR</th><th>PRECIO</th><th>% DIA</th><th>{value_label}</th></tr></thead>
    <tbody>{trs}</tbody>
  </table>
</div>'''


def _radar_table_simple(title, rows):
    """Igual que _radar_table pero sin columna de valor extra (para Movers del Día,
    donde el valor que ordena ya ES el % DIA — mostrarlo dos veces era redundante)."""
    if not rows:
        return f'''<div style="border:1px solid #333;background:#000;padding:10px">
  <div style="color:#ff6600;font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px">{title}</div>
  <div style="color:#555;font-size:12px">Sin señales por encima del umbral hoy.</div>
</div>'''
    trs = ""
    for t, sector, price, chg, _value in rows:
        p_s = _price_fmt(price) if price else "—"
        trs += (
            f'<tr><td>{t}</td><td style="color:#999;font-size:11px">{sector}</td>'
            f'<td style="color:#ffcc00">{p_s}</td><td>{_pct_html(chg)}</td></tr>'
        )
    return f'''<div style="border:1px solid #333;background:#000">
  <div style="background:#111;color:#ff6600;font-size:11px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;padding:4px 8px;border-bottom:1px solid #ff6600">{title}</div>
  <table class="t" style="border-collapse:collapse;width:100%">
    <thead><tr><th>TICKER</th><th>SECTOR</th><th>PRECIO</th><th>% DIA</th></tr></thead>
    <tbody>{trs}</tbody>
  </table>
</div>'''


def _radar_row(html_left, html_right):
    """Grid HTML puro para dos tablas lado a lado — mismo patrón que el grid de
    SECTORES. No usa st.columns(): evita por completo el auto-stretch de altura
    que Streamlit aplica a sus columnas nativas."""
    return (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:start">'
        f'<div>{html_left}</div><div>{html_right}</div>'
        '</div>'
    )


def _radar_mini_header(title):
    return (
        f'<div style="color:#ff6600;font-size:11px;font-weight:bold;letter-spacing:2px;'
        f'text-transform:uppercase;border-bottom:1px solid #333;padding-bottom:4px;'
        f'margin:14px 0 6px 0">{title}</div>'
    )


def _radar_section(title):
    st.markdown(
        f'<div style="color:#ff6600;font-size:12px;font-weight:bold;letter-spacing:2px;'
        f'text-transform:uppercase;border-bottom:1px solid #333;padding-bottom:4px;'
        f'margin:18px 0 8px 0">{title}</div>',
        unsafe_allow_html=True,
    )


def _render_radar(quotes):
    sector_map = _ticker_sector_map()

    # Piso de liquidez: por debajo de esto, cualquier ratio o % es más ruido de
    # papel ilíquido que señal real. Se aplica a todas las categorías del radar.
    MIN_MONTO_FLOOR = 3_000_000

    spikes, trends = [], []
    mover_pool = []

    for t in ALL_TICKERS:
        q = quotes.get(t, {})
        price  = q.get("price")
        chg    = q.get("change_pct", 0)
        avg21  = q.get("avg_monto_21") or 0
        sector = sector_map.get(t, "—")

        liquid = avg21 >= MIN_MONTO_FLOOR
        if not liquid or price is None:
            continue

        mr = q.get("monto_ratio")
        tr = q.get("trend_ratio")
        if mr is not None and mr >= 1.5:
            spikes.append((t, sector, price, chg, mr))
        if tr is not None and tr >= 1.15:
            trends.append((t, sector, price, chg, tr))

        mover_pool.append((t, sector, price, chg, chg))

    spikes.sort(key=lambda x: x[4], reverse=True)
    trends.sort(key=lambda x: x[4], reverse=True)
    movers_up   = sorted(mover_pool, key=lambda x: x[4], reverse=True)[:5]
    movers_down = sorted(mover_pool, key=lambda x: x[4])[:5]

    # ── MOVERS DEL DÍA ──
    left_movers = _radar_mini_header("MOVERS DEL DÍA") + _radar_table_simple("TOP 5 SUBEN HOY", movers_up)
    right_movers = _radar_mini_header("MOVERS DEL DÍA") + _radar_table_simple("TOP 5 BAJAN HOY", movers_down)
    st.markdown(_radar_row(left_movers, right_movers), unsafe_allow_html=True)

    # ── Selector de período — va pegado arriba de Performance, que es a lo único
    #    que aplica. Necesita interactividad real de Streamlit, por eso está
    #    aparte de los bloques de grid HTML. ──
    period_labels = {"1S": "1 SEMANA", "1M": "1 MES", "3M": "3 MESES", "YTD": "YTD", "12M": "12 MESES"}
    period_keys = list(period_labels.keys())

    if "radar_period" not in st.session_state:
        st.session_state.radar_period = "YTD"

    st.markdown(_radar_mini_header("PERFORMANCE"), unsafe_allow_html=True)
    with st.container(key="radar_period_buttons"):
        pcols = st.columns(len(period_keys))
        for i, pk in enumerate(period_keys):
            with pcols[i]:
                active = st.session_state.radar_period == pk
                if st.button(
                    period_labels[pk], key=f"radar_btn_{pk}",
                    type="primary" if active else "secondary",
                ):
                    st.session_state.radar_period = pk

    period = st.session_state.radar_period

    perf_pool = []
    for t in ALL_TICKERS:
        q = quotes.get(t, {})
        price = q.get("price")
        chg   = q.get("change_pct", 0)
        avg21 = q.get("avg_monto_21") or 0
        ret   = q.get("returns", {}).get(period)
        if price is None or avg21 < MIN_MONTO_FLOOR or ret is None:
            continue
        perf_pool.append((t, sector_map.get(t, "—"), price, chg, ret))

    perf_best  = sorted(perf_pool, key=lambda x: x[4], reverse=True)[:5]
    perf_worst = sorted(perf_pool, key=lambda x: x[4])[:5]

    left_perf = _radar_table(f"TOP 5 MEJORES · {period_labels[period]}", perf_best, period, value_fmt=_fmt_pct_signed)
    right_perf = _radar_table(f"TOP 5 PEORES · {period_labels[period]}", perf_worst, period, value_fmt=_fmt_pct_signed)
    st.markdown(_radar_row(left_perf, right_perf), unsafe_allow_html=True)

    # ── FLUJOS DE VOLUMEN ──
    left_flujos = _radar_mini_header("FLUJOS DE VOLUMEN") + _radar_table("VOLUMEN INUSUAL", spikes[:15], "HOY/PROM")
    right_flujos = _radar_mini_header("FLUJOS DE VOLUMEN") + _radar_table("ACUMULACIÓN DE VOLUMEN", trends[:15], "5D/16D")
    st.markdown(_radar_row(left_flujos, right_flujos), unsafe_allow_html=True)


def render():
    subtabs = st.tabs(["SECTORES", "HEATMAP", "RADAR"])

    with st.spinner(""):
        quotes = _fetch_arg_equity(_radar_cache_bucket())

    with subtabs[0]:
        st.markdown(_market_kpi_html(quotes), unsafe_allow_html=True)

        sector_list = list(SECTORS.items())

        panels = []
        for sector_name, sector_info in sector_list:
            p = _build_sector_panel(
                sector_name,
                sector_info["tickers"],
                quotes,
                sector_info["color"],
            )
            panels.append(p)

        while len(panels) < 9:
            panels.append(_panel_html("—", [], "", "#333"))

        grid_html = f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;grid-template-rows:auto auto auto;gap:4px;margin-top:4px">
          <div>{panels[0]}</div><div>{panels[1]}</div><div>{panels[2]}</div>
          <div>{panels[3]}</div><div>{panels[4]}</div><div>{panels[5]}</div>
          <div>{panels[6]}</div><div>{panels[7]}</div><div>{panels[8]}</div>
        </div>"""

        st.markdown(grid_html, unsafe_allow_html=True)

    with subtabs[1]:
        fig = _build_heatmap(quotes)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<p style="color:#555;font-size:10px">Sin datos para heatmap</p>', unsafe_allow_html=True)

    with subtabs[2]:
        _render_radar(quotes)
