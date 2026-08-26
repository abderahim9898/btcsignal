from typing import Optional, Dict, Any
from config import config
from logger import logger
from models import FullAnalysisResult
from market_data import MarketDataManager
from indicators import compute_indicators
from price_action import analyze_price_action
from market_structure import analyze_market_structure
from support_resistance import find_support_resistance_zones, format_sr_zones_str
from smc_ict import detect_fair_value_gaps, detect_order_blocks, detect_liquidity_sweeps, calculate_premium_discount
from gemini_client import GeminiClient
from signal_validator import SignalValidator
from database import DatabaseManager
from telegram_bot import TelegramNotifier
from chart_generator import generate_candlestick_chart
from utils import get_current_utc_time


class MarketAnalyzer:
    """Orchestrates market data fetching, ICT/SMC analysis, AI prompt construction, validation, DB saving, and Telegram notification."""

    def __init__(
        self,
        market_data_mgr: Optional[MarketDataManager] = None,
        gemini_client: Optional[GeminiClient] = None,
        validator: Optional[SignalValidator] = None,
        db_mgr: Optional[DatabaseManager] = None,
        telegram_notifier: Optional[TelegramNotifier] = None
    ):
        self.market_data_mgr = market_data_mgr or MarketDataManager()
        self.gemini_client = gemini_client or GeminiClient()
        self.validator = validator or SignalValidator()
        self.db_mgr = db_mgr or DatabaseManager()
        self.telegram = telegram_notifier or TelegramNotifier()

    def run_analysis_cycle(self, ignore_stale: bool = False, force: bool = False, only_signals: bool = False) -> Optional[FullAnalysisResult]:
        """Runs a single 5-minute market analysis cycle focusing on ICT / Smart Money Concepts."""
        logger.info("=== STARTING ICT/SMC ANALYSIS CYCLE ===")

        # 1. Fetch & Validate Market Data
        quote, df, status = self.market_data_mgr.get_validated_market_snapshot(
            symbol=config.symbol,
            interval=config.timeframe,
            min_candles=config.candle_count,
            max_quote_age=config.max_quote_age_seconds,
            ignore_stale=ignore_stale
        )

        if status != "OK" or quote is None or df is None:
            logger.warning(f"Analysis cycle aborted. Data status: {status}")
            return None

        # 2. Extract latest closed candle timestamp
        latest_candle = df.iloc[-1]
        candle_time = str(latest_candle["timestamp"])
        analysis_time = get_current_utc_time().isoformat()
        current_price = round(float(quote.mid), 2)

        logger.info(f"CLOSED CANDLE FOUND: {config.symbol} {config.timeframe} at {candle_time}, Current Mid={current_price}")

        # 3. Duplicate Prevention Check (Bypassed if force=True)
        if not force and self.db_mgr.is_candle_analyzed(config.symbol, config.timeframe, candle_time):
            logger.info(f"DUPLICATE CANDLE: {config.symbol} {config.timeframe} {candle_time} already analyzed. Skipping.")
            return None

        # 4. Calculate Market Structure & ICT Concepts
        logger.info("Analyzing Market Structure (MSS / CHOCH / BOS)...")
        ms = analyze_market_structure(df, lookback_candles=50)

        logger.info("Detecting ICT Fair Value Gaps (FVG)...")
        fvgs = detect_fair_value_gaps(df)

        logger.info("Detecting ICT Order Blocks (OB)...")
        order_blocks = detect_order_blocks(df)

        logger.info("Detecting ICT Liquidity Sweeps (BSL/SSL)...")
        sweeps = detect_liquidity_sweeps(df)

        logger.info("Calculating Premium vs Discount Pricing...")
        prem_disc = calculate_premium_discount(df)

        # 5. Support & Resistance Zones
        s_zones, r_zones = find_support_resistance_zones(df, current_price=current_price)
        s_zones_str = format_sr_zones_str(s_zones)
        r_zones_str = format_sr_zones_str(r_zones)

        # 6. Build Compact Market Snapshot Context for Gemini (ICT / SMC Focus)
        market_context: Dict[str, Any] = {
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "candle_time": candle_time,
            "analysis_time": analysis_time,
            "current_price": current_price,
            "bid": quote.bid,
            "ask": quote.ask,
            "quote_age_seconds": quote.quoteAgeSeconds,
            "ict_smc_analysis": {
                "market_structure_shift": ms,
                "fair_value_gaps": fvgs,
                "order_blocks": order_blocks,
                "liquidity_sweeps": sweeps,
                "premium_discount_pricing": prem_disc
            },
            "support_zones": s_zones_str,
            "resistance_zones": r_zones_str,
            "recent_candles_summary": [
                {
                    "time": str(row["timestamp"]),
                    "open": round(row["open"], 2),
                    "high": round(row["high"], 2),
                    "low": round(row["low"], 2),
                    "close": round(row["close"], 2)
                } for _, row in df.iloc[-5:].iterrows()
            ]
        }

        # 7. Query Gemini AI API
        logger.info("Sending ICT/SMC market snapshot to Gemini AI...")
        gemini_resp = self.gemini_client.analyze_market_snapshot(market_context)

        if not gemini_resp:
            logger.error("Gemini API failed to return a response. Aborting analysis cycle.")
            return None

        # 8. Validate & Calculate Risk/Reward in Python
        logger.info("Validating Gemini response and calculating Risk/Reward...")
        raw_json_str = gemini_resp.model_dump_json()
        validated_analysis = self.validator.validate_and_enrich(gemini_resp, raw_json_str)

        # Ensure correct candle_time and current_price
        validated_analysis.candle_time = candle_time
        validated_analysis.current_price = current_price

        # 9. Save Analysis to SQLite Database
        logger.info("Saving analysis record to SQLite database...")
        self.db_mgr.save_analysis(validated_analysis)

        # 10. Generate Candlestick Chart Image
        logger.info("Generating candlestick chart image...")
        chart_path = generate_candlestick_chart(df, validated_analysis)

        # 11. Send Telegram Notification with Chart Photo & Arabic Text
        logger.info("Sending Arabic Telegram notification with chart photo...")
        self.telegram.send_analysis_notification(validated_analysis, chart_path=chart_path, only_signals=only_signals)

        logger.info(f"=== ANALYSIS CYCLE COMPLETED ({validated_analysis.signal}) ===")
        return validated_analysis
