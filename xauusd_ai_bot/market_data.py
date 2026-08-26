from typing import Tuple, Optional
import pandas as pd
from biquote_client import BiquoteClient
from config import config
from logger import logger
from models import BiQuoteQuote


class MarketDataManager:
    """Manages market data retrieval, strict validation, and dataframe preparation."""

    def __init__(self, biquote_client: Optional[BiquoteClient] = None):
        self.client = biquote_client or BiquoteClient()

    def get_validated_market_snapshot(
        self,
        symbol: str = config.symbol,
        interval: str = config.timeframe,
        min_candles: int = config.candle_count,
        max_quote_age: int = config.max_quote_age_seconds,
        ignore_stale: bool = False
    ) -> Tuple[Optional[BiQuoteQuote], Optional[pd.DataFrame], str]:
        """
        Retrieves real-time quote and closed OHLC candles.
        Validates all conditions. Returns (quote, df, status_code).
        Status code will be "OK", "DATA_INSUFFICIENT", "DATA_UNAVAILABLE", or "VALIDATION_FAILED".
        """
        # 1. Fetch current price quote
        quote = self.client.get_quote(symbol)
        valid_quote, quote_msg = self.client.validate_quote(quote, max_quote_age, ignore_stale=ignore_stale)
        if not valid_quote:
            logger.warning(f"Market quote validation failed: {quote_msg}")
            return None, None, "DATA_UNAVAILABLE"

        # 2. Fetch closed candles
        closed_bars = self.client.get_closed_candles(symbol, interval, min_candles + 10)
        if len(closed_bars) < min_candles:
            if len(closed_bars) >= 50:
                logger.info(f"BiQuote returned {len(closed_bars)} closed candles (requested {min_candles}). Proceeding with available {len(closed_bars)} candles.")
            else:
                logger.warning(f"DATA_INSUFFICIENT: Got {len(closed_bars)} closed candles, but minimum 50 required.")
                return quote, None, "DATA_INSUFFICIENT"

        # 3. Normalize to DataFrame
        df = self.client.normalize_candles(closed_bars)

        # 4. Strict DataFrame Validation
        valid_df, df_msg = self.validate_dataframe(df, min_candles)
        if not valid_df:
            logger.error(f"CANDLE VALIDATION FAILED: {df_msg}")
            return quote, None, "VALIDATION_FAILED"

        logger.info(f"MARKET DATA VALIDATED: {symbol} quote mid={quote.mid}, DataFrame with {len(df)} candles ready.")
        return quote, df, "OK"

    def validate_dataframe(self, df: pd.DataFrame, min_candles: int) -> Tuple[bool, str]:
        """Performs rigorous numerical and logical checks on candle DataFrame."""
        if df.empty:
            return False, "DataFrame is empty"

        if len(df) < min_candles:
            if len(df) >= 50:
                logger.info(f"BiQuote returned {len(df)} candles (requested {min_candles}). Proceeding with available {len(df)} candles.")
            else:
                return False, f"DataFrame length {len(df)} is below minimum threshold 50"

        required_cols = ["timestamp", "open", "high", "low", "close"]
        for col in required_cols:
            if col not in df.columns:
                return False, f"Missing required column '{col}'"

        # Check for NaN / Null values
        if df[required_cols].isnull().any().any():
            return False, "DataFrame contains NaN / Null values"

        # Check numeric types and non-negative
        for col in ["open", "high", "low", "close"]:
            if (df[col] <= 0).any():
                return False, f"Column '{col}' contains non-positive price values"

        # OHLC logical relationships
        if not (df["high"] >= df["low"]).all():
            return False, "high >= low constraint violated"
        if not (df["high"] >= df["open"]).all():
            return False, "high >= open constraint violated"
        if not (df["high"] >= df["close"]).all():
            return False, "high >= close constraint violated"
        if not (df["low"] <= df["open"]).all():
            return False, "low <= open constraint violated"
        if not (df["low"] <= df["close"]).all():
            return False, "low <= close constraint violated"

        # Timestamp duplicate check
        if df["timestamp"].duplicated().any():
            return False, "Duplicate timestamps detected in candle data"

        # Chronological order check
        timestamps = pd.to_datetime(df["timestamp"])
        if not timestamps.is_monotonic_increasing:
            return False, "Candles are not sorted chronologically ascending"

        return True, "DataFrame validation passed"
