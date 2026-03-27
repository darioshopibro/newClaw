"""
Central logging for calendar scripts.
All logs go to /var/log/openclaw_calendar.log
"""

import os
import sys
from datetime import datetime

LOG_FILE = "/var/log/openclaw_calendar.log"


def log(script_name: str, message: str):
    """Log a message with timestamp and script name."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{script_name}] {message}"

    # Print to stderr (goes to journalctl)
    print(line, file=sys.stderr)

    # Also write to log file
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[logger] Failed to write to {LOG_FILE}: {e}", file=sys.stderr)


def quiz_log(message: str):
    """Log from simple_quiz.py"""
    log("quiz", message)


def create_event_log(message: str):
    """Log from create_event.py"""
    log("create_event", message)


def calendar_log(message: str):
    """Log from google_calendar.py"""
    log("calendar", message)
