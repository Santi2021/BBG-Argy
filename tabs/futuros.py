import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_futuros_dolar, get_cauciones_resumen, get_letras_ppi


# ── Mapeo mes abreviado ROFEX → número de mes ──
_MES_MAP = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}


def _rofex_dias(contrato: str) -> int | None:
    """Calcula días al vencimiento desde el nombre del contrato ROFEX (ej: MAR25)."""
    try:
        mes_str = contrato[:3].upper()
        anio_str = contrato[3:]
        mes = _MES_MAP.get(mes_str)
        if not mes:
            return None
        anio = int("20" + anio_str) if len(anio_str) == 2 else int(anio_str)
        # ROFEX vence el último día hábil del mes — usamos el último día del mes
        import calendar
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        vto = date(anio, mes, ultimo_dia)
        dias = (vto - date.today()).days
        return dias if dias > 0 else None
    except Exception:
        return None


def render():
    with st.spinner(""):
        df = get_futuros_dolar()
        cauciones = get_cauciones_resumen()
        letras_ppi = get_letras_ppi()

    # ════════════════════════════════════════════════════════════════
    #  TABLA FUTUROS
    # ════════════════════════════════════════════════════════════════
    if df.empty:
        st.markdown('<p style="color:#333;font-size:10px">Sin datos</p>', unsafe_allow_html=True)
        return

    rows = ""
    rofex_pts = []  # (dias, tna, label)

    for _, r in df.iterrows():
        esp = r.iloc[0] if len(r) > 0 else "—"
        ult = r.iloc[1] if len(r) > 1 else "—"
        var = r.iloc[2] if len(r) > 2 else "—"
        tna = r.iloc[3] if len(r) > 3 else "—"
        pase = r.iloc[4] if len(r) > 4 else "—"

        try:
            v = float(str(var).replace(",", "."))
            vc = f'<span style="color:{"#00ff41" if v > 0 else "#ff3b3b"};font-weight:bold">{var}</span>'
        except:
            vc = f'<span style="color:#555">{var}</span>'

        try:
            t = float(str(tna).replace(",", ".").replace("%", ""))
            tc = f'<span style="color:#ff6600;font-weight:bold">{t:.1f}%</span>'
        except:
            t = None
            tc = f'<span style="color:#555">{tna}</span>'

        rows += f"<tr><td>{esp}</td><td style='color:#ffcc00'>{ult}</td><td>{vc}</td><td>{tc}</td><td style='color:#555'>{pase}</td></tr>"

        if t is not None and t > 0:
            dias = _rofex_dias(str(esp))
            if dias:
                rofex_pts.append((dias, t, str(esp)))

    st.markdown(f"""<table class="t">
    <thead><tr><th>CONTRATO</th><th>ÚLTIMO</th><th>VAR DIA</th><th>TNA</th><th>PASE</th></tr></thead>
    <tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    #  GRÁFICO ROFEX solo (el original)
    # ════════════════════════════════════════════════════════════════
    contracts = [p[2] for p in rofex_pts]
    tna_vals  = [p[1] for p in rofex_pts]

    if contracts and tna_vals:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=contracts,
            y=tna_vals,
            mode="lines+markers+text",
            line=dict(color="#ff6600", width=2),
            marker=dict(color="#ff6600", size=7, line=dict(color="#222", width=0.8)),
            text=[f"{v:.1f}%" for v in tna_vals],
            textposition="top center",
            textfont=dict(size=8, family="Courier New", color="#ff6600"),
            hovertemplate="<b>%{x}</b><br>TNA: %{y:.1f}%<extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(255,102,0,0.08)",
        ))
        y_max = max(tna_vals) * 1.15
        y_min = min(tna_vals) * 0.85
        fig.update_layout(
            paper_bgcolor="#000", plot_bgcolor="#000",
            font=dict(family="Courier New", size=9, color="#555"),
            margin=dict(l=50, r=20, t=30, b=35),
            height=280,
            showlegend=False,
            title=dict(
                text="TNA IMPLÍCITA POR VENCIMIENTO · ROFEX",
                font=dict(family="Courier New", size=10, color="#ff6600"),
                x=0.01, xanchor="left",
            ),
            xaxis=dict(
                gridcolor="#111", linecolor="#333",
                tickfont=dict(size=9, color="#ccc", family="Courier New"),
                categoryorder="array", categoryarray=contracts,
                range=[-0.6, len(contracts) - 0.4],
            ),
            yaxis=dict(
                gridcolor="#111", linecolor="#333",
                tickfont=dict(size=8, color="#555", family="Courier New"),
                ticksuffix="%", range=[y_min, y_max],
            ),
            hoverlabel=dict(
                bgcolor="#111", bordercolor="#ff6600",
                font=dict(family="Courier New", size=9, color="#fff"),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ════════════════════════════════════════════════════════════════
    #  CURVA COMBINADA: ROFEX + CAUCIONES + LETRAS
    # ════════════════════════════════════════════════════════════════

    # ── Cauciones ──
    cauc_pts = []
    for c in (cauciones or []):
        try:
            plazo = int("".join(filter(str.isdigit, c.get("plazo", ""))))
            tasa = float(c.get("tasa", 0))
            if tasa > 0:
                cauc_pts.append((plazo, tasa, f"{plazo}d"))
        except Exception:
            pass

    # ── Letras capitalizables (S/T prefix, TNA > 0) ──
    hoy = date.today().isoformat()
    letras_pts = []
    vistos = set()
    candidatos = sorted(
        [
            item for item in (letras_ppi or [])
            if item.get("currency") == "ARS"
            and item.get("tna") is not None
            and item.get("tna") > 0
            and item.get("expiration_date", "") >= hoy
            and item.get("last", 0) > 0
            and item.get("last", 0) < 10000
            and str(item.get("ticker", ""))[0] in ("S", "T")
        ],
        key=lambda x: x.get("volume", 0) or 0,
        reverse=True,
    )
    for item in candidatos:
        mes = item["expiration_date"][:7]
        if mes in vistos:
            continue
        vistos.add(mes)
        dias = (datetime.strptime(item["expiration_date"], "%Y-%m-%d").date() - date.today()).days
        if dias > 0:
            letras_pts.append((dias, item["tna"], item["ticker"]))

    letras_pts.sort(key=lambda x: x[0])

    # ── Graficar curva combinada ──
    if cauc_pts or letras_pts or rofex_pts:
        fig2 = go.Figure()

        # Cauciones
        if cauc_pts:
            cauc_pts.sort(key=lambda x: x[0])
            fig2.add_trace(go.Scatter(
                x=[p[0] for p in cauc_pts],
                y=[p[1] for p in cauc_pts],
                mode="lines+markers+text",
                name="CAUCIONES",
                line=dict(color="#00ff41", width=1.5),
                marker=dict(color="#00ff41", size=6),
                text=[p[2] for p in cauc_pts],
                textposition="top center",
                textfont=dict(size=7, color="#00ff41", family="Courier New"),
                hovertemplate="<b>%{text}</b><br>Días: %{x}<br>TNA: %{y:.1f}%<extra>CAUCION</extra>",
            ))

        # ROFEX
        if rofex_pts:
            rofex_pts.sort(key=lambda x: x[0])
            fig2.add_trace(go.Scatter(
                x=[p[0] for p in rofex_pts],
                y=[p[1] for p in rofex_pts],
                mode="lines+markers+text",
                name="ROFEX",
                line=dict(color="#ff6600", width=1.5),
                marker=dict(color="#ff6600", size=6),
                text=[p[2] for p in rofex_pts],
                textposition="top center",
                textfont=dict(size=7, color="#ff6600", family="Courier New"),
                hovertemplate="<b>%{text}</b><br>Días: %{x}<br>TNA: %{y:.1f}%<extra>ROFEX</extra>",
            ))

        # Letras
        if letras_pts:
            fig2.add_trace(go.Scatter(
                x=[p[0] for p in letras_pts],
                y=[p[1] for p in letras_pts],
                mode="lines+markers+text",
                name="LETRAS",
                line=dict(color="#ffcc00", width=1.5),
                marker=dict(color="#ffcc00", size=6),
                text=[p[2] for p in letras_pts],
                textposition="top center",
                textfont=dict(size=7, color="#ffcc00", family="Courier New"),
                hovertemplate="<b>%{text}</b><br>Días: %{x}<br>TNA: %{y:.1f}%<extra>LETRA</extra>",
            ))

        # Rango Y combinado
        all_tna = [p[1] for p in cauc_pts + rofex_pts + letras_pts]
        y_min = max(0, min(all_tna) * 0.85)
        y_max = max(all_tna) * 1.12

        fig2.update_layout(
            paper_bgcolor="#000", plot_bgcolor="#000",
            font=dict(family="Courier New", size=9, color="#555"),
            margin=dict(l=50, r=20, t=35, b=40),
            height=340,
            title=dict(
                text="CURVA DE RENDIMIENTOS ARS · CAUCIONES · ROFEX · LETRAS",
                font=dict(family="Courier New", size=10, color="#ffcc00"),
                x=0.01, xanchor="left",
            ),
            xaxis=dict(
                title=dict(text="DÍAS AL VENCIMIENTO", font=dict(size=8, color="#555")),
                gridcolor="#111", linecolor="#333",
                tickfont=dict(size=8, color="#555", family="Courier New"),
            ),
            yaxis=dict(
                gridcolor="#111", linecolor="#333",
                tickfont=dict(size=8, color="#555", family="Courier New"),
                ticksuffix="%", range=[y_min, y_max],
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0.7)", bordercolor="#333", borderwidth=1,
                font=dict(size=9, color="#ccc", family="Courier New"),
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            ),
            hoverlabel=dict(
                bgcolor="#111", bordercolor="#333",
                font=dict(family="Courier New", size=9, color="#fff"),
            ),
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
