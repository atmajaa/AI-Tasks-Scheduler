"""
OpenAI GPT integration for task parsing module.
"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#get JSON format from user inputs
def generate_task_prompt(user_input, user_priority):
    """Generates a prompt for OpenAI to parse task input."""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%A, %Y-%m-%d")
    day_of_week = today.strftime("%A")
    
    return f"""
You are a smart scheduling assistant. A user will describe their day's plans in natural language. Your task is to convert the description into a JSON array of task objects, based on the following schema:

### CURRENT DATE CONTEXT:
- Today: {today_str} ({day_of_week})
- Tomorrow: {tomorrow_str}
- Current time: {today.strftime("%Y-%m-%d %H:%M:%S")} (Asia/Kolkata)

### DATE PARSING RULES:
- "today" = {today_str}
- "tomorrow" = {tomorrow.strftime("%Y-%m-%d")}
- "next Monday/Tuesday/etc." = calculate the next occurrence
- "July 15" or "15th July" = 2025-07-15
- "this Friday" = the upcoming Friday
- If NO date mentioned, assume TODAY

Each task must include:

- task_name (string): a short name summarizing the task
- duration (integer): estimated duration in minutes
- start_time : full ISO 8601 string (e.g. "2025-07-13T09:00:00+05:30") 
- deadline (required): full ISO 8601 string — latest time by which the task must be finished
- priority: one of "high", "medium", or "low" — inferred from urgency or keywords
- fixed (boolean): true if the task has a specific start time, false otherwise
- date (string): the date this task is meant for in YYYY-MM-DD format

### Instructions:
- Use Asia/Kolkata timezone in all timestamps.
- If the user writes "at 4pm", "from 10am to 11am", or "after dinner at 8", set `fixed = true` and include `start_time`.
- If only a latest time is given (e.g. "before 5pm", "by 8"), set `fixed = false` and use that as the `deadline`.
- If no time is given at all, set `fixed = false` and use the task date at 10pm as the default `deadline`.
- If no duration is mentioned, default to 60 minutes.
- IMPORTANT: Parse dates correctly - "meeting tomorrow" should have date = "{tomorrow.strftime("%Y-%m-%d")}"
- Do not return empty/null values. Only return valid JSON.

### Output Format:
Return ONLY a clean JSON array with the required fields, and nothing else.

### Example Input:
"Gym at 7pm today. Meeting with John tomorrow at 2pm. Finish report before 3pm."

### Example Output:
[
  {{
    "task_name": "Gym",
    "duration": 60,
    "start_time": "{today_str}T19:00:00+05:30",
    "deadline": "{today_str}T20:00:00+05:30",
    "priority": "medium",
    "fixed": true,
    "date": "{today_str}"
  }},
  {{
    "task_name": "Meeting with John",
    "duration": 60,
    "start_time": "{tomorrow.strftime("%Y-%m-%d")}T14:00:00+05:30",
    "deadline": "{tomorrow.strftime("%Y-%m-%d")}T15:00:00+05:30",
    "priority": "high",
    "fixed": true,
    "date": "{tomorrow.strftime("%Y-%m-%d")}"
  }},
  {{
    "task_name": "Finish report",
    "duration": 90,
    "deadline": "{today_str}T15:00:00+05:30",
    "priority": "high",
    "fixed": false,
    "date": "{today_str}"
  }}
]

### User Input:
\"\"\"{user_input}\"\"\"
"""
#Act as a smart scheduler
def generate_ai_schedule_prompt(user_input, user_priority, multi_day_slots):
    """Generates a comprehensive prompt for AI to handle both parsing and intelligent scheduling across multiple days."""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    day_of_week = today.strftime("%A")
    
    return f"""
You are an expert AI scheduling assistant. Your job is to:
1. Parse the user's natural language input into tasks with proper date handling
2. Intelligently schedule ALL tasks into the available time slots across multiple days
3. Optimize each day from 8:00 AM to 7:00 PM for maximum productivity

### CURRENT DATE CONTEXT:
- Today: {today_str} ({day_of_week})
- Tomorrow: {tomorrow_str} ({tomorrow.strftime("%A")})
- Current time: {today.strftime("%Y-%m-%d %H:%M:%S")} (Asia/Kolkata)

