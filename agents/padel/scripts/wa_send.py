#!/usr/bin/env python3
"""
wa_send.py - Send WhatsApp messages to padel venues.

Supports:
  - Template messages (initial booking request)
  - Free-form text messages (agent replies)

Usage:
  # Send booking template
  python3 wa_send.py template \
    --to "+971501234567" \
    --booking_date "2026-04-04" \
    --booking_time "18:00" \
    --duration "90"

  # Send text message
  python3 wa_send.py text \
    --to "+971501234567" \
    --message "I'd like to confirm the 6 PM slot"

  # Check message status
  python3 wa_send.py status --message_id "wamid.xxx"

Output: JSON with message_id and status
"""

import os
import sys
import json
import argparse
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import padel_log as log

# WhatsApp Cloud API config
WA_PHONE_NUMBER_ID = os.environ.get("WA_PHONE_NUMBER_ID", "995894160271205")
WA_ACCESS_TOKEN = os.environ.get("WA_ACCESS_TOKEN", "")
WA_API_URL = f"https://graph.facebook.com/v19.0/{WA_PHONE_NUMBER_ID}/messages"
WA_TEMPLATE_NAME = "padel_booking_util"
WA_TEMPLATE_LANG = "en"

# Fallback: read from /etc/environment
if not WA_ACCESS_TOKEN:
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                if line.startswith("WA_ACCESS_TOKEN="):
                    WA_ACCESS_TOKEN = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    except Exception:
        pass


def send_template(to_phone: str, booking_date: str, booking_time: str, duration: str) -> dict:
    """Send WhatsApp template message for booking request."""
    if not WA_ACCESS_TOKEN:
        return {"success": False, "error": "WA_ACCESS_TOKEN not set"}

    # Ensure phone has proper format (no + prefix for WA API)
    phone = to_phone.strip().lstrip("+")

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": WA_TEMPLATE_NAME,
            "language": {"code": WA_TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": booking_date},
                        {"type": "text", "text": booking_time},
                        {"type": "text", "text": str(duration)},
                    ]
                }
            ]
        }
    }

    headers = {
        "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    log(f"Sending WA template to {phone}: {booking_date} {booking_time} {duration}min")

    try:
        resp = requests.post(WA_API_URL, headers=headers, json=payload, timeout=15)
        data = resp.json()

        if resp.status_code in (200, 201):
            msg_id = data.get("messages", [{}])[0].get("id", "")
            log(f"WA template sent: {msg_id}")
            return {
                "success": True,
                "message_id": msg_id,
                "status": "sent",
                "to": phone,
            }
        else:
            error = data.get("error", {}).get("message", resp.text[:200])
            log(f"WA template error {resp.status_code}: {error}")
            return {"success": False, "error": error}

    except Exception as e:
        log(f"WA send failed: {e}")
        return {"success": False, "error": str(e)}


def send_text(to_phone: str, message: str) -> dict:
    """Send free-form text message to venue."""
    if not WA_ACCESS_TOKEN:
        return {"success": False, "error": "WA_ACCESS_TOKEN not set"}

    phone = to_phone.strip().lstrip("+")

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    headers = {
        "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    log(f"Sending WA text to {phone}: {message[:50]}...")

    try:
        resp = requests.post(WA_API_URL, headers=headers, json=payload, timeout=15)
        data = resp.json()

        if resp.status_code in (200, 201):
            msg_id = data.get("messages", [{}])[0].get("id", "")
            log(f"WA text sent: {msg_id}")
            return {
                "success": True,
                "message_id": msg_id,
                "status": "sent",
                "to": phone,
            }
        else:
            error = data.get("error", {}).get("message", resp.text[:200])
            log(f"WA text error {resp.status_code}: {error}")
            return {"success": False, "error": error}

    except Exception as e:
        log(f"WA send failed: {e}")
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Template command
    tmpl_p = subparsers.add_parser('template')
    tmpl_p.add_argument('--to', required=True, help="Venue phone number")
    tmpl_p.add_argument('--booking_date', required=True)
    tmpl_p.add_argument('--booking_time', required=True)
    tmpl_p.add_argument('--duration', default="90")

    # Text command
    text_p = subparsers.add_parser('text')
    text_p.add_argument('--to', required=True, help="Venue phone number")
    text_p.add_argument('--message', required=True)

    args = parser.parse_args()

    if args.command == 'template':
        result = send_template(args.to, args.booking_date, args.booking_time, args.duration)
        print(json.dumps(result, indent=2))
    elif args.command == 'text':
        result = send_text(args.to, args.message)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: wa_send.py {template|text} --help")


if __name__ == "__main__":
    main()
