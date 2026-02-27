import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data import fmt_price, fmt_change

DEFAULT = ["MELI","NU","GGAL","YPF","BMA","NVDA","AAPL","MSFT","GOOGL","AMZN","GC=F","BTC-USD"]

@st.cache_data(ttl=60, show_spinner=False)
def _hist(ticker, period="1mo"):
    try: return yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)["Close"].dropna()
    except: return None

def _spark(closes, color):
    if closes is None or len(closes) < 2: return None
    fig = go.Figure(go.Scatter(y=closes.tolist(), mode="lines", line=dict(color=color,width=1.2), hoverinfo="skip"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=36, showlegend=False)
    return fig

def render():
    st.markdown('<div style="font-size:8px;color:#555;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px">Tickers separados por coma (Yahoo Finance)</div>', unsafe_allow_html=True)
    raw = st.text_input("WL", value=", ".join(DEFAULT), label_visibility="collapsed")
    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
    if not tickers:
        st.markdown('<p style="color:#333;font-size:10px">Ingresá al menos un ticker.</p>', unsafe_allow_html=True)
        return
    st.markdown('<div class="sh">WATCHLIST</div>', unsafe_allow_html=True)
    for tk in tickers:
        cl = _hist(tk)
        if cl is None or len(cl) == 0: continue
        p = float(cl.iloc[-1])
        prev = float(cl.iloc[-2]) if len(cl)>=2 else p
        chg = (p-prev)/prev*100 if prev else 0
        chg_s, css = fmt_change(chg)
        c = "#00ff41" if chg>0 else ("#ff3b3b" if chg<0 else "#555")
        ci, cc = st.columns([2,3])
        with ci:
            st.markdown(f"""<div style="border:1px solid #222;padding:4px 8px;height:48px;display:flex;flex-direction:column;justify-content:center">
              <div style="font-size:10px;font-weight:bold;color:#fff;letter-spacing:1px">{tk}</div>
              <div style="font-size:14px;font-weight:bold;color:#ffcc00;line-height:1">{fmt_price(p)}</div>
              <div style="font-size:9px;font-weight:bold;color:{c}">{chg_s}</div>
            </div>""", unsafe_allow_html=True)
        with cc:
            fig = _spark(cl, c)
            if fig: st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
