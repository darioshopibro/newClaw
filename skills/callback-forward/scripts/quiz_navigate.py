#!/usr/bin/env python3
"""
quiz_navigate.py - Handle quiz_nav| callbacks (pagination Prev/Next)
Translated from n8n Quiz Page Navigator - IDENTICAL logic
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

def handle_quiz_navigate(task_id, question_index, new_page, chat_id, message_id, callback_query_id):
    """
    Handle pagination navigation - IDENTICAL to n8n Quiz Page Navigator
    Only updates buttons, not text (uses editMessageReplyMarkup)
    """
    # Answer callback query immediately
    answer_callback_query(callback_query_id)

    # 1. Lookup quiz session from Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    result = supabase.table('task_temp_data').select('*').eq('task_id', task_id).eq('data_type', 'quiz_session').execute()

    if not result.data:
        return "ERROR: Quiz session not found"

    record = result.data[0]
    record_id = record['id']
    quiz_data = record['data'] if isinstance(record['data'], dict) else json.loads(record['data'])

    # 2. Get quiz state
    questions = quiz_data.get('questions', [])
    answers = quiz_data.get('answers', {})
    venues_by_city = quiz_data.get('venues_by_city', {})
    all_options_cache = quiz_data.get('all_options_cache', {})

    # 3. Get current question
    if question_index < 1 or question_index > len(questions):
        return "ERROR: Invalid question index"

    current_question = questions[question_index - 1]

    # 4. Get ALL options - check cache first, then rebuild - IDENTICAL to n8n
    all_options = all_options_cache.get(str(question_index))

    if not all_options:
        # Rebuild options based on type - IDENTICAL to n8n
        q_type = current_question.get('type', '')

        if q_type == 'contact_choice':
            all_options = current_question.get('options', [])

        elif q_type == 'venue_choice':
            selected_city = quiz_data.get('detected_city')
            if not selected_city:
                for i in range(1, question_index):
                    q = questions[i - 1]
                    if q.get('type') == 'city_choice' and answers.get(str(i)):
                        selected_city = answers.get(str(i))
                        break

            if selected_city and selected_city in venues_by_city:
                all_options = venues_by_city[selected_city]
            else:
                all_options = []

        elif q_type == 'city_choice':
            all_options = list(venues_by_city.keys())

        else:
            all_options = current_question.get('options', [])

    if not all_options:
        return "ERROR: No options available"

    # 5. Paginate - IDENTICAL to n8n
    total_pages = max(1, (len(all_options) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    safe_page = max(0, min(new_page, total_pages - 1))
    start_idx = safe_page * ITEMS_PER_PAGE
    page_options = all_options[start_idx:start_idx + ITEMS_PER_PAGE]

    # 6. Build keyboard - IDENTICAL layout to n8n
    keyboard = {"inline_keyboard": []}

    i = 0
    while i < len(page_options):
        row = []
        items_to_add = 3

        # Back button on first row of first page if not first question
        if i == 0 and safe_page == 0 and question_index > 1:
            row.append({
                "text": "⬅️",
                "callback_data": f"quiz_back|{task_id}|{question_index - 1}"
            })
            items_to_add = 2

        for j in range(items_to_add):
            if i >= len(page_options):
                break
            row.append({
                "text": page_options[i],
                "callback_data": f"quiz|{task_id}|{question_index}|{start_idx + i}"
            })
            i += 1

        keyboard["inline_keyboard"].append(row)

    # Navigation row - IDENTICAL to n8n
    if total_pages > 1:
        nav_row = []
        if safe_page > 0:
            nav_row.append({"text": "⬅️ Prev", "callback_data": f"quiz_nav|{task_id}|{question_index}|{safe_page - 1}"})
        nav_row.append({"text": f"📄 {safe_page + 1}/{total_pages}", "callback_data": "noop"})
        if safe_page < total_pages - 1:
            nav_row.append({"text": "Next ➡️", "callback_data": f"quiz_nav|{task_id}|{question_index}|{safe_page + 1}"})
        keyboard["inline_keyboard"].append(nav_row)

    # 7. Update cache in Supabase
    all_options_cache[str(question_index)] = all_options
    quiz_data['all_options_cache'] = all_options_cache
    quiz_data['current_page'] = safe_page
    supabase.table('task_temp_data').update({'data': quiz_data}).eq('id', record_id).execute()

    # 8. Edit message buttons ONLY (not text) - uses editMessageReplyMarkup
    edit_message_reply_markup(chat_id, message_id, keyboard)

    return "NO_REPLY"


def answer_callback_query(callback_query_id):
    """Answer callback query to remove loading state"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_query_id})


def edit_message_reply_markup(chat_id, message_id, keyboard):
    """Edit message buttons only (not text)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup"
    requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": keyboard
    })


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 7:
        result = handle_quiz_navigate(
            sys.argv[1],  # task_id
            int(sys.argv[2]),  # question_index
            int(sys.argv[3]),  # page
            sys.argv[4],  # chat_id
            sys.argv[5],  # message_id
            sys.argv[6]   # callback_query_id
        )
        print(result)
