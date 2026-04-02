"""
Central logging for padel scripts.
All logs go to /var/log/openclaw_padel.log
"""

import os
import sys
from datetime import datetime

LOG_FILE = "/var/log/openclaw_padel.log"


def log(script_name: str, message: str):
    """Log a message with timestamp and script name."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [padel/{script_name}] {message}"

    # Print to stderr (goes to journalctl)
    print(line, file=sys.stderr)

    # Also write to log file
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except Exception:
        pass


def padel_log(message: str):
    """Log from padel_quiz.py"""
    log("quiz", message)


def venues_log(message: str):
    """Log from airtable_venues.py"""
    log("venues", message)


def conflicts_log(message: str):
    """Log from check_conflicts.py"""
    log("conflicts", message)
