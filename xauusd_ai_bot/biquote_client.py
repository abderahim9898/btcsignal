import time
from typing import Optional, Tuple
import requests
import pandas as pd
from config import config
from logger import logger
from models import BiQuoteQuote, CandleBar


class BiquoteClient:
    """Client for retrieving real-time quotes and OHLC candle data from BiQuote.io."""

    def __init__(self, base_url: Optional[str] = None, max_retries: int = 3, backoff_factor: float = 1.5):
        self.base_url = (base_url or config.biquote_base_url).rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "XAUUSD-AI-Trading-Bot/1.0",
            "Accept": "application/json"
        })

    def _request_with_retry(self, url: str, params: Optional[dict] = None) -> dict:
        """Helper method to make HTTP GET requests with exponential backoff."""
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"BIQUOTE REQUEST: GET {url} (params={params}, attempt={attempt})")
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                return data
            except (requests.RequestException, ValueError) as e:
                logger.warning(f"BiQuote API error (attempt {attempt}/{self.max_retries}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"BiQuote API failed after {self.max_retries} attempts.")
                    raise
                time.sleep(self.backoff_factor ** attempt)
        return {}

    def get_quote(self, symbol: str = config.symbol) -> Optional[BiQuoteQuote]:
        """Fetch real-time current market quote for symbol."""
        url = f"{self.base_url}/{symbol}"
        try:
            data = self._request_with_retry(url)
            if not data:
                return None
            
            # Map fields safely
            quote = BiQuoteQuote(
                symbol=data.get("symbol", symbol),
                bid=float(data.get("bid", 0.0)),
                ask=float(data.get("ask", 0.0)),
                mid=float(data.get("mid", 0.0)),
                last=float(data.get("last", 0.0)),
                volume=int(data.get("volume", 0)),
                timestamp=str(data.get("timestamp", "")),
                source=data.get("source"),
                high=float(data.get("high", 0.0)),
                low=float(data.get("low", 0.0)),
                direction=data.get("direction"),
                dayDiffPercent=float(data.get("dayDiffPercent")) if data.get("dayDiffPercent") is not None else None,
                description=data.get("description"),
                time=data.get("time"),
                spread=float(data.get("spread", 0.0)),
                stale=bool(data.get("stale", False)),
                quoteAgeSeconds=int(data.get("quoteAgeSeconds", 0)),
                marketState=str(data.get("marketState", "open")),
                lastQuoteAt=data.get("lastQuoteAt")
            )
            # If mid is missing but bid & ask exist, calculate mid
            if quote.mid == 0.0 and quote.bid > 0 and quote.ask > 0:
                quote.mid = round((quote.bid + quote.ask) / 2.0, 5)

            logger.info(f"PRICE FETCHED: {symbol} mid={quote.mid} bid={quote.bid} ask={quote.ask} age={quote.quoteAgeSeconds}s stale={quote.stale}")
            return quote
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            return None

    def get_ohlc(self, symbol: str = config.symbol, interval: str = config.timeframe, limit: int = config.candle_count) -> list[dict]:
        """Fetch raw OHLC bars from BiQuote API."""
        url = f"{self.base_url}/{symbol}/ohlc"
        params = {"interval": interval, "limit": limit}
        try:
            data = self._request_with_retry(url, params=params)
            bars = data.get("bars", [])
            logger.info(f"CANDLES FETCHED: {len(bars)} raw candles retrieved for {symbol} ({interval})")
            return bars
        except Exception as e:
            logger.error(f"Failed to fetch OHLC for {symbol}: {e}")
            return []

    def validate_quote(self, quote: Optional[BiQuoteQuote], max_age_seconds: int = config.max_quote_age_seconds, ignore_stale: bool = False) -> Tuple[bool, str]:
        """Validates quote presence, non-zero price, freshness, and staleness flag."""
        if not quote:
            return False, "Quote object is null or empty"
        if quote.mid <= 0 and quote.last <= 0 and quote.bid <= 0:
            return False, "Quote price is zero or negative"
        if not ignore_stale:
            if quote.stale:
                return False, f"Quote marked stale by BiQuote (stale=True, age={quote.quoteAgeSeconds}s)"
            if quote.quoteAgeSeconds > max_age_seconds:
                return False, f"Quote age {quote.quoteAgeSeconds}s exceeds MAX_QUOTE_AGE_SECONDS ({max_age_seconds}s)"
        return True, "Quote valid"

    def validate_candles(self, bars: list[dict]) -> Tuple[bool, str]:
        """Validates raw candle structures."""
        if not bars:
            return False, "No candle bars returned"
        for idx, bar in enumerate(bars):
            if "openTime" not in bar or "open" not in bar or "high" not in bar or "low" not in bar or "close" not in bar:
                return False, f"Candle at index {idx} missing essential OHLC fields"
            o, h, l, c = bar["open"], bar["high"], bar["low"], bar["close"]
            if not (isinstance(o, (int, float)) and isinstance(h, (int, float)) and isinstance(l, (int, float)) and isinstance(c, (int, float))):
                return False, f"Candle at index {idx} has non-numeric OHLC values"
            if h < l or h < o or h < c or l > o or l > c:
                return False, f"Candle at index {idx} invalid OHLC high/low relationships (O:{o}, H:{h}, L:{l}, C:{c})"
        return True, "Candle bars structure valid"

    def get_closed_candles(self, symbol: str = config.symbol, interval: str = config.timeframe, limit: int = config.candle_count) -> list[CandleBar]:
        """Retrieves candles, filters out open candles (isOpen == True), and returns normalized list of CandleBars."""
        raw_bars = self.get_ohlc(symbol, interval, limit + 10)  # fetch a few extra to account for filtering
        valid, msg = self.validate_candles(raw_bars)
        if not valid:
            logger.warning(f"Candle validation warning: {msg}")
            return []

        closed_bars = []
        for b in raw_bars:
            if not b.get("isOpen", False):
                closed_bars.append(CandleBar(
                    openTime=str(b["openTime"]),
                    open=float(b["open"]),
                    high=float(b["high"]),
                    low=float(b["low"]),
                    close=float(b["close"]),
                    volume=float(b.get("volume", 0.0)),
                    tickVolume=float(b.get("tickVolume", 0.0)),
                    isOpen=False
                ))

        logger.info(f"CLOSED CANDLE FOUND: Filtered {len(raw_bars) - len(closed_bars)} open candles. {len(closed_bars)} closed candles remaining.")
        return closed_bars

    def normalize_candles(self, bars: list[CandleBar]) -> pd.DataFrame:
        """Converts closed CandleBars to a clean, chronologically sorted pandas DataFrame."""
        if not bars:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "tickVolume"])

        data = [{
            "timestamp": b.openTime,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
            "tickVolume": b.tickVolume
        } for b in bars]

        df = pd.DataFrame(data)
        # Convert timestamp to ISO/datetime and sort ascending (oldest first, newest closed candle last)
        df["dt"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("dt").drop(columns=["dt"]).reset_index(drop=True)
        return df
