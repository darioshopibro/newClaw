#!/usr/bin/env python3
"""
handle_callback.py - Main router for callback processing
Parses callback_data pattern and routes to appropriate handler
NO forwarding to n8n - everything processed directly here

LOGGING: Sends debug logs to Telegram so we can see what's happening
"""

import sys
import os
import requests

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quiz_progress import handle_quiz_progress
from quiz_navigate import handle_quiz_navigate
from quiz_back import handle_quiz_back
from settings_handler import handle_calendar_settings

# Telegram logging
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
LOG_CHAT_ID = "5127607280"


def log_to_telegram(message: str):
    """Send log message to Telegram for debugging"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": LOG_CHAT_ID,
            "text": f"🔧 [handle_callback.py]\n{message}",
            "parse_mode": "HTML"
        }, timeout=5)
    except:
        pass  # Don't fail if logging fails


def main():
    if len(sys.argv) < 5:
        print("Usage: handle_callback.py <callback_data> <chat_id> <message_id> <callback_query_id>")
        sys.exit(1)

    callback_data = sys.argv[1]
    chat_id = sys.argv[2]
    message_id = sys.argv[3]
    callback_query_id = sys.argv[4]

    log_to_telegram(f"📥 Received callback:\n<code>{callback_data}</code>")

    # Parse callback pattern and route
    if callback_data.startswith('quiz|'):
        # quiz|taskId|questionIndex|answerIndex
        parts = callback_data.split('|')
        if len(parts) >= 4:
            task_id = parts[1]
            question_index = int(parts[2])
            answer_index = int(parts[3])
            log_to_telegram(f"➡️ Routing to quiz_progress\ntask: {task_id}\nq: {question_index}, a: {answer_index}")
            result = handle_quiz_progress(task_id, question_index, answer_index, chat_id, message_id, callback_query_id)
            log_to_telegram(f"📤 Result: {result[:100] if len(result) > 100 else result}")
            print(result)

    elif callback_data.startswith('quiz_nav|'):
        # quiz_nav|taskId|questionIndex|page
        parts = callback_data.split('|')
        if len(parts) >= 4:
            task_id = parts[1]
            question_index = int(parts[2])
            page = int(parts[3])
            log_to_telegram(f"➡️ Routing to quiz_navigate\ntask: {task_id}\nq: {question_index}, page: {page}")
            result = handle_quiz_navigate(task_id, question_index, page, chat_id, message_id, callback_query_id)
            log_to_telegram(f"📤 Result: {result[:100] if len(result) > 100 else result}")
            print(result)

    elif callback_data.startswith('quiz_back|'):
        # quiz_back|taskId|targetStep
        parts = callback_data.split('|')
        if len(parts) >= 3:
            task_id = parts[1]
            target_step = int(parts[2])
            log_to_telegram(f"➡️ Routing to quiz_back\ntask: {task_id}\ntarget: {target_step}")
            result = handle_quiz_back(task_id, target_step, chat_id, message_id, callback_query_id)
            log_to_telegram(f"📤 Result: {result[:100] if len(result) > 100 else result}")
            print(result)

    elif callback_data.startswith('cs|'):
        # cs|taskId|field|value - Calendar Settings
        parts = callback_data.split('|')
        if len(parts) >= 3:
            task_id = parts[1]
            field = parts[2]
            value = parts[3] if len(parts) >= 4 else None
            log_to_telegram(f"➡️ Routing to calendar_settings\ntask: {task_id}\nfield: {field}, value: {value}")
            result = handle_calendar_settings(task_id, field, value, chat_id, message_id, callback_query_id)
            log_to_telegram(f"📤 Result: {result[:100] if len(result) > 100 else result}")
            print(result)

    elif callback_data in ['noop', 'ignore']:
        # Ignore these - just answer the callback query
        log_to_telegram(f"⏹️ noop/ignore callback")
        answer_callback_query(callback_query_id)
        print("NO_REPLY")

    else:
        log_to_telegram(f"❓ Unknown callback: {callback_data}")
        print(f"UNKNOWN_CALLBACK: {callback_data}")


def answer_callback_query(callback_query_id):
    """Answer callback query to remove loading state"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_query_id})


if __name__ == "__main__":
    main()
