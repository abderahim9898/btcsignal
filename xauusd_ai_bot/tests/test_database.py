import os
import pytest
from database import DatabaseManager
from models import FullAnalysisResult


def test_database_operations(tmp_path):
    db_file = tmp_path / "test_xauusd.db"
    db_mgr = DatabaseManager(db_path=str(db_file))

    # Check deduplication on fresh DB
    assert not db_mgr.is_candle_analyzed("XAUUSD", "M5", "2026-08-26T20:00:00Z")

    analysis = FullAnalysisResult(
        symbol="XAUUSD",
        timeframe="M5",
        candle_time="2026-08-26T20:00:00Z",
        analysis_time="2026-08-26T20:05:00Z",
        current_price=2650.0,
        signal="LONG",
        confidence=80,
        entry=2650.0,
        stop_loss=2640.0,
        take_profit_1=2665.0,
        risk_reward_tp1=1.5,
        trend="BULLISH",
        trend_strength=80,
        momentum="POSITIVE",
        volatility="NORMAL",
        setup_type="BULLISH_RETEST",
        support_zones="2640-2645",
        resistance_zones="2665-2670",
        market_structure="BULLISH",
        reasoning="Test reasoning",
        warnings=""
    )

    # Save analysis
    saved = db_mgr.save_analysis(analysis)
    assert saved

    # Verify deduplication prevents double insertion
    assert db_mgr.is_candle_analyzed("XAUUSD", "M5", "2026-08-26T20:00:00Z")
    saved_again = db_mgr.save_analysis(analysis)
    assert not saved_again

    # Query recent
    recent = db_mgr.get_recent_analyses(limit=5)
    assert len(recent) == 1
    assert recent[0]["candle_time"] == "2026-08-26T20:00:00Z"
    assert recent[0]["signal"] == "LONG"
