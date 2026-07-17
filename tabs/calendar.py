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
#  Botoneras — CSS scopeado por container(key=...) en vez de nth-child
# ═══════════════════════════════════════════════════════════════════════════════

def _toggle_btn_css(is_active, accent):
    bg = "#0a0000" if is_active else "#000"
    color = accent if is_active else "#777"
    bb = f"2px solid {accent}" if is_active else "2px solid transparent"
    return (
        f"background:{bg} !important;"
        f"color:{color} !important;"
        f"border-left:none !important;"
        f"border-right:1px solid #1a1a1a !important;"
        f"border-top:none !important;"
        f"border-bottom:{bb} !important;"
        f"border-radius:0 !important;"
        f"font-family:'Courier New',monospace !important;"
        f"font-size:10px !important;"
        f"font-weight:bold !important;"
        f"letter-spacing:1.5px !important;"
        f"padding:0 12px !important;"
        f"height:28px !important;"
        f"width:100% !important;"
    )


def _row_css(container_key, n_cols, is_active_list, accent):
    rules = ""
    for i in range(1, n_cols + 1):
        rules += (
            f'.st-key-{container_key} div[data-testid="column"]:nth-child({i}) .stButton > button {{'
            f'{_toggle_btn_css(is_active_list[i-1], accent)}'
            f'}}\n'
        )
    rules += (
        f'.st-key-{container_key} .stButton > button:hover {{ opacity:0.85 !important; }}\n'
    )
    return f"<style>{rules}</style>"


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    from data import get_economic_calendar

    if "cal_market" not in st.session_state:
        st.session_state["cal_market"] = "US"
    if "cal_day" not in st.session_state:
        st.session_state["cal_day"] = "HOY"
    if "cal_min_imp" not in st.session_state:
        st.session_state["cal_min_imp"] = 1

    with st.spinner("Cargando calendario económico..."):
        us_data  = get_economic_calendar("US")
        arg_data = get_economic_calendar("ARG")

    us_err  = isinstance(us_data,  dict) and "error" in us_data
    arg_err = isinstance(arg_data, dict) and "error" in arg_data
    us_records  = us_data  if isinstance(us_data,  list) else []
    arg_records = arg_data if isinstance(arg_data, list) else []

    active  = st.session_state["cal_market"]
    day_sel = st.session_state["cal_day"]
    min_imp = st.session_state["cal_min_imp"]

    n_us, n_arg = len(us_records), len(arg_records)
    records_all = us_records if active == "US" else arg_records

    yest_str, today_str, tom_str = _art_date_str(-1), _art_date_str(0), _art_date_str(1)
    day_dates = {"AYER": yest_str, "HOY": today_str, "MAÑANA": tom_str}

    n_yest = sum(1 for r in records_all if r.get("date") == yest_str)
    n_today = sum(1 for r in records_all if r.get("date") == today_str)
    n_tom  = sum(1 for r in records_all if r.get("date") == tom_str)

    day_target  = day_dates[day_sel]
    day_records = [r for r in records_all if r.get("date") == day_target]
    n_all_imp  = len(day_records)
    n_med_imp  = sum(1 for r in day_records if int(r.get("imp_final", 1) or 1) >= 2)
    n_high_imp = sum(1 for r in day_records if int(r.get("imp_final", 1) or 1) >= 3)

    # ── Fila 1: US / ARG ──────────────────────────────────────────────────────
    with st.container(key="cal_row_mkt"):
        st.markdown(_row_css("cal_row_mkt", 2, [active == "US", active == "ARG"], ORANGE),
                    unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 8])
        with c1:
            lbl = f"🇺🇸  US · {n_us}"
            if st.button(lbl, key="cal_btn_us", use_container_width=True):
                st.session_state["cal_market"] = "US"
                st.rerun()
        with c2:
            lbl = f"🇦🇷  ARG · {n_arg}"
            if st.button(lbl, key="cal_btn_arg", use_container_width=True):
                st.session_state["cal_market"] = "ARG"
                st.rerun()

    # ── Fila 2: AYER / HOY / MAÑANA ────────────────────────────────────────────
    with st.container(key="cal_row_day"):
        st.markdown(
            _row_css("cal_row_day", 3,
                     [day_sel == "AYER", day_sel == "HOY", day_sel == "MAÑANA"], GOLD),
            unsafe_allow_html=True
        )
        c1, c2, c3, c4 = st.columns([1, 1, 1, 7])
        with c1:
            if st.button(f"AYER · {n_yest}", key="cal_btn_yest", use_container_width=True):
                st.session_state["cal_day"] = "AYER"
                st.rerun()
        with c2:
            if st.button(f"HOY · {n_today}", key="cal_btn_today", use_container_width=True):
                st.session_state["cal_day"] = "HOY"
                st.rerun()
        with c3:
            if st.button(f"MAÑANA · {n_tom}", key="cal_btn_tom", use_container_width=True):
                st.session_state["cal_day"] = "MAÑANA"
                st.rerun()

    # ── Fila 3: filtro de importancia ──────────────────────────────────────────
    with st.container(key="cal_row_imp"):
        st.markdown(
            _row_css("cal_row_imp", 3,
                     [min_imp == 1, min_imp == 2, min_imp == 3], CYAN),
            unsafe_allow_html=True
        )
        c1, c2, c3, c4 = st.columns([1, 1, 1, 7])
        with c1:
            if st.button(f"●○○ TODOS · {n_all_imp}", key="cal_btn_imp1", use_container_width=True):
                st.session_state["cal_min_imp"] = 1
                st.rerun()
        with c2:
            if st.button(f"●●○ MED+ · {n_med_imp}", key="cal_btn_imp2", use_container_width=True):
                st.session_state["cal_min_imp"] = 2
                st.rerun()
        with c3:
            if st.button(f"●●● ALTA · {n_high_imp}", key="cal_btn_imp3", use_container_width=True):
                st.session_state["cal_min_imp"] = 3
                st.rerun()

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
