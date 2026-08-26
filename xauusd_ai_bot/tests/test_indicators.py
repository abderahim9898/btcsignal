import pytest
import pandas as pd
import numpy as np
from indicators import compute_indicators, calculate_ema, calculate_rsi, calculate_macd, calculate_atr, calculate_adx


def test_indicator_calculations():
    # Generate 250 synthetic candles
    np.random.seed(42)
    prices = 2600 + np.cumsum(np.random.randn(250) * 2)

    data = []
    for i in range(250):
        p = prices[i]
        data.append({
            "timestamp": f"2026-08-26T10:{i:02d}:00Z",
            "open": p - 0.5,
            "high": p + 1.5,
            "low": p - 1.5,
            "close": p + 0.5,
            "volume": 100,
            "tickVolume": 100
        })

    df = pd.DataFrame(data)

    snapshot = compute_indicators(df)
    assert snapshot.ema20 > 0
    assert snapshot.ema50 > 0
    assert snapshot.ema200 > 0
    assert 0 <= snapshot.rsi14 <= 100
    assert snapshot.atr14 > 0
    assert snapshot.adx14 >= 0
    assert 0 <= snapshot.stoch_k <= 100
    assert snapshot.ema_alignment in ["BULLISH", "BEARISH", "MIXED"]
