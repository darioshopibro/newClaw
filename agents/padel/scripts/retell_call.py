#!/usr/bin/env python3
"""
retell_call.py - Start a VAPI/Retell voice call to a padel venue.

Usage:
  python3 retell_call.py start \
    --venue_phone "+971501234567" \
    --venue_name "Central Padel" \
    --booking_date "2026-04-03" \
    --booking_time "18:00" \
    --duration "90" \
    --city "Dubai" \
    --task_id "padel_123" \
    --chat_id "5127607280"

  python3 retell_call.py status --call_id "call_xxx"

Output: JSON with call_id or call status
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import padel_log as log

# VAPI credentials - read from env with fallbacks
VAPI_API_KEY = os.environ.get("VAPI_API_KEY", "77aa4e70-843e-4f41-963c-79214522af40")
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID", "9d7be5f7-28fa-43ec-acfa-88dc0fcb23fa")
VAPI_PHONE_NUMBER_ID = os.environ.get("VAPI_PHONE_NUMBER_ID", "336ca3a4-21f5-4c2d-bd24-a69c5c83f08e")
VAPI_API_URL = "https://api.vapi.ai/call"

# Also try /etc/environment
if VAPI_API_KEY == "77aa4e70-843e-4f41-963c-79214522af40":
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                if line.startswith("VAPI_API_KEY="):
                    VAPI_API_KEY = line.strip().split("=", 1)[1].strip('"').strip("'")
    except Exception:
        pass


def start_call(
    venue_phone: str,
    venue_name: str,
    booking_date: str,
    booking_time: str,
    duration: str = "90",
    city: str = "",
    court_type: str = "any",
    task_id: str = "",
    chat_id: str = "",
    user_id: str = "",
    timezone: str = "Europe/Berlin",
) -> dict:
    """Start a VAPI voice call to a venue."""

    # Format current datetime in timezone
    now = datetime.now()
    current_datetime = now.strftime("%Y-%m-%d %H:%M:%S")

    # Ensure phone has + prefix
    phone = venue_phone.strip()
    if phone and not phone.startswith("+"):
        phone = f"+{phone}"

    payload = {
        "assistantId": VAPI_ASSISTANT_ID,
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": phone,
        },
        "assistantOverrides": {
            "variableValues": {
                "venue_name": venue_name,
                "booking_date": booking_date,
                "booking_time": booking_time,
                "duration": str(duration),
                "court_type": court_type,
                "city": city,
                "timezone": timezone,
                "number_courts": 1,
                "venue_phone": phone,
                "telegram_chat_id": str(chat_id),
                "telegram_user_id": str(user_id),
                "telegram_task_id": str(task_id),
                "current_datetime": current_datetime,
                "Recall": None,
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }

    log(f"Starting call to {venue_name} ({phone})")

    try:
        resp = requests.post(VAPI_API_URL, headers=headers, json=payload, timeout=15)

        if resp.status_code in (200, 201):
            data = resp.json()
            call_id = data.get("id", "")
            log(f"Call started: {call_id}")
            return {
                "success": True,
                "call_id": call_id,
                "status": "queued",
                "venue_name": venue_name,
                "venue_phone": phone,
            }
        else:
            error = resp.text[:300]
            log(f"VAPI error {resp.status_code}: {error}")
            return {
                "success": False,
                "error": f"VAPI API error {resp.status_code}: {error}",
                "venue_name": venue_name,
            }

    except Exception as e:
        log(f"Call failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "venue_name": venue_name,
        }


def get_call_status(call_id: str) -> dict:
    """Check status of a VAPI call."""
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(f"{VAPI_API_URL}/{call_id}", headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")

            result = {
                "success": True,
                "call_id": call_id,
                "status": status,  # queued, ringing, in-progress, forwarding, ended
                "ended_reason": data.get("endedReason", ""),
            }

            # If call ended, extract transcript and analysis
            if status == "ended":
                # Get transcript
                transcript_parts = data.get("transcript", "")
                messages = data.get("messages", [])

                # Build transcript lines
                transcript_lines = []
                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("message", msg.get("content", ""))
                    if role and content:
                        prefix = "🤖 Sam" if role == "assistant" else "👤 Venue"
                        transcript_lines.append(f"{prefix}: {content}")

                # Get analysis/summary from VAPI
                analysis = data.get("analysis", {})
                summary = analysis.get("summary", "")
                structured_data = analysis.get("structuredData", {})

                # Determine success
                ended_reason = data.get("endedReason", "")
                was_picked_up = ended_reason not in [
                    "dial_no_answer", "dial_busy", "dial_failed",
                    "voicemail_reached", "phone-call-provider-bypass-enabled-but-]]]"
                ]

                # Check if booking was successful
                was_successful = False
                if structured_data:
                    was_successful = structured_data.get("booking_confirmed", False)
                if not was_successful and summary:
                    was_successful = any(kw in summary.lower() for kw in [
                        "booking confirmed", "booked", "reserved", "confirmation"
                    ])

                # Extract available times
                times_available = []
                if structured_data:
                    times_available = structured_data.get("available_times", [])
                    if not times_available:
                        times_available = structured_data.get("times_available", [])

                result.update({
                    "was_picked_up": was_picked_up,
                    "was_successful": was_successful,
                    "ended_reason": ended_reason,
                    "transcript_lines": transcript_lines,
                    "transcript_text": transcript_parts,
                    "summary": summary,
                    "times_available": times_available,
                    "structured_data": structured_data,
                    "recording_url": data.get("recordingUrl", ""),
                    "cost_cents": int(data.get("cost", 0) * 100) if data.get("cost") else 0,
                    "duration_seconds": data.get("duration", 0),
                })

            return result
        else:
            return {
                "success": False,
                "call_id": call_id,
                "error": f"VAPI status check failed: {resp.status_code}",
            }

    except Exception as e:
        return {
            "success": False,
            "call_id": call_id,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Start call
    start_p = subparsers.add_parser('start')
    start_p.add_argument('--venue_phone', required=True)
    start_p.add_argument('--venue_name', required=True)
    start_p.add_argument('--booking_date', required=True)
    start_p.add_argument('--booking_time', required=True)
    start_p.add_argument('--duration', default="90")
    start_p.add_argument('--city', default="")
    start_p.add_argument('--court_type', default="any")
    start_p.add_argument('--task_id', default="")
    start_p.add_argument('--chat_id', default="")
    start_p.add_argument('--user_id', default="")
    start_p.add_argument('--timezone', default="Europe/Berlin")

    # Check status
    status_p = subparsers.add_parser('status')
    status_p.add_argument('--call_id', required=True)

    args = parser.parse_args()

    if args.command == 'start':
        result = start_call(
            venue_phone=args.venue_phone,
            venue_name=args.venue_name,
            booking_date=args.booking_date,
            booking_time=args.booking_time,
            duration=args.duration,
            city=args.city,
            court_type=args.court_type,
            task_id=args.task_id,
            chat_id=args.chat_id,
            user_id=args.user_id,
            timezone=args.timezone,
        )
        print(json.dumps(result, indent=2))

    elif args.command == 'status':
        result = get_call_status(args.call_id)
        print(json.dumps(result, indent=2))

    else:
        print("Usage: retell_call.py {start|status} --help")


if __name__ == "__main__":
    main()
