"""Data validation utilities."""
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from pydantic import BaseModel, validator


class MeetingDurationValidator(BaseModel):
    """Validator for meeting duration."""
    duration_min: int
    
    @validator("duration_min")
    def validate_duration(cls, v):
        """Validate meeting duration."""
        if v < 15:
            raise ValueError("Meeting duration must be at least 15 minutes")
        if v > 480:  # 8 hours
            raise ValueError("Meeting duration cannot exceed 8 hours")
        if v % 5 != 0:
            raise ValueError("Meeting duration must be in 5-minute increments")
        return v


class TimeSlotValidator(BaseModel):
    """Validator for time slots."""
    start: datetime
    end: datetime
    duration_min: int
    
    @validator("end")
    def validate_end_time(cls, v, values):
        """Validate end time."""
        if "start" in values:
            duration = (v - values["start"]).total_seconds() / 60
            if duration != values.get("duration_min", 0):
                raise ValueError("End time does not match duration")
        return v
    
    @validator("start")
    def validate_start_time(cls, v):
        """Validate start time."""
        if v < datetime.now(timezone.utc):
            raise ValueError("Start time cannot be in the past")
        return v


class WorkingHoursValidator(BaseModel):
    """Validator for working hours."""
    start_hour: int
    end_hour: int
    
    @validator("start_hour")
    def validate_start_hour(cls, v):
        """Validate start hour."""
        if not 0 <= v <= 23:
            raise ValueError("Start hour must be between 0 and 23")
        return v
    
    @validator("end_hour")
    def validate_end_hour(cls, v):
        """Validate end hour."""
        if not 0 <= v <= 23:
            raise ValueError("End hour must be between 0 and 23")
        return v
    
    @validator("end_hour")
    def validate_end_after_start(cls, v, values):
        """Validate end hour is after start hour."""
        if "start_hour" in values and v <= values["start_hour"]:
            raise ValueError("End hour must be after start hour")
        return v


def validate_telegram_username(username: str) -> bool:
    """Validate Telegram username format."""
    if not username:
        return False
    
    # Telegram username rules: 5-32 characters, alphanumeric and underscores
    pattern = r"^[a-zA-Z0-9_]{5,32}$"
    return bool(re.match(pattern, username))


def validate_timezone(timezone_str: str) -> bool:
    """Validate timezone string."""
    try:
        import pytz
        pytz.timezone(timezone_str)
        return True
    except:
        return False


def validate_participant_list(participants: List[int], max_participants: int = 30) -> bool:
    """Validate participant list."""
    if not participants:
        return False
    
    if len(participants) > max_participants:
        return False
    
    # Check for duplicates
    if len(participants) != len(set(participants)):
        return False
    
    return True


def validate_meeting_topic(topic: str) -> bool:
    """Validate meeting topic."""
    if not topic:
        return False
    
    if len(topic) > 500:
        return False
    
    # Check for potentially harmful content
    harmful_patterns = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, topic, re.IGNORECASE):
            return False
    
    return True
