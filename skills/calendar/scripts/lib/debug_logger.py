#!/usr/bin/env python3
"""
debug_logger.py - Centralized logging to Telegram

Usage:
    from lib.debug_logger import log

    log("Step 1: Searching contacts", {"query": "John", "source": "search_contacts.py"})
    log("ERROR: Contact not found", error=True)
"""

import requests
import json
from datetime import datetime

BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
LOG_CHAT_ID = "5127607280"

# Emojis for different log types
ICONS = {
    'start': '🚀',
    'step': '📍',
    'data': '📦',
    'api': '🌐',
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'callback': '🔔',
    'result': '📤'
}


def log(message: str, data: dict = None, log_type: str = 'step', source: str = None, error: bool = False):
    """
    Send structured log message to Telegram

    Args:
        message: Main log message
        data: Optional dict of data to include
        log_type: One of: start, step, data, api, success, error, warning, callback, result
        source: Script/function name
        error: If True, uses error icon
    """
    if error:
        log_type = 'error'

    icon = ICONS.get(log_type, '📝')
    timestamp = datetime.now().strftime('%H:%M:%S')

    # Build message
    text_parts = [f"{icon} [{timestamp}]"]

    if source:
        text_parts[0] += f" <b>{source}</b>"

    text_parts.append(message)

    if data:
        # Format data nicely
        data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        if len(data_str) > 500:
            data_str = data_str[:500] + "..."
        text_parts.append(f"<pre>{data_str}</pre>")

    text = "\n".join(text_parts)

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": LOG_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=5)
        return response.ok
    except Exception as e:
        # Silently fail - don't break main flow
        return False


def log_start(script_name: str, args: dict = None):
    """Log script start"""
    log(f"Starting", data=args, log_type='start', source=script_name)


def log_step(step_name: str, data: dict = None, source: str = None):
    """Log a processing step"""
    log(step_name, data=data, log_type='step', source=source)


def log_api_call(endpoint: str, data: dict = None, source: str = None):
    """Log an API call"""
    log(f"API: {endpoint}", data=data, log_type='api', source=source)


def log_success(message: str, data: dict = None, source: str = None):
    """Log success"""
    log(message, data=data, log_type='success', source=source)


def log_error(message: str, data: dict = None, source: str = None):
    """Log error"""
    log(message, data=data, log_type='error', source=source)


def log_result(result: dict, source: str = None):
    """Log final result"""
    log("Result", data=result, log_type='result', source=source)


# Quick test
if __name__ == "__main__":
    log_start("debug_logger.py", {"test": True})
    log_step("Testing logging", {"value": 123})
    log_api_call("telegram/sendMessage", {"chat_id": "123"})
    log_success("Test passed!")
    print("Logs sent to Telegram")
