"""
tabs/calendar.py — Economic Calendar
Investing.com · US + ARG · BBG estilo
"""

import streamlit as st
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
    _ART = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:
    _ART = None

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
#  Hora Argentina — "hoy" consistente sin importar el huso horario del server
# ═══════════════════════════════════════════════════════════════════════════════

def _art_now() -> datetime:
    if _ART is not None:
        return datetime.now(_ART).replace(tzinfo=None)
    return datetime.utcnow() - timedelta(hours=3)


def _art_date_str(offset_days: int = 0) -> str:
    return (_art_now() + timedelta(days=offset_days)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDERER — recibe los eventos de UN solo día ya filtrado
# ═══════════════════════════════════════════════════════════════════════════════

def _render_calendar_html(records: list, market: str) -> str:
    import re, pandas as pd

    if not records:
        return f'<p style="color:{MUTED};font-family:\'Courier New\',monospace;padding:20px;font-size:12px">Sin eventos para este día.</p>'

    T          = "font-family:'Courier New',monospace;"
    cat_colors = CAT_COLORS_US if market == "US" else CAT_COLORS_ARG
    mkt_label  = "🇺🇸  US ECONOMIC CALENDAR" if market == "US" else "🇦🇷  ARGENTINA ECONOMIC CALENDAR"

    dates = sorted(set(r.get("date", "") for r in records if r.get("date")))
    date_range = ""
    if dates:
        try:
            if len(dates) == 1:
                date_range = pd.Timestamp(dates[0]).strftime("%d %b %Y").upper()
            else:
                d0 = pd.Timestamp(dates[0]).strftime("%d %b")
                d1 = pd.Timestamp(dates[-1]).strftime("%d %b %Y")
                date_range = f"{d0} – {d1}".upper()
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
    headers = ["HORA ARG", "IMP", "CAT", "EVENTO", "PERÍODO", "FORECAST", "ACTUAL", "PREVIO"]

    css = f"""
    <style>
      .eco-wrap    {{ background:{BG}; padding:8px 4px; }}
      .eco-hdr     {{ color:{ORANGE}; font-size:12px; font-weight:bold; letter-spacing:3px;
                     text-transform:uppercase; border-bottom:2px solid {ORANGE};
                     padding-bottom:6px; margin-bottom:14px; {T}
                     display:flex; justify-content:space-between; align-items:flex-end; }}
      .eco-range   {{ color:#999; font-size:11px; letter-spacing:1px; }}
      .eco-day-blk {{ margin-bottom:12px; }}
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

    from collections import defaultdict
    by_date = defaultdict(list)
    for r in records:
        by_date[r.get("date", "")].append(r)

    today_str = _art_date_str(0)
    yest_str  = _art_date_str(-1)
    tom_str   = _art_date_str(1)

    for date in sorted(by_date.keys()):
        day_records = by_date[date]

        def sort_key(r):
            t = r.get("time_et", "00:00") or "00:00"
            t = t.replace("All Day", "00:00")
            try:
                h, m = t.split(":")
                return (int(h) * 60 + int(m), -int(r.get("imp_final", 1) or 1))
            except Exception:
                return (0, 0)
        day_records = sorted(day_records, key=sort_key)

        try:
            dt = pd.Timestamp(date)
            if date == today_str:
                day_tag = "HOY"
            elif date == yest_str:
                day_tag = "AYER"
            elif date == tom_str:
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

            if actual and actual not in ("", "—", " "):
                try:
                    a_n = float(re.sub(r"[^\d.\-]", "", actual))
                    f_n = float(re.sub(r"[^\d.\-]", "", forecast))
                    act_color = GREEN if a_n >= f_n else RED
                except Exception:
                    act_color = GOLD
                actual_cell = f'<span style="color:{act_color};font-weight:bold">{actual} ✓</span>'
            else:
                actual_cell = f'<span style="color:{MUTED}">—</span>'

            html += f'<tr class="{row_cls}">'
            html += f'<td style="{TD_BASE}color:#999;font-size:11px">{time_et}</td>'
            html += f'<td style="{TD_BASE}color:{imp_color};font-weight:bold;text-align:center">{imp_dots}</td>'
            html += f'<td style="{TD_BASE}color:{cat_color};font-size:10px;font-weight:bold;letter-spacing:1px">{cat_short}</td>'
            html += f'<td style="{TD_BASE}color:{TEXT};max-width:360px;overflow:hidden;text-overflow:ellipsis">{event_name}</td>'
            html += f'<td style="{TD_BASE}color:{CYAN};font-size:11px">{period}</td>'
            html += f'<td style="{TD_BASE}color:#999;text-align:right">{forecast}</td>'
            html += f'<td style="{TD_BASE}text-align:right">{actual_cell}</td>'
            html += f'<td style="{TD_BASE}color:#999;text-align:right">{previous}</td>'
            html += "</tr>"

        html += "</tbody></table></div>"

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
#  Botoneras — st.segmented_control nativo (pills prolijas, sin CSS casero)
# ═══════════════════════════════════════════════════════════════════════════════

_SEGCTL_CSS = """
<style>
  div[data-testid="stSegmentedControl"] {
    font-family: 'Courier New', monospace !important;
  }
  div[data-testid="stSegmentedControl"] label p {
    font-family: 'Courier New', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1px !important;
  }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    from data import get_economic_calendar

    st.markdown(_SEGCTL_CSS, unsafe_allow_html=True)

    with st.spinner("Cargando calendario económico..."):
        us_data  = get_economic_calendar("US")
        arg_data = get_economic_calendar("ARG")

    us_err  = isinstance(us_data,  dict) and "error" in us_data
    arg_err = isinstance(arg_data, dict) and "error" in arg_data
    us_records  = us_data  if isinstance(us_data,  list) else []
    arg_records = arg_data if isinstance(arg_data, list) else []

    n_us, n_arg = len(us_records), len(arg_records)

    # ── Fila 1: US / ARG ──────────────────────────────────────────────────────
    market_sel = st.segmented_control(
        "Mercado",
        options=["US", "ARG"],
        format_func=lambda v: f"🇺🇸 US · {n_us}" if v == "US" else f"🇦🇷 ARG · {n_arg}",
        default="US",
        key="cal_market",
        label_visibility="collapsed",
    )
    active = market_sel or st.session_state.get("_cal_market_last", "US")
    st.session_state["_cal_market_last"] = active

    records_all = us_records if active == "US" else arg_records

    yest_str, today_str, tom_str = _art_date_str(-1), _art_date_str(0), _art_date_str(1)
    day_dates = {"AYER": yest_str, "HOY": today_str, "MAÑANA": tom_str}

    n_yest  = sum(1 for r in records_all if r.get("date") == yest_str)
    n_today = sum(1 for r in records_all if r.get("date") == today_str)
    n_tom   = sum(1 for r in records_all if r.get("date") == tom_str)
    day_counts = {"AYER": n_yest, "HOY": n_today, "MAÑANA": n_tom}

    # ── Fila 2: AYER / HOY / MAÑANA ────────────────────────────────────────────
    day_sel_raw = st.segmented_control(
        "Día",
        options=["AYER", "HOY", "MAÑANA"],
        format_func=lambda v: f"{v} · {day_counts[v]}",
        default="HOY",
        key="cal_day",
        label_visibility="collapsed",
    )
    day_sel = day_sel_raw or st.session_state.get("_cal_day_last", "HOY")
    st.session_state["_cal_day_last"] = day_sel

    day_target  = day_dates[day_sel]
    day_records = [r for r in records_all if r.get("date") == day_target]
    n_all_imp   = len(day_records)
    n_med_imp   = sum(1 for r in day_records if int(r.get("imp_final", 1) or 1) >= 2)
    n_high_imp  = sum(1 for r in day_records if int(r.get("imp_final", 1) or 1) >= 3)
    imp_counts  = {"TODOS": n_all_imp, "MED+": n_med_imp, "ALTA": n_high_imp}
    imp_dots    = {"TODOS": "●○○", "MED+": "●●○", "ALTA": "●●●"}
    imp_min     = {"TODOS": 1, "MED+": 2, "ALTA": 3}

    # ── Fila 3: filtro de importancia ──────────────────────────────────────────
    imp_sel_raw = st.segmented_control(
        "Importancia",
        options=["TODOS", "MED+", "ALTA"],
        format_func=lambda v: f"{imp_dots[v]} {v} · {imp_counts[v]}",
        default="TODOS",
        key="cal_imp",
        label_visibility="collapsed",
    )
    imp_sel = imp_sel_raw or st.session_state.get("_cal_imp_last", "TODOS")
    st.session_state["_cal_imp_last"] = imp_sel
    min_imp = imp_min[imp_sel]

    # ── Filtrar y renderizar ────────────────────────────────────────────────────
    filtered = [r for r in day_records if int(r.get("imp_final", 1) or 1) >= min_imp]
    st.markdown(_render_calendar_html(filtered, active), unsafe_allow_html=True)

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
    try:
        import pandas as pd
        day_fmt = pd.Timestamp(day_target).strftime("%d %b %Y").upper()
    except Exception:
        day_fmt = day_target
    st.markdown(
        f'<div style="color:#888;font-size:10px;font-family:Courier New;'
        f'padding:8px 4px;border-top:1px solid #1a1a1a;margin-top:4px;">'
        f'FUENTE: INVESTING.COM · ACTUALIZACIÓN CADA 60 MIN · '
        f'VIENDO: {day_sel} · {day_fmt}'
        f'</div>',
        unsafe_allow_html=True
    )