### DATE INTELLIGENCE RULES:
- "today" = {today_str}
- "tomorrow" = {tomorrow_str}
- "next Monday/Tuesday/etc." = calculate the next occurrence of that day
- "July 15" or "15th July" = 2025-07-15
- "this Friday" = the upcoming Friday
- If NO date is mentioned, assume TODAY ({today_str})

### Available Free Time Slots (Multiple Days):
{json.dumps(multi_day_slots, indent=2)}

### Scheduling Rules:
- Working hours: 8:00 AM to 7:00 PM (Asia/Kolkata timezone)
- Schedule tasks on their intended dates (today, tomorrow, specific dates)
- Fixed-time tasks (e.g., "meeting at 3pm") must be scheduled at their specified times
- Flexible tasks should be optimally placed considering:
  * Priority levels (high > medium > low)
  * Deadlines (urgent tasks first)
  * Task dependencies and logical flow
  * Energy levels (demanding tasks in morning, lighter tasks later)
  * Buffer time between tasks

### INTELLIGENT OPTIMIZATION RULES:

1. PRIORITY-CONFLICT RESOLUTION:
   - If two tasks conflict at the same time:
     * The task with HIGHER priority must be scheduled in that time slot.
     * The displaced LOWER-priority task must be rescheduled intelligently in the nearest available slot (before deadline, if any).
   - If both tasks have the SAME priority and time:
     * Adjust one of them to the nearest possible free slot.
     * Try to maintain task flow and logical ordering.
     * NEVER skip a task due to conflicts.

2. NO-TASK-DROPPING POLICY:
   - Every task must be scheduled.
   - Do NOT discard tasks even if the time slot is occupied.
   - If no time is available on the same day, schedule it for the next available day.

3. OVERFLOW HANDLING:
   - If the current day (8 AM–7 PM) is full:
     * Push overflow tasks to the next day, preserving relative priorities and deadlines.
     * Use available time intelligently without bunching high-effort tasks back-to-back.

4. NATURAL-LANGUAGE DATE INTERPRETATION:
   - If user says: “Lunch with Raya at 2 PM” → assume it’s for TODAY unless otherwise specified.
   - Keywords like “tomorrow”, “Friday”, or specific dates override this.
   - If no date is mentioned at all → default to TODAY.

5. BUFFER AND CONTEXT MANAGEMENT:
   - Add short buffer gaps (5–15 minutes) between tasks to allow transitions.
   - Minimize mental fatigue by grouping similar types of tasks.
   - Avoid rapid switching between very different task categories (deep work, meetings, creative, admin, etc.)

6. RESCHEDULING, CANCELING, OR MOVING:
   - Recognize task control instructions:
     * “Reschedule” → find a smarter time slot while respecting priority.
     * “Cancel” → remove the task.
     * “Move X to Y” → shift task X to time Y, adjusting others if needed.
   - Use forceful placement if user insists (e.g., “put this at 3 PM no matter what”).

7. DEFAULT TIME INFERENCE (IF TIME IS MISSING):
   - Guess based on task type (e.g., “lunch” → early afternoon, “review” → afternoon, “standup” → morning).
   - Otherwise, pick the next available time slot in the day.

8. SCHEDULING STRATEGY:
   - Schedule high-priority, high-effort tasks during peak mental energy hours (8–11 AM).
   - Schedule admin or low-effort tasks later (post-lunch).
   - Consider balancing each day’s workload evenly across the week if tasks span multiple days.


### CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY valid JSON - no markdown, no code blocks, no explanatory text
- Do not wrap the JSON in ```json``` blocks
- Do not include any text before or after the JSON
- The response must start with {{ and end with }}

### Required JSON Structure:
{{
  "scheduled_tasks": [
    {{
      "task_name": "string",
      "start": "ISO 8601 datetime string",
      "end": "ISO 8601 datetime string", 
      "status": "on-time" or "late",
      "priority": "high/medium/low",
      "reasoning": "brief explanation of placement decision"
    }}
  ],
  "skipped_tasks": [
    {{
      "task_name": "string",
      "reason": "why it wasn't scheduled (e.g., 'No available time slots', 'Conflicts with existing events', etc.)"
    }}
  ],
  "reasoning_logs": "Concise thought process of how the AI approached the scheduling decisions - what it considered, prioritized, or optimized for"
}}

