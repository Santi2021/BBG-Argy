"""
tabs/calendar.py — Economic Calendar
Investing.com scraper · US + ARG · BBG estilo
"""

import streamlit as st

# ── Paleta (heredada del CSS global de app.py) ─────────────────────────────────
ORANGE = "#ff6600"
GOLD   = "#ffcc00"
GREEN  = "#00ff41"
RED    = "#ff3b3b"
CYAN   = "#00d4ff"
MUTED  = "#555555"
TEXT   = "#cccccc"
AMBER  = "#f59e0b"
VIOLET = "#a78bfa"
BLUE   = "#60a5fa"
BG     = "#000000"

IMP_COLOR = {3: RED,   2: AMBER,  1: "#555555"}
IMP_LABEL = {3: "●●●", 2: "●●○",  1: "●○○"}

CAT_COLORS_US = {
    "LABOR":     CYAN,
    "INFLATION": RED,
    "GROWTH":    GREEN,
    "HOUSING":   AMBER,
    "FED":       ORANGE,
    "RATES":     VIOLET,
    "OTHER":     MUTED,
}
CAT_COLORS_ARG = {
    "INFLACIÓN": RED,
    "ACTIVIDAD": GREEN,
    "EMPLEO":    CYAN,
    "COMERCIO":  BLUE,
    "FISCAL":    GOLD,
    "MONETARIO": ORANGE,
    "OTHER":     MUTED,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDERER
# ═══════════════════════════════════════════════════════════════════════════════

def _render_calendar_html(records: list, market: str) -> str:
    import re, pandas as pd

    if not records:
        return f'<p style="color:{MUTED};font-family:\'Courier New\',monospace;padding:20px;font-size:12px">Sin eventos para esta ventana (ayer / hoy / mañana).</p>'

    T          = "font-family:'Courier New',monospace;"
    cat_colors = CAT_COLORS_US if market == "US" else CAT_COLORS_ARG
    mkt_label  = "🇺🇸  US ECONOMIC CALENDAR" if market == "US" else "🇦🇷  ARGENTINA ECONOMIC CALENDAR"

    # Rango de fechas para el sub-header
    dates = sorted(set(r.get("date", "") for r in records if r.get("date")))
    date_range = ""
    if dates:
        try:
            d0 = pd.Timestamp(dates[0]).strftime("%d %b")
            d1 = pd.Timestamp(dates[-1]).strftime("%d %b %Y")
            date_range = f"{d0} – {d1}"
        except Exception:
            pass

    TH = (
        f"padding:4px 10px;{T}font-size:10px;color:#666;"
        "background:#0a0a0a;border-bottom:1px solid #1a1a1a;"
        "border-right:1px solid #111;text-align:left;"
        "letter-spacing:1px;white-space:nowrap;"
    )
    TD_BASE = (
        f"padding:5px 10px;{T}font-size:12px;"
        "border-bottom:1px solid #0d0d0d;"
        "border-right:1px solid #0a0a0a;"
        "vertical-align:middle;white-space:nowrap;"
    )
    headers = ["HORA ET", "IMP", "CAT", "EVENTO", "PERÍODO", "FORECAST", "PREVIO"]

    css = f"""
    <style>
      .eco-wrap    {{ background:{BG}; padding:8px 4px; }}
      .eco-hdr     {{ color:{ORANGE}; font-size:12px; font-weight:bold; letter-spacing:3px;
                     text-transform:uppercase; border-bottom:2px solid {ORANGE};
                     padding-bottom:6px; margin-bottom:16px; {T}
                     display:flex; justify-content:space-between; align-items:flex-end; }}
      .eco-range   {{ color:#999; font-size:11px; letter-spacing:1px; }}
      .eco-day-blk {{ margin-bottom:20px; }}
      .eco-day-hdr {{ color:{GOLD}; font-size:11px; font-weight:bold; letter-spacing:2px;
                     text-transform:uppercase; border-bottom:1px solid #222;
                     padding:8px 0 4px 0; margin-bottom:0; {T}
                     display:flex; justify-content:space-between; align-items:center; }}
      .eco-day-cnt {{ color:#888; font-size:10px; font-weight:normal; }}
      .eco-tbl     {{ border-collapse:collapse; width:100%; }}
      .eco-r3      {{ background:#0d0000; }}
      .eco-r2      {{ background:#080808; }}
      .eco-r1      {{ background:{BG}; }}
      .eco-r3:hover,.eco-r2:hover,.eco-r1:hover {{ background:#111; }}
      .eco-legend  {{ display:flex; gap:16px; margin-top:12px; padding-top:8px;
                     border-top:1px solid #1a1a1a; flex-wrap:wrap; }}
      .eco-leg-itm {{ font-size:10px; {T} color:#888; }}
    </style>
    """

    html = css + '<div class="eco-wrap">'
    html += (
        f'<div class="eco-hdr">'
        f'<span>{mkt_label}</span>'
        f'<span class="eco-range">{date_range}</span>'
        f'</div>'
    )

    # Agrupar por fecha
    from collections import defaultdict
    by_date = defaultdict(list)
    for r in records:
        by_date[r.get("date", "")].append(r)

    for date in sorted(by_date.keys()):
        day_records = by_date[date]

        # Ordenar: hora ASC, importancia DESC
        def sort_key(r):
            t = r.get("time_et", "00:00") or "00:00"
            t = t.replace("All Day", "00:00")
            try:
                h, m = t.split(":")
                return (int(h) * 60 + int(m), -int(r.get("imp_final", 1) or 1))
            except Exception:
                return (0, 0)
        day_records = sorted(day_records, key=sort_key)

        # Header del día
        try:
            dt        = pd.Timestamp(date)
            today_ts  = pd.Timestamp.today().normalize()
            if dt.normalize() == today_ts:
                day_tag = "HOY"
            elif dt.normalize() == today_ts - pd.Timedelta(days=1):
                day_tag = "AYER"
            elif dt.normalize() == today_ts + pd.Timedelta(days=1):
                day_tag = "MAÑANA"
            else:
                day_tag = ""
            day_label = dt.strftime("%A").upper() + "  ·  " + dt.strftime("%d %b %Y").upper()
            if day_tag:
                day_label = f"{day_tag}  ·  {day_label}"
        except Exception:
            day_label = str(date).upper()

        n_high    = sum(1 for r in day_records if int(r.get("imp_final", 1) or 1) == 3)
        count_str = f"{n_high} HIGH · {len(day_records)} total" if n_high else f"{len(day_records)} eventos"

        html += '<div class="eco-day-blk">'
        html += (
            f'<div class="eco-day-hdr">'
            f'<span>{day_label}</span>'
            f'<span class="eco-day-cnt">{count_str}</span>'
            f'</div>'
        )
        html += '<table class="eco-tbl">'
        html += "<thead><tr>" + "".join(f'<th style="{TH}">{h}</th>' for h in headers) + "</tr></thead>"
        html += "<tbody>"

        for rec in day_records:
            imp       = max(1, min(3, int(rec.get("imp_final", 1) or 1)))
            row_cls   = f"eco-r{imp}"
            imp_color = IMP_COLOR[imp]
            imp_dots  = IMP_LABEL[imp]

            cat       = rec.get("category", "OTHER") or "OTHER"
            cat_color = cat_colors.get(cat, MUTED)
            cat_short = cat[:7]

            time_et    = rec.get("time_et", "") or "All Day"
            event_name = rec.get("event", "")
            period     = rec.get("period", "") or "—"
            forecast   = rec.get("forecast", "") or "—"
            previous   = rec.get("previous", "") or "—"
            actual     = rec.get("actual", "") or ""

            # Celda forecast/actual
            if actual and actual not in ("", "—", " "):
                try:
                    a_n = float(re.sub(r"[^\d.\-]", "", actual))
                    f_n = float(re.sub(r"[^\d.\-]", "", forecast))
                    act_color = GREEN if a_n >= f_n else RED
                except Exception:
                    act_color = GOLD
                fc_cell = f'<span style="color:{act_color};font-weight:bold">{actual} ✓</span>'
            else:
                fc_cell = f'<span style="color:{MUTED}">{forecast}</span>'

            html += f'<tr class="{row_cls}">'
            html += f'<td style="{TD_BASE}color:#999;font-size:11px">{time_et}</td>'
            html += f'<td style="{TD_BASE}color:{imp_color};font-weight:bold;text-align:center">{imp_dots}</td>'
            html += f'<td style="{TD_BASE}color:{cat_color};font-size:10px;font-weight:bold;letter-spacing:1px">{cat_short}</td>'
            html += f'<td style="{TD_BASE}color:{TEXT};max-width:360px;overflow:hidden;text-overflow:ellipsis">{event_name}</td>'
            html += f'<td style="{TD_BASE}color:{CYAN};font-size:11px">{period}</td>'
            html += f'<td style="{TD_BASE}text-align:right">{fc_cell}</td>'
            html += f'<td style="{TD_BASE}color:#999;text-align:right">{previous}</td>'
            html += "</tr>"

        html += "</tbody></table></div>"

    # Leyenda
    cats_seen = list(dict.fromkeys(r.get("category", "OTHER") for r in records))
    legend    = ""
    for cat in cats_seen:
        c      = cat_colors.get(cat, MUTED)
        legend += f'<span class="eco-leg-itm"><span style="color:{c}">■</span> {cat}</span>'

    html += f"""
    <div class="eco-legend">
      <span class="eco-leg-itm"><span style="color:{RED}">●●●</span>&nbsp;HIGH</span>
      <span class="eco-leg-itm"><span style="color:{AMBER}">●●○</span>&nbsp;MED</span>
      <span class="eco-leg-itm"><span style="color:#555">●○○</span>&nbsp;LOW</span>
      <span style="flex:1"></span>
      {legend}
    </div>
    """
    html += "</div>"
    return html


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL
#  Toggle via st.session_state — JS no ejecuta dentro de st.markdown en Streamlit
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    from data import get_economic_calendar  # lazy — evita error si data.py viejo

    # ── Estado del toggle ─────────────────────────────────────────────────────
    if "cal_market" not in st.session_state:
        st.session_state["cal_market"] = "US"

    # ── Cargar datos ──────────────────────────────────────────────────────────
    with st.spinner("Cargando calendario económico..."):
        us_data  = get_economic_calendar("US")
        arg_data = get_economic_calendar("ARG")

    us_err  = isinstance(us_data,  dict) and "error" in us_data
    arg_err = isinstance(arg_data, dict) and "error" in arg_data
    us_records  = us_data  if isinstance(us_data,  list) else []
    arg_records = arg_data if isinstance(arg_data, list) else []

    # ── Toggle bar ────────────────────────────────────────────────────────────
    active  = st.session_state["cal_market"]
    n_us    = len(us_records)
    n_arg   = len(arg_records)

    # CSS que sobreescribe el estilo global de botones solo para esta toggle bar
    us_active  = active == "US"
    arg_active = active == "ARG"

    def _btn_css(is_active):
        bg    = "#0a0000" if is_active else "#000"
        color = ORANGE    if is_active else "#777"
        bb    = f"2px solid {ORANGE}" if is_active else "2px solid transparent"
        return (
            f"background:{bg} !important;"
            f"color:{color} !important;"
            f"border-left:none !important;"
            f"border-right:1px solid #1a1a1a !important;"
            f"border-top:none !important;"
            f"border-bottom:{bb} !important;"
            f"border-radius:0 !important;"
            f"font-family:'Courier New',monospace !important;"
            f"font-size:11px !important;"
            f"font-weight:bold !important;"
            f"letter-spacing:2px !important;"
            f"padding:0 18px !important;"
            f"height:34px !important;"
            f"width:100% !important;"
        )

    st.markdown(f"""
    <style>
      div[data-testid="column"]:nth-child(1) .stButton > button {{
        {_btn_css(us_active)}
      }}
      div[data-testid="column"]:nth-child(2) .stButton > button {{
        {_btn_css(arg_active)}
      }}
      div[data-testid="column"]:nth-child(1) .stButton > button:hover,
      div[data-testid="column"]:nth-child(2) .stButton > button:hover {{
        opacity: 0.85 !important;
      }}
    </style>
    <div style="display:flex;align-items:center;background:#000;
                border-bottom:1px solid #222;padding-left:4px;margin-bottom:2px;">
      <span style="color:#555;font-size:10px;letter-spacing:2px;
                   font-family:'Courier New',monospace;padding:0 12px 0 4px;
                   border-right:1px solid #1a1a1a;margin-right:0;">
        ECO CAL
      </span>
    </div>
    """, unsafe_allow_html=True)

    col_us, col_arg, col_rest = st.columns([1, 1, 10])
    with col_us:
        lbl_us = f"🇺🇸  US  · {n_us} EVT" if us_active else f"🇺🇸  US  · {n_us}"
        if st.button(lbl_us, key="cal_btn_us", use_container_width=True):
            st.session_state["cal_market"] = "US"
            st.rerun()
    with col_arg:
        lbl_arg = f"🇦🇷  ARG  · {n_arg} EVT" if arg_active else f"🇦🇷  ARG  · {n_arg}"
        if st.button(lbl_arg, key="cal_btn_arg", use_container_width=True):
            st.session_state["cal_market"] = "ARG"
            st.rerun()

    # ── Renderizar el calendario activo ───────────────────────────────────────
    records = us_records if active == "US" else arg_records
    market  = active
    st.markdown(_render_calendar_html(records, market), unsafe_allow_html=True)

    # ── Errores no-fatales ────────────────────────────────────────────────────
    if us_err and active == "US":
        st.markdown(
            f'<p style="color:{MUTED};font-family:Courier New;font-size:11px">'
            f'US calendar error: {us_data["error"]}</p>',
            unsafe_allow_html=True
        )
    if arg_err and active == "ARG":
        st.markdown(
            f'<p style="color:{MUTED};font-family:Courier New;font-size:11px">'
            f'ARG calendar error: {arg_data["error"]}</p>',
            unsafe_allow_html=True
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="color:#888;font-size:10px;font-family:Courier New;'
        f'padding:8px 4px;border-top:1px solid #1a1a1a;margin-top:4px;">'
        f'FUENTE: INVESTING.COM · ACTUALIZACIÓN CADA 60 MIN · '
        f'VENTANA: {_week_label()}'
        f'</div>',
        unsafe_allow_html=True
    )


def _week_label() -> str:
    """Ayer · Hoy · Mañana — ventana de 3 días que muestra el calendario."""
    from datetime import datetime, timedelta
    today     = datetime.today()
    yesterday = today - timedelta(days=1)
    tomorrow  = today + timedelta(days=1)
    return (
        f"AYER {yesterday.strftime('%d %b')} · HOY {today.strftime('%d %b')} · "
        f"MAÑANA {tomorrow.strftime('%d %b %Y')}"
    ).upper()
