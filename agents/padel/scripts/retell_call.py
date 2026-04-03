#!/usr/bin/env python3
"""
retell_call.py - Start a Retell AI voice call to a padel venue.

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

# Retell AI credentials
RETELL_API_KEY = os.environ.get("RETELL_API_KEY", "key_e5ece90d29d8b4f85f9f944e8a78")
RETELL_AGENT_ID = os.environ.get("RETELL_AGENT_ID", "agent_bcc0e2aca3fc80385361d5ec3b")
RETELL_FROM_NUMBER = os.environ.get("RETELL_FROM_NUMBER", "+13502203982")
RETELL_API_URL = "https://api.retellai.com/v2"

# Fallback: read from /etc/environment
for var_name, current_val, default_val in [
    ("RETELL_API_KEY", RETELL_API_KEY, "key_e5ece90d29d8b4f85f9f944e8a78"),
]:
    if current_val == default_val:
        try:
            with open("/etc/environment", "r") as f:
                for line in f:
                    if line.startswith(f"{var_name}="):
                        globals()[var_name] = line.strip().split("=", 1)[1].strip('"').strip("'")
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
    sub_location: str = "",
) -> dict:
    """Start a Retell AI voice call to a venue."""

    # Format current datetime in timezone
    now = datetime.now()
    current_datetime = now.strftime("%d/%m/%Y, %H:%M:%S")

    # Ensure phone has + prefix (E.164 format)
    phone = venue_phone.strip()
    if phone and not phone.startswith("+"):
        phone = f"+{phone}"

    # Build venue_greeting (handle Central Padel sub-locations)
    venue_greeting = venue_name
    if "central padel" in venue_name.lower() and sub_location:
        if "marina" in sub_location.lower():
            venue_greeting = "Central Padel Marina"
        elif "alco" in sub_location.lower():
            venue_greeting = "Central Padel Alco"

    payload = {
        "agent_id": RETELL_AGENT_ID,
        "from_number": RETELL_FROM_NUMBER,
        "to_number": phone,
        "retell_llm_dynamic_variables": {
            "city": city.strip(),
            "venue_name": venue_name,
            "venue_greeting": venue_greeting,
            "sub_location": sub_location,
            "booking_date": booking_date,
            "booking_time": booking_time,
            "duration": str(duration),
            "court_type": court_type,
            "timezone": timezone,
            "current_datetime": current_datetime,
            # Both formats - askFelix uses chat_id/user_id/task_id
            "chat_id": str(chat_id),
            "user_id": str(user_id),
            "task_id": str(task_id),
            "telegram_chat_id": str(chat_id),
            "telegram_task_id": str(task_id),
            "telegram_user_id": str(user_id),
        }
    }

    headers = {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json",
    }

    log(f"Starting Retell call to {venue_name} ({phone})")

    try:
        resp = requests.post(
            f"{RETELL_API_URL}/create-phone-call",
            headers=headers,
            json=payload,
            timeout=15,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            call_id = data.get("call_id", "")
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
            log(f"Retell error {resp.status_code}: {error}")
            return {
                "success": False,
                "error": f"Retell API error {resp.status_code}: {error}",
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
    """Check status of a Retell call via GET /v2/get-call/{call_id}."""
    headers = {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(
            f"{RETELL_API_URL}/get-call/{call_id}",
            headers=headers,
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            call_status = data.get("call_status", "unknown")
            disconnection_reason = data.get("disconnection_reason", "")

            result = {
                "success": True,
                "call_id": call_id,
                "status": call_status,  # registered, ongoing, ended, error
                "disconnection_reason": disconnection_reason,
            }

            # If call ended, extract transcript and analysis
            if call_status == "ended":
                # Get transcript
                transcript = data.get("transcript", "")
                transcript_object = data.get("transcript_object", [])

                # Build transcript lines
                transcript_lines = []
                for entry in transcript_object:
                    role = entry.get("role", "")
                    content = entry.get("content", "")
                    if role and content:
                        prefix = "🤖 Sam" if role == "agent" else "👤 Venue"
                        transcript_lines.append(f"{prefix}: {content}")

                # Get dynamic variables collected during call
                dynamic_vars = data.get("call_analysis", {})
                if not dynamic_vars:
                    dynamic_vars = {}

                # Also check retell_llm_dynamic_variables for current_node
                collected_vars = data.get("retell_llm_dynamic_variables", {})
                current_node = collected_vars.get("current_node", "")

                # Determine if call was picked up
                not_picked_up = disconnection_reason in [
                    "dial_no_answer", "dial_busy", "dial_failed",
                    "voicemail_reached", "no_answer",
                ]
                was_picked_up = not not_picked_up and call_status == "ended"

                # Determine success
                was_successful = False
                if current_node:
                    was_successful = "success" in current_node.lower()
                if not was_successful and transcript:
                    was_successful = any(kw in transcript.lower() for kw in [
                        "booking confirmed", "booked", "reserved",
                    ])

                # Extract available times
                times_available = []
                call_analysis = data.get("call_analysis", {})
                if call_analysis:
                    times_available = call_analysis.get("available_times", [])
                    if not times_available:
                        times_available = call_analysis.get("times_available", [])

                # Summary
                summary = call_analysis.get("call_summary", "")
                if not summary:
                    summary = call_analysis.get("summary", "")

                result.update({
                    "was_picked_up": was_picked_up,
                    "was_successful": was_successful,
                    "ended_reason": disconnection_reason,
                    "transcript_lines": transcript_lines,
                    "transcript_text": transcript,
                    "summary": summary,
                    "times_available": times_available,
                    "recording_url": data.get("recording_url", ""),
                    "cost_cents": int(float(data.get("cost", 0)) * 100),
                    "duration_seconds": int(data.get("call_duration_ms", 0) / 1000),
                    "current_node": current_node,
                })

            return result
        else:
            return {
                "success": False,
                "call_id": call_id,
                "error": f"Retell status check failed: {resp.status_code}",
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
    start_p.add_argument('--sub_location', default="")

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
            sub_location=args.sub_location,
        )
        print(json.dumps(result, indent=2))

    elif args.command == 'status':
        result = get_call_status(args.call_id)
        print(json.dumps(result, indent=2))

    else:
        print("Usage: retell_call.py {start|status} --help")


if __name__ == "__main__":
    main()
