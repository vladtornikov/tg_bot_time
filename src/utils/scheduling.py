"""Scheduling utilities for time slot computation."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import pytz


def snap_to_interval(dt: datetime, interval_minutes: int = 15) -> datetime:
    """Snap datetime to the nearest interval."""
    # Round down to the nearest interval
    minutes = dt.minute
    snapped_minutes = (minutes // interval_minutes) * interval_minutes
    
    return dt.replace(minute=snapped_minutes, second=0, microsecond=0)


def generate_time_slots(
    start: datetime,
    end: datetime,
    duration_minutes: int,
    interval_minutes: int = 15,
) -> List[Tuple[datetime, datetime]]:
    """Generate time slots between start and end times."""
    slots = []
    current = snap_to_interval(start, interval_minutes)
    
    while current + timedelta(minutes=duration_minutes) <= end:
        slot_end = current + timedelta(minutes=duration_minutes)
        slots.append((current, slot_end))
        current += timedelta(minutes=interval_minutes)
    
    return slots


def clip_to_working_hours(
    slots: List[Tuple[datetime, datetime]],
    user_tz: str,
    working_start_hour: int = 8,
    working_end_hour: int = 20,
) -> List[Tuple[datetime, datetime]]:
    """Clip time slots to working hours in user timezone."""
    user_timezone = pytz.timezone(user_tz)
    clipped_slots = []
    
    for start, end in slots:
        # Convert to user timezone
        start_local = start.astimezone(user_timezone)
        end_local = end.astimezone(user_timezone)
        
        # Check if slot overlaps with working hours
        working_start = start_local.replace(hour=working_start_hour, minute=0, second=0, microsecond=0)
        working_end = start_local.replace(hour=working_end_hour, minute=0, second=0, microsecond=0)
        
        # If slot starts before working hours, adjust start
        if start_local < working_start:
            start = working_start.astimezone(timezone.utc)
        
        # If slot ends after working hours, adjust end
        if end_local > working_end:
            end = working_end.astimezone(timezone.utc)
        
        # Only include if slot is still valid after clipping
        if start < end:
            clipped_slots.append((start, end))
    
    return clipped_slots


def find_intersection(
    slots1: List[Tuple[datetime, datetime]],
    slots2: List[Tuple[datetime, datetime]],
) -> List[Tuple[datetime, datetime]]:
    """Find intersection of two slot lists."""
    intersection = []
    
    for start1, end1 in slots1:
        for start2, end2 in slots2:
            # Find overlap
            overlap_start = max(start1, start2)
            overlap_end = min(end1, end2)
            
            if overlap_start < overlap_end:
                intersection.append((overlap_start, overlap_end))
    
    return intersection


def find_common_slots(
    all_slots: List[List[Tuple[datetime, datetime]]],
) -> List[Tuple[datetime, datetime]]:
    """Find common slots across all participant slot lists."""
    if not all_slots:
        return []
    
    if len(all_slots) == 1:
        return all_slots[0]
    
    # Start with first participant's slots
    common = all_slots[0]
    
    # Intersect with each subsequent participant
    for participant_slots in all_slots[1:]:
        common = find_intersection(common, participant_slots)
        
        # If no common slots, return empty list
        if not common:
            return []
    
    return common


def paginate_slots(
    slots: List[Tuple[datetime, datetime]],
    page: int = 0,
    page_size: int = 5,
) -> Tuple[List[Tuple[datetime, datetime]], bool]:
    """Paginate time slots."""
    start_idx = page * page_size
    end_idx = start_idx + page_size
    
    page_slots = slots[start_idx:end_idx]
    has_next = end_idx < len(slots)
    
    return page_slots, has_next


def sort_slots_by_start_time(slots: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    """Sort slots by start time."""
    return sorted(slots, key=lambda x: x[0])


def filter_slots_by_date_range(
    slots: List[Tuple[datetime, datetime]],
    start_date: datetime,
    end_date: datetime,
) -> List[Tuple[datetime, datetime]]:
    """Filter slots by date range."""
    filtered = []
    
    for slot_start, slot_end in slots:
        if start_date <= slot_start < end_date:
            filtered.append((slot_start, slot_end))
    
    return filtered
