"""
GRAFICADORA — TradingView Advanced Chart Widget
"""
import streamlit as st
import streamlit.components.v1 as components


DEFAULT_SYMBOL = "BCBA:GGAL"


def _tv_widget_html(symbol, height=700):
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
    components.html(_tv_widget_html(DEFAULT_SYMBOL, height=700), height=710, scrolling=False)
