"""
tabs/calendar.py — Economic Calendar
Investing.com scraper · US + ARG · BBG estilo
"""

import streamlit as st
from data import get_economic_calendar

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
        return f'<p style="color:{MUTED};font-family:\'Courier New\',monospace;padding:20px;font-size:10px">Sin eventos para esta semana.</p>'

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
        f"padding:3px 10px;{T}font-size:8px;color:#444;"
        "background:#0a0a0a;border-bottom:1px solid #1a1a1a;"
        "border-right:1px solid #111;text-align:left;"
        "letter-spacing:1px;white-space:nowrap;"
    )
    TD_BASE = (
        f"padding:4px 10px;{T}font-size:10px;"
        "border-bottom:1px solid #0d0d0d;"
        "border-right:1px solid #0a0a0a;"
        "vertical-align:middle;white-space:nowrap;"
    )
    headers = ["HORA ET", "IMP", "CAT", "EVENTO", "PERÍODO", "FORECAST", "PREVIO"]

    css = f"""
    <style>
      .eco-wrap    {{ background:{BG}; padding:8px 4px; }}
      .eco-hdr     {{ color:{ORANGE}; font-size:10px; font-weight:bold; letter-spacing:3px;
                     text-transform:uppercase; border-bottom:2px solid {ORANGE};
                     padding-bottom:5px; margin-bottom:14px; {T}
                     display:flex; justify-content:space-between; align-items:flex-end; }}
      .eco-range   {{ color:{MUTED}; font-size:9px; letter-spacing:1px; }}
      .eco-day-blk {{ margin-bottom:18px; }}
      .eco-day-hdr {{ color:{GOLD}; font-size:9px; font-weight:bold; letter-spacing:2px;
                     text-transform:uppercase; border-bottom:1px solid #222;
                     padding:7px 0 3px 0; margin-bottom:0; {T}
                     display:flex; justify-content:space-between; align-items:center; }}
      .eco-day-cnt {{ color:{MUTED}; font-size:8px; font-weight:normal; }}
      .eco-tbl     {{ border-collapse:collapse; width:100%; }}
      .eco-r3      {{ background:#0d0000; }}
      .eco-r2      {{ background:#080808; }}
      .eco-r1      {{ background:{BG}; }}
      .eco-r3:hover,.eco-r2:hover,.eco-r1:hover {{ background:#111; }}
      .eco-legend  {{ display:flex; gap:14px; margin-top:10px; padding-top:7px;
                     border-top:1px solid #1a1a1a; flex-wrap:wrap; }}
      .eco-leg-itm {{ font-size:8px; {T} color:{MUTED}; }}
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
            day_label = dt.strftime("%A").upper() + "  ·  " + dt.strftime("%d %b %Y").upper()
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
            html += f'<td style="{TD_BASE}color:{MUTED};font-size:9px">{time_et}</td>'
            html += f'<td style="{TD_BASE}color:{imp_color};font-weight:bold;text-align:center">{imp_dots}</td>'
            html += f'<td style="{TD_BASE}color:{cat_color};font-size:8px;font-weight:bold;letter-spacing:1px">{cat_short}</td>'
            html += f'<td style="{TD_BASE}color:{TEXT};max-width:360px;overflow:hidden;text-overflow:ellipsis">{event_name}</td>'
            html += f'<td style="{TD_BASE}color:{CYAN};font-size:9px">{period}</td>'
            html += f'<td style="{TD_BASE}text-align:right">{fc_cell}</td>'
            html += f'<td style="{TD_BASE}color:{MUTED};text-align:right">{previous}</td>'
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
#  TOGGLE BAR HTML (puro CSS/JS, sin ipywidgets)
# ═══════════════════════════════════════════════════════════════════════════════

def _toggle_bar(n_us: int, n_arg: int) -> str:
    T = "font-family:'Courier New',monospace;"
    return f"""
    <style>
      .cal-bar        {{ display:flex; align-items:center; background:#000;
                        border-bottom:1px solid #222; margin-bottom:0; }}
      .cal-lbl        {{ flex-shrink:0; padding:0 14px; color:#2a2a2a; font-size:8px;
                        letter-spacing:2px; text-transform:uppercase; {T}
                        height:30px; display:flex; align-items:center;
                        border-right:1px solid #1a1a1a; }}
      .cal-btn        {{ position:relative; background:#000; border:none;
                        border-right:1px solid #1a1a1a; color:#444; {T}
                        font-size:9px; font-weight:bold; letter-spacing:3px;
                        text-transform:uppercase; padding:0 18px; height:30px;
                        cursor:pointer; transition:color .15s,background .15s; outline:none; }}
      .cal-btn::after {{ content:''; position:absolute; bottom:0; left:0; right:0;
                        height:2px; background:transparent; transition:background .15s; }}
      .cal-btn:hover  {{ color:#888; background:#0a0a0a; }}
      .cal-btn.cal-active           {{ color:{ORANGE}; background:#0a0000; }}
      .cal-btn.cal-active::after    {{ background:{ORANGE}; }}
      .cal-badge      {{ display:inline-block; margin-left:7px; background:#1a1a1a;
                        color:#444; font-size:7px; padding:1px 5px; border-radius:2px;
                        letter-spacing:0; transition:background .15s,color .15s; }}
      .cal-btn.cal-active .cal-badge {{ background:#2a1000; color:{ORANGE}; }}
      .cal-spacer     {{ flex:1; }}
      .cal-src        {{ color:#2a2a2a; font-size:8px; letter-spacing:1px;
                        padding:0 12px; {T} }}
    </style>
    <div class="cal-bar">
      <span class="cal-lbl">ECO CAL</span>
      <button class="cal-btn cal-active" id="cal-btn-us"
              onclick="calSwitch('US')">
        🇺🇸&nbsp;US<span class="cal-badge" id="cal-bdg-us">{n_us} EVT</span>
      </button>
      <button class="cal-btn" id="cal-btn-arg"
              onclick="calSwitch('ARG')">
        🇦🇷&nbsp;ARG<span class="cal-badge" id="cal-bdg-arg">{n_arg} EVT</span>
      </button>
      <div class="cal-spacer"></div>
      <span class="cal-src">INVESTING.COM</span>
    </div>
    <script>
      var _calCurrent = 'US';
      function calSwitch(mkt) {{
        if (mkt === _calCurrent) return;
        _calCurrent = mkt;
        ['US','ARG'].forEach(function(m) {{
          var btn  = document.getElementById('cal-btn-' + m.toLowerCase());
          var pane = document.getElementById('cal-pane-' + m.toLowerCase());
          if (m === mkt) {{
            btn.classList.add('cal-active');
            if (pane) pane.style.display = 'block';
          }} else {{
            btn.classList.remove('cal-active');
            if (pane) pane.style.display = 'none';
          }}
        }});
      }}
    </script>
    """


# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def render():
    # ── Cargar datos ──────────────────────────────────────────────────────────
    with st.spinner("Cargando calendario económico..."):
        us_data  = get_economic_calendar("US")
        arg_data = get_economic_calendar("ARG")

    us_err  = isinstance(us_data,  dict) and "error" in us_data
    arg_err = isinstance(arg_data, dict) and "error" in arg_data

    us_records  = us_data  if isinstance(us_data,  list) else []
    arg_records = arg_data if isinstance(arg_data, list) else []

    # ── Renderizar calendarios ────────────────────────────────────────────────
    html_us  = _render_calendar_html(us_records,  "US")
    html_arg = _render_calendar_html(arg_records, "ARG")

    # ── Toggle bar ────────────────────────────────────────────────────────────
    toggle = _toggle_bar(len(us_records), len(arg_records))

    # ── Ensamblar todo en un solo bloque HTML con panes ocultos/visibles ─────
    full_html = f"""
    {toggle}
    <div id="cal-pane-us"  style="display:block">{html_us}</div>
    <div id="cal-pane-arg" style="display:none">{html_arg}</div>
    """

    st.markdown(full_html, unsafe_allow_html=True)

    # ── Errores no-fatales (mostrar debajo, no rompen la UI) ──────────────────
    if us_err:
        st.markdown(
            f'<p style="color:{MUTED};font-family:Courier New;font-size:9px">'
            f'US calendar error: {us_data["error"]}</p>',
            unsafe_allow_html=True
        )
    if arg_err:
        st.markdown(
            f'<p style="color:{MUTED};font-family:Courier New;font-size:9px">'
            f'ARG calendar error: {arg_data["error"]}</p>',
            unsafe_allow_html=True
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="color:{MUTED};font-size:8px;font-family:Courier New;'
        f'padding:8px 4px;border-top:1px solid #1a1a1a;margin-top:4px;">'
        f'FUENTE: INVESTING.COM · ACTUALIZACIÓN CADA 60 MIN · '
        f'SEMANA: {_week_label()}'
        f'</div>',
        unsafe_allow_html=True
    )


def _week_label() -> str:
    """Lunes–Viernes de la semana que muestra el calendario."""
    from datetime import datetime, timedelta
    today = datetime.today()
    wd    = today.weekday()
    if wd >= 5:
        monday = today + timedelta(days=(7 - wd))
    else:
        monday = today - timedelta(days=wd)
    friday = monday + timedelta(days=4)
    return f"{monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}".upper()
