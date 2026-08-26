from typing import Dict, List, Any
import pandas as pd


def analyze_price_action(df: pd.DataFrame, lookback: int = 10) -> Dict[str, Any]:
    """
    Analyzes candlestick patterns and price action features over recent candles.
    Returns dictionary with detected patterns, candle features, and summary.
    """
    if len(df) < 2:
        return {"patterns": [], "summary": "Insufficient candle data"}

    recent_df = df.iloc[-lookback:].copy()
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    c_open, c_high, c_low, c_close = curr["open"], curr["high"], curr["low"], curr["close"]
    p_open, p_high, p_low, p_close = prev["open"], prev["high"], prev["low"], prev["close"]

    body = abs(c_close - c_open)
    total_range = c_high - c_low
    upper_wick = c_high - max(c_open, c_close)
    lower_wick = min(c_open, c_close) - c_low

    patterns: List[str] = []

    # 1. Bullish Engulfing
    if p_close < p_open and c_close > c_open:
        if c_close >= p_open and c_open <= p_close:
            patterns.append("BULLISH_ENGULFING")

    # 2. Bearish Engulfing
    if p_close > p_open and c_close < c_open:
        if c_close <= p_open and c_open >= p_close:
            patterns.append("BEARISH_ENGULFING")

    # 3. Pin Bar
    if total_range > 0:
        if lower_wick >= 2 * body and upper_wick <= 0.5 * body:
            patterns.append("BULLISH_PIN_BAR")
        elif upper_wick >= 2 * body and lower_wick <= 0.5 * body:
            patterns.append("BEARISH_PIN_BAR")

    # 4. Long Wicks
    if total_range > 0:
        if upper_wick / total_range > 0.45:
            patterns.append("LONG_UPPER_WICK_REJECTION")
        if lower_wick / total_range > 0.45:
            patterns.append("LONG_LOWER_WICK_REJECTION")

    # 5. Strong Momentum Candle
    avg_body = abs(recent_df["close"] - recent_df["open"]).mean()
    if total_range > 0 and (body / total_range) >= 0.70 and body >= 1.3 * avg_body:
        if c_close > c_open:
            patterns.append("BULLISH_MOMENTUM_CANDLE")
        else:
            patterns.append("BEARISH_MOMENTUM_CANDLE")

    # 6. Inside Bar / Consolidation
    if c_high <= p_high and c_low >= p_low:
        patterns.append("INSIDE_BAR")

    # Range / Volatility Expansion
    ranges = recent_df["high"] - recent_df["low"]
    is_expanding = total_range > 1.5 * ranges.mean()
    is_contracting = total_range < 0.6 * ranges.mean()

    volatility_state = "EXPANDING" if is_expanding else ("CONTRACTING" if is_contracting else "NORMAL")

    summary_str = f"Candle body={round(body,2)}, range={round(total_range,2)}, patterns={', '.join(patterns) if patterns else 'None'}"

    return {
        "patterns": patterns,
        "body_size": round(float(body), 3),
        "total_range": round(float(total_range), 3),
        "upper_wick": round(float(upper_wick), 3),
        "lower_wick": round(float(lower_wick), 3),
        "volatility_state": volatility_state,
        "summary": summary_str
    }
