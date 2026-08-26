import time
from datetime import datetime, timedelta
from typing import Optional
import pytz
from config import config
from logger import logger
from utils import convert_utc_to_timezone, get_current_utc_time


class MarketScheduler:
    """Manages timezone-aware 5-minute candle interval scheduling for Morocco local time (10:00 - 20:00)."""

    def __init__(
        self,
        tz_name: str = config.timezone,
        start_hour: int = config.work_start_hour,
        end_hour: int = config.work_end_hour
    ):
        self.tz_name = tz_name
        self.tz = pytz.timezone(tz_name)
        self.start_hour = start_hour
        self.end_hour = end_hour

    def get_current_local_time(self) -> datetime:
        """Returns current datetime localized to configured timezone."""
        utc_now = get_current_utc_time()
        return convert_utc_to_timezone(utc_now, self.tz_name)

    def is_within_working_hours(self, dt: datetime) -> bool:
        """Checks if localized datetime is within the allowed operating schedule (10:00 - 20:00)."""
        local_dt = convert_utc_to_timezone(dt, self.tz_name) if dt.tzinfo else self.tz.localize(dt)
        # Allowed if hour is between start_hour and end_hour
        # Note: Exactly at end_hour:00:00 is allowed for the final 20:00 candle analysis
        if self.start_hour <= local_dt.hour < self.end_hour:
            return True
        if local_dt.hour == self.end_hour and local_dt.minute == 0 and local_dt.second <= 30:
            return True
        return False

    def get_next_execution_time(self, now_dt: Optional[datetime] = None) -> datetime:
        """
        Calculates the exact localized datetime for the next valid 5-minute analysis tick.
        """
        if now_dt is None:
            now_dt = get_current_utc_time()

        local_dt = convert_utc_to_timezone(now_dt, self.tz_name)

        # 1. If before start_hour today (e.g. 09:30) -> today at start_hour:00:00
        if local_dt.hour < self.start_hour:
            next_dt = local_dt.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            return next_dt

        # 2. If after end_hour today (e.g. 20:01) -> tomorrow at start_hour:00:00
        if local_dt.hour > self.end_hour or (local_dt.hour == self.end_hour and (local_dt.minute > 0 or local_dt.second > 0)):
            tomorrow = local_dt.date() + timedelta(days=1)
            next_dt = self.tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, self.start_hour, 0, 0))
            return next_dt

        # 3. Within working hours (10:00 to 20:00) -> find next 5-minute boundary
        next_minute = ((local_dt.minute // 5) + 1) * 5
        if next_minute == 60:
            next_dt = local_dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            next_dt = local_dt.replace(minute=next_minute, second=0, microsecond=0)

        # Check if next_dt exceeds end_hour:00:00
        cutoff = local_dt.replace(hour=self.end_hour, minute=0, second=0, microsecond=0)
        if next_dt > cutoff:
            tomorrow = local_dt.date() + timedelta(days=1)
            next_dt = self.tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, self.start_hour, 0, 0))

        return next_dt

    def wait_until_next_tick(self) -> float:
        """
        Calculates remaining seconds until next execution mark, logs wait duration,
        and sleeps until then. Returns wait time in seconds.
        """
        local_now = self.get_current_local_time()
        next_exec = self.get_next_execution_time(get_current_utc_time())

        delta = (next_exec - local_now).total_seconds()
        if delta <= 0:
            delta = 1.0  # safety floor

        logger.info(f"SCHEDULER: Current local time: {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"SCHEDULER: Next scheduled execution: {next_exec.strftime('%Y-%m-%d %H:%M:%S %Z')} (in {round(delta, 1)} seconds)")

        time.sleep(delta)
        return delta
