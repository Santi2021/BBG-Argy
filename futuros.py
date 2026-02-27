import streamlit as st
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import get_futuros_dolar, get_tasas_implicitas, get_curva_rendimientos
import pandas as pd


PLOT_LAYOUT = dict(
    paper_bgcolor="#0a0a0a",
    plot_bgcolor="#0a0a0a",
    font=dict(family="IBM Plex Mono", size=10, color="#666"),
    margin=dict(l=50, r=20, t=30, b=40),
    xaxis=dict(
        gridcolor="#141414", linecolor="#1e1e1e", zerolinecolor="#1e1e1e",
        tickfont=dict(size=9, color="#555"),
    ),
    yaxis=dict(
        gridcolor="#141414", linecolor="#1e1e1e", zerolinecolor="#1e1e1e",
        tickfont=dict(size=9, color="#555"),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)", bordercolor="#1e1e1e",
        font=dict(size=9, color="#888"),
    ),
    hoverlabel=dict(
        bgcolor="#111", bordercolor="#333",
        font=dict(family="IBM Plex Mono", size=10, color="#e8e0d0"),
    ),
)


def render():
    subtabs = st.tabs(["FUTUROS DÓLAR", "TASAS IMPLÍCITAS TNA", "CURVA DE RENDIMIENTOS"])

    # ── Tabla de futuros ─────────────────────────────────────────────────────
    with subtabs[0]:
        with st.spinner(""):
            df_fut = get_futuros_dolar()

        if df_fut.empty:
            st.markdown('<p style="color:#444;padding:20px">Sin datos de futuros</p>', unsafe_allow_html=True)
        else:
            # Clean up
            df = df_fut.copy()
            df.columns = [c.strip() for c in df.columns]

            # Table
            rows = ""
            for _, row in df.iterrows():
                especie = row.iloc[0]
                ultimo  = row.iloc[1] if len(row) > 1 else "—"
                var     = row.iloc[2] if len(row) > 2 else "—"
                tna     = row.iloc[3] if len(row) > 3 else "—"
                pase    = row.iloc[4] if len(row) > 4 else "—"

                try:
                    v = float(str(var).replace(",","."))
                    var_html = f'<span style="color:{"#00c853" if v>0 else "#ff3d3d"}">{var}</span>'
                except Exception:
                    var_html = f'<span style="color:#555">{var}</span>'

                try:
                    tna_f = float(str(tna).replace(",",".").replace("%",""))
                    tna_html = f'<span style="color:#f5a623;font-weight:500">{tna_f:.1f}%</span>'
                except Exception:
                    tna_html = f'<span style="color:#555">{tna}</span>'

                rows += f"""
                <tr>
                  <td style="text-align:left;color:#f5a623;font-weight:500">{especie}</td>
                  <td>{ultimo}</td>
                  <td>{var_html}</td>
                  <td>{tna_html}</td>
                  <td style="color:#555">{pase}</td>
                </tr>"""

            st.markdown(f"""
            <div style="overflow-x:auto">
            <table class="bbg-table">
              <thead><tr>
                <th style="text-align:left">CONTRATO</th>
                <th>ÚLTIMO</th><th>VAR. DÍA</th>
                <th>TNA %</th><th>PASE %</th>
              </tr></thead>
              <tbody>{rows}</tbody>
            </table>
            </div>""", unsafe_allow_html=True)

    # ── Tasas implícitas TNA ─────────────────────────────────────────────────
    with subtabs[1]:
        with st.spinner(""):
            tna_data = get_tasas_implicitas()

        if not tna_data:
            st.markdown('<p style="color:#444;padding:20px">Sin datos de tasas implícitas</p>', unsafe_allow_html=True)
        else:
            days  = [p[0] for p in tna_data]
            rates = [p[1] for p in tna_data]
            labels= [p[2] for p in tna_data]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=days, y=rates,
                mode="lines+markers",
                line=dict(color="#f5a623", width=2),
                marker=dict(color="#f5a623", size=6, symbol="circle"),
                text=labels,
                hovertemplate="<b>%{text}</b><br>Días: %{x}<br>TNA: %{y:.2f}%<extra></extra>",
                name="TNA Futuro",
            ))

            layout = dict(PLOT_LAYOUT)
            layout["title"] = dict(
                text="TASAS IMPLÍCITAS · TNA FUTUROS DÓLAR",
                font=dict(size=10, color="#444", family="IBM Plex Mono"),
                x=0.02, y=0.98,
            )
            layout["yaxis"] = dict(
                **PLOT_LAYOUT["yaxis"],
                title=dict(text="TNA %", font=dict(size=9, color="#444")),
                ticksuffix="%",
            )
            layout["xaxis"] = dict(
                **PLOT_LAYOUT["xaxis"],
                title=dict(text="Días al vencimiento", font=dict(size=9, color="#444")),
            )
            fig.update_layout(**layout, height=420)
            st.plotly_chart(fig, use_container_width=True)

    # ── Curva de rendimientos ─────────────────────────────────────────────────
    with subtabs[2]:
        with st.spinner(""):
            cer_data, usd_data = get_curva_rendimientos()

        if not cer_data and not usd_data:
            st.markdown('<p style="color:#444;padding:20px">Sin datos de curva</p>', unsafe_allow_html=True)
        else:
            fig = go.Figure()

            if cer_data:
                dur_cer = [p[0] for p in cer_data]
                tir_cer = [p[1] for p in cer_data]
                lbl_cer = [p[2] for p in cer_data]
                fig.add_trace(go.Scatter(
                    x=dur_cer, y=tir_cer,
                    mode="markers+text",
                    marker=dict(color="#00c853", size=8, symbol="circle"),
                    text=lbl_cer,
                    textposition="top center",
                    textfont=dict(size=8, color="#00c853"),
                    hovertemplate="<b>%{text}</b><br>Dur: %{x:.2f}<br>TIR: %{y:.2f}%<extra></extra>",
                    name="CER",
                ))

            if usd_data:
                dur_usd = [p[0] for p in usd_data]
                tir_usd = [p[1] for p in usd_data]
                lbl_usd = [p[2] for p in usd_data]
                fig.add_trace(go.Scatter(
                    x=dur_usd, y=tir_usd,
                    mode="markers+text",
                    marker=dict(color="#f5a623", size=8, symbol="diamond"),
                    text=lbl_usd,
                    textposition="top center",
                    textfont=dict(size=8, color="#f5a623"),
                    hovertemplate="<b>%{text}</b><br>Dur: %{x:.2f}<br>TIR: %{y:.2f}%<extra></extra>",
                    name="USD",
                ))

            layout = dict(PLOT_LAYOUT)
            layout["title"] = dict(
                text="CURVA DE RENDIMIENTOS · CER vs USD",
                font=dict(size=10, color="#444", family="IBM Plex Mono"),
                x=0.02, y=0.98,
            )
            layout["xaxis"] = dict(
                **PLOT_LAYOUT["xaxis"],
                title=dict(text="Duración modificada", font=dict(size=9, color="#444")),
            )
            layout["yaxis"] = dict(
                **PLOT_LAYOUT["yaxis"],
                title=dict(text="TIR %", font=dict(size=9, color="#444")),
                ticksuffix="%",
            )
            fig.update_layout(**layout, height=460)
            st.plotly_chart(fig, use_container_width=True)

            # Mini legend
            st.markdown("""
            <div style="display:flex;gap:24px;font-size:9px;color:#333;
                        letter-spacing:.1em;text-transform:uppercase;margin-top:-8px">
              <span><span style="color:#00c853">●</span> CER (ajustado inflación)</span>
              <span><span style="color:#f5a623">◆</span> USD (bonos en dólares)</span>
            </div>""", unsafe_allow_html=True)
