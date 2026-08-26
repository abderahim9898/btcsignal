import pytest
import pandas as pd
from price_action import analyze_price_action
from market_structure import analyze_market_structure
from support_resistance import find_support_resistance_zones


def test_bullish_engulfing_detection():
    data = [
        {"timestamp": "t1", "open": 2650.0, "high": 2652.0, "low": 2640.0, "close": 2642.0, "volume": 100},  # Bearish
        {"timestamp": "t2", "open": 2640.0, "high": 2655.0, "low": 2638.0, "close": 2654.0, "volume": 150},  # Engulfing Bullish
    ]
    df = pd.DataFrame(data)
    pa = analyze_price_action(df)
    assert "BULLISH_ENGULFING" in pa["patterns"]


def test_support_resistance_zones():
    data = []
    # Create price oscillating between 2600 and 2650
    for i in range(100):
        if i % 10 < 5:
            p = 2600.0 + (i % 5)
        else:
            p = 2650.0 - (i % 5)

        data.append({
            "timestamp": f"t{i}",
            "open": p,
            "high": p + 2,
            "low": p - 2,
            "close": p + 1,
            "volume": 100
        })

    df = pd.DataFrame(data)
    s_zones, r_zones = find_support_resistance_zones(df, current_price=2625.0)

    assert len(s_zones) > 0
    assert len(r_zones) > 0
    assert all(z["high"] <= 2625.0 for z in s_zones)
    assert all(z["low"] >= 2625.0 for z in r_zones)
