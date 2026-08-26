import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from biquote_client import BiquoteClient
from database import DatabaseManager
from indicators import compute_indicators, calculate_ema, calculate_rsi, calculate_macd
from market_data import MarketDataManager
from config import config

st.set_page_config(
    page_title="XAUUSD AI Trading Analysis Bot",
    page_icon="🟡",
    layout="wide"
)

st.title("🟡 XAUUSD AI Trading Analysis Bot Dashboard")
st.caption("Live Market Monitoring, Interactive Candlestick Charts & Technical AI Insights (Analysis Only - No Auto Trading)")

db_mgr = DatabaseManager()
biquote_client = BiquoteClient()
market_data_mgr = MarketDataManager(biquote_client)

# Top Bar Metrics
col1, col2, col3, col4 = st.columns(4)

quote = biquote_client.get_quote()
mid_price = quote.mid if quote else 0.0
stale_status = "STALE" if (quote and quote.stale) else "FRESH"

with col1:
    st.metric("XAUUSD Current Mid Price", f"${mid_price:.2f}" if mid_price else "N/A", delta=f"{quote.dayDiffPercent}%" if quote and quote.dayDiffPercent else None)

with col2:
    st.metric("Quote Staleness", stale_status, delta=f"{quote.quoteAgeSeconds}s age" if quote else None)

with col3:
    st.metric("Operating Timezone", config.timezone, "10:00 - 20:00")

with col4:
    st.metric("Configured Symbol / Timeframe", f"{config.symbol} / {config.timeframe}")

st.divider()

# Interactive Candlestick Chart Section
st.subheader("📈 XAUUSD M5 Live Candlestick & Technical Indicators Chart")

closed_bars = biquote_client.get_closed_candles(limit=100)
if closed_bars:
    df = biquote_client.normalize_candles(closed_bars)

    # Calculate indicators for chart
    df["ema20"] = calculate_ema(df["close"], 20)
    df["ema50"] = calculate_ema(df["close"], 50)
    df["ema200"] = calculate_ema(df["close"], 200)
    df["rsi14"] = calculate_rsi(df["close"], 14)
    macd_line, macd_sig, macd_hist = calculate_macd(df["close"], 12, 26, 9)
    df["macd"] = macd_line
    df["macd_signal"] = macd_sig
    df["macd_hist"] = macd_hist

    # Create 3-panel subplot: 1. Price/EMAs (row 1), 2. RSI (row 2), 3. MACD (row 3)
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("Price (OHLC) & EMAs", "RSI (14)", "MACD (12, 26, 9)")
    )

    # 1. Candlestick Trace
    fig.add_trace(
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="XAUUSD M5",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350"
        ),
        row=1, col=1
    )

    # EMA Overlays
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["ema20"], mode="lines", name="EMA 20", line=dict(color="#00bcd4", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["ema50"], mode="lines", name="EMA 50", line=dict(color="#ff9800", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["ema200"], mode="lines", name="EMA 200", line=dict(color="#e91e63", width=1.5)), row=1, col=1)

    # 2. RSI Trace
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["rsi14"], mode="lines", name="RSI 14", line=dict(color="#9c27b0", width=1.5)), row=2, col=1)
    # RSI thresholds
    fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=2, col=1)

    # 3. MACD Traces
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["macd"], mode="lines", name="MACD", line=dict(color="#2196f3", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["macd_signal"], mode="lines", name="Signal", line=dict(color="#ff5722", width=1.5)), row=3, col=1)

    # MACD Histogram bars
    colors = ["#26a69a" if val >= 0 else "#ef5350" for val in df["macd_hist"]]
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["macd_hist"], name="Histogram", marker_color=colors), row=3, col=1)

    # Layout styling
    fig.update_layout(
        template="plotly_dark",
        height=750,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Unable to fetch candle data from BiQuote API for chart rendering.")

st.divider()

# Recent Analyses from SQLite
st.subheader("📊 Recent AI Analysis Signals")
recent_records = db_mgr.get_recent_analyses(limit=20)

if recent_records:
    latest = recent_records[0]

    # Display Latest Signal Card
    card_col1, card_col2, card_col3, card_col4 = st.columns(4)

    sig = latest["signal"]
    sig_color = "green" if sig == "LONG" else ("red" if sig == "SHORT" else "gray")

    with card_col1:
        st.markdown(f"### Latest Signal: :{sig_color}[{sig}]")
        st.write(f"**Candle Time:** `{latest['candle_time']}`")
        st.write(f"**Confidence:** `{latest['confidence']}%`")

    with card_col2:
        st.write(f"🟢 **Entry:** `{latest['entry'] if latest['entry'] else 'N/A'}`")
        st.write(f"🛑 **Stop Loss:** `{latest['stop_loss'] if latest['stop_loss'] else 'N/A'}`")

    with card_col3:
        st.write(f"🎯 **TP1:** `{latest['take_profit_1'] if latest['take_profit_1'] else 'N/A'}`")
        st.write(f"🎯 **TP2:** `{latest['take_profit_2'] if latest['take_profit_2'] else 'N/A'}`")
        st.write(f"🎯 **TP3:** `{latest['take_profit_3'] if latest['take_profit_3'] else 'N/A'}`")

    with card_col4:
        rr1 = f"1:{latest['risk_reward_tp1']:.1f}" if latest['risk_reward_tp1'] else "N/A"
        st.write(f"📊 **Risk/Reward TP1:** `{rr1}`")
        st.write(f"📈 **Trend:** `{latest['trend']}`")

    st.markdown("#### Analytical Reasoning")
    st.info(latest["reasoning"] or "No specific reasoning logged.")

    st.divider()

    # Table of Historical Analyses
    df_history = pd.DataFrame(recent_records)
    cols_to_display = ["id", "candle_time", "signal", "confidence", "current_price", "entry", "stop_loss", "take_profit_1", "risk_reward_tp1", "trend"]
    existing_cols = [c for c in cols_to_display if c in df_history.columns]
    st.dataframe(df_history[existing_cols], use_container_width=True)

else:
    st.info("No analysis records found in SQLite database yet. Run `python main.py --once` to perform the first analysis.")
