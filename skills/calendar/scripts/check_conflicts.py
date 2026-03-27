#!/usr/bin/env python3
"""
Check calendar conflicts for a given time slot.

Usage:
    python check_conflicts.py --date 2024-03-15 --time 14:00 --duration 60

Output: JSON with conflicts found
"""

import argparse
import json
import sys
from lib.google_calendar import GoogleCalendarClient


def main():
    parser = argparse.ArgumentParser(description='Check calendar conflicts')
    parser.add_argument('--date', required=True, help='Date in YYYY-MM-DD format')
    parser.add_argument('--time', required=True, help='Time in HH:MM format')
    parser.add_argument('--duration', type=int, default=60, help='Duration in minutes')
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
            calendars=calendars
        )
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
