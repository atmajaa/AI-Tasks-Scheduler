"""
Google Calendar API integration module.
"""
from googleapiclient.discovery import build
import google.oauth2.credentials
from datetime import datetime, timedelta
import pytz
import re

#Analyzes user input to determine the optimal date range for calendar API calls.
def analyze_user_input_for_date_range(user_input):

    today = datetime.now()
    user_input_lower = user_input.lower()
    
    # Keywords that suggest different time ranges
    today_keywords = ['today', 'now', 'this morning', 'this afternoon', 'this evening', 'tonight']
    tomorrow_keywords = ['tomorrow', 'next day']
    this_week_keywords = ['this week', 'by friday', 'by the weekend', 'rest of the week']
    next_week_keywords = ['next week', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    # Check for specific dates (e.g., "July 15", "15th", etc.)
    date_patterns = [
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b',
        r'\b\d{1,2}(st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b',
        r'\b\d{1,2}/\d{1,2}\b',
        r'\b\d{4}-\d{1,2}-\d{1,2}\b'
    ]
    
    # Priority-based analysis (most specific first)
    # Check for specific dates - if found, get range from today to that date
    for pattern in date_patterns:
        if re.search(pattern, user_input_lower):
            # For specific dates, give a wider range (7 days) to be safe
            return today, 7
    # Check for today-only tasks
    today_count = sum(1 for keyword in today_keywords if keyword in user_input_lower)
    if today_count > 0:
        # Check if there are also future references
        future_count = sum(1 for keyword in tomorrow_keywords + this_week_keywords + next_week_keywords if keyword in user_input_lower)
        if future_count == 0:
            return today, 1  # Only today
    # Check for tomorrow tasks
    tomorrow_count = sum(1 for keyword in tomorrow_keywords if keyword in user_input_lower)
    if tomorrow_count > 0 and today_count == 0:
        # If only tomorrow is mentioned
        other_future_count = sum(1 for keyword in this_week_keywords + next_week_keywords if keyword in user_input_lower)
        if other_future_count == 0:
            return today, 2  # Today and tomorrow
    # Check for this week tasks
    this_week_count = sum(1 for keyword in this_week_keywords if keyword in user_input_lower)
    if this_week_count > 0:
        return today, 7  # This week
    # Check for next week tasks
    next_week_count = sum(1 for keyword in next_week_keywords if keyword in user_input_lower)
    if next_week_count > 0:
        return today, 14  # Two weeks
    # Default: if no clear timeframe is detected, use a conservative 3-day range
    return today, 3

#Gets free slots with optimized date range based on user input analysis.
def get_optimized_free_slots(creds_dict, user_input=None, start_date=None, num_days=None):
    if start_date is None or num_days is None:
        if user_input:
            start_date, num_days = analyze_user_input_for_date_range(user_input)
            print(f"Analyzed user input: optimized to {num_days} day(s) starting from {start_date.strftime('%Y-%m-%d')}")
        else:
            # Default fallback
            start_date = datetime.now()
            num_days = 3
            print(f"Using default: {num_days} day(s) starting from {start_date.strftime('%Y-%m-%d')}")
    
    return get_free_slots_multi_day(creds_dict, start_date, num_days)

def get_free_slots_for_date(creds_dict, target_date):
    creds = google.oauth2.credentials.Credentials(**creds_dict)
    service = build('calendar', 'v3', credentials=creds)

    tz = pytz.timezone("Asia/Kolkata")
    
    if target_date.tzinfo is None:
        target_date = tz.localize(target_date)
    
    start_of_day = target_date.replace(hour=8, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=19, minute=0, second=0, microsecond=0)  # 7 PM

    body = {
        "timeMin": start_of_day.isoformat(),
        "timeMax": end_of_day.isoformat(),
        "timeZone": "Asia/Kolkata",
        "items": [{"id": "primary"}]
    }

    events_result = service.freebusy().query(body=body).execute()
    busy_times = events_result['calendars']['primary']['busy']

    free_slots = []
    current = start_of_day

    for slot in busy_times:
        busy_start = datetime.fromisoformat(slot['start'])
        busy_end = datetime.fromisoformat(slot['end'])

        if current < busy_start:
            free_slots.append({
                'start': current.isoformat(),
                'end': busy_start.isoformat()
            })

        current = max(current, busy_end)

    if current < end_of_day:
        free_slots.append({
            'start': current.isoformat(),
            'end': end_of_day.isoformat()
        })

    return free_slots

def get_free_slots_multi_day(creds_dict, start_date, num_days=7):
    all_slots = {}
    
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        all_slots[date_str] = get_free_slots_for_date(creds_dict, current_date)
    
    return all_slots

def get_existing_events_for_ai(creds_dict, start_date, num_days=7):
    """
    Get existing calendar events formatted for AI scheduling context.
    This helps the AI understand what's already scheduled to avoid conflicts.
    """
    creds = google.oauth2.credentials.Credentials(**creds_dict)
    service = build('calendar', 'v3', credentials=creds)
    
    tz = pytz.timezone("Asia/Kolkata")
    
    end_date = start_date + timedelta(days=num_days)
    
    if start_date.tzinfo is None:
        start_date = tz.localize(start_date.replace(hour=0, minute=0, second=0))
    if end_date.tzinfo is None:
        end_date = tz.localize(end_date.replace(hour=23, minute=59, second=59))
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_date.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    # Group events by date for AI context
    events_by_date = {}
    
    for event in events:
        if 'dateTime' in event.get('start', {}):
            event_start = datetime.fromisoformat(event['start']['dateTime'])
            event_date = event_start.strftime("%Y-%m-%d")
            
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            
            events_by_date[event_date].append({
                'summary': event.get('summary', 'Untitled Event'),
                'start': event['start']['dateTime'],
                'end': event['end']['dateTime'],
                'start_time': event_start.strftime("%H:%M"),
                'end_time': datetime.fromisoformat(event['end']['dateTime']).strftime("%H:%M")
            })
    
    return events_by_date

def insert_event(credentials_dict, task):
    creds = google.oauth2.credentials.Credentials(**credentials_dict)
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': task['task_name'],
        'start': {
            'dateTime': task['start'],
            'timeZone': 'Asia/Kolkata'
        },
        'end': {
            'dateTime': task['end'],
            'timeZone': 'Asia/Kolkata'
        }
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    return event['htmlLink']

def update_free_slots_after_scheduling(free_slots, scheduled_task, buffer_minutes=5):
   
    updated_slots = {}
    task_start = datetime.fromisoformat(scheduled_task['start'])
    task_end = datetime.fromisoformat(scheduled_task['end'])
    
    # Add buffer to task timings
    buffer = timedelta(minutes=buffer_minutes)
    buffered_task_start = task_start - buffer
    buffered_task_end = task_end + buffer
    
    for date, slots in free_slots.items():
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_updated_slots = []
        
        for slot in slots:
            slot_start = datetime.fromisoformat(slot['start'])
            slot_end = datetime.fromisoformat(slot['end'])
            
            # If the slot ends before the task starts or starts after the task ends, keep it
            if slot_end <= buffered_task_start or slot_start >= buffered_task_end:
                date_updated_slots.append(slot)
        
        updated_slots[date] = date_updated_slots
    
    return updated_slots
