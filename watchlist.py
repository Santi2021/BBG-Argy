import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import fmt_price, fmt_change

DEFAULT_WATCHLIST = [
    "MELI", "NU", "GGAL", "YPF", "BMA",
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN",
    "GC=F", "BTC-USD",
]


@st.cache_data(ttl=60, show_spinner=False)
def get_history(ticker: str, period="1mo"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
        return df["Close"].dropna()
    except Exception:
        return None


def _sparkline(closes, color="#f5a623"):
    if closes is None or len(closes) < 2:
        return None
    fig = go.Figure(go.Scatter(
        y=closes.tolist(), mode="lines",
        line=dict(color=color, width=1.5),
        hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=50, showlegend=False,
    )
    return fig


def render():
    st.markdown("""
    <div style="font-size:9px;color:#333;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px">
      Ingresá tickers separados por coma (Yahoo Finance format)
    </div>""", unsafe_allow_html=True)

    raw = st.text_input(
        "WATCHLIST",
        value=", ".join(DEFAULT_WATCHLIST),
        label_visibility="collapsed",
    )

    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]

    if not tickers:
        st.markdown('<p style="color:#333;font-size:11px">Ingresá al menos un ticker.</p>', unsafe_allow_html=True)
        return

    st.markdown('<div class="sec-header" style="margin-top:8px">WATCHLIST</div>', unsafe_allow_html=True)

    for ticker in tickers:
        closes = get_history(ticker)
        if closes is None or len(closes) == 0:
            continue

        price  = float(closes.iloc[-1])
        prev   = float(closes.iloc[-2]) if len(closes) >= 2 else price
        chg    = (price - prev) / prev * 100 if prev else 0
        chg_str, css = fmt_change(chg)
        color  = "#00c853" if chg > 0 else ("#ff3d3d" if chg < 0 else "#555")

        col_info, col_chart = st.columns([2, 3])

        with col_info:
            st.markdown(f"""
            <div style="background:#0d0d0d;border:1px solid #161616;padding:10px 14px;height:72px;
                        display:flex;flex-direction:column;justify-content:center">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:600;
                          color:#f5a623;letter-spacing:.08em;margin-bottom:4px">{ticker}</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:18px;color:#e8e0d0;line-height:1">
                {fmt_price(price)}
              </div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:{color};margin-top:2px">
                {chg_str}
              </div>
            </div>""", unsafe_allow_html=True)

        with col_chart:
            fig = _sparkline(closes, color=color)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div style="height:1px;background:#111;margin:2px 0"></div>', unsafe_allow_html=True)
