#!/usr/bin/env python3
"""
quiz_back.py - Handle quiz_back| callbacks (back button)
Translated from n8n Quiz Back Handler - IDENTICAL logic
"""

import os
import json
import requests
from supabase import create_client

# Config
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://qdrtfwnftwfuykjyvyxd.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
ITEMS_PER_PAGE = 9

def handle_quiz_back(task_id, target_step, chat_id, message_id, callback_query_id):
    """
    Handle back button - IDENTICAL to n8n Quiz Back Handler
    Clears answers from target_step onwards and shows that step
    """
    # Answer callback query immediately
    answer_callback_query(callback_query_id)

    # 1. Lookup quiz session from Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    result = supabase.table('task_temp_data').select('*').eq('task_id', task_id).eq('data_type', 'quiz_session').execute()

    if not result.data:
        edit_message_text(chat_id, message_id, "❌ Quiz session not found. Please start a new booking.", {"inline_keyboard": []})
        return "ERROR: Quiz session not found"

    record = result.data[0]
    record_id = record['id']
    quiz_data = record['data'] if isinstance(record['data'], dict) else json.loads(record['data'])

    # 2. Get quiz state
    questions = quiz_data.get('questions', [])
    answers = dict(quiz_data.get('answers', {}))  # Copy to modify
    venues_by_city = quiz_data.get('venues_by_city', {})
    total_questions = len(questions)

    # Restaurant data - IDENTICAL to n8n
    locations_by_cuisine = quiz_data.get('locations_by_cuisine', {})
    venues_by_cuisine_location = quiz_data.get('venues_by_cuisine_location', {})
    all_cuisines = quiz_data.get('all_cuisines', [])
    all_locations = quiz_data.get('all_locations', [])
    all_venues = quiz_data.get('all_venues', [])

    if target_step < 1 or target_step > total_questions:
        edit_message_text(chat_id, message_id, "❌ Invalid step. Please try again.", {"inline_keyboard": []})
        return "ERROR: Invalid step"

    target_question = questions[target_step - 1]

    # 3. Clear answers from target_step onwards - IDENTICAL to n8n
    for i in range(target_step, total_questions + 1):
        q = questions[i - 1] if i <= len(questions) else None
        if q:
            q_id = q.get('id')
            if q_id:
                answers.pop(str(q_id), None)
            answers.pop(str(i), None)

    # 4. Rebuild options for target question - IDENTICAL to n8n
    question_options = []
    q_type = target_question.get('type', '')
    q_id = target_question.get('id', '')

    # Padel flow - by type
    if q_type == 'city_choice':
        question_options = list(venues_by_city.keys())

    elif q_type == 'venue_choice':
        selected_city = quiz_data.get('detected_city')
        if not selected_city:
            for i in range(1, target_step):
                q = questions[i - 1]
                if q.get('type') == 'city_choice' and answers.get(str(i)):
                    selected_city = answers.get(str(i))
                    break
        if selected_city and selected_city in venues_by_city:
            question_options = venues_by_city[selected_city]

    elif q_type == 'duration_choice':
        question_options = target_question.get('options', ["90 minutes", "120 minutes"])

    elif q_type == 'venue_type':
        question_options = target_question.get('options', ["Indoor", "Outdoor"])

    elif q_type == 'conflict_choice':
        question_options = target_question.get('options', ["Yes", "No"])

    # Restaurant flow - by id
    elif q_id == 'cuisine':
        question_options = ['Any'] + all_cuisines

    elif q_id == 'location':
        selected_cuisine = answers.get('cuisine')
        if selected_cuisine and selected_cuisine != 'Any' and selected_cuisine in locations_by_cuisine:
            question_options = ['Any'] + locations_by_cuisine[selected_cuisine]
        else:
            question_options = ['Any'] + all_locations

    elif q_id == 'venue':
        selected_cuisine = answers.get('cuisine')
        selected_location = answers.get('location')

        if selected_cuisine == 'Any' and selected_location == 'Any':
            question_options = all_venues
        elif selected_cuisine == 'Any':
            venues = []
            for key in venues_by_cuisine_location:
                if key.endswith(f"|{selected_location}"):
                    venues.extend(venues_by_cuisine_location[key])
            question_options = list(set(venues))
        elif selected_location == 'Any':
            venues = []
            for key in venues_by_cuisine_location:
                if key.startswith(f"{selected_cuisine}|"):
                    venues.extend(venues_by_cuisine_location[key])
            question_options = list(set(venues))
        else:
            key = f"{selected_cuisine}|{selected_location}"
            question_options = venues_by_cuisine_location.get(key, [])

    elif q_type == 'static':
        question_options = target_question.get('options', [])

    else:
        question_options = target_question.get('options', [])

    # 5. Pagination - IDENTICAL to n8n
    total_pages = max(1, (len(question_options) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page_options = question_options[:ITEMS_PER_PAGE]

    # 6. Build keyboard - IDENTICAL to n8n
    keyboard = {"inline_keyboard": []}

    i = 0
    while i < len(page_options):
        row = []
        items_to_add = 3

        # Back button on first row if not first question
        if i == 0 and target_step > 1:
            row.append({
                "text": "⬅️",
                "callback_data": f"quiz_back|{task_id}|{target_step - 1}"
            })
            items_to_add = 2

        for j in range(items_to_add):
            if i >= len(page_options):
                break
            row.append({
                "text": page_options[i],
                "callback_data": f"quiz|{task_id}|{target_step}|{i}"
            })
            i += 1

        keyboard["inline_keyboard"].append(row)

    # Navigation row
    if total_pages > 1:
        keyboard["inline_keyboard"].append([
            {"text": f"📄 1/{total_pages}", "callback_data": "noop"},
            {"text": "Next ➡️", "callback_data": f"quiz_nav|{task_id}|{target_step}|1"}
        ])

    # 7. Build message text - IDENTICAL to n8n
    context = quiz_data.get('context', '')
    clean_context = remove_html_tags(context)
    message_text = f"{clean_context}\n\n"

    # Show completed answers before target step
    for i in range(1, target_step):
        q = questions[i - 1]
        ans = answers.get(str(q.get('id'))) or answers.get(str(i))
        if ans:
            message_text += f"✅ {q.get('text', '')}: {ans}\n"

    message_text += f"\n📋 Step {target_step} of {total_questions}: {target_question.get('text', '')}"

    # 8. Update Supabase
    quiz_data['answers'] = answers
    quiz_data['current_step'] = target_step
    supabase.table('task_temp_data').update({'data': quiz_data}).eq('id', record_id).execute()

    # 9. Edit message
    edit_message_text(chat_id, message_id, message_text, keyboard)

    return "NO_REPLY"


def remove_html_tags(text):
    """Remove HTML tags from text"""
    import re
    return re.sub(r'<[^>]*>', '', text)


def answer_callback_query(callback_query_id):
    """Answer callback query to remove loading state"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_query_id})


def edit_message_text(chat_id, message_id, text, keyboard):
    """Edit message text and buttons"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    })


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 6:
        result = handle_quiz_back(
            sys.argv[1],  # task_id
            int(sys.argv[2]),  # target_step
            sys.argv[3],  # chat_id
            sys.argv[4],  # message_id
            sys.argv[5]   # callback_query_id
        )
        print(result)
