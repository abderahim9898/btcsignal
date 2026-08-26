from typing import Optional, Literal, Any
from pydantic import BaseModel, Field


class BiQuoteQuote(BaseModel):
    symbol: str
    bid: float = 0.0
    ask: float = 0.0
    mid: float = 0.0
    last: float = 0.0
    volume: int = 0
    timestamp: str = ""
    source: Optional[str] = None
    high: float = 0.0
    low: float = 0.0
    direction: Optional[str] = None
    dayDiffPercent: Optional[float] = None
    description: Optional[str] = None
    time: Optional[str] = None
    spread: float = 0.0
    stale: bool = False
    quoteAgeSeconds: int = 0
    marketState: str = "open"
    lastQuoteAt: Optional[str] = None


class CandleBar(BaseModel):
    openTime: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    tickVolume: float = 0.0
    isOpen: bool = False


class ZoneLevel(BaseModel):
    low: float
    high: float
    label: Optional[str] = None


class TechnicalSnapshot(BaseModel):
    ema20: float
    ema50: float
    ema200: float
    ema_alignment: str  # "BULLISH", "BEARISH", "MIXED"
    rsi14: float
    rsi_previous: float
    rsi_direction: str  # "UP", "DOWN", "FLAT"
    rsi_state: str  # "OVERBOUGHT", "OVERSOLD", "NEUTRAL"
    macd: float
    macd_signal: float
    macd_histogram: float
    macd_state: str
    atr14: float
    adx14: float
    adx_trend_strength: str  # "STRONG_TREND", "WEAK_TREND", "RANGING"
    stoch_k: float
    stoch_d: float
    stoch_state: str
    avg_volume: float
    price_change: float
    rate_of_change: float
    body_size: float
    upper_wick: float
    lower_wick: float
    body_range_ratio: float


class GeminiAnalysisResponse(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: str = "M5"
    candle_time: str
    analysis_time: str

    signal: Literal["LONG", "SHORT", "NO_TRADE"]
    confidence: int = Field(ge=0, le=100)

    current_price: Optional[float] = None
    entry: Optional[float] = None
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None

    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None

    trend: str = "NEUTRAL"
    trend_strength: int = 50
    momentum: str = "NEUTRAL"
    volatility: str = "NORMAL"

    support_zones: list[str] = Field(default_factory=list)
    resistance_zones: list[str] = Field(default_factory=list)

    market_structure: str = ""
    setup_type: str = ""
    invalidation_level: Optional[float] = None

    bullish_scenario: str = ""
    bullish_probability: int = 50
    bearish_scenario: str = ""
    bearish_probability: int = 50

    reasoning: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FullAnalysisResult(BaseModel):
    id: Optional[int] = None
    symbol: str
    timeframe: str
    candle_time: str
    analysis_time: str
    current_price: float

    signal: str  # "LONG", "SHORT", "NO_TRADE"
    confidence: int

    entry: Optional[float] = None
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None

    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None

    risk: Optional[float] = None
    reward_tp1: Optional[float] = None
    reward_tp2: Optional[float] = None
    reward_tp3: Optional[float] = None

    risk_reward_tp1: Optional[float] = None
    risk_reward_tp2: Optional[float] = None
    risk_reward_tp3: Optional[float] = None

    trend: str
    trend_strength: int
    momentum: str
    volatility: str

    setup_type: str
    support_zones: str  # JSON or comma-separated string
    resistance_zones: str
    invalidation_level: Optional[float] = None

    bullish_scenario: str = ""
    bullish_probability: int = 50
    bearish_scenario: str = ""
    bearish_probability: int = 50

    market_structure: str
    reasoning: str  # formatted lines or JSON string
    warnings: str

    raw_gemini_response: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    created_at: str = ""
