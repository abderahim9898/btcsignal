import pytest
from models import GeminiAnalysisResponse
from signal_validator import SignalValidator


def test_valid_long_signal_enrichment():
    validator = SignalValidator(min_confidence=70)
    raw = GeminiAnalysisResponse(
        symbol="XAUUSD",
        timeframe="M5",
        candle_time="2026-08-26T20:00:00Z",
        analysis_time="2026-08-26T20:05:00Z",
        signal="LONG",
        confidence=80,
        current_price=2650.0,
        entry=2650.0,
        stop_loss=2640.0,
        take_profit_1=2665.0,
        take_profit_2=2675.0,
        take_profit_3=2690.0,
        trend="BULLISH"
    )

    res = validator.validate_and_enrich(raw)
    assert res.signal == "LONG"
    assert res.risk == 10.0
    assert res.reward_tp1 == 15.0
    assert res.risk_reward_tp1 == 1.5
    assert res.risk_reward_tp2 == 2.5
    assert res.risk_reward_tp3 == 4.0


def test_invalid_long_sl_rejection():
    validator = SignalValidator(min_confidence=70)
    # Invalid: SL > Entry for LONG
    raw = GeminiAnalysisResponse(
        symbol="XAUUSD",
        timeframe="M5",
        candle_time="2026-08-26T20:00:00Z",
        analysis_time="2026-08-26T20:05:00Z",
        signal="LONG",
        confidence=85,
        current_price=2650.0,
        entry=2650.0,
        stop_loss=2660.0,
        take_profit_1=2670.0
    )

    res = validator.validate_and_enrich(raw)
    assert res.signal == "NO_TRADE"
    assert res.entry is None
    assert res.stop_loss is None


def test_confidence_below_threshold_override():
    validator = SignalValidator(min_confidence=75)
    # Confidence is 60%, below 75%
    raw = GeminiAnalysisResponse(
        symbol="XAUUSD",
        timeframe="M5",
        candle_time="2026-08-26T20:00:00Z",
        analysis_time="2026-08-26T20:05:00Z",
        signal="SHORT",
        confidence=60,
        current_price=2650.0,
        entry=2650.0,
        stop_loss=2660.0,
        take_profit_1=2635.0
    )

    res = validator.validate_and_enrich(raw)
    assert res.signal == "NO_TRADE"
    assert "Confidence (60%) below threshold" in res.warnings
