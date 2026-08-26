from datetime import datetime, timezone
import pytz


def get_current_utc_time() -> datetime:
    """Returns the current UTC datetime."""
    return datetime.now(timezone.utc)


def convert_utc_to_timezone(utc_dt: datetime, tz_name: str = "Africa/Casablanca") -> datetime:
    """Converts a UTC datetime object to the target timezone (default: Africa/Casablanca)."""
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    target_tz = pytz.timezone(tz_name)
    return utc_dt.astimezone(target_tz)


def format_morocco_time(utc_dt: datetime) -> str:
    """Formats datetime string for Telegram and display in Morocco local time."""
    local_dt = convert_utc_to_timezone(utc_dt, "Africa/Casablanca")
    return local_dt.strftime("%Y-%m-%d %H:%M:%S Morocco")


def make_candle_key(symbol: str, timeframe: str, candle_time: str) -> str:
    """Generates a unique string key for candle deduplication: symbol_timeframe_candle_time."""
    return f"{symbol.upper()}_{timeframe.lower()}_{candle_time}"


def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses an ISO format datetime string into a timezone-aware UTC datetime."""
    clean_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt
