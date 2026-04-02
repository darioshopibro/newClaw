#!/usr/bin/env python3
"""
padel_quiz.py - Multi-step padel booking quiz with inline buttons.

Steps (skipped if value provided via args):
  1. City selection (Dubai, Belgrade, Lisbon, Tel Aviv, Jurmala)
  2. Venue selection (paginated list from Airtable)
  3. Settings (duration, court type, players) with toggle checkboxes
  4. Conflict check (auto - Google Calendar)
  5. Confirm → Save booking data (ready for Phase 2 voice calls)

State stored in: /root/.openclaw/padel_state/<task_id>.json
Callback format: padel:<task_id>|<action>|<value>

Usage:
  # Start quiz (agent calls this):
  python3 padel_quiz.py start \
    --task_id "padel_123" --chat_id "5127607280" \
    --city "Dubai" --date "2026-04-03" --time "18:00"

  # Handle callback (plugin or agent calls this):
  python3 padel_quiz.py handle \
    --callback_data "padel:padel_123|city|Dubai" \
    --chat_id "5127607280" --message_id "12345"
"""

import os
import sys
import json
import argparse
import subprocess
import requests
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import padel_log as log

# Config
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Fallback: read tokens from /etc/environment if env vars not set
if not BOT_TOKEN:
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    BOT_TOKEN = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    except Exception:
        pass
STATE_DIR = os.environ.get("PADEL_STATE_DIR", "/root/.openclaw/padel_state")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Steps
STEP_CITY = "city"
STEP_VENUE = "venue"
STEP_SETTINGS = "settings"
STEP_CONFLICTS = "conflicts"
STEP_CONFIRM = "confirm"

# Defaults
DEFAULT_SETTINGS = {
    "duration": "1.5hr",
}

CITIES = [
    {"key": "dubai", "name": "Dubai"},
    {"key": "jurmala", "name": "Jurmala"},
    {"key": "lisbon", "name": "Lisbon"},
    {"key": "tel_aviv", "name": "Tel Aviv"},
    {"key": "belgrade", "name": "Belgrade"},
]

PAGE_SIZE = 5


# ── State management ─────────────────────────────────────────

def get_state_path(task_id: str) -> str:
    safe_id = task_id.replace("/", "_").replace("\\", "_")
    return os.path.join(STATE_DIR, f"{safe_id}.json")


def load_state(task_id: str) -> dict:
    path = get_state_path(task_id)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def save_state(task_id: str, state: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    path = get_state_path(task_id)
    with open(path, 'w') as f:
        json.dump(state, f, indent=2)


def delete_state(task_id: str):
    path = get_state_path(task_id)
    if os.path.exists(path):
        os.remove(path)


# ── Telegram helpers ─────────────────────────────────────────

def send_message(chat_id: str, text: str, keyboard: dict) -> int:
    if not BOT_TOKEN:
        log("ERROR: TELEGRAM_BOT_TOKEN not set")
        return 0
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
    }, timeout=10)
    if resp.status_code == 200 and resp.json().get('ok'):
        return resp.json()['result']['message_id']
    log(f"Send error: {resp.text[:200]}")
    return 0


def edit_message(chat_id: str, message_id: str, text: str, keyboard: dict = None):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": int(message_id),
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code != 200:
        log(f"Edit error: {resp.text[:200]}")


# ── Keyboard builders ────────────────────────────────────────

def cb(selected: bool, label: str) -> str:
    return f"{'✅' if selected else '⬜'} {label}"


def build_city_keyboard(task_id: str) -> dict:
    # 3 cities per row for compact layout
    rows = []
    row = []
    for city in CITIES:
        row.append({
            "text": city['name'],
            "callback_data": f"padel:{task_id}|city|{city['key']}",
        })
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "❌ Cancel", "callback_data": f"padel:{task_id}|cancel"}])
    return {"inline_keyboard": rows}


def build_venue_keyboard(task_id: str, venues: list, page: int = 0) -> dict:
    total = len(venues)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_venues = venues[start:end]

    rows = []
    for i, venue in enumerate(page_venues):
        idx = start + i
        name = venue.get("name", "Unknown")
        rows.append([{
            "text": name,
            "callback_data": f"padel:{task_id}|venue|{idx}",
        }])

    # Pagination
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append({"text": "⬅️ Prev", "callback_data": f"padel:{task_id}|page|{page - 1}"})
        nav_row.append({"text": f"📄 {page + 1}/{total_pages}", "callback_data": "noop"})
        if page < total_pages - 1:
            nav_row.append({"text": "Next ➡️", "callback_data": f"padel:{task_id}|page|{page + 1}"})
        rows.append(nav_row)

    # Back + Cancel
    rows.append([
        {"text": "⬅️ Back to cities", "callback_data": f"padel:{task_id}|back_to_city"},
        {"text": "❌ Cancel", "callback_data": f"padel:{task_id}|cancel"},
    ])

    return {"inline_keyboard": rows}


def build_settings_keyboard(task_id: str, settings: dict, has_venue: bool = True) -> dict:
    dur = settings.get("duration", "1.5hr")

    rows = [
        # Duration only
        [
            {"text": cb(dur == "1hr", "1 hour"), "callback_data": f"padel:{task_id}|dur|1hr"},
            {"text": cb(dur == "1.5hr", "1.5 hours"), "callback_data": f"padel:{task_id}|dur|1.5hr"},
        ],
    ]

    # Action row
    action_row = []
    if has_venue:
        action_row.append({"text": "⬅️ Back", "callback_data": f"padel:{task_id}|back_to_venues"})
    action_row.append({"text": "⏩ Proceed", "callback_data": f"padel:{task_id}|proceed"})
    action_row.append({"text": "❌ Cancel", "callback_data": f"padel:{task_id}|cancel"})
    rows.append(action_row)

    return {"inline_keyboard": rows}


# ── Message builders ─────────────────────────────────────────

def build_message(state: dict) -> str:
    step = state.get("current_step", STEP_CITY)

    text = "🎾 <b>Book Padel</b>\n\n"

    # Show collected info
    if state.get("date"):
        text += f"📆 Date: {state['date']}\n"
    if state.get("time"):
        text += f"🕐 Time: {state['time']}\n"
    if state.get("city_name"):
        text += f"🌍 City: {state['city_name']}\n"
    if state.get("selected_venue"):
        text += f"🏟 Venue: {state['selected_venue'].get('name', '')}\n"

    text += "\n"

    if step == STEP_CITY:
        text += "Select a city:"
    elif step == STEP_VENUE:
        venues = state.get("venues", [])
        text += f"📍 <b>Select venue ({len(venues)} found):</b>"
    elif step == STEP_SETTINGS:
        settings = state.get("settings", DEFAULT_SETTINGS)
        dur_display = {"1hr": "1 hour", "1.5hr": "1.5 hours"}
        text += "⚙️ <b>Select duration:</b>\n\n"
        text += f"⏱ Duration: {dur_display.get(settings['duration'], settings['duration'])}\n"
    elif step == STEP_CONFLICTS:
        conflicts = state.get("conflicts", [])
        if conflicts:
            text += "⚠️ <b>Calendar conflicts found:</b>\n\n"
            for c in conflicts[:5]:
                text += f"  • {c.get('title', 'Event')} at {c.get('time', '?')}\n"
            text += "\nBook anyway?"
        else:
            text += "✅ No calendar conflicts found."
    elif step == STEP_CONFIRM:
        text += "✅ <b>Booking data collected!</b>\n"
        text += "Ready for voice call booking (Phase 2)."

    return text


# ── Venue fetching ───────────────────────────────────────────

def fetch_venues_for_city(city_key: str, use_priority: bool = False) -> list:
    """Call airtable_venues.py to get venues."""
    cmd = ["python3", os.path.join(SCRIPTS_DIR, "airtable_venues.py"), "--city", city_key]
    if use_priority and city_key == "dubai":
        cmd.append("--priority")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return json.loads(result.stdout)
        log(f"airtable_venues.py error: {result.stderr[:200]}")
    except Exception as e:
        log(f"Failed to fetch venues: {e}")
    return []


# ── Conflict checking ────────────────────────────────────────

