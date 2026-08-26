from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from market_structure import find_swing_points


def detect_fair_value_gaps(df: pd.DataFrame, min_gap_size: float = 0.3) -> List[Dict[str, Any]]:
    """
    Detects 3-candle Fair Value Gaps (FVG) / Imbalances.
    Bullish FVG: low of candle 3 > high of candle 1.
    Bearish FVG: high of candle 3 < low of candle 1.
    """
    fvgs = []
    if len(df) < 3:
        return fvgs

    n = len(df)
    for i in range(2, n):
        c1 = df.iloc[i - 2]
        c2 = df.iloc[i - 1]
        c3 = df.iloc[i]

        # Bullish FVG
        if c3["low"] > c1["high"]:
            gap_size = c3["low"] - c1["high"]
            if gap_size >= min_gap_size:
                fvgs.append({
                    "type": "BULLISH_FVG",
                    "top": round(float(c3["low"]), 2),
                    "bottom": round(float(c1["high"]), 2),
                    "gap_size": round(float(gap_size), 2),
                    "candle_time": str(c2["timestamp"])
                })

        # Bearish FVG
        elif c3["high"] < c1["low"]:
            gap_size = c1["low"] - c3["high"]
            if gap_size >= min_gap_size:
                fvgs.append({
                    "type": "BEARISH_FVG",
                    "top": round(float(c1["low"]), 2),
                    "bottom": round(float(c3["high"]), 2),
                    "gap_size": round(float(gap_size), 2),
                    "candle_time": str(c2["timestamp"])
                })

    return fvgs[-5:]  # Return latest 5 FVGs


def detect_order_blocks(df: pd.DataFrame, lookback: int = 40) -> Dict[str, Any]:
    """
    Identifies ICT Bullish Order Blocks (OB) and Bearish Order Blocks (OB).
    Bullish OB: Last down-candle before a strong bullish impulse.
    Bearish OB: Last up-candle before a strong bearish impulse.
    """
    if len(df) < 10:
        return {"bullish_ob": None, "bearish_ob": None}

    subset = df.iloc[-lookback:].reset_index(drop=True)
    n = len(subset)

    bullish_ob = None
    bearish_ob = None

    for i in range(1, n - 2):
        c_curr = subset.iloc[i]
        c_next1 = subset.iloc[i + 1]
        c_next2 = subset.iloc[i + 2]

        # Bullish OB Check: Bearish candle followed by strong bullish move
        if c_curr["close"] < c_curr["open"]:
            move = c_next2["close"] - c_curr["low"]
            if move > 4.0:  # Significant $4+ displacement in Gold
                bullish_ob = {
                    "high": round(float(c_curr["high"]), 2),
                    "low": round(float(c_curr["low"]), 2),
                    "open_time": str(c_curr["timestamp"])
                }

        # Bearish OB Check: Bullish candle followed by strong bearish move
        if c_curr["close"] > c_curr["open"]:
            move = c_curr["high"] - c_next2["close"]
            if move > 4.0:
                bearish_ob = {
                    "high": round(float(c_curr["high"]), 2),
                    "low": round(float(c_curr["low"]), 2),
                    "open_time": str(c_curr["timestamp"])
                }

    return {"bullish_ob": bullish_ob, "bearish_ob": bearish_ob}


def detect_liquidity_sweeps(df: pd.DataFrame, lookback: int = 30) -> List[Dict[str, Any]]:
    """
    Detects ICT Liquidity Sweeps:
    Buy-Side Liquidity (BSL) Sweep: Wick pierces above previous swing high, but candle closes below it.
    Sell-Side Liquidity (SSL) Sweep: Wick pierces below previous swing low, but candle closes above it.
    """
    sweeps = []
    if len(df) < 15:
        return sweeps

    subset = df.iloc[-lookback:].reset_index(drop=True)
    swing_highs, swing_lows = find_swing_points(subset, left=2, right=2)

    curr = df.iloc[-1]
    c_high, c_low, c_close = curr["high"], curr["low"], curr["close"]

    for sh in swing_highs[:-1]:
        if c_high > sh["price"] and c_close < sh["price"]:
            sweeps.append({
                "type": "BUY_SIDE_LIQUIDITY_SWEEP",
                "swept_level": sh["price"],
                "candle_time": str(curr["timestamp"])
            })

    for sl in swing_lows[:-1]:
        if c_low < sl["price"] and c_close > sl["price"]:
            sweeps.append({
                "type": "SELL_SIDE_LIQUIDITY_SWEEP",
                "swept_level": sl["price"],
                "candle_time": str(curr["timestamp"])
            })

    return sweeps


def calculate_premium_discount(df: pd.DataFrame, lookback: int = 50) -> Dict[str, Any]:
    """
    Calculates ICT Premium vs Discount zone based on 50% Equilibrium level of recent swing range.
    Discount: Price < Equilibrium (Favorable for BUY)
    Premium: Price > Equilibrium (Favorable for SELL)
    """
    if len(df) < 10:
        return {"zone": "EQUILIBRIUM", "equilibrium": 0.0, "high": 0.0, "low": 0.0}

    subset = df.iloc[-lookback:]
    range_high = subset["high"].max()
    range_low = subset["low"].min()
    eq = round(float((range_high + range_low) / 2.0), 2)
    current_price = df.iloc[-1]["close"]

    zone = "DISCOUNT" if current_price < eq else ("PREMIUM" if current_price > eq else "EQUILIBRIUM")

    return {
        "zone": zone,
        "equilibrium": eq,
        "range_high": round(float(range_high), 2),
        "range_low": round(float(range_low), 2)
    }
