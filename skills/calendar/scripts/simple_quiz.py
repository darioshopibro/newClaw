#!/usr/bin/env python3
"""
simple_quiz.py - Local quiz system with toggle checkboxes
Uses JSON file for state storage

TWO steps (if multiple contacts):
  Step 1: Contact selection (only if multiple contacts provided)
  Step 2: Settings (calendar, type, duration) with toggles

ONE step (if single/no contact):
  Step 1: Settings only

- Proceed = create event
- Cancel = don't create

Usage:
  # With multiple contacts (2-step flow):
  python3 simple_quiz.py start --task_id "cal_123" --chat_id "5127607280" \
    --title "Meeting with Dario" --date "2026-03-15" --time "17:00" \
    --contacts '[{"name": "Dario A", "email": "a@x.com"}, {"name": "Dario B", "email": "b@x.com"}]'

  # Without contacts (1-step flow):
  python3 simple_quiz.py start --task_id "cal_123" --chat_id "5127607280" \
    --title "Meeting with Kelsi" --date "2026-03-15" --time "17:00"

  python3 simple_quiz.py handle --callback_data "quiz|cal_123|cal|shopibro" \
    --chat_id "5127607280" --message_id "12345"
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime

# Add lib to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import quiz_log as log

# Config
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
STATE_DIR = "/root/.openclaw/quiz_state"
LOG_CHAT_ID = "5127607280"

# Ensure state dir exists
os.makedirs(STATE_DIR, exist_ok=True)

# Default settings
DEFAULT_SETTINGS = {
    "calendar": "shopibro",
    "type": "in-person",
    "duration": "1hr"
}

# Steps
STEP_CONTACT = "contact"
STEP_SETTINGS = "settings"


def get_state_path(task_id: str) -> str:
    """Get path to state file"""
    safe_id = task_id.replace("/", "_").replace("\\", "_")
    return os.path.join(STATE_DIR, f"{safe_id}.json")


def load_state(task_id: str) -> dict:
    """Load quiz state from file"""
    path = get_state_path(task_id)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def save_state(task_id: str, state: dict):
    """Save quiz state to file"""
    path = get_state_path(task_id)
    with open(path, 'w') as f:
        json.dump(state, f, indent=2)


def delete_state(task_id: str):
    """Delete quiz state file"""
    path = get_state_path(task_id)
    if os.path.exists(path):
        os.remove(path)


def send_message(chat_id: str, text: str, keyboard: dict) -> int:
    """Send message with buttons, return message_id"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    })
    if resp.status_code == 200 and resp.json().get('ok'):
        return resp.json()['result']['message_id']
    log(f"Send error: {resp.text}")
    return 0


