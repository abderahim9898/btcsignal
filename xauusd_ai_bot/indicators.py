from typing import Tuple
import numpy as np
import pandas as pd
from models import TechnicalSnapshot

Tuple_MACD = Tuple[pd.Series, pd.Series, pd.Series]


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average (EMA)."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).copy()
    loss = (-delta.where(delta < 0, 0.0)).copy()

    # Wilders smoothing
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple_MACD:
    """Calculates MACD Line, Signal Line, and Histogram."""
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


Tuple_MACD = tuple[pd.Series, pd.Series, pd.Series]


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Average True Range (ATR)."""
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return atr


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculates Average Directional Index (ADX)."""
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    tr_smoothed = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, min_periods=period, adjust=False).mean() / (tr_smoothed + 1e-10)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, min_periods=period, adjust=False).mean() / (tr_smoothed + 1e-10)

    dx = (plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-10) * 100
    adx = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return adx


def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> tuple[pd.Series, pd.Series]:
    """Calculates Stochastic Oscillator %K and %D."""
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()

    stoch_k = 100 * ((df["close"] - low_min) / ((high_max - low_min) + 1e-10))
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return stoch_k, stoch_d


def compute_indicators(df: pd.DataFrame) -> TechnicalSnapshot:
    """
    Computes all technical indicators for the DataFrame and returns a TechnicalSnapshot
    for the latest closed candle.
    """
    df = df.copy()

    # Calculate indicators
    df["ema20"] = calculate_ema(df["close"], 20)
    df["ema50"] = calculate_ema(df["close"], 50)
    df["ema200"] = calculate_ema(df["close"], 200)

    df["rsi14"] = calculate_rsi(df["close"], 14)

    macd, macd_sig, macd_hist = calculate_macd(df["close"], 12, 26, 9)
    df["macd"] = macd
    df["macd_signal"] = macd_sig
    df["macd_hist"] = macd_hist

    df["atr14"] = calculate_atr(df, 14)
    df["adx14"] = calculate_adx(df, 14)

    stoch_k, stoch_d = calculate_stochastic(df, 14, 3)
    df["stoch_k"] = stoch_k
    df["stoch_d"] = stoch_d

    # Volume & Candle Body
    volume_col = "tickVolume" if "tickVolume" in df.columns and df["tickVolume"].sum() > 0 else "volume"
    df["avg_volume"] = df[volume_col].rolling(20).mean()

    # Latest candle index
    idx = len(df) - 1
    curr = df.iloc[idx]
    prev = df.iloc[idx - 1] if idx > 0 else curr

    price = curr["close"]
    ema20 = curr["ema20"]
    ema50 = curr["ema50"]
    ema200 = curr["ema200"]

    # EMA Alignment
    if ema20 > ema50 > ema200 and price > ema20:
        ema_alignment = "BULLISH"
    elif ema20 < ema50 < ema200 and price < ema20:
        ema_alignment = "BEARISH"
    else:
        ema_alignment = "MIXED"

    # RSI analysis
    rsi_val = curr["rsi14"]
    rsi_prev_val = prev["rsi14"]
    if rsi_val > rsi_prev_val + 0.5:
        rsi_dir = "UP"
    elif rsi_val < rsi_prev_val - 0.5:
        rsi_dir = "DOWN"
    else:
        rsi_dir = "FLAT"

    if rsi_val >= 70:
        rsi_state = "OVERBOUGHT"
    elif rsi_val <= 30:
        rsi_state = "OVERSOLD"
    else:
        rsi_state = "NEUTRAL"

    # MACD state
    macd_val = curr["macd"]
    macd_sig_val = curr["macd_signal"]
    macd_h_val = curr["macd_hist"]
    macd_h_prev = prev["macd_hist"]

    if macd_val > macd_sig_val:
        if macd_h_val > macd_h_prev:
            macd_state = "BULLISH_STRENGTHENING"
        else:
            macd_state = "BULLISH_WEAKENING"
    else:
        if macd_h_val < macd_h_prev:
            macd_state = "BEARISH_STRENGTHENING"
        else:
            macd_state = "BEARISH_WEAKENING"

    # ADX state
    adx_val = curr["adx14"]
    if adx_val >= 25:
        adx_strength = "STRONG_TREND"
    elif adx_val >= 15:
        adx_strength = "WEAK_TREND"
    else:
        adx_strength = "RANGING"

    # Stochastic state
    k_val = curr["stoch_k"]
    d_val = curr["stoch_d"]
    if k_val >= 80:
        stoch_state = "OVERBOUGHT"
    elif k_val <= 20:
        stoch_state = "OVERSOLD"
    else:
        stoch_state = "NEUTRAL"

    # Price & Candle metrics
    price_change = price - prev["close"]
    rate_of_change = (price_change / (prev["close"] + 1e-10)) * 100

    o, h, l, c = curr["open"], curr["high"], curr["low"], curr["close"]
    body_size = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    total_range = h - l
    body_range_ratio = body_size / (total_range + 1e-10)

    snapshot = TechnicalSnapshot(
        ema20=round(float(ema20), 3),
        ema50=round(float(ema50), 3),
        ema200=round(float(ema200), 3),
        ema_alignment=ema_alignment,
        rsi14=round(float(rsi_val), 2),
        rsi_previous=round(float(rsi_prev_val), 2),
        rsi_direction=rsi_dir,
        rsi_state=rsi_state,
        macd=round(float(macd_val), 3),
        macd_signal=round(float(macd_sig_val), 3),
        macd_histogram=round(float(macd_h_val), 3),
        macd_state=macd_state,
        atr14=round(float(curr["atr14"]), 3),
        adx14=round(float(adx_val), 2),
        adx_trend_strength=adx_strength,
        stoch_k=round(float(k_val), 2),
        stoch_d=round(float(d_val), 2),
        stoch_state=stoch_state,
        avg_volume=round(float(curr["avg_volume"]), 2),
        price_change=round(float(price_change), 3),
        rate_of_change=round(float(rate_of_change), 3),
        body_size=round(float(body_size), 3),
        upper_wick=round(float(upper_wick), 3),
        lower_wick=round(float(lower_wick), 3),
        body_range_ratio=round(float(body_range_ratio), 3)
    )

    return snapshot
