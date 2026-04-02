#!/usr/bin/env python3
"""
Check calendar conflicts for a padel booking time slot.
Reuses the same GoogleCalendarClient as the calendar skill.

Usage:
    python3 check_conflicts.py --date 2026-04-03 --time 18:00 --duration 90

Output: JSON with conflicts found
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from google_calendar import GoogleCalendarClient


def main():
    parser = argparse.ArgumentParser(description='Check calendar conflicts for padel booking')
    parser.add_argument('--date', required=True, help='Date in YYYY-MM-DD format')
    parser.add_argument('--time', required=True, help='Time in HH:MM format')
    parser.add_argument('--duration', type=int, default=90, help='Duration in minutes (default: 90)')
    parser.add_argument('--calendars', help='Comma-separated calendar keys (default: all)')

    args = parser.parse_args()

    calendars = None
    if args.calendars:
        calendars = [c.strip() for c in args.calendars.split(',')]

    try:
        client = GoogleCalendarClient()
        result = client.check_conflicts(
            date=args.date,
            time=args.time,
            duration_minutes=args.duration,
            calendars=calendars,
        )
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'conflicts': [],
            'error': str(e),
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