def edit_message(chat_id: str, message_id: str, text: str, keyboard: dict = None):
    """Edit existing message"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": int(message_id),
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    resp = requests.post(url, json=payload)
    if resp.status_code != 200:
        log(f"Edit error: {resp.text}")


def build_contact_keyboard(task_id: str, contacts: list, page: int = 0) -> dict:
    """Build contact selection keyboard with pagination"""
    PAGE_SIZE = 4  # Show 4 contacts per page
    total = len(contacts)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_contacts = contacts[start:end]

    rows = []

    # Contact buttons (one per row for clarity)
    for i, contact in enumerate(page_contacts):
        idx = start + i
        name = contact.get("name", "Unknown")
        email = contact.get("email", "")
        # Show name, add email hint if available
        label = name
        if email:
            # Truncate email if too long
            email_short = email[:20] + "..." if len(email) > 23 else email
            label = f"{name} ({email_short})"
        rows.append([
            {"text": label, "callback_data": f"quiz:{task_id}|contact|{idx}"}
        ])

    # Navigation row (if multiple pages)
    nav_row = []
    if total_pages > 1:
        if page > 0:
            nav_row.append({"text": "⬅️ Prev", "callback_data": f"quiz:{task_id}|page|{page - 1}"})
        nav_row.append({"text": f"📄 {page + 1}/{total_pages}", "callback_data": "noop"})
        if page < total_pages - 1:
            nav_row.append({"text": "Next ➡️", "callback_data": f"quiz:{task_id}|page|{page + 1}"})
        rows.append(nav_row)

    # Cancel button
    rows.append([
        {"text": "❌ Cancel", "callback_data": f"quiz:{task_id}|cancel"}
    ])

    return {"inline_keyboard": rows}


def build_settings_keyboard(task_id: str, settings: dict) -> dict:
    """Build toggle-style keyboard"""
    cal = settings.get("calendar", "shopibro")
    typ = settings.get("type", "in-person")
    dur = settings.get("duration", "1hr")

    # Helper to show checkbox
    def cb(selected, label):
        return f"{'✅' if selected else '⬜'} {label}"

    keyboard = {"inline_keyboard": [
        # Row 1: Calendar options
        [
            {"text": cb(cal == "shopibro", "Shopibro"), "callback_data": f"quiz:{task_id}|cal|shopibro"},
            {"text": cb(cal == "private", "Private"), "callback_data": f"quiz:{task_id}|cal|private"},
        ],
        # Row 2: Type options
        [
            {"text": cb(typ == "in-person", "In-person"), "callback_data": f"quiz:{task_id}|type|in-person"},
            {"text": cb(typ == "online", "Online"), "callback_data": f"quiz:{task_id}|type|online"},
        ],
        # Row 3: Duration options
        [
            {"text": cb(dur == "30m", "30m"), "callback_data": f"quiz:{task_id}|dur|30m"},
            {"text": cb(dur == "1hr", "1hr"), "callback_data": f"quiz:{task_id}|dur|1hr"},
            {"text": cb(dur == "1.5hr", "1.5hr"), "callback_data": f"quiz:{task_id}|dur|1.5hr"},
            {"text": cb(dur == "2hr", "2hr"), "callback_data": f"quiz:{task_id}|dur|2hr"},
        ],
        # Row 4: Action buttons (with back if came from contact step)
        [
            {"text": "⏩ Proceed", "callback_data": f"quiz:{task_id}|proceed"},
            {"text": "❌ Cancel", "callback_data": f"quiz:{task_id}|cancel"},
        ],
    ]}
    return keyboard


def build_settings_keyboard_with_back(task_id: str, settings: dict) -> dict:
    """Build settings keyboard with back button (when contact was selected)"""
    keyboard = build_settings_keyboard(task_id, settings)
    # Add back button to last row
    keyboard["inline_keyboard"][-1].insert(0,
        {"text": "⬅️ Back", "callback_data": f"quiz:{task_id}|back_to_contact"}
    )
    return keyboard


def build_message(state: dict) -> str:
    """Build message text based on current step"""
    current_step = state.get("current_step", STEP_SETTINGS)
    contacts = state.get("contacts", [])
    selected_contact = state.get("selected_contact")

    text = f"📅 <b>Schedule Event</b>\n\n"
    text += f"Title: {state['title']}\n"
    text += f"Date: {state['date']}\n"
    text += f"Time: {state['time']}\n\n"

    if current_step == STEP_CONTACT:
        # Contact selection step
        text += f"👥 <b>Multiple contacts found ({len(contacts)})</b>\n"
        text += f"Select which one to invite:"
    else:
        # Settings step
        if selected_contact:
            contact_name = selected_contact.get("name", "Unknown")
            contact_email = selected_contact.get("email", "")
            text += f"👤 Attendee: <b>{contact_name}</b>"
            if contact_email:
                text += f" ({contact_email})"
            text += "\n\n"
        text += f"📋 Configure event settings:"

    return text


def parse_message_for_settings(message: str) -> dict:
    """Parse original user message to detect type and duration."""
    if not message:
        return {}

    msg_lower = message.lower()
    result = {}

    # Detect meeting type
    online_keywords = ["online", "video", "zoom", "teams", "call", "virtual"]
    inperson_keywords = ["in-person", "in person", "lunch", "coffee", "dinner", "breakfast"]

    for kw in online_keywords:
        if kw in msg_lower:
            result["type"] = "online"
            break

    if "type" not in result:
        for kw in inperson_keywords:
            if kw in msg_lower:
                result["type"] = "in-person"
                break

    # Detect duration
    if "30 min" in msg_lower or "30m" in msg_lower or "half hour" in msg_lower:
        result["duration"] = "30m"
    elif "1.5 hour" in msg_lower or "90 min" in msg_lower or "1.5hr" in msg_lower:
        result["duration"] = "1.5hr"
    elif "2 hour" in msg_lower or "2hr" in msg_lower or "two hour" in msg_lower:
        result["duration"] = "2hr"
    elif "1 hour" in msg_lower or "1hr" in msg_lower or "one hour" in msg_lower:
        result["duration"] = "1hr"

    return result


def start_quiz(args):
    """Start a new calendar quiz"""
    task_id = args.task_id
    chat_id = args.chat_id
    title = args.title
    date = args.date
    time = args.time
    attendee_email = getattr(args, 'attendee_email', "")

    # Get optional overrides from args
    meeting_type = getattr(args, 'type', None)
    duration = getattr(args, 'duration', None)

    # Parse contacts JSON if provided
    contacts_json = getattr(args, 'contacts', None)
    contacts = []
    if contacts_json:
        try:
            contacts = json.loads(contacts_json)
            log(f"Parsed {len(contacts)} contacts from JSON")
        except json.JSONDecodeError as e:
            log(f"Failed to parse contacts JSON: {e}")

    # Parse original message if provided (fallback for when agent doesn't pass --type)
    original_message = getattr(args, 'message', None)
    if original_message:
        parsed = parse_message_for_settings(original_message)
        log(f"Parsed from message: {parsed}")
        # Only use parsed values if not already set via args
        if not meeting_type and "type" in parsed:
            meeting_type = parsed["type"]
        if not duration and "duration" in parsed:
            duration = parsed["duration"]

    log(f"Starting quiz: {task_id}\ntitle: {title}, attendee: {attendee_email}, type: {meeting_type}, duration: {duration}, contacts: {len(contacts)}")

    # Build initial state with default settings, override if provided
    settings = DEFAULT_SETTINGS.copy()
    if meeting_type and meeting_type in ["in-person", "online"]:
        settings["type"] = meeting_type
    if duration and duration in ["30m", "1hr", "1.5hr", "2hr"]:
        settings["duration"] = duration

    # Determine starting step
    # If multiple contacts (>1) → start with contact selection
    # If single contact or no contacts → start with settings
    if len(contacts) > 1:
        current_step = STEP_CONTACT
        selected_contact = None
    elif len(contacts) == 1:
        # Single contact - auto-select and go to settings
        current_step = STEP_SETTINGS
        selected_contact = contacts[0]
        attendee_email = selected_contact.get("email", attendee_email)
    else:
        current_step = STEP_SETTINGS
        selected_contact = None

    state = {
        "task_id": task_id,
        "chat_id": chat_id,
        "title": title,
        "date": date,
        "time": time,
        "attendee_email": attendee_email,
        "settings": settings,
        "contacts": contacts,
        "selected_contact": selected_contact,
        "current_step": current_step,
        "contact_page": 0,
        "message_id": None
    }

    # Build message and keyboard based on step
    text = build_message(state)
    if current_step == STEP_CONTACT:
        keyboard = build_contact_keyboard(task_id, contacts, page=0)
    else:
        # If contact was selected (from single contact), show back button
        if selected_contact and len(contacts) > 0:
            keyboard = build_settings_keyboard_with_back(task_id, state["settings"])
        else:
            keyboard = build_settings_keyboard(task_id, state["settings"])

    # Send message
    message_id = send_message(chat_id, text, keyboard)

    if message_id:
        state["message_id"] = message_id
        save_state(task_id, state)
        log(f"Quiz started, message_id: {message_id}, step: {current_step}")
        print(f"QUIZ_STARTED:message_id={message_id}")
    else:
        print("ERROR: Failed to send message")


def handle_callback(args):
    """Handle button click callback"""
    callback_data = args.callback_data
    chat_id = args.chat_id
    message_id = args.message_id

    log(f"Callback: {callback_data}")

    # Parse callback: quiz|task_id|action|value
    parts = callback_data.split("|")
    if len(parts) < 3:
        log(f"Invalid callback format: {callback_data}")
        print("ERROR: Invalid callback")
        return

    task_id = parts[1]
    action = parts[2]
    value = parts[3] if len(parts) > 3 else None

    state = load_state(task_id)
    if not state:
        log(f"No state for {task_id}")
        print("ERROR: No quiz state found")
        return

    actual_message_id = state.get("message_id") or message_id
    settings = state.get("settings", DEFAULT_SETTINGS.copy())
    contacts = state.get("contacts", [])

    # Handle different actions

    # CONTACT SELECTION ACTIONS
    if action == "contact":
        # User selected a contact
        try:
            contact_idx = int(value)
            if 0 <= contact_idx < len(contacts):
                selected = contacts[contact_idx]
                state["selected_contact"] = selected
                state["attendee_email"] = selected.get("email", "")
                state["current_step"] = STEP_SETTINGS
                save_state(task_id, state)

                log(f"Contact selected: {selected.get('name')} ({selected.get('email')})")

                # Move to settings step
                text = build_message(state)
                keyboard = build_settings_keyboard_with_back(task_id, settings)
                edit_message(chat_id, actual_message_id, text, keyboard)
        except (ValueError, IndexError) as e:
            log(f"Invalid contact index: {value}, error: {e}")
        print("NO_REPLY")

    elif action == "page":
        # Navigate contact pages
        try:
            page = int(value)
            state["contact_page"] = page
            save_state(task_id, state)

            text = build_message(state)
            keyboard = build_contact_keyboard(task_id, contacts, page=page)
            edit_message(chat_id, actual_message_id, text, keyboard)
        except ValueError:
            log(f"Invalid page: {value}")
        print("NO_REPLY")

    elif action == "back_to_contact":
        # Go back to contact selection
        state["current_step"] = STEP_CONTACT
        state["selected_contact"] = None
        state["attendee_email"] = ""
        page = state.get("contact_page", 0)
        save_state(task_id, state)

        text = build_message(state)
        keyboard = build_contact_keyboard(task_id, contacts, page=page)
        edit_message(chat_id, actual_message_id, text, keyboard)
        print("NO_REPLY")

    # SETTINGS ACTIONS
    elif action == "cal":
        # Toggle calendar
        settings["calendar"] = value
        state["settings"] = settings
        save_state(task_id, state)
        text = build_message(state)
        # Use keyboard with back if we came from contact selection
        if state.get("selected_contact") and len(contacts) > 1:
            keyboard = build_settings_keyboard_with_back(task_id, settings)
        else:
            keyboard = build_settings_keyboard(task_id, settings)
        edit_message(chat_id, actual_message_id, text, keyboard)
        print("NO_REPLY")

    elif action == "type":
        # Toggle type
        settings["type"] = value
        state["settings"] = settings
        save_state(task_id, state)
        text = build_message(state)
        if state.get("selected_contact") and len(contacts) > 1:
            keyboard = build_settings_keyboard_with_back(task_id, settings)
        else:
            keyboard = build_settings_keyboard(task_id, settings)
        edit_message(chat_id, actual_message_id, text, keyboard)
        print("NO_REPLY")

    elif action == "dur":
        # Toggle duration
        settings["duration"] = value
        state["settings"] = settings
        save_state(task_id, state)
        text = build_message(state)
        if state.get("selected_contact") and len(contacts) > 1:
            keyboard = build_settings_keyboard_with_back(task_id, settings)
        else:
            keyboard = build_settings_keyboard(task_id, settings)
        edit_message(chat_id, actual_message_id, text, keyboard)
        print("NO_REPLY")

    elif action == "proceed":
        # Create the event
        complete_quiz(state, chat_id, actual_message_id)
        delete_state(task_id)

    elif action == "cancel":
        # Cancel the quiz
        delete_state(task_id)
        text = f"❌ <b>Event Cancelled</b>\n\n"
        text += f"You cancelled the event creation."
        edit_message(chat_id, actual_message_id, text, {"inline_keyboard": []})
        log("User cancelled")
        print("NO_REPLY")

    else:
        log(f"Unknown action: {action}")
        print(f"UNKNOWN: {callback_data}")


def complete_quiz(state: dict, chat_id: str, message_id: str):
    """Quiz completed - create the event"""
    import subprocess

    settings = state.get("settings", DEFAULT_SETTINGS)

    log(f"Quiz complete! Settings: {settings}")

    # Map settings to values
    calendar_key = settings["calendar"]
    meeting_type = settings["type"]
    duration_key = settings["duration"]

    # Map duration to minutes
    duration_map = {
        "30m": 30,
        "1hr": 60,
        "1.5hr": 90,
        "2hr": 120,
    }
    duration_minutes = duration_map.get(duration_key, 60)

    # Map to display names
    cal_display = {"shopibro": "Shopibro", "private": "Private"}.get(calendar_key, calendar_key)
    type_display = {"in-person": "In-person", "online": "Online"}.get(meeting_type, meeting_type)
    dur_display = {"30m": "30 min", "1hr": "1 hour", "1.5hr": "1.5 hours", "2hr": "2 hours"}.get(duration_key, duration_key)

    log(f"Calendar: {calendar_key}")
    log(f"Meeting type: {meeting_type}")
    log(f"Duration: {duration_key} -> {duration_minutes} min")

    # Show "creating..." message first
    text = f"⏳ <b>Creating event...</b>\n\n"
    text += f"📅 {state['title']}\n"
    text += f"📆 {state['date']} at {state['time']}\n"
    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    # Build description from meeting type
    description = meeting_type

    # Create the event
    try:
        attendee = state.get("attendee_email", "")
        cmd = [
            "python3", "create_event.py",
            "--skip_quiz_check",
            "--title", state['title'],
            "--date", state['date'],
            "--time", state['time'],
            "--duration", str(duration_minutes),
            "--calendar", calendar_key,
            "--description", description,
        ]

        if attendee:
            cmd.extend(["--attendees", attendee])

        log(f"Running: {' '.join(cmd)}")

        # Run SYNCHRONOUSLY and capture output
        result = subprocess.run(
            cmd,
            cwd="/root/.openclaw/workspace/skills/calendar/scripts",
            capture_output=True,
            text=True,
            timeout=30
        )

        log(f"create_event stdout: {result.stdout}")
        log(f"create_event stderr: {result.stderr}")
        log(f"create_event returncode: {result.returncode}")

        # Parse the JSON output
        try:
            event_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            event_result = {"success": False, "error": f"Invalid JSON: {result.stdout}"}

        if event_result.get("success"):
            # SUCCESS
            text = f"✅ <b>Event Created!</b>\n\n"
            text += f"📅 {state['title']}\n"
            text += f"📆 {state['date']} at {state['time']}\n"
            text += f"⏱ {dur_display}\n"
            text += f"🏢 {type_display}\n"
            text += f"📍 Calendar: {cal_display}\n"
            # Show attendee if selected
            selected_contact = state.get("selected_contact")
            if selected_contact:
                text += f"👤 Attendee: {selected_contact.get('name', '')}"
                if selected_contact.get('email'):
                    text += f" ({selected_contact.get('email')})"
                text += "\n"
            elif state.get("attendee_email"):
                text += f"👤 Attendee: {state.get('attendee_email')}\n"
            if event_result.get("link"):
                text += f"\n🔗 <a href=\"{event_result['link']}\">Open in Calendar</a>"
            log(f"Event created successfully: {event_result.get('event_id')}")
        else:
            # FAILED
            error_msg = event_result.get("error", "Unknown error")
            text = f"❌ <b>Failed to create event</b>\n\n"
            text += f"📅 {state['title']}\n"
            text += f"📆 {state['date']} at {state['time']}\n\n"
            text += f"⚠️ Error: {error_msg[:200]}"
            log(f"Event creation FAILED: {error_msg}")

    except subprocess.TimeoutExpired:
        text = f"❌ <b>Timeout</b>\n\nEvent creation took too long."
        log("Event creation timed out")

    except Exception as e:
        text = f"❌ <b>Error</b>\n\n{str(e)}"
        log(f"Exception: {str(e)}")

    # Edit message with final result
    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    # Output result for agent
    selected_contact = state.get("selected_contact")
    output = {
        "calendar": calendar_key,
        "meeting_type": meeting_type,
        "duration_minutes": duration_minutes,
        "title": state['title'],
        "date": state['date'],
        "time": state['time'],
        "attendee_email": state.get("attendee_email", ""),
        "selected_contact": selected_contact
    }

    print(f"QUIZ_COMPLETE:{json.dumps(output)}")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Start command
    start_parser = subparsers.add_parser('start')
    start_parser.add_argument('--task_id', required=True)
    start_parser.add_argument('--chat_id', required=True)
    start_parser.add_argument('--title', required=True)
    start_parser.add_argument('--date', required=True)
    start_parser.add_argument('--time', required=True)
    start_parser.add_argument('--attendee_email', required=False, default="")
    start_parser.add_argument('--type', required=False, choices=["in-person", "online"], help="Meeting type")
    start_parser.add_argument('--duration', required=False, choices=["30m", "1hr", "1.5hr", "2hr"], help="Duration")
    start_parser.add_argument('--contacts', required=False, help="JSON array of contacts [{name, email, ...}]")

    # Handle command
    handle_parser = subparsers.add_parser('handle')
    handle_parser.add_argument('--callback_data', required=True)
    handle_parser.add_argument('--chat_id', required=True)
    handle_parser.add_argument('--message_id', required=True)

    args = parser.parse_args()

    if args.command == 'start':
        start_quiz(args)
    elif args.command == 'handle':
        handle_callback(args)
    else:
        print("Usage: simple_quiz.py {start|handle} --help")


if __name__ == "__main__":
    main()
