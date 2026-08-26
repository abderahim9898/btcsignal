import pytest
from models import BiQuoteQuote, CandleBar, GeminiAnalysisResponse, FullAnalysisResult


def test_biquote_quote_model():
    quote = BiQuoteQuote(
        symbol="XAUUSD",
        bid=2650.50,
        ask=2650.80,
        mid=2650.65,
        last=2650.60,
        volume=100,
        timestamp="2026-08-26T20:00:00Z",
        stale=False,
        quoteAgeSeconds=10
    )
    assert quote.symbol == "XAUUSD"
    assert quote.mid == 2650.65
    assert not quote.stale


def test_candle_bar_model():
    bar = CandleBar(
        openTime="2026-08-26T20:00:00Z",
        open=2650.0,
        high=2655.0,
        low=2648.0,
        close=2652.0,
        volume=120.0,
        isOpen=False
    )
    assert bar.open == 2650.0
    assert not bar.isOpen


def test_gemini_response_schema():
    resp = GeminiAnalysisResponse(
        symbol="XAUUSD",
        timeframe="M5",
        candle_time="2026-08-26T20:00:00Z",
        analysis_time="2026-08-26T20:05:00Z",
        signal="LONG",
        confidence=85,
        current_price=2652.0,
        entry=2652.0,
        stop_loss=2645.0,
        take_profit_1=2660.0,
        reasoning=["Bullish EMA alignment", "RSI positive"]
    )
    assert resp.signal == "LONG"
    assert resp.confidence == 85
    assert resp.stop_loss == 2645.0
