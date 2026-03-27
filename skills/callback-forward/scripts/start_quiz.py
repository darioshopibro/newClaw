#!/usr/bin/env python3
"""
start_quiz.py - START a quiz session (creates Supabase record + sends first message)
This is the MISSING piece - callback handlers only process AFTER quiz starts!

LOGGING: Sends debug logs to Telegram so we can see what's happening

Usage:
  python3 start_quiz.py --task_id "task_123" --chat_id "5127607280" --type "calendar" --data '{"title":"Meeting","contacts":["John","Jane"]}'

Quiz Types:
  - calendar: Contact selection, calendar selection, duration, type (online/in-person)
  - contact: Just contact selection from multiple matches
  - confirm: Simple yes/no confirmation
"""

import os
import sys
import json
import argparse
import requests
from supabase import create_client

# Config
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://qdrtfwnftwfuykjyvyxd.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
LOG_CHAT_ID = "5127607280"
ITEMS_PER_PAGE = 9


def log_to_telegram(message: str):
    """Send log message to Telegram for debugging"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": LOG_CHAT_ID,
            "text": f"🎯 [start_quiz.py]\n{message}",
            "parse_mode": "HTML"
        }, timeout=5)
    except:
        pass  # Don't fail if logging fails


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task_id', required=True)
    parser.add_argument('--chat_id', required=True)
    parser.add_argument('--type', required=True, choices=['calendar', 'contact', 'confirm', 'venue', 'time'])
    parser.add_argument('--data', required=True, help='JSON data for quiz')
    parser.add_argument('--context', default='', help='Context text to show above quiz')
    args = parser.parse_args()

    task_id = args.task_id
    chat_id = args.chat_id
    quiz_type = args.type
    data = json.loads(args.data)
    context = args.context

    log_to_telegram(f"🚀 Starting quiz\ntype: {quiz_type}\ntask_id: {task_id}\nchat_id: {chat_id}")

    # Build quiz based on type
    if quiz_type == 'calendar':
        result = start_calendar_quiz(task_id, chat_id, data, context)
    elif quiz_type == 'contact':
        result = start_contact_quiz(task_id, chat_id, data, context)
    elif quiz_type == 'confirm':
        result = start_confirm_quiz(task_id, chat_id, data, context)
    elif quiz_type == 'venue':
        result = start_venue_quiz(task_id, chat_id, data, context)
    elif quiz_type == 'time':
        result = start_time_quiz(task_id, chat_id, data, context)
    else:
        log_to_telegram(f"❌ Unknown quiz type: {quiz_type}")
        print(f"ERROR: Unknown quiz type: {quiz_type}")
        return

    log_to_telegram(f"📤 Result: {result}")
    print(result)


def start_calendar_quiz(task_id, chat_id, data, context):
    """
    Full calendar booking quiz:
    1. Contact selection (if multiple)
    2. Calendar selection
    3. Duration
    4. Meeting type (online/in-person)
    """
    contacts = data.get('contacts', [])
    calendars = data.get('calendars', ['Primary', 'Work', 'Personal'])
    durations = data.get('durations', ['30 minutes', '1 hour', '1.5 hours', '2 hours'])
    meeting_types = data.get('meeting_types', ['Online', 'In-person'])
    title = data.get('title', 'Meeting')
    date = data.get('date', '')
    time = data.get('time', '')

    log_to_telegram(f"📅 Calendar quiz\ntitle: {title}\ncontacts: {len(contacts)}")

    questions = []

    # Step 1: Contact selection (if multiple contacts)
    if len(contacts) > 1:
        questions.append({
            'id': len(questions) + 1,
            'text': f'Which {contacts[0].split()[0] if contacts else "contact"}?',
            'type': 'contact_choice',
            'options': contacts
        })

    # Step 2: Calendar selection
    questions.append({
        'id': len(questions) + 1,
        'text': 'Which calendar?',
        'type': 'calendar_choice',
        'options': calendars
    })

    # Step 3: Duration
    questions.append({
        'id': len(questions) + 1,
        'text': 'How long?',
        'type': 'duration_choice',
        'options': durations
    })

    # Step 4: Meeting type
    questions.append({
        'id': len(questions) + 1,
        'text': 'Online or in-person?',
        'type': 'meeting_type',
        'options': meeting_types
    })

    log_to_telegram(f"📝 Created {len(questions)} questions")

    # Build context
    if not context:
        context = f"📅 Schedule: {title}"
        if date:
            context += f"\n📆 Date: {date}"
        if time:
            context += f"\n🕐 Time: {time}"

    # Create quiz session
    return create_quiz_session(task_id, chat_id, questions, context, data)


def start_contact_quiz(task_id, chat_id, data, context):
    """Simple contact selection from multiple matches"""
    contacts = data.get('contacts', [])

    if not contacts:
        return "ERROR: No contacts provided"

    log_to_telegram(f"👥 Contact quiz with {len(contacts)} contacts")

    questions = [{
        'id': 1,
        'text': 'Which contact?',
        'type': 'contact_choice',
        'options': contacts
    }]

    if not context:
        context = "Multiple contacts found. Please select one:"

    return create_quiz_session(task_id, chat_id, questions, context, data)


def start_confirm_quiz(task_id, chat_id, data, context):
    """Simple yes/no confirmation"""
    log_to_telegram(f"✅ Confirm quiz")

    questions = [{
        'id': 1,
        'text': 'Confirm?',
        'type': 'confirm_choice',
        'options': ['Yes, confirm', 'No, cancel']
    }]

    if not context:
        title = data.get('title', 'Action')
        context = f"Confirm: {title}?"

    return create_quiz_session(task_id, chat_id, questions, context, data)


def start_venue_quiz(task_id, chat_id, data, context):
    """Venue selection quiz (for padel/restaurant)"""
    venues = data.get('venues', [])
    city = data.get('city', '')

    if not venues:
        return "ERROR: No venues provided"

    log_to_telegram(f"🏟 Venue quiz with {len(venues)} venues")

    questions = [{
        'id': 1,
        'text': f'Which venue{" in " + city if city else ""}?',
        'type': 'venue_choice',
        'options': venues
    }]

    if not context:
        context = f"🏟 Select venue{' in ' + city if city else ''}:"

    return create_quiz_session(task_id, chat_id, questions, context, data)


def start_time_quiz(task_id, chat_id, data, context):
    """Time slot selection quiz"""
    times = data.get('times', [])
    venue = data.get('venue', '')

    if not times:
        return "ERROR: No times provided"

    log_to_telegram(f"🕐 Time quiz with {len(times)} slots")

    questions = [{
        'id': 1,
        'text': 'Which time slot?',
        'type': 'time_choice',
        'options': times
    }]

    if not context:
        context = f"🕐 Select time{' at ' + venue if venue else ''}:"

    return create_quiz_session(task_id, chat_id, questions, context, data)


def create_quiz_session(task_id, chat_id, questions, context, original_data):
    """Create quiz session in Supabase and send first message"""

    log_to_telegram(f"💾 Creating session in Supabase\ntask: {task_id}")

    # Get first question options
    first_question = questions[0]
    all_options = first_question.get('options', [])
    total_questions = len(questions)

    # Pagination for first question
    total_pages = max(1, (len(all_options) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page_options = all_options[:ITEMS_PER_PAGE]

    # Build message text
    message_text = f"{context}\n\n📋 Step 1 of {total_questions}: {first_question.get('text', '')}"

    # Build keyboard
    keyboard = build_keyboard(task_id, 1, page_options, 0, 0, total_pages)

    # Send message to Telegram
    message_id = send_message(chat_id, message_text, keyboard)

    if not message_id:
        log_to_telegram(f"❌ Failed to send message to Telegram")
        return "ERROR: Failed to send message"

    log_to_telegram(f"✅ Sent message: {message_id}")

    # Create quiz session in Supabase
    quiz_data = {
        'questions': questions,
        'answers': {},
        'current_step': 1,
        'context': context,
        'original_data': original_data,
        'message_id': message_id,
        'chat_id': chat_id,
        'all_options_cache': {
            '1': all_options
        }
    }

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Check if session already exists
        existing = supabase.table('task_temp_data').select('id').eq('task_id', task_id).eq('data_type', 'quiz_session').execute()

        if existing.data:
            # Update existing
            supabase.table('task_temp_data').update({
                'data': quiz_data
            }).eq('id', existing.data[0]['id']).execute()
            log_to_telegram(f"📝 Updated existing session")
        else:
            # Create new
            supabase.table('task_temp_data').insert({
                'task_id': task_id,
                'data_type': 'quiz_session',
                'data': quiz_data
            }).execute()
            log_to_telegram(f"📝 Created new session")

    except Exception as e:
        log_to_telegram(f"❌ Supabase error: {str(e)}")
        return f"ERROR: Supabase failed: {str(e)}"

    return f"QUIZ_STARTED:message_id={message_id}"


def build_keyboard(task_id, question_index, page_options, start_idx, page, total_pages):
    """Build keyboard - IDENTICAL layout to n8n"""
    keyboard = {"inline_keyboard": []}

    i = 0
    while i < len(page_options):
        row = []
        items_to_add = 3

        # Back button on first row if not first question
        if i == 0 and question_index > 1:
            row.append({
                "text": "⬅️",
                "callback_data": f"quiz_back|{task_id}|{question_index - 1}"
            })
            items_to_add = 2

        # Add options
        for j in range(items_to_add):
            if i >= len(page_options):
                break
            row.append({
                "text": page_options[i],
                "callback_data": f"quiz|{task_id}|{question_index}|{start_idx + i}"
            })
            i += 1

        keyboard["inline_keyboard"].append(row)

    # Navigation row
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append({"text": "⬅️ Prev", "callback_data": f"quiz_nav|{task_id}|{question_index}|{page - 1}"})
        nav_row.append({"text": f"📄 {page + 1}/{total_pages}", "callback_data": "noop"})
        if page < total_pages - 1:
            nav_row.append({"text": "Next ➡️", "callback_data": f"quiz_nav|{task_id}|{question_index}|{page + 1}"})
        keyboard["inline_keyboard"].append(nav_row)

    return keyboard


def send_message(chat_id, text, keyboard):
    """Send message to Telegram and return message_id"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    })

    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            return data['result']['message_id']

    log_to_telegram(f"❌ Telegram error: {response.text}")
    print(f"ERROR sending message: {response.text}")
    return None


if __name__ == "__main__":
    main()
