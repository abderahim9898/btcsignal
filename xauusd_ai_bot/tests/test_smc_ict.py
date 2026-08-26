import pytest
import pandas as pd
from smc_ict import detect_fair_value_gaps, detect_order_blocks, detect_liquidity_sweeps, calculate_premium_discount


def test_fair_value_gap_detection():
    data = [
        {"timestamp": "t1", "open": 2600.0, "high": 2602.0, "low": 2598.0, "close": 2601.0},
        {"timestamp": "t2", "open": 2601.0, "high": 2615.0, "low": 2600.0, "close": 2614.0},  # Strong impulse
        {"timestamp": "t3", "open": 2614.0, "high": 2620.0, "low": 2605.0, "close": 2618.0},  # c3 low (2605) > c1 high (2602) -> Bullish FVG
    ]
    df = pd.DataFrame(data)
    fvgs = detect_fair_value_gaps(df, min_gap_size=0.3)
    assert len(fvgs) == 1
    assert fvgs[0]["type"] == "BULLISH_FVG"
    assert fvgs[0]["bottom"] == 2602.0
    assert fvgs[0]["top"] == 2605.0


def test_premium_discount_calculation():
    data = []
    for i in range(20):
        p = 2600.0 + i * 2.0
        data.append({"timestamp": f"t{i}", "open": p, "high": p + 1, "low": p - 1, "close": p})

    df = pd.DataFrame(data)
    res = calculate_premium_discount(df, lookback=20)
    assert res["range_low"] == 2599.0
    assert res["range_high"] == 2639.0
    assert res["equilibrium"] == 2619.0
    assert res["zone"] == "PREMIUM"
