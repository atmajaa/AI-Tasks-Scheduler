"""
Utility functions for date handling and other common operations.
"""
from datetime import datetime

def safe_parse_datetime(dt_str, fallback_hour=22):
    """Handles invalid/missing deadlines by falling back to today at 10 PM."""
    try:
        return datetime.fromisoformat(dt_str)
    except:
        now = datetime.now().astimezone()
        fallback = now.replace(hour=fallback_hour, minute=0, second=0, microsecond=0)
        return fallback
