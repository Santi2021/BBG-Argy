"""
GRAFICADORA — TradingView Advanced Chart Widget
"""
import streamlit as st
import streamlit.components.v1 as components


DEFAULT_SYMBOL = "BCBA:GGAL"


def _tv_widget_html(symbol, height=640):
    return f"""
    <div class="tradingview-widget-container" style="height:{height}px;width:100%">
      <div id="tradingview_chart" style="height:100%;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "America/Argentina/Buenos_Aires",
        "theme": "dark",
        "style": "1",
        "locale": "es",
        "backgroundColor": "rgba(0, 0, 0, 1)",
        "gridColor": "rgba(30, 30, 30, 1)",
        "toolbar_bg": "#000000",
        "enable_publishing": false,
        "hide_top_toolbar": true,
        "hide_legend": false,
        "save_image": true,
        "hide_volume": false,
        "container_id": "tradingview_chart",
        "allow_symbol_change": true,
        "details": false,
        "hotlist": false,
        "calendar": false,
        "studies": ["STD;EMA"],
        "support_host": "https://www.tradingview.com"
      }});
      </script>
    </div>
    """


def render():
    st.markdown('<div style="font-size:8px;color:#555;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px">SÍMBOLO · Ej: AAPL, BCBA:GGAL, BINANCE:BTCUSDT, TVC:GOLD, FX:EURUSD</div>', unsafe_allow_html=True)
    symbol = st.text_input("SYM", value=DEFAULT_SYMBOL, label_visibility="collapsed")
    symbol = symbol.strip().upper() if symbol else DEFAULT_SYMBOL

    components.html(_tv_widget_html(symbol, height=640), height=650, scrolling=False)

    st.markdown(
        '<div style="color:#333;font-size:8px;text-align:center;margin-top:2px;letter-spacing:1px">'
        'CHART BY TRADINGVIEW · CAMBIAR SÍMBOLO, TIMEFRAME, INDICADORES Y ESCALA DESDE EL GRÁFICO'
        '</div>',
        unsafe_allow_html=True
    )
