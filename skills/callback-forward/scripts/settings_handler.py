#!/usr/bin/env python3
"""
settings_handler.py - Handle cs| callbacks (Calendar Settings)
Translated from n8n CalendarSettingsHandler - IDENTICAL logic
"""

import os
import json
import requests
from supabase import create_client

# Config
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://qdrtfwnftwfuykjyvyxd.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"

def handle_calendar_settings(task_id, field, value, chat_id, message_id, callback_query_id):
    """
    Handle calendar settings toggle - IDENTICAL to n8n CalendarSettingsHandler
    3-column layout: Calendar | Duration | Type
    """
    # Answer callback query immediately
    answer_callback_query(callback_query_id)

    # 1. Lookup session from Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    result = supabase.table('task_temp_data').select('*').eq('task_id', task_id).execute()

    if not result.data:
        return "ERROR: Session not found"

    record = result.data[0]
    record_id = record['id']
    data = record['data'] if isinstance(record['data'], dict) else json.loads(record['data'])

    settings = data.get('settings', {
        'calendar': 'moses',
        'duration': '1hr',
        'type': 'in-person'
    })
    context = data.get('context', '')
    steps = data.get('steps', [])
    current_step = data.get('current_step', 1)
    total_steps = data.get('total_steps', 1)

    # 2. Handle action - IDENTICAL to n8n
    if field == 'back':
        # Go back to previous step
        # This would be handled differently based on your flow
        return "BACK"

    elif field == 'proceed':
        # User confirmed settings - mark complete
        data['settings_confirmed'] = True
        supabase.table('task_temp_data').update({'data': data}).eq('id', record_id).execute()

        # Clear buttons
        edit_message_reply_markup(chat_id, message_id, {"inline_keyboard": []})
        return "SETTINGS_CONFIRMED"

    elif field == 'cancel':
        # User cancelled
        data['cancelled'] = True
        supabase.table('task_temp_data').update({'data': data}).eq('id', record_id).execute()

        edit_message_text(chat_id, message_id, "❌ Cancelled", {"inline_keyboard": []})
        return "CANCELLED"

    elif field == 'cal':
        # Toggle calendar selection
        settings['calendar'] = value

    elif field == 'dur':
        # Toggle duration selection
        settings['duration'] = value

    elif field == 'type':
        # Toggle meeting type selection
        settings['type'] = value

    # 3. Save updated settings
    data['settings'] = settings
    supabase.table('task_temp_data').update({'data': data}).eq('id', record_id).execute()

    # 4. Find settings step index for step list
    settings_step_idx = -1
    for i, step in enumerate(steps):
        if step.get('type') == 'settings':
            settings_step_idx = i
            break
    show_back = settings_step_idx > 0

    # 5. Build compact 3-column layout - IDENTICAL to n8n
    keyboard = {"inline_keyboard": []}

    # Row 1: Back (if needed) | Moses | 30m
    row1 = []
    if show_back:
        row1.append({"text": "⬅️ Back", "callback_data": f"cs|{task_id}|back"})
    row1.append({
        "text": "✅ Moses" if settings.get('calendar') == 'moses' else "⬜ Moses",
        "callback_data": f"cs|{task_id}|cal|moses"
    })
    row1.append({
        "text": "✅ 30m" if settings.get('duration') == '30m' else "⬜ 30m",
        "callback_data": f"cs|{task_id}|dur|30m"
    })
    keyboard["inline_keyboard"].append(row1)

    # Row 2: Online | ETG | 1hr
    keyboard["inline_keyboard"].append([
        {
            "text": "✅ Online" if settings.get('type') == 'online' else "⬜ Online",
            "callback_data": f"cs|{task_id}|type|online"
        },
        {
            "text": "✅ ETG" if settings.get('calendar') == 'etg' else "⬜ ETG",
            "callback_data": f"cs|{task_id}|cal|etg"
        },
        {
            "text": "✅ 1hr" if settings.get('duration') == '1hr' else "⬜ 1hr",
            "callback_data": f"cs|{task_id}|dur|1hr"
        }
    ])

    # Row 3: In-person | Family | 1.5hr
    keyboard["inline_keyboard"].append([
        {
            "text": "✅ In-person" if settings.get('type') == 'in-person' else "⬜ In-person",
            "callback_data": f"cs|{task_id}|type|in-person"
        },
        {
            "text": "✅ Family" if settings.get('calendar') == 'family' else "⬜ Family",
            "callback_data": f"cs|{task_id}|cal|family"
        },
        {
            "text": "✅ 1.5hr" if settings.get('duration') == '1.5hr' else "⬜ 1.5hr",
            "callback_data": f"cs|{task_id}|dur|1.5hr"
        }
    ])

    # Row 4: Proceed | Cancel
    keyboard["inline_keyboard"].append([
        {"text": "⏩ Proceed", "callback_data": f"cs|{task_id}|proceed"},
        {"text": "❌ Cancel", "callback_data": f"cs|{task_id}|cancel"}
    ])

    # 6. Edit message buttons only
    edit_message_reply_markup(chat_id, message_id, keyboard)

    return "NO_REPLY"


def answer_callback_query(callback_query_id):
    """Answer callback query to remove loading state"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_query_id})


def edit_message_reply_markup(chat_id, message_id, keyboard):
    """Edit message buttons only"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup"
    requests.post(url, json={
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": keyboard
    })


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
        result = handle_calendar_settings(
            sys.argv[1],  # task_id
            sys.argv[2],  # field
            sys.argv[3] if len(sys.argv) > 3 else None,  # value
            sys.argv[4],  # chat_id
            sys.argv[5],  # message_id
            sys.argv[6] if len(sys.argv) > 6 else ""  # callback_query_id
        )
        print(result)