### IMPORTANT SCHEDULING RULES:
- Schedule tasks on their correct dates (today's tasks today, tomorrow's tasks tomorrow)
- Use the appropriate day's free slots for each task
- If no slots available on the intended date, try to find the closest available slot
- Only skip tasks if absolutely no time slots are available

### User Input:
Priority Level: {user_priority}
Tasks: "{user_input}"

IMPORTANT: Return ONLY the JSON object - no other text, explanations, or formatting.
"""

def extract_json_from_response(content):
    # Try to parse as-is first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Look for JSON within code blocks
    import re
    
    # Try to find JSON in ```json``` blocks
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find any JSON object in the response (more flexible)
    json_match = re.search(r'(\{.*\})', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # If all else fails, raise the original error with helpful debug info
    print(f"DEBUG - AI Response Content:\n{content}")
    raise ValueError("AI response was not valid JSON. Please check the debug output above.")

def ai_schedule_tasks(user_input, user_priority, multi_day_slots):
    prompt = generate_ai_schedule_prompt(user_input, user_priority, multi_day_slots)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert AI scheduling assistant that creates optimized daily schedules. You must return ONLY valid JSON without any markdown formatting or explanatory text. The response must start with { and end with }."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content

    try:
        result = extract_json_from_response(content)
        return result.get("scheduled_tasks", []), result.get("skipped_tasks", []), result.get("reasoning_logs", "")
    except ValueError as e:
        raise e

def parse_tasks_with_gpt(user_input, user_priority):
    """Uses OpenAI GPT to parse user input into structured task data."""
    prompt = generate_task_prompt(user_input, user_priority)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You convert task descriptions into structured JSON for a calendar scheduling app."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content

    try:
        tasks = json.loads(content)
        return tasks
    except json.JSONDecodeError:
        raise ValueError("GPT response was not valid JSON:\n\n" + content)

def agentic_batch_schedule(parsed_tasks, user_priority, multi_day_slots, existing_events=None):
    """
    Agentic AI scheduler that processes ALL tasks at once for global optimization.
    This is the truly intelligent scheduling function that considers:
    - All tasks holistically 
    - Cross-task dependencies and relationships
    - Global priority optimization
    - Intelligent conflict resolution
    - Energy and productivity patterns
    """
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    tomorrow = today + timedelta(days=1)
    day_of_week = today.strftime("%A")
    
    # Convert parsed tasks to a clean JSON string for the prompt
    tasks_json = json.dumps(parsed_tasks, indent=2)
    
    # Add existing events context if provided
    existing_events_context = ""
    if existing_events:
        existing_events_context = f"""
### EXISTING CALENDAR EVENTS (DO NOT DOUBLE-BOOK):
{json.dumps(existing_events, indent=2)}

⚠️  CRITICAL: The above events are ALREADY SCHEDULED. You must NOT overlap with any of these times.
"""
    
    prompt = f"""
You are an elite AI scheduling agent with advanced optimization capabilities. You must schedule ALL the provided tasks optimally across multiple days using sophisticated reasoning.

### CURRENT CONTEXT:
- Today: {today_str} ({day_of_week})
- Current time: {today.strftime("%Y-%m-%d %H:%M:%S")} (Asia/Kolkata)
- User's overall priority preference: {user_priority}

### AVAILABLE TIME SLOTS (Multi-Day):
{json.dumps(multi_day_slots, indent=2)}
{existing_events_context}
### TASKS TO SCHEDULE:
{tasks_json}

### AGENTIC SCHEDULING INTELLIGENCE:

You are not just a scheduler - you are an intelligent agent that understands:

1. **HOLISTIC OPTIMIZATION**: 
   - See the entire workload and optimize globally, not task-by-task
   - Balance workload across days to prevent burnout
   - Create natural task flow and logical sequences
   - Consider cognitive load and context switching

