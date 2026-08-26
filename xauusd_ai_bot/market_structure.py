from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np


def find_swing_points(df: pd.DataFrame, left: int = 3, right: int = 3) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Identifies swing highs and swing lows in the candle dataframe.
    A swing high has higher highs than `left` candles before and `right` candles after.
    """
    swing_highs = []
    swing_lows = []

    highs = df["high"].values
    lows = df["low"].values
    timestamps = df["timestamp"].values
    n = len(df)

    for i in range(left, n - right):
        current_high = highs[i]
        current_low = lows[i]

        # Check Swing High
        if all(current_high > highs[i - l] for l in range(1, left + 1)) and \
           all(current_high >= highs[i + r] for r in range(1, right + 1)):
            swing_highs.append({
                "index": i,
                "timestamp": str(timestamps[i]),
                "price": round(float(current_high), 3)
            })

        # Check Swing Low
        if all(current_low < lows[i - l] for l in range(1, left + 1)) and \
           all(current_low <= lows[i + r] for r in range(1, right + 1)):
            swing_lows.append({
                "index": i,
                "timestamp": str(timestamps[i]),
                "price": round(float(current_low), 3)
            })

    return swing_highs, swing_lows


def analyze_market_structure(df: pd.DataFrame, lookback_candles: int = 50) -> Dict[str, Any]:
    """
    Analyzes market structure trend, swing points, BOS (Break of Structure), and CHOCH.
    """
    if len(df) < 20:
        return {
            "trend": "NEUTRAL",
            "recent_swing_highs": [],
            "recent_swing_lows": [],
            "bos": None,
            "choch": None,
            "summary": "Insufficient data for market structure analysis"
        }

    subset = df.iloc[-lookback_candles:].reset_index(drop=True)
    swing_highs, swing_lows = find_swing_points(subset, left=2, right=2)

    recent_high_prices = [sh["price"] for sh in swing_highs[-3:]]
    recent_low_prices = [sl["price"] for sl in swing_lows[-3:]]

    trend = "NEUTRAL"
    structure_type = "SIDEWAYS"

    if len(recent_high_prices) >= 2 and len(recent_low_prices) >= 2:
        hh = recent_high_prices[-1] > recent_high_prices[-2]
        hl = recent_low_prices[-1] > recent_low_prices[-2]
        lh = recent_high_prices[-1] < recent_high_prices[-2]
        ll = recent_low_prices[-1] < recent_low_prices[-2]

        if hh and hl:
            trend = "BULLISH"
            structure_type = "HIGHER_HIGHS_HIGHER_LOWS"
        elif lh and ll:
            trend = "BEARISH"
            structure_type = "LOWER_HIGHS_LOWER_LOWS"
        elif hh and ll:
            trend = "EXPANDING"
            structure_type = "EXPANDING_VOLATILITY"
        elif lh and hl:
            trend = "CONSOLIDATING"
            structure_type = "TRIANGLE_CONSOLIDATION"

    # Check for Break of Structure (BOS) / CHOCH on latest candle
    latest_close = df.iloc[-1]["close"]
    bos_event = None
    choch_event = None

    if swing_highs:
        last_sh = swing_highs[-1]["price"]
        if latest_close > last_sh:
            bos_event = f"BULLISH_BOS: Closed above recent swing high {last_sh}"
            if trend == "BEARISH":
                choch_event = f"BULLISH_CHOCH: Change of Character above {last_sh}"

    if swing_lows:
        last_sl = swing_lows[-1]["price"]
        if latest_close < last_sl:
            bos_event = f"BEARISH_BOS: Closed below recent swing low {last_sl}"
            if trend == "BULLISH":
                choch_event = f"BEARISH_CHOCH: Change of Character below {last_sl}"

    summary = f"Structure: {trend} ({structure_type}). "
    if bos_event:
        summary += f"Event: {bos_event}. "
    if choch_event:
        summary += f"Event: {choch_event}."

    return {
        "trend": trend,
        "structure_type": structure_type,
        "recent_swing_highs": [sh["price"] for sh in swing_highs[-4:]],
        "recent_swing_lows": [sl["price"] for sl in swing_lows[-4:]],
        "bos": bos_event,
        "choch": choch_event,
        "summary": summary
    }
