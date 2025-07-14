# AI Task Scheduler - Complete Application Flow

## Overview
This is an intelligent AI-powered task scheduling application that integrates with Google Calendar and uses OpenAI's GPT-4 to automatically parse, prioritize, and optimally schedule tasks across multiple days. The app features sophisticated conflict resolution, energy-based scheduling, and agentic AI decision-making.

## Architecture Overview

### Core Components
- **Flask Web Application** (`app.py`) - Main web server and routing
- **Google OAuth Authentication** (`auth.py`) - Handles Google Calendar API access
- **Calendar Integration** (`calendar_api.py`) - Google Calendar API operations
- **AI Task Processing** (`gpt_parser.py`) - OpenAI GPT-4 integration for parsing and scheduling
- **Utility Functions** (`utils.py`) - Date handling and common operations
- **Web Interface** (`templates/`) - HTML templates for user interaction

## 🔄 Complete Application Flow

### 1. **Initial Setup & Authentication**
User visits app → Login page → Google OAuth consent → Calendar permissions → Authenticated session

**Technical Flow:**
- User accesses the root route (`/`) which renders `index.html`
- User clicks "Login with Google" which redirects to `/login`
- `auth.py` creates OAuth2 flow and generates Google authorization URL
- User grants calendar permissions on Google's servers
- Google redirects back to `/callback` with authorization code
- Application exchanges code for credentials using `exchange_code_for_credentials()`
- Credentials stored in Flask session for subsequent API calls

### 2. **Task Input & Interface**
Chat interface → User describes tasks → Priority selection → Submit for processing

**Technical Details:**
- After authentication, user redirected to `/chat` route
- `chat.html` displays split-screen interface:
  - **Left side**: Embedded Google Calendar iframe showing user's actual calendar
  - **Right side**: Task input form with natural language text area and priority dropdown
- User can describe multiple tasks in natural language (e.g., "Gym at 7pm today, meeting with John tomorrow at 2pm, finish report before 3pm")

### 3. **Intelligent Date Range Analysis**
User input → AI analyzes temporal keywords → Optimized calendar API calls

**Smart Analysis Process:**
- `analyze_user_input_for_date_range()` in `calendar_api.py` examines user input for temporal clues
- **Keywords detected:**
  - "today", "now" → 1 day range
  - "tomorrow" → 2 day range  
  - "this week", "by Friday" → 7 day range
  - "next week" → 14 day range
  - Specific dates ("July 15") → calculated range
- **Default fallback**: 3 days if no temporal keywords found
- This optimization prevents unnecessary API calls and improves performance

### 4. **Calendar Data Retrieval**
Optimized date range → Google Calendar API → Free slots + Existing events

**Two-Phase Data Collection:**
1. **Free Time Slots**: `get_optimized_free_slots()`
   - Calls Google Calendar Freebusy API for each day in the optimized range
   - Working hours: 8:00 AM to 7:00 PM (Asia/Kolkata timezone)
   - Returns multi-day dictionary of available time slots

2. **Existing Events Context**: `get_existing_events_for_ai()`
   - Retrieves already scheduled events for AI context
   - Prevents double-booking and provides scheduling intelligence
   - Groups events by date for better AI understanding

### 5. **AI Task Parsing**
Natural language → GPT-4 → Structured JSON tasks

**Intelligent Parsing Process:**
- `parse_tasks_with_gpt()` sends user input to GPT-4 with sophisticated prompt
- **AI understands:**
  - Date references ("today", "tomorrow", "July 15th")
  - Time specifications ("at 3pm", "before 5pm", "after dinner")
  - Task priorities (inferred from urgency keywords)
  - Fixed vs flexible timing
  - Duration estimates
- **Output**: Array of structured task objects with:
  ```json
  {
    "task_name": "string",
    "duration": "minutes",
    "start_time": "ISO 8601 (if fixed)",
    "deadline": "ISO 8601",
    "priority": "high/medium/low",
    "fixed": "boolean",
    "date": "YYYY-MM-DD"
  }
  ```
### 6. Agentic AI Scheduling
     Parsed tasks + Free slots + Existing events → Agentic AI → Optimized schedule
     Advanced Scheduling Intelligence:

agentic_batch_schedule() uses GPT-4 with sophisticated global optimization

Holistic Analysis:

Considers ALL tasks simultaneously (not one-by-one)
Global priority optimization across multiple days
Energy-based scheduling (complex tasks in morning)
Intelligent conflict resolution
Natural task flow and grouping
Smart Conflict Resolution:

Priority-based displacement (high > medium > low)
Never drops tasks - always finds alternative solutions
Respects existing calendar events (no double-booking)
Maintains deadline compliance or flags as "late" with reasoning
Optimization Strategies:

Morning (8-11 AM): High-focus, complex tasks
Mid-morning (11 AM-1 PM): Collaborative work, meetings
Post-lunch (2-4 PM): Moderate effort tasks
Late afternoon (4-6 PM): Administrative tasks

### 7. Google Calendar Integration
Optimized schedule → Google Calendar Events API → Live calendar updates

Event Creation Process:

For each scheduled task, insert_event() calls Google Calendar Events API
Creates calendar events with:
Task name as event title
Optimized start/end times
Asia/Kolkata timezone
Direct links to view events
Returns HTML links for user to view created events


  
