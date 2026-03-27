#!/usr/bin/env python3
"""
quiz_progress.py - Handle quiz| callbacks (user selects an option)
Translated from n8n Quiz Progress Handler - IDENTICAL logic

LOGGING: Sends debug logs to Telegram so we can see what's happening
"""

import os
import json
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
            "text": f"📊 [quiz_progress.py]\n{message}",
            "parse_mode": "HTML"
        }, timeout=5)
    except:
        pass  # Don't fail if logging fails


def handle_quiz_progress(task_id, question_index, answer_index, chat_id, message_id, callback_query_id):
    """
    Handle quiz answer selection - IDENTICAL to n8n Quiz Progress Handler
    """
    log_to_telegram(f"📥 Quiz progress\ntask: {task_id}\nq: {question_index}, a: {answer_index}")

    # Answer callback query immediately
    answer_callback_query(callback_query_id)

    # 1. Lookup quiz session from Supabase
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = supabase.table('task_temp_data').select('*').eq('task_id', task_id).eq('data_type', 'quiz_session').execute()
    except Exception as e:
        log_to_telegram(f"❌ Supabase error: {str(e)}")
        return f"ERROR: Supabase failed: {str(e)}"

    if not result.data:
        log_to_telegram(f"❌ Session not found")
        return "ERROR: Quiz session not found"

    record = result.data[0]
    record_id = record['id']
    quiz_data = record['data'] if isinstance(record['data'], dict) else json.loads(record['data'])

    # 2. Get quiz state
    questions = quiz_data.get('questions', [])
    answers = quiz_data.get('answers', {})
    venues_by_city = quiz_data.get('venues_by_city', {})
    clubs_data = quiz_data.get('clubs_data', {})
    total_questions = len(questions)

    log_to_telegram(f"📝 Found session: {len(questions)} questions, {len(answers)} answered")

    if question_index < 1 or question_index > total_questions:
        log_to_telegram(f"❌ Invalid question index: {question_index}")
        return "ERROR: Invalid question index"

    current_question = questions[question_index - 1]

    # 3. Get current options (dynamic based on type) - IDENTICAL to n8n
    current_options = get_options_for_question(current_question, quiz_data, answers, question_index, venues_by_city, clubs_data)

    if answer_index < 0 or answer_index >= len(current_options):
        log_to_telegram(f"❌ Invalid answer index: {answer_index}, options: {len(current_options)}")
        return "ERROR: Invalid answer index"

    # 4. Save answer
    answer = current_options[answer_index]
    answers[str(question_index)] = answer
    log_to_telegram(f"✅ Saved: q{question_index} = {answer}")

    # 5. Check for Central Padel sub-location injection - IDENTICAL to n8n
    if current_question.get('type') == 'venue_choice' and 'central padel' in answer.lower():
        if not any(q.get('type') == 'sub_location_choice' for q in questions):
            sub_location_question = {
                'id': question_index + 1,
                'text': 'Which Central Padel location?',
                'type': 'sub_location_choice',
                'options': ["Alco's flagship center", "Dubai Marina"],
                'parent_venue': 'Central Padel'
            }
            questions.insert(question_index, sub_location_question)
            # Renumber questions
            for i in range(question_index, len(questions)):
                questions[i]['id'] = i + 1
            total_questions = len(questions)
            log_to_telegram(f"📝 Injected sub-location question")

    # 6. Check if quiz is complete
    if question_index == total_questions:
        log_to_telegram(f"🎉 Quiz complete! Building completion message...")

        # Build completion message - IDENTICAL to n8n
        formatted_answers = []
        for i in range(1, total_questions + 1):
            q = questions[i - 1]
            user_answer = answers.get(str(i))
            if user_answer:
                q_type = q.get('type', '')
                if q_type == 'contact_choice':
                    formatted_answers.append(f"Contact: {user_answer}")
                elif q_type == 'calendar_choice':
                    formatted_answers.append(f"Calendar: {user_answer}")
                elif q_type == 'city_choice':
                    formatted_answers.append(f"City: {user_answer}")
                elif q_type == 'venue_choice':
                    formatted_answers.append(f"Venue: {user_answer}")
                elif q_type == 'sub_location_choice':
                    formatted_answers.append(f"Location: {user_answer}")
                elif q_type == 'time_choice':
                    formatted_answers.append(f"Time: {user_answer}")
                elif q_type == 'duration_choice':
                    formatted_answers.append(f"Duration: {user_answer}")
                elif q_type == 'venue_type':
                    formatted_answers.append(f"Type: {user_answer}")
                elif q_type == 'people_choice':
                    formatted_answers.append(f"People: {user_answer}")
                elif q_type == 'conflict_choice':
                    formatted_answers.append(f"Proceed with conflict: {user_answer}")
                elif q_type == 'meeting_type':
                    formatted_answers.append(f"Meeting type: {user_answer}")

        context = quiz_data.get('context', '')
        clean_context = remove_html_tags(context)

        completion_text = (
            f"{clean_context}\n\n"
            f"✅ Quiz completed!\n\n"
            f"{chr(10).join(formatted_answers)}\n\n"
            f"⏳ Processing your request..."
        )

        # Update Supabase
        quiz_data['answers'] = answers
        quiz_data['questions'] = questions
        quiz_data['status'] = 'completed'
        supabase.table('task_temp_data').update({'data': quiz_data}).eq('id', record_id).execute()

        log_to_telegram(f"✅ Marked quiz as completed in Supabase")

        # Edit message - clear buttons
        edit_message_text(chat_id, message_id, completion_text, {"inline_keyboard": []})

        log_to_telegram(f"📤 Sent completion message")

        return "QUIZ_COMPLETE"

    # 7. Build next question - IDENTICAL pagination to n8n
    next_index = question_index + 1
    next_question = questions[next_index - 1]

    log_to_telegram(f"➡️ Moving to question {next_index}: {next_question.get('text', '')}")

    # Get options for next question
    next_options = get_options_for_question(next_question, quiz_data, answers, next_index, venues_by_city, clubs_data)

    # Cache options
    cache = quiz_data.get('all_options_cache', {})
    cache[str(next_index)] = next_options
    quiz_data['all_options_cache'] = cache

    # Pagination - IDENTICAL to n8n
    page = 0
    total_pages = max(1, (len(next_options) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start_idx = page * ITEMS_PER_PAGE
    page_options = next_options[start_idx:start_idx + ITEMS_PER_PAGE]

    # Build message text - IDENTICAL to n8n
    context = quiz_data.get('context', '')
    clean_context = remove_html_tags(context)
    message_text = f"{clean_context}\n\n"

    for i in range(1, question_index + 1):
        q = questions[i - 1]
        ans = answers.get(str(i))
        if ans:
            message_text += f"✅ {q.get('text', '')}: {ans}\n"

    message_text += f"\n📋 Step {next_index} of {total_questions}: {next_question.get('text', '')}"

    # Build keyboard - IDENTICAL layout to n8n
    keyboard = build_keyboard(task_id, next_index, page_options, start_idx, page, total_pages)

    # Update Supabase
    quiz_data['answers'] = answers
    quiz_data['questions'] = questions
    quiz_data['current_step'] = next_index
    supabase.table('task_temp_data').update({'data': quiz_data}).eq('id', record_id).execute()

    # Edit message
    edit_message_text(chat_id, message_id, message_text, keyboard)

    log_to_telegram(f"📤 Updated message with question {next_index}")

    return "NO_REPLY"


def get_options_for_question(question, quiz_data, answers, question_index, venues_by_city, clubs_data):
    """Get options for a question - IDENTICAL logic to n8n"""
    q_type = question.get('type', '')

    if q_type == 'venue_choice':
        # Get city from detected_city or previous answer
        selected_city = quiz_data.get('detected_city')
        if not selected_city:
            questions = quiz_data.get('questions', [])
            for i in range(1, question_index):
                q = questions[i - 1]
                if q.get('type') == 'city_choice' and answers.get(str(i)):
                    selected_city = answers.get(str(i))
                    break

        if selected_city and selected_city in venues_by_city:
            return venues_by_city[selected_city]
        return question.get('options', [])

    elif q_type == 'city_choice':
        return question.get('options', list(venues_by_city.keys()))

    elif q_type == 'time_choice':
        selected_venue = answers.get(str(question_index - 1))
        if selected_venue and selected_venue in clubs_data:
            times = clubs_data[selected_venue].get('times', [])
            # Format times
            formatted = []
            for t in times:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                    formatted.append(dt.strftime('%I:%M %p'))
                except:
                    formatted.append(t)
            return formatted
        return question.get('options', [])

    elif q_type == 'sub_location_choice':
        return question.get('options', ["Alco's flagship center", "Dubai Marina"])

    elif q_type == 'contact_choice':
        return question.get('options', [])

    elif q_type == 'calendar_choice':
        return question.get('options', [])

    else:
        return question.get('options', [])


def build_keyboard(task_id, question_index, page_options, start_idx, page, total_pages):
    """Build keyboard - IDENTICAL layout to n8n"""
    keyboard = {"inline_keyboard": []}

    i = 0
    while i < len(page_options):
        row = []
        items_to_add = 3

        # Back button on first row if not first question - IDENTICAL to n8n
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

    # Navigation row - IDENTICAL to n8n
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append({"text": "⬅️ Prev", "callback_data": f"quiz_nav|{task_id}|{question_index}|{page - 1}"})
        nav_row.append({"text": f"📄 {page + 1}/{total_pages}", "callback_data": "noop"})
        if page < total_pages - 1:
            nav_row.append({"text": "Next ➡️", "callback_data": f"quiz_nav|{task_id}|{question_index}|{page + 1}"})
        keyboard["inline_keyboard"].append(nav_row)

    return keyboard


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
    response = requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    })
    if response.status_code != 200:
        log_to_telegram(f"❌ Edit failed: {response.text[:100]}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 7:
        result = handle_quiz_progress(
            sys.argv[1],  # task_id
            int(sys.argv[2]),  # question_index
            int(sys.argv[3]),  # answer_index
            sys.argv[4],  # chat_id
            sys.argv[5],  # message_id
            sys.argv[6]   # callback_query_id
        )
        print(result)
