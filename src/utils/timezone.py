"""Timezone utilities."""
from datetime import datetime, timezone
from typing import Optional

import pytz


def get_user_timezone(timezone_str: str) -> pytz.BaseTzInfo:
    """Get timezone object from string."""
    try:
        return pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        return pytz.UTC


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def to_utc(dt: datetime, user_tz: str) -> datetime:
    """Convert datetime from user timezone to UTC."""
    if dt.tzinfo is None:
        # Assume datetime is in user timezone
        user_timezone = get_user_timezone(user_tz)
        dt = user_timezone.localize(dt)
    
    return dt.astimezone(timezone.utc)


def from_utc(dt: datetime, user_tz: str) -> datetime:
    """Convert datetime from UTC to user timezone."""
    if dt.tzinfo is None:
        # Assume datetime is in UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    user_timezone = get_user_timezone(user_tz)
    return dt.astimezone(user_timezone)


def format_datetime(dt: datetime, user_tz: str, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime in user timezone."""
    local_dt = from_utc(dt, user_tz)
    return local_dt.strftime(format_str)


def parse_datetime(dt_str: str, user_tz: str, format_str: str = "%Y-%m-%d %H:%M") -> datetime:
    """Parse datetime string in user timezone and return UTC datetime."""
    user_timezone = get_user_timezone(user_tz)
    dt = datetime.strptime(dt_str, format_str)
    dt = user_timezone.localize(dt)
    return dt.astimezone(timezone.utc)