2. **INTELLIGENT CONFLICT RESOLUTION**:
   - The provided free slots exclude existing calendar events
   - If existing events are listed above, you MUST NOT schedule anything that overlaps with them
   - Focus on optimizing WITHIN the available free time slots
   - When multiple new tasks want the same time slot:
     * Priority-based displacement (high > medium > low)
     * Deadline urgency analysis
     * Task difficulty and energy requirements
     * Natural grouping of similar tasks
   - NEVER double-book or overlap tasks
   - NEVER drop tasks - always find creative solutions
   - If a preferred time is unavailable, intelligently shift to next best option

3. **ADVANCED TEMPORAL REASONING**:
   - Morning: High-focus, complex tasks (8-11 AM)
   - Mid-morning: Collaborative work, meetings (11 AM-1 PM)  
   - Post-lunch: Moderate effort tasks (2-4 PM)
   - Late afternoon: Admin, light tasks (4-6 PM)
   - Evening: Planning, review tasks (6-7 PM)

4. **SMART PATTERNS**:
   - Group similar task types to minimize context switching
   - Leave buffers between high-intensity tasks
   - Respect natural energy rhythms
   - Consider commute/travel time between locations
   - Handle fixed-time tasks as immovable anchors

5. **PROACTIVE PROBLEM SOLVING**:
   - If today is overloaded, intelligently distribute to tomorrow
   - If deadlines are tight, prioritize and compress durations
   - If tasks have dependencies, schedule in logical order
   - Handle recurring vs one-time tasks differently

6. **CONTEXTUAL INTELLIGENCE**:
   - Understand task relationships (prep work before meetings)
   - Recognize task categories (deep work, admin, social, creative)
   - Adapt to user's working style and preferences
   - Consider external factors (weather, day of week, etc.)

### CRITICAL SUCCESS METRICS:
- **Zero task dropping**: Every task must be scheduled somewhere
- **Deadline compliance**: Respect all deadlines or flag as late with reasoning
- **Energy optimization**: Match task difficulty to optimal time slots
- **Flow state protection**: Minimize disruptive interruptions
- **Stress minimization**: Avoid overwhelming any single day

### OUTPUT REQUIREMENTS:
Return ONLY valid JSON - no markdown, no explanations outside the JSON structure.

### CRITICAL SCHEDULING RULES:
1. **ZERO CONFLICTS**: Never schedule a task at a time that overlaps with existing events
2. **RESPECT FREE SLOTS**: Only schedule within the provided available time slots
3. **NO DOUBLE-BOOKING**: Each time slot can only have ONE task
4. **BUFFER TIME**: Leave at least 5 minutes between tasks for transitions

Required JSON structure:
{{
  "scheduled_tasks": [
    {{
      "task_name": "string",
      "start": "2025-07-14T09:00:00+05:30",
      "end": "2025-07-14T10:00:00+05:30",
      "status": "on-time",
      "priority": "high",
      "reasoning": "Placed in morning for optimal focus and energy"
    }}
  ],
  "skipped_tasks": [
    {{
      "task_name": "string", 
      "reason": "Specific reason why scheduling wasn't possible"
    }}
  ],
  "optimization_summary": "Brief explanation of your global optimization strategy and key decisions",
  "schedule_insights": [
    "Key insight about the schedule you created",
    "Another strategic decision explanation"
  ]
}}

### STRATEGIC DIRECTIVES:
- Think like a world-class executive assistant
- Prioritize long-term productivity over short-term convenience  
- Make bold but logical scheduling decisions
- Show your reasoning for complex placement decisions
- Optimize for the user's success, not just task completion

Execute your agentic scheduling intelligence now.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an elite agentic AI scheduler with advanced optimization capabilities. You must schedule ALL tasks optimally using sophisticated global reasoning. Return ONLY valid JSON without markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4  # Slightly higher for creative optimization
    )

    content = response.choices[0].message.content

    try:
        result = extract_json_from_response(content)
        return (
            result.get("scheduled_tasks", []), 
            result.get("skipped_tasks", []), 
            result.get("optimization_summary", ""),
            result.get("schedule_insights", [])
        )
    except ValueError as e:
        print(f"DEBUG - Agentic AI Response: {content}")
        raise e
