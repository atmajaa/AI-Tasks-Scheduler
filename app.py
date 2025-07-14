from flask import Flask, render_template, request, redirect, session, url_for
import os
from dotenv import load_dotenv

# Import our custom modules
from auth import get_authorization_url, exchange_code_for_credentials, credentials_to_dict
from calendar_api import get_optimized_free_slots, get_existing_events_for_ai, insert_event, update_free_slots_after_scheduling
from gpt_parser import ai_schedule_tasks, parse_tasks_with_gpt

# Load environment variables from .env file
load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for local development (not safe for production)

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Replace with a secure key in production

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Redirects user to Google login and asks for calendar access
@app.route('/login')
def login():
    auth_url = get_authorization_url()
    return redirect(auth_url)

# Handles Google's OAuth2 callback and stores credentials in session
@app.route('/callback')
def callback():
    credentials = exchange_code_for_credentials(request.url)
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('chat'))

# Chat interface shown after login
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'credentials' not in session:
        return redirect(url_for('index'))

    result_html = ""

    if request.method == 'POST':
        user_input = request.form['task_input']
        user_priority = request.form['priority']

        try:
            # Step 1: Get free slots from Google Calendar with optimized date range based on user input
            multi_day_slots = get_optimized_free_slots(session['credentials'], user_input)

            # Step 1.5: Get existing events to provide context for AI scheduling  
            from datetime import datetime
            from calendar_api import analyze_user_input_for_date_range
            start_date, num_days = analyze_user_input_for_date_range(user_input) if user_input else (datetime.now(), 3)
            existing_events = get_existing_events_for_ai(session['credentials'], start_date, num_days)

            # Step 2: Parse tasks using AI to get individual tasks with priorities
            from gpt_parser import parse_tasks_with_gpt, agentic_batch_schedule
            parsed_tasks = parse_tasks_with_gpt(user_input, user_priority)
            
            print(f"DEBUG: Parsed {len(parsed_tasks)} tasks, now using agentic batch scheduling...")
            print(f"DEBUG: Found {sum(len(events) for events in existing_events.values())} existing events to avoid conflicts")
            
            # Step 3: Use AGENTIC AI to schedule ALL tasks 
            scheduled_tasks, skipped_tasks, optimization_summary, schedule_insights = agentic_batch_schedule(
                parsed_tasks, 
                user_priority, 
                multi_day_slots,
                existing_events
            )
            
            print(f"DEBUG: Agentic AI scheduled {len(scheduled_tasks)} tasks")
            print(f"DEBUG: Optimization Summary: {optimization_summary}")
            
            for task in scheduled_tasks:
                print(f"DEBUG: {task['task_name']} → {task['start']} to {task['end']} ({task.get('status', 'scheduled')})")
            
            if skipped_tasks:
                for skipped in skipped_tasks:
                    print(f"DEBUG: Skipped: {skipped['task_name']} - {skipped['reason']}")

            # Step 4: Schedule tasks - AI has already resolved conflicts in Step 3
            links = []
            
            for task in scheduled_tasks:
                event_link = insert_event(session['credentials'], task)
                status = task.get("status", "on-time")
                reasoning = task.get("reasoning", "")
                
                # Extract date from start time for display
                from datetime import datetime
                start_time = datetime.fromisoformat(task['start'].replace('+05:30', ''))
                task_date = start_time.strftime("%A, %B %d")
                
                links.append(f"{task['task_name']} on {task_date} ({status}): <a href='{event_link}' target='_blank'>View Event</a><br><small><em>{reasoning}</em></small>")

            # Step 4: Build HTML result with AI optimization summary
            result_html += f"<h3>🧠 AI Scheduling Intelligence:</h3>"
            result_html += f"<p><strong>Optimization Strategy:</strong> {optimization_summary}</p>"
            
            if schedule_insights:
                result_html += "<h4>💡 Key Scheduling Insights:</h4><ul>"
                for insight in schedule_insights:
                    result_html += f"<li>{insight}</li>"
                result_html += "</ul>"
            
            result_html += "<h3>📅 Scheduled Tasks (AI-Optimized Multi-Day Schedule):</h3><ul>"
            for link in links:
                result_html += f"<li>{link}</li>"
            result_html += "</ul>"

            # AI scheduling feedback
            late_tasks = [t for t in scheduled_tasks if t.get("status") == "late"]
            if late_tasks:
                result_html += "<h3>Tasks Scheduled After Deadline:</h3><ul>"
                for t in late_tasks:
                    result_html += f"<li>{t['task_name']} → Scheduled at {t['start']}<br><small><em>AI Reasoning: {t.get('reasoning', 'Optimized placement')}</em></small></li>"
                result_html += "</ul>"

            if skipped_tasks:
                result_html += "<h3>Tasks That Couldn't Be Scheduled:</h3><ul>"
                for t in skipped_tasks:
                    result_html += f"<li>{t.get('task_name', 'Unknown task')} - {t.get('reason', 'No available time slots')}</li>"
                result_html += "</ul>"

            if not late_tasks and not skipped_tasks:
                result_html += "<h3>Perfect Agentic Schedule! AI optimally scheduled all tasks with global intelligence!</h3>"

        except Exception as e:
            result_html = f"<h3>Error:</h3><pre>{str(e)}</pre>"

    return render_template('chat.html', result=result_html)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
