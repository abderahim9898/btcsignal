import pytest
import pandas as pd
from market_data import MarketDataManager
from biquote_client import BiquoteClient
from models import CandleBar, BiQuoteQuote


def test_biquote_client_closed_candle_filtering():
    client = BiquoteClient()
    raw_bars = [
        {"openTime": "2026-08-26T20:05:00Z", "open": 2650, "high": 2655, "low": 2649, "close": 2652, "volume": 10, "isOpen": True},
        {"openTime": "2026-08-26T20:00:00Z", "open": 2645, "high": 2651, "low": 2644, "close": 2650, "volume": 20, "isOpen": False},
        {"openTime": "2026-08-26T19:55:00Z", "open": 2640, "high": 2646, "low": 2639, "close": 2645, "volume": 15, "isOpen": False},
    ]

    valid, msg = client.validate_candles(raw_bars)
    assert valid

    # Ensure normalization sorts chronologically ascending
    closed_bars = [
        CandleBar(openTime=b["openTime"], open=b["open"], high=b["high"], low=b["low"], close=b["close"], isOpen=False)
        for b in raw_bars if not b["isOpen"]
    ]
    df = client.normalize_candles(closed_bars)
    assert len(df) == 2
    assert df.iloc[0]["timestamp"] == "2026-08-26T19:55:00Z"
    assert df.iloc[1]["timestamp"] == "2026-08-26T20:00:00Z"


def test_dataframe_validation_checks():
    mgr = MarketDataManager()

    # Valid DF
    data = []
    for i in range(60):
        data.append({
            "timestamp": f"2026-08-26T10:{i:02d}:00Z",
            "open": 2600.0 + i,
            "high": 2605.0 + i,
            "low": 2595.0 + i,
            "close": 2602.0 + i,
            "volume": 100
        })
    df_valid = pd.DataFrame(data)

    valid, msg = mgr.validate_dataframe(df_valid, min_candles=50)
    assert valid

    # Invalid high < low
    df_invalid = df_valid.copy()
    df_invalid.loc[0, "high"] = 2500.0
    valid, msg = mgr.validate_dataframe(df_invalid, min_candles=50)
    assert not valid
    assert "high >= low" in msg