def check_conflicts(date: str, time: str, duration_minutes: int) -> list:
    """Call check_conflicts.py to check calendar."""
    cmd = [
        "python3", os.path.join(SCRIPTS_DIR, "check_conflicts.py"),
        "--date", date,
        "--time", time,
        "--duration", str(duration_minutes),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("conflicts", [])
        log(f"check_conflicts.py error: {result.stderr[:200]}")
    except Exception as e:
        log(f"Failed to check conflicts: {e}")
    return []


# ── Start quiz ───────────────────────────────────────────────

def start_quiz(args):
    task_id = args.task_id
    chat_id = args.chat_id

    # Optional pre-parsed values from agent
    city = getattr(args, 'city', None)
    venue_name = getattr(args, 'venue', None)
    date = getattr(args, 'date', None)
    time_str = getattr(args, 'time', None)
    duration = getattr(args, 'duration', None)

    log(f"Starting quiz: {task_id}, city={city}, venue={venue_name}, date={date}, time={time_str}")

    # Build settings with overrides
    settings = DEFAULT_SETTINGS.copy()
    if duration and duration in ["1hr", "1.5hr"]:
        settings["duration"] = duration

    # Determine starting step based on what's provided
    city_key = None
    city_name = None
    venues = []
    selected_venue = None

    if city:
        # Normalize city
        city_lower = city.lower().strip().replace(" ", "_")
        aliases = {"tel aviv": "tel_aviv", "telaviv": "tel_aviv", "tel-aviv": "tel_aviv"}
        city_key = aliases.get(city.lower().strip(), city_lower)
        city_name = next((c["name"] for c in CITIES if c["key"] == city_key), city)

        # Fetch venues for this city
        use_priority = city_key == "dubai"
        venues = fetch_venues_for_city(city_key, use_priority)
        log(f"Fetched {len(venues)} venues for {city_key}")

        if venue_name and venues:
            # Try to find the venue by name
            venue_lower = venue_name.lower()
            for v in venues:
                if venue_lower in v.get("name", "").lower():
                    selected_venue = v
                    break

    # Determine starting step
    if not city_key:
        current_step = STEP_CITY
    elif not selected_venue and len(venues) > 1:
        current_step = STEP_VENUE
    elif len(venues) == 1:
        selected_venue = venues[0]
        current_step = STEP_SETTINGS
    elif selected_venue:
        current_step = STEP_SETTINGS
    elif len(venues) == 0:
        current_step = STEP_VENUE  # Show empty list with error
    else:
        current_step = STEP_SETTINGS

    state = {
        "task_id": task_id,
        "chat_id": chat_id,
        "date": date or "",
        "time": time_str or "",
        "city_key": city_key or "",
        "city_name": city_name or "",
        "venues": venues,
        "selected_venue": selected_venue,
        "settings": settings,
        "current_step": current_step,
        "venue_page": 0,
        "conflicts": [],
        "message_id": None,
    }

    # Build message and keyboard
    text = build_message(state)

    if current_step == STEP_CITY:
        keyboard = build_city_keyboard(task_id)
    elif current_step == STEP_VENUE:
        keyboard = build_venue_keyboard(task_id, venues)
    else:
        keyboard = build_settings_keyboard(task_id, settings, has_venue=len(venues) > 1)

    message_id = send_message(chat_id, text, keyboard)

    if message_id:
        state["message_id"] = message_id
        save_state(task_id, state)
        log(f"Quiz started, msg={message_id}, step={current_step}")
        print(f"QUIZ_STARTED:message_id={message_id}")
    else:
        print("ERROR: Failed to send message")


# ── Handle callback ──────────────────────────────────────────

def handle_callback(args):
    callback_data = args.callback_data
    chat_id = args.chat_id
    message_id = args.message_id

    log(f"Callback: {callback_data}")

    # Parse: padel:<task_id>|<action>|<value>
    # The plugin strips "padel:" prefix, so we get task_id|action|value
    parts = callback_data.split("|")
    if len(parts) < 2:
        log(f"Invalid callback format: {callback_data}")
        print("ERROR: Invalid callback")
        return

    task_id = parts[0]
    action = parts[1]
    value = parts[2] if len(parts) > 2 else ""

    state = load_state(task_id)
    if not state:
        log(f"No state for {task_id}")
        print("ERROR: No quiz state found")
        return

    actual_msg_id = state.get("message_id") or message_id
    settings = state.get("settings", DEFAULT_SETTINGS.copy())
    venues = state.get("venues", [])

    # ── City selection ──
    if action == "city":
        city_key = value
        city_name = next((c["name"] for c in CITIES if c["key"] == city_key), city_key)

        # Fetch venues
        use_priority = city_key == "dubai"
        venues = fetch_venues_for_city(city_key, use_priority)

        state["city_key"] = city_key
        state["city_name"] = city_name
        state["venues"] = venues
        state["venue_page"] = 0
        state["selected_venue"] = None

        if len(venues) == 0:
            state["current_step"] = STEP_VENUE
            save_state(task_id, state)
            text = build_message(state)
            text += "\n\n⚠️ No venues found for this city."
            keyboard = build_venue_keyboard(task_id, venues)
            edit_message(chat_id, actual_msg_id, text, keyboard)
        elif len(venues) == 1:
            state["selected_venue"] = venues[0]
            state["current_step"] = STEP_SETTINGS
            save_state(task_id, state)
            text = build_message(state)
            keyboard = build_settings_keyboard(task_id, settings, has_venue=False)
            edit_message(chat_id, actual_msg_id, text, keyboard)
        else:
            state["current_step"] = STEP_VENUE
            save_state(task_id, state)
            text = build_message(state)
            keyboard = build_venue_keyboard(task_id, venues)
            edit_message(chat_id, actual_msg_id, text, keyboard)
        print("NO_REPLY")

    # ── Venue selection ──
    elif action == "venue":
        try:
            idx = int(value)
            if 0 <= idx < len(venues):
                state["selected_venue"] = venues[idx]
                state["current_step"] = STEP_SETTINGS
                save_state(task_id, state)
                text = build_message(state)
                keyboard = build_settings_keyboard(task_id, settings, has_venue=len(venues) > 1)
                edit_message(chat_id, actual_msg_id, text, keyboard)
        except (ValueError, IndexError) as e:
            log(f"Invalid venue index: {value}, error: {e}")
        print("NO_REPLY")

    # ── Venue page navigation ──
    elif action == "page":
        try:
            page = int(value)
            state["venue_page"] = page
            save_state(task_id, state)
            text = build_message(state)
            keyboard = build_venue_keyboard(task_id, venues, page)
            edit_message(chat_id, actual_msg_id, text, keyboard)
        except ValueError:
            log(f"Invalid page: {value}")
        print("NO_REPLY")

    # ── Back to city ──
    elif action == "back_to_city":
        state["current_step"] = STEP_CITY
        state["city_key"] = ""
        state["city_name"] = ""
        state["venues"] = []
        state["selected_venue"] = None
        save_state(task_id, state)
        text = build_message(state)
        keyboard = build_city_keyboard(task_id)
        edit_message(chat_id, actual_msg_id, text, keyboard)
        print("NO_REPLY")

    # ── Back to venues ──
    elif action == "back_to_venues":
        state["current_step"] = STEP_VENUE
        state["selected_venue"] = None
        page = state.get("venue_page", 0)
        save_state(task_id, state)
        text = build_message(state)
        keyboard = build_venue_keyboard(task_id, venues, page)
        edit_message(chat_id, actual_msg_id, text, keyboard)
        print("NO_REPLY")

    # ── Settings toggles ──
    elif action == "dur":
        if value in ["1hr", "1.5hr", "2hr"]:
            settings["duration"] = value
            state["settings"] = settings
            save_state(task_id, state)
            text = build_message(state)
            keyboard = build_settings_keyboard(task_id, settings, has_venue=len(venues) > 1)
            edit_message(chat_id, actual_msg_id, text, keyboard)
        print("NO_REPLY")

    elif action == "court":
        if value in ["indoor", "outdoor", "any"]:
            settings["court_type"] = value
            state["settings"] = settings
            save_state(task_id, state)
            text = build_message(state)
            keyboard = build_settings_keyboard(task_id, settings, has_venue=len(venues) > 1)
            edit_message(chat_id, actual_msg_id, text, keyboard)
        print("NO_REPLY")

    elif action == "players":
        if value in ["2", "4"]:
            settings["players"] = value
            state["settings"] = settings
            save_state(task_id, state)
            text = build_message(state)
            keyboard = build_settings_keyboard(task_id, settings, has_venue=len(venues) > 1)
            edit_message(chat_id, actual_msg_id, text, keyboard)
        print("NO_REPLY")

    # ── Proceed ──
    elif action == "proceed":
        # Check conflicts first
        date = state.get("date", "")
        time_str = state.get("time", "")
        duration_map = {"1hr": 60, "1.5hr": 90, "2hr": 120}
        duration_minutes = duration_map.get(settings.get("duration", "1.5hr"), 90)

        if date and time_str:
            edit_message(chat_id, actual_msg_id,
                         "⏳ Checking calendar conflicts...",
                         {"inline_keyboard": []})
            conflicts = check_conflicts(date, time_str, duration_minutes)
            state["conflicts"] = conflicts
        else:
            conflicts = []

        # Save final booking data
        venue = state.get("selected_venue", {})
        booking_data = {
            "task_id": task_id,
            "chat_id": chat_id,
            "date": date,
            "time": time_str,
            "city": state.get("city_name", ""),
            "city_key": state.get("city_key", ""),
            "venue_name": venue.get("name", ""),
            "venue_phone": venue.get("phone", ""),
            "venue_id": venue.get("id", ""),
            "playtomic_url": venue.get("playtomic_url", ""),
            "booking_methods": venue.get("primary_booking", []),
            "availability_methods": venue.get("availability_methods", []),
            "duration": settings.get("duration", "1.5hr"),
            "duration_minutes": duration_minutes,
            "conflicts": conflicts,
            "status": "ready_for_booking",
            "created_at": datetime.utcnow().isoformat(),
        }
        state["booking_data"] = booking_data
        state["current_step"] = STEP_CONFIRM
        save_state(task_id, state)

        # Show confirmation
        dur_display = {"1hr": "1 hour", "1.5hr": "1.5 hours"}
        text = "🎾 <b>Booking Ready!</b>\n\n"
        text += f"📆 {date} at {time_str}\n"
        text += f"🌍 {state.get('city_name', '')}\n"
        text += f"🏟 {venue.get('name', 'TBD')}\n"
        text += f"⏱ {dur_display.get(settings['duration'], settings['duration'])}\n"

        if conflicts:
            text += f"\n⚠️ <b>{len(conflicts)} conflict(s) found:</b>\n"
            for c in conflicts[:3]:
                text += f"  • {c.get('title', 'Event')} at {c.get('time', '?')}\n"

        text += "\n✅ Data saved. Ready for voice call booking."

        edit_message(chat_id, actual_msg_id, text, {"inline_keyboard": []})

        log(f"Booking data saved: {venue.get('name', 'TBD')} on {date} at {time_str}")
        print(f"BOOKING_READY:{json.dumps(booking_data)}")

    # ── Cancel ──
    elif action == "cancel":
        delete_state(task_id)
        text = "❌ <b>Booking Cancelled</b>\n\nPadel booking was cancelled."
        edit_message(chat_id, actual_msg_id, text, {"inline_keyboard": []})
        log("User cancelled")
        print("NO_REPLY")

    else:
        log(f"Unknown action: {action}")
        print(f"UNKNOWN: {callback_data}")


# ── CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Start command
    start_p = subparsers.add_parser('start')
    start_p.add_argument('--task_id', required=True)
    start_p.add_argument('--chat_id', required=True)
    start_p.add_argument('--city', help="Pre-detected city")
    start_p.add_argument('--venue', help="Pre-detected venue name")
    start_p.add_argument('--date', help="Booking date YYYY-MM-DD")
    start_p.add_argument('--time', help="Booking time HH:MM")
    start_p.add_argument('--duration', choices=["1hr", "1.5hr"])

    # Handle command
    handle_p = subparsers.add_parser('handle')
    handle_p.add_argument('--callback_data', required=True)
    handle_p.add_argument('--chat_id', required=True)
    handle_p.add_argument('--message_id', required=True)

    args = parser.parse_args()

    if args.command == 'start':
        start_quiz(args)
    elif args.command == 'handle':
        handle_callback(args)
    else:
        print("Usage: padel_quiz.py {start|handle} --help")


if __name__ == "__main__":
    main()
