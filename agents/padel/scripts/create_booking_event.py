#!/usr/bin/env python3
"""
create_booking_event.py - Create Google Calendar event for confirmed padel booking.

Usage:
  python3 create_booking_event.py \
    --title "Padel at Central Padel" \
    --date "2026-04-03" \
    --time "18:00" \
    --duration "90" \
    --venue "Central Padel" \
    --city "Dubai" \
    --calendar "shopibro"

Output: JSON with success, event_id, link
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import padel_log as log
from google_calendar import GoogleCalendarClient


def create_event(
    title: str,
    date: str,
    time_str: str,
    duration: int = 90,
    venue: str = "",
    city: str = "",
    calendar: str = "shopibro",
    attendees: str = "",
) -> dict:
    """Create a Google Calendar event for padel booking."""

    description = f"Padel booking at {venue}"
    if city:
        description += f", {city}"

    log(f"Creating event: {title} on {date} at {time_str}, {duration}min, calendar={calendar}")

    try:
        client = GoogleCalendarClient()
        result = client.create_event(
            title=title,
            date=date,
            time=time_str,
            duration_minutes=duration,
            calendar_key=calendar,
            description=description,
            attendees=attendees.split(",") if attendees else [],
        )

        if result.get("success"):
            log(f"Event created: {result.get('event_id')}")
        else:
            log(f"Event creation failed: {result.get('error')}")

        return result

    except Exception as e:
        log(f"Error creating event: {e}")
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--title', required=True)
    parser.add_argument('--date', required=True, help="YYYY-MM-DD")
    parser.add_argument('--time', required=True, help="HH:MM")
    parser.add_argument('--duration', type=int, default=90, help="Minutes")
    parser.add_argument('--venue', default="")
    parser.add_argument('--city', default="")
    parser.add_argument('--calendar', default="shopibro")
    parser.add_argument('--attendees', default="", help="Comma-separated emails")

    args = parser.parse_args()

    result = create_event(
        title=args.title,
        date=args.date,
        time_str=args.time,
        duration=args.duration,
        venue=args.venue,
        city=args.city,
        calendar=args.calendar,
        attendees=args.attendees,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
