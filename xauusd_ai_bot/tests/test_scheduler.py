import pytest
from datetime import datetime
import pytz
from scheduler import MarketScheduler


def test_scheduler_working_hours():
    scheduler = MarketScheduler(tz_name="Africa/Casablanca", start_hour=10, end_hour=20)
    tz = pytz.timezone("Africa/Casablanca")

    # 14:30 is working hour
    dt_work = tz.localize(datetime(2026, 8, 26, 14, 30, 0))
    assert scheduler.is_within_working_hours(dt_work)

    # 09:30 is outside working hour
    dt_off = tz.localize(datetime(2026, 8, 26, 9, 30, 0))
    assert not scheduler.is_within_working_hours(dt_off)

    # 20:30 is outside working hour
    dt_evening = tz.localize(datetime(2026, 8, 26, 20, 30, 0))
    assert not scheduler.is_within_working_hours(dt_evening)


def test_scheduler_next_execution_time_calculation():
    scheduler = MarketScheduler(tz_name="Africa/Casablanca", start_hour=10, end_hour=20)
    tz = pytz.timezone("Africa/Casablanca")

    # If 14:37 -> next should be 14:40
    now_1437 = tz.localize(datetime(2026, 8, 26, 14, 37, 22))
    next_exec = scheduler.get_next_execution_time(now_1437)
    assert next_exec.hour == 14
    assert next_exec.minute == 40
    assert next_exec.second == 0

    # If 09:30 -> next should be 10:00 today
    now_0930 = tz.localize(datetime(2026, 8, 26, 9, 30, 0))
    next_exec_morning = scheduler.get_next_execution_time(now_0930)
    assert next_exec_morning.day == 26
    assert next_exec_morning.hour == 10
    assert next_exec_morning.minute == 0

    # If 20:30 -> next should be 10:00 tomorrow
    now_2030 = tz.localize(datetime(2026, 8, 26, 20, 30, 0))
    next_exec_tomorrow = scheduler.get_next_execution_time(now_2030)
    assert next_exec_tomorrow.day == 27
    assert next_exec_tomorrow.hour == 10
    assert next_exec_tomorrow.minute == 0
