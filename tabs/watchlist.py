"""
GRAFICADORA — TradingView Advanced Chart Widget
Replaces the old Watchlist tab with a full-featured charting tool.
"""
import streamlit as st
import streamlit.components.v1 as components


DEFAULT_SYMBOL = "BCBA:GGAL"

# Preset symbol groups for quick access
PRESETS = {
    "ARG Acciones": ["BCBA:GGAL", "BCBA:YPF", "BCBA:BBAR", "BCBA:BMA", "BCBA:SUPV", "BCBA:PAMP", "BCBA:TECO2", "BCBA:ALUA", "BCBA:TXAR", "BCBA:CEPU"],
    "ADRs": ["GGAL", "YPF", "BBAR", "BMA", "SUPV", "PAM", "TEO", "TGS", "LOMA", "CEPU", "CRESY", "EDN"],
    "CEDEARs": ["BCBA:MELI", "BCBA:NVDA", "BCBA:AAPL", "BCBA:MSFT", "BCBA:GOOGL", "BCBA:AMZN", "BCBA:META", "BCBA:TSLA"],
    "US Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL", "AMD"],
    "Commodities": ["TVC:GOLD", "TVC:SILVER", "NYMEX:CL1!", "NYMEX:NG1!", "CBOT:ZS1!", "CBOT:ZC1!", "CBOT:ZW1!"],
    "Crypto": ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT"],
    "FX": ["FX:EURUSD", "FX:USDJPY", "FX:GBPUSD", "FX_IDC:USDBRL", "FX_IDC:USDARS"],
    "Índices": ["SP:SPX", "NASDAQ:NDX", "TVC:DJI", "BCBA:IMV", "INDEX:IBOV", "TVC:DAX", "TVC:NI225"],
}


def _tv_widget_html(symbol, height=620):
    """Generate TradingView Advanced Chart widget HTML."""
    return f"""
    <!-- TradingView Widget BEGIN -->
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
        "hide_top_toolbar": false,
        "hide_legend": false,
        "save_image": true,
        "hide_volume": false,
        "container_id": "tradingview_chart",
        "allow_symbol_change": true,
        "watchlist": {list(_get_watchlist_symbols())},
        "details": true,
        "hotlist": false,
        "calendar": false,
        "studies": ["STD;EMA"],
        "support_host": "https://www.tradingview.com"
      }});
      </script>
    </div>
    <!-- TradingView Widget END -->
    """


def _get_watchlist_symbols():
    """Flat list of unique symbols for TV sidebar watchlist."""
    seen = set()
    result = []
    for symbols in PRESETS.values():
        for s in symbols:
            if s not in seen:
                seen.add(s)
                result.append(s)
    return result


def render():
    # ── Symbol input row ──
    col_input, col_preset = st.columns([2, 3])

    with col_input:
        st.markdown('<div style="font-size:8px;color:#555;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px">SÍMBOLO (TradingView format)</div>', unsafe_allow_html=True)
        symbol = st.text_input("SYM", value=DEFAULT_SYMBOL, label_visibility="collapsed",
                               help="Ej: AAPL, BCBA:GGAL, BINANCE:BTCUSDT, TVC:GOLD")

    with col_preset:
        st.markdown('<div style="font-size:8px;color:#555;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px">PRESETS</div>', unsafe_allow_html=True)
        preset_cols = st.columns(len(PRESETS))
        for i, (label, symbols) in enumerate(PRESETS.items()):
            with preset_cols[i]:
                if st.button(label, key=f"preset_{i}", use_container_width=True):
                    symbol = symbols[0]
                    st.session_state["SYM"] = symbol

    # ── Clean symbol ──
    symbol = symbol.strip().upper() if symbol else DEFAULT_SYMBOL

    # ── TradingView Chart ──
    chart_html = _tv_widget_html(symbol, height=620)
    components.html(chart_html, height=630, scrolling=False)

    # ── Footer hint ──
    st.markdown(
        '<div style="color:#333;font-size:8px;text-align:center;margin-top:2px;letter-spacing:1px">'
        'CHART BY TRADINGVIEW · CLICK EN EL GRÁFICO PARA CAMBIAR SÍMBOLO, TIMEFRAME, INDICADORES, ESCALA LOG, ETC.'
        '</div>',
        unsafe_allow_html=True
    )
