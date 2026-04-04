#!/usr/bin/env python3
"""
wa_booking_db.py - Supabase operations for WhatsApp padel bookings.

Tables:
  - whatsapp_bookings: Per-venue WA booking status
  - venue_availability_results: Aggregated progress data

Usage:
  python3 wa_booking_db.py create --task_id "padel_123" --venue_name "Central Padel" \
    --venue_phone "+971501234567" --booking_date "2026-04-04" --booking_time "18:00" \
    --duration 90 --chat_id "5127607280"

  python3 wa_booking_db.py get --task_id "padel_123" --venue_name "Central Padel"

  python3 wa_booking_db.py update-status --task_id "padel_123" --venue_name "Central Padel" \
    --status "has_times" --times '["18:00","19:00"]'

  python3 wa_booking_db.py list --task_id "padel_123"
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import padel_log as log

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qluqynpozzukaoxyuqou.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Fallback
if not SUPABASE_KEY:
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                if line.startswith("SUPABASE_SERVICE_KEY="):
                    SUPABASE_KEY = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    except Exception:
        pass

# Use requests directly instead of supabase-py (simpler, no dependency issues)
import requests

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def _url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


# ── whatsapp_bookings operations ─────────────────────────────

def create_wa_booking(
    task_id: str,
    venue_name: str,
    venue_phone: str,
    booking_date: str,
    booking_time: str,
    duration_minutes: int,
    chat_id: str,
    user_id: str = "",
    progress_message_id: int = 0,
) -> dict:
    """Create a new WA booking entry."""
    data = {
        "task_id": task_id,
        "venue_name": venue_name,
        "venue_phone": venue_phone,
        "booking_date": booking_date,
        "booking_time": booking_time,
        "duration_minutes": duration_minutes,
        "chat_id": chat_id,
        "user_id": user_id,
        "status": "pending",
        "delivery_status": "sending",
        "conversation_history": [],
    }

    try:
        resp = requests.post(_url("whatsapp_bookings"), headers=HEADERS, json=data, timeout=10)
        if resp.status_code in (200, 201):
            result = resp.json()
            row = result[0] if isinstance(result, list) else result
            log(f"WA booking created: {task_id}/{venue_name}")
            return {"success": True, "id": row.get("id"), "data": row}
        else:
            log(f"Create WA booking error {resp.status_code}: {resp.text[:200]}")
            return {"success": False, "error": resp.text[:200]}
    except Exception as e:
        log(f"Create WA booking failed: {e}")
        return {"success": False, "error": str(e)}


def get_wa_booking(task_id: str, venue_name: str = None) -> dict:
    """Get WA booking(s) for a task."""
    params = {"task_id": f"eq.{task_id}"}
    if venue_name:
        params["venue_name"] = f"eq.{venue_name}"

    try:
        resp = requests.get(_url("whatsapp_bookings"), headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if venue_name:
                return {"success": True, "data": data[0] if data else None}
            return {"success": True, "data": data}
        return {"success": False, "error": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_wa_booking(task_id: str, venue_name: str, updates: dict) -> dict:
    """Update WA booking fields."""
    params = {
        "task_id": f"eq.{task_id}",
        "venue_name": f"eq.{venue_name}",
    }

    try:
        resp = requests.patch(
            _url("whatsapp_bookings"),
            headers=HEADERS,
            params=params,
            json=updates,
            timeout=10,
        )
        if resp.status_code in (200, 204):
            log(f"WA booking updated: {task_id}/{venue_name} → {list(updates.keys())}")
            return {"success": True}
        return {"success": False, "error": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_wa_status(task_id: str, venue_name: str, status: str, **extra) -> dict:
    """Update venue booking status."""
    updates = {"status": status}
    if extra.get("times"):
        updates["times"] = json.dumps(extra["times"]) if isinstance(extra["times"], list) else extra["times"]
    if extra.get("delivery_status"):
        updates["delivery_status"] = extra["delivery_status"]
    if extra.get("confirmed_at"):
        updates["confirmed_at"] = extra["confirmed_at"]
    if extra.get("wait_until"):
        updates["wait_until"] = extra["wait_until"]
    if extra.get("conversation_history"):
        updates["conversation_history"] = json.dumps(extra["conversation_history"])
    return update_wa_booking(task_id, venue_name, updates)


def add_conversation_message(task_id: str, venue_name: str, role: str, message: str) -> dict:
    """Add a message to conversation history."""
    booking = get_wa_booking(task_id, venue_name)
    if not booking.get("success") or not booking.get("data"):
        return {"success": False, "error": "Booking not found"}

    data = booking["data"]
    history = data.get("conversation_history", [])
    if isinstance(history, str):
        history = json.loads(history)

    history.append({
        "role": role,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return update_wa_booking(task_id, venue_name, {
        "conversation_history": json.dumps(history),
    })


def mark_confirmed(task_id: str, venue_name: str, confirmed_time: str = "") -> dict:
    """Mark booking as confirmed."""
    return update_wa_status(
        task_id, venue_name, "confirmed",
        confirmed_at=datetime.utcnow().isoformat(),
    )


def mark_rejected(task_id: str, venue_name: str) -> dict:
    """Mark booking as rejected."""
    return update_wa_status(
        task_id, venue_name, "rejected",
        wait_until=datetime.utcnow().isoformat(),
    )


def extend_wait(task_id: str, venue_name: str, extra_seconds: int = 30) -> dict:
    """Extend wait deadline."""
    booking = get_wa_booking(task_id, venue_name)
    if not booking.get("success") or not booking.get("data"):
        return {"success": False, "error": "Booking not found"}

    data = booking["data"]
    current_wait = data.get("wait_until", datetime.utcnow().isoformat())
    current_extended = data.get("total_extended_seconds", 0)

    new_wait = (datetime.fromisoformat(current_wait.replace("Z", "+00:00").replace("+00:00", "")) +
                timedelta(seconds=extra_seconds))

    return update_wa_booking(task_id, venue_name, {
        "wait_until": new_wait.isoformat(),
        "total_extended_seconds": current_extended + extra_seconds,
    })


def get_active_bookings(task_id: str) -> list:
    """Get all active WA bookings for a task (not rejected/confirmed)."""
    params = {
        "task_id": f"eq.{task_id}",
        "status": "not.in.(rejected,confirmed,timeout)",
    }
    try:
        resp = requests.get(_url("whatsapp_bookings"), headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []


def find_booking_by_phone(venue_phone: str) -> dict:
    """Find active booking by venue phone (for incoming WA messages)."""
    phone = venue_phone.strip().lstrip("+")
    params = {
        "venue_phone": f"like.*{phone}*",
        "status": "not.in.(rejected,confirmed,timeout)",
        "order": "created_at.desc",
        "limit": "1",
    }
    try:
        resp = requests.get(_url("whatsapp_bookings"), headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {"success": True, "data": data[0] if data else None}
        return {"success": False, "error": resp.text[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Create
    create_p = subparsers.add_parser('create')
    create_p.add_argument('--task_id', required=True)
    create_p.add_argument('--venue_name', required=True)
    create_p.add_argument('--venue_phone', required=True)
    create_p.add_argument('--booking_date', required=True)
    create_p.add_argument('--booking_time', required=True)
    create_p.add_argument('--duration', type=int, default=90)
    create_p.add_argument('--chat_id', required=True)
    create_p.add_argument('--user_id', default="")
    create_p.add_argument('--progress_message_id', type=int, default=0)

    # Get
    get_p = subparsers.add_parser('get')
    get_p.add_argument('--task_id', required=True)
    get_p.add_argument('--venue_name')

    # Update status
    upd_p = subparsers.add_parser('update-status')
    upd_p.add_argument('--task_id', required=True)
    upd_p.add_argument('--venue_name', required=True)
    upd_p.add_argument('--status', required=True)
    upd_p.add_argument('--times', help="JSON array of times")
    upd_p.add_argument('--delivery_status')

    # List active
    list_p = subparsers.add_parser('list')
    list_p.add_argument('--task_id', required=True)

    # Find by phone
    find_p = subparsers.add_parser('find-by-phone')
    find_p.add_argument('--phone', required=True)

    args = parser.parse_args()

    if args.command == 'create':
        result = create_wa_booking(
            args.task_id, args.venue_name, args.venue_phone,
            args.booking_date, args.booking_time, args.duration,
            args.chat_id, args.user_id, args.progress_message_id,
        )
        print(json.dumps(result, indent=2))
    elif args.command == 'get':
        result = get_wa_booking(args.task_id, args.venue_name)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == 'update-status':
        extra = {}
        if args.times:
            extra["times"] = json.loads(args.times)
        if args.delivery_status:
            extra["delivery_status"] = args.delivery_status
        result = update_wa_status(args.task_id, args.venue_name, args.status, **extra)
        print(json.dumps(result, indent=2))
    elif args.command == 'list':
        result = get_active_bookings(args.task_id)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == 'find-by-phone':
        result = find_booking_by_phone(args.phone)
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: wa_booking_db.py {create|get|update-status|list|find-by-phone} --help")


if __name__ == "__main__":
    main()
