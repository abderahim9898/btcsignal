import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file if available
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


@dataclass
class Config:
    # BiQuote API
    biquote_base_url: str = os.getenv("BIQUOTE_BASE_URL", "https://biquote.io/api")
    symbol: str = os.getenv("SYMBOL", "XAUUSD")
    timeframe: str = os.getenv("TIMEFRAME", "5m")
    candle_count: int = int(os.getenv("CANDLE_COUNT", "200"))
    max_quote_age_seconds: int = int(os.getenv("MAX_QUOTE_AGE_SECONDS", "300"))

    # Gemini AI
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    min_confidence: int = int(os.getenv("MIN_CONFIDENCE", "70"))

    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    only_send_trade_signals: bool = os.getenv("ONLY_SEND_TRADE_SIGNALS", "false").lower() in ("true", "1", "yes")

    # Timezone & Schedule
    timezone: str = os.getenv("TIMEZONE", "Africa/Casablanca")
    work_start_hour: int = int(os.getenv("WORK_START_HOUR", "10"))
    work_end_hour: int = int(os.getenv("WORK_END_HOUR", "20"))

    # Database
    db_path: str = os.getenv("DB_PATH", "xauusd_ai.db")

    def validate(self) -> list[str]:
        """Validate configuration settings and return list of warnings/errors."""
        errors = []
        if not self.biquote_base_url:
            errors.append("BIQUOTE_BASE_URL is missing.")
        if not self.symbol:
            errors.append("SYMBOL is missing.")
        if self.candle_count < 50:
            errors.append("CANDLE_COUNT should be at least 50.")
        if self.min_confidence < 0 or self.min_confidence > 100:
            errors.append("MIN_CONFIDENCE must be between 0 and 100.")
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is not set in .env")
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is not set in .env")
        if not self.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID is not set in .env")
        return errors


config = Config()
