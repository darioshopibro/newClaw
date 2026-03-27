#!/usr/bin/env python3
"""
contact_quiz.py - Merge decision quiz for duplicate contacts
Uses JSON file for state storage (same pattern as calendar simple_quiz.py)

Buttons:
- Toggle Email (add new email to existing contact)
- Toggle Phone (add new phone to existing contact)
- Create New (ignore duplicate, create separate contact)
- Merge (add selected fields to existing contact)
- Cancel (abort operation)

Usage:
  python3 contact_quiz.py start --task_id "contact_123" --chat_id "5127607280" \
    --existing_id "people/c123" --existing_name "John Doe" \
    --existing_email "john@old.com" --new_email "john@new.com" \
    --new_phone "+222"

  python3 contact_quiz.py handle --callback_data "contact|task_123|te" \
    --chat_id "5127607280" --message_id "12345"
"""

import os
import sys
import json
import argparse
import requests

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# Config
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
STATE_DIR = "/root/.openclaw/contact_state"
LOG_FILE = "/var/log/openclaw_calendar.log"

# Ensure state dir exists
os.makedirs(STATE_DIR, exist_ok=True)


def log(msg: str):
    """Log to calendar log file and stderr"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] [contact_quiz] {msg}\n")
    except:
        pass
    print(f"[contact_quiz] {msg}", file=sys.stderr)


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


def build_keyboard(task_id: str, state: dict) -> dict:
    """Build toggle-style keyboard for merge decision"""
    selections = state.get("selections", {})
    new_data = state.get("new_data", {})

    rows = []

    # Toggle rows for each new field
    toggle_row = []

    if new_data.get("email"):
        selected = selections.get("email", True)  # Default: selected
        emoji = "✅" if selected else "⬜"
        toggle_row.append({
            "text": f"{emoji} Email",
            "callback_data": f"contact:{task_id}|te"
        })

    if new_data.get("phone"):
        selected = selections.get("phone", True)  # Default: selected
        emoji = "✅" if selected else "⬜"
        toggle_row.append({
            "text": f"{emoji} Phone",
            "callback_data": f"contact:{task_id}|tp"
        })

    if toggle_row:
        rows.append(toggle_row)

    # Action buttons
    rows.append([
        {"text": "➕ Create New", "callback_data": f"contact:{task_id}|new"},
        {"text": "🔀 Merge", "callback_data": f"contact:{task_id}|confirm"},
    ])
    rows.append([
        {"text": "❌ Cancel", "callback_data": f"contact:{task_id}|cancel"},
    ])

    return {"inline_keyboard": rows}


def build_message(state: dict) -> str:
    """Build message text showing merge options"""
    existing = state.get("existing_contact", {})
    new_data = state.get("new_data", {})
    selections = state.get("selections", {})

    text = f"📇 <b>Similar contact found: {existing.get('name', 'Unknown')}</b>\n\n"

    # Show existing contact info
    if existing.get("email"):
        text += f"📧 Current email: {existing['email']}\n"
    if existing.get("phone"):
        text += f"📱 Current phone: {existing['phone']}\n"

    text += "\n<b>What to add to existing contact?</b>\n\n"

    # Show new fields with selection status
    if new_data.get("email"):
        emoji = "✅" if selections.get("email", True) else "⬜"
        text += f"{emoji} Email: {new_data['email']}\n"

    if new_data.get("phone"):
        emoji = "✅" if selections.get("phone", True) else "⬜"
        text += f"{emoji} Phone: {new_data['phone']}\n"

    return text


def start_quiz(args):
    """Start a new merge decision quiz"""
    task_id = args.task_id
    chat_id = args.chat_id

    log(f"Starting contact quiz: {task_id}")

    # Build initial state
    state = {
        "task_id": task_id,
        "chat_id": chat_id,
        "mode": "merge",  # merge mode (duplicate found)
        "existing_contact": {
            "id": args.existing_id,
            "name": args.existing_name,
            "email": getattr(args, 'existing_email', None),
            "phone": getattr(args, 'existing_phone', None),
        },
        "new_data": {
            "email": getattr(args, 'new_email', None),
            "phone": getattr(args, 'new_phone', None),
            "first_name": getattr(args, 'new_first_name', None),
            "last_name": getattr(args, 'new_last_name', None),
        },
        "selections": {
            "email": True if getattr(args, 'new_email', None) else False,
            "phone": True if getattr(args, 'new_phone', None) else False,
        },
        "message_id": None
    }

    # Build message and keyboard
    text = build_message(state)
    keyboard = build_keyboard(task_id, state)

    # Send message
    message_id = send_message(chat_id, text, keyboard)

    if message_id:
        state["message_id"] = message_id
        save_state(task_id, state)
        log(f"Contact quiz started, message_id: {message_id}")
        print(f"QUIZ_STARTED:message_id={message_id}")
    else:
        print("ERROR: Failed to send message")


def start_confirm(args):
    """Start a simple confirmation quiz (no duplicate, just confirm add)"""
    task_id = args.task_id
    chat_id = args.chat_id

    log(f"Starting contact confirmation: {task_id}")

    first_name = getattr(args, 'first_name', '') or ''
    last_name = getattr(args, 'last_name', '') or ''
    name = f"{first_name} {last_name}".strip() or "Unknown"
    email = getattr(args, 'email', None)
    phone = getattr(args, 'phone', None)

    # Build state
    state = {
        "task_id": task_id,
        "chat_id": chat_id,
        "mode": "confirm",  # simple confirm mode
        "new_data": {
            "first_name": first_name,
            "last_name": last_name,
            "name": name,
            "email": email,
            "phone": phone,
        },
        "message_id": None
    }

    # Build message
    text = f"📇 <b>Add this contact?</b>\n\n"
    text += f"👤 {name}\n"
    if phone:
        text += f"📱 {phone}\n"
    if email:
        text += f"📧 {email}\n"

    # Simple keyboard: Add or Cancel
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Add", "callback_data": f"contact:{task_id}|add"},
                {"text": "❌ Cancel", "callback_data": f"contact:{task_id}|cancel"}
            ]
        ]
    }

    # Send message
    message_id = send_message(chat_id, text, keyboard)

    if message_id:
        state["message_id"] = message_id
        save_state(task_id, state)
        log(f"Contact confirm started, message_id: {message_id}")
        print(f"QUIZ_STARTED:message_id={message_id}")
    else:
        print("ERROR: Failed to send message")


def handle_callback(args):
    """Handle button click callback"""
    callback_data = args.callback_data
    chat_id = args.chat_id
    message_id = args.message_id

    log(f"Contact callback: {callback_data}")

    # Parse callback: contact|task_id|action
    parts = callback_data.split("|")
    if len(parts) < 3:
        log(f"Invalid callback format: {callback_data}")
        print("ERROR: Invalid callback")
        return

    task_id = parts[1]
    action = parts[2]

    state = load_state(task_id)
    if not state:
        log(f"No state for {task_id}")
        print("ERROR: No contact quiz state found")
        return

    actual_message_id = state.get("message_id") or message_id
    selections = state.get("selections", {})

    if action == "te":
        # Toggle email
        selections["email"] = not selections.get("email", True)
        state["selections"] = selections
        save_state(task_id, state)
        text = build_message(state)
        keyboard = build_keyboard(task_id, state)
        edit_message(chat_id, actual_message_id, text, keyboard)
        print("NO_REPLY")

    elif action == "tp":
        # Toggle phone
        selections["phone"] = not selections.get("phone", True)
        state["selections"] = selections
        save_state(task_id, state)
        text = build_message(state)
        keyboard = build_keyboard(task_id, state)
        edit_message(chat_id, actual_message_id, text, keyboard)
        print("NO_REPLY")

    elif action == "confirm":
        # Merge selected fields into existing contact
        complete_merge(state, chat_id, actual_message_id)
        delete_state(task_id)

    elif action == "new":
        # Create as new contact (ignore duplicate)
        create_new(state, chat_id, actual_message_id)
        delete_state(task_id)

    elif action == "cancel":
        # Cancel operation
        delete_state(task_id)
        text = "❌ <b>Operation Cancelled</b>\n\nContact was not created or modified."
        edit_message(chat_id, actual_message_id, text, {"inline_keyboard": []})
        log("User cancelled")
        print("NO_REPLY")

    elif action == "add":
        # Simple add confirmation (no duplicate)
        add_new_contact(state, chat_id, actual_message_id)
        delete_state(task_id)

    else:
        log(f"Unknown action: {action}")
        print(f"UNKNOWN: {callback_data}")


def complete_merge(state: dict, chat_id: str, message_id: str):
    """Merge selected fields into existing contact"""
    from google_contacts_write import GoogleContactsWriteClient

    existing = state.get("existing_contact", {})
    new_data = state.get("new_data", {})
    selections = state.get("selections", {})

    contact_id = existing.get("id")
    contact_name = existing.get("name", "Unknown")

    log(f"Merging into {contact_id}: selections={selections}")

    # Show "merging..." message
    text = f"⏳ <b>Merging...</b>\n\nAdding selected fields to {contact_name}"
    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    try:
        client = GoogleContactsWriteClient()

        # Build update args
        update_args = {}
        fields_added = []

        if selections.get("email") and new_data.get("email"):
            update_args["add_email"] = new_data["email"]
            fields_added.append(f"📧 {new_data['email']}")

        if selections.get("phone") and new_data.get("phone"):
            update_args["add_phone"] = new_data["phone"]
            fields_added.append(f"📱 {new_data['phone']}")

        if update_args:
            result = client.update(contact_id=contact_id, **update_args)

            if result.get("success"):
                text = f"✅ <b>Contact Merged</b>\n\n"
                text += f"Updated: {contact_name}\n\n"
                text += "Added:\n" + "\n".join(fields_added)
                log(f"Merge successful: {fields_added}")
            else:
                text = f"❌ <b>Merge Failed</b>\n\n{result.get('error', 'Unknown error')}"
                log(f"Merge failed: {result.get('error')}")
        else:
            text = f"ℹ️ <b>No Changes</b>\n\nNo fields were selected to merge."
            log("No fields selected for merge")

    except Exception as e:
        text = f"❌ <b>Error</b>\n\n{str(e)}"
        log(f"Merge exception: {str(e)}")

    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    output = {
        "action": "merge",
        "contact_id": contact_id,
        "contact_name": contact_name,
        "fields_added": fields_added if 'fields_added' in dir() else []
    }
    print(f"CONTACT_MERGED:{json.dumps(output)}")


def create_new(state: dict, chat_id: str, message_id: str):
    """Create as new contact (ignoring duplicate)"""
    from google_contacts_write import GoogleContactsWriteClient

    new_data = state.get("new_data", {})

    first_name = new_data.get("first_name") or "Unknown"
    last_name = new_data.get("last_name")
    email = new_data.get("email")
    phone = new_data.get("phone")

    log(f"Creating new contact: {first_name} {last_name}")

    # Show "creating..." message
    text = f"⏳ <b>Creating new contact...</b>"
    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    try:
        client = GoogleContactsWriteClient()
        result = client.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone
        )

        if result.get("success"):
            name = result.get("name", f"{first_name} {last_name or ''}".strip())
            text = f"✅ <b>Contact Created</b>\n\n"
            text += f"📇 {name}\n"
            if email:
                text += f"📧 {email}\n"
            if phone:
                text += f"📱 {phone}\n"
            log(f"Contact created: {result.get('contact_id')}")
        else:
            text = f"❌ <b>Failed to Create</b>\n\n{result.get('error', 'Unknown error')}"
            log(f"Create failed: {result.get('error')}")

    except Exception as e:
        text = f"❌ <b>Error</b>\n\n{str(e)}"
        log(f"Create exception: {str(e)}")

    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    output = {
        "action": "create_new",
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone
    }
    print(f"CONTACT_CREATED:{json.dumps(output)}")


def add_new_contact(state: dict, chat_id: str, message_id: str):
    """Add new contact (simple confirmation, no duplicate)"""
    from google_contacts_write import GoogleContactsWriteClient

    new_data = state.get("new_data", {})

    first_name = new_data.get("first_name") or new_data.get("name", "").split()[0] if new_data.get("name") else "Unknown"
    last_name = new_data.get("last_name") or (" ".join(new_data.get("name", "").split()[1:]) if new_data.get("name") else None)
    email = new_data.get("email")
    phone = new_data.get("phone")
    name = new_data.get("name") or f"{first_name} {last_name or ''}".strip()

    log(f"Adding new contact: {name}")

    # Show "creating..." message
    text = f"⏳ <b>Adding contact...</b>"
    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    try:
        client = GoogleContactsWriteClient()
        result = client.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone
        )

        if result.get("success"):
            text = f"✅ <b>Contact Added!</b>\n\n"
            text += f"👤 {name}\n"
            if phone:
                text += f"📱 {phone}\n"
            if email:
                text += f"📧 {email}\n"
            text += f"\n🆔 {result.get('contact_id', 'N/A')}"
            log(f"Contact added: {result.get('contact_id')}")
        else:
            text = f"❌ <b>Failed to Add</b>\n\n{result.get('error', 'Unknown error')}"
            log(f"Add failed: {result.get('error')}")

    except Exception as e:
        text = f"❌ <b>Error</b>\n\n{str(e)}"
        log(f"Add exception: {str(e)}")

    edit_message(chat_id, message_id, text, {"inline_keyboard": []})

    output = {
        "action": "add",
        "name": name,
        "email": email,
        "phone": phone
    }
    print(f"CONTACT_ADDED:{json.dumps(output)}")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Start command (merge mode - duplicate found)
    start_parser = subparsers.add_parser('start')
    start_parser.add_argument('--task_id', required=True)
    start_parser.add_argument('--chat_id', required=True)
    start_parser.add_argument('--existing_id', required=True, help='Resource name of existing contact')
    start_parser.add_argument('--existing_name', required=True, help='Display name of existing contact')
    start_parser.add_argument('--existing_email', help='Current email')
    start_parser.add_argument('--existing_phone', help='Current phone')
    start_parser.add_argument('--new_email', help='New email to potentially add')
    start_parser.add_argument('--new_phone', help='New phone to potentially add')
    start_parser.add_argument('--new_first_name', help='First name (for create new)')
    start_parser.add_argument('--new_last_name', help='Last name (for create new)')

    # Confirm command (simple mode - no duplicate, just confirm)
    confirm_parser = subparsers.add_parser('confirm')
    confirm_parser.add_argument('--task_id', required=True)
    confirm_parser.add_argument('--chat_id', required=True)
    confirm_parser.add_argument('--first_name', help='First name')
    confirm_parser.add_argument('--last_name', help='Last name')
    confirm_parser.add_argument('--email', help='Email')
    confirm_parser.add_argument('--phone', help='Phone')

    # Handle command
    handle_parser = subparsers.add_parser('handle')
    handle_parser.add_argument('--callback_data', required=True)
    handle_parser.add_argument('--chat_id', required=True)
    handle_parser.add_argument('--message_id', required=True)

    args = parser.parse_args()

    if args.command == 'start':
        start_quiz(args)
    elif args.command == 'confirm':
        start_confirm(args)
    elif args.command == 'handle':
        handle_callback(args)
    else:
        print("Usage: contact_quiz.py {start|confirm|handle} --help")


if __name__ == "__main__":
    main()
