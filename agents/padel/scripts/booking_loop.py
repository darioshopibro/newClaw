#!/usr/bin/env python3
"""
booking_loop.py - Main booking loop. Calls venues one by one via VAPI,
polls for results, updates Telegram progress message in real-time.

Runs as background process (launched by plugin on "Proceed").

Usage:
  python3 booking_loop.py --task_id "padel_123"

Reads booking data from padel state file, then:
1. Send initial progress message
2. For each venue: start call → poll VAPI → update Telegram
3. Show alternatives or confirmation when done
"""

import os
import sys
import json
import time
import signal
import atexit
import argparse
import requests
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import padel_log as log

# Config
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
STATE_DIR = os.environ.get("PADEL_STATE_DIR", "/root/.openclaw/padel_state")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PID_DIR = "/root/.openclaw/padel_pids"

# Fallback: read from /etc/environment
if not BOT_TOKEN:
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    BOT_TOKEN = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    except Exception:
        pass

# Polling config
POLL_INTERVAL = 5  # seconds between Retell status checks
MAX_CALL_WAIT = 360  # 6 minutes max per venue call
MAX_TOTAL_TIME = 1800  # 30 minutes max for entire loop


# ── PID management ───────────────────────────────────────────

def get_pid_path(task_id: str) -> str:
    os.makedirs(PID_DIR, exist_ok=True)
    return os.path.join(PID_DIR, f"{task_id}.pid")


def kill_existing(task_id: str):
    """Kill any existing booking_loop for this task."""
    pid_path = get_pid_path(task_id)
    if os.path.exists(pid_path):
        try:
            with open(pid_path, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            log(f"Killed old process {old_pid}")
            time.sleep(0.5)
        except (ProcessLookupError, ValueError):
            pass
        try:
            os.remove(pid_path)
        except Exception:
            pass


def write_pid(task_id: str):
    """Write current PID to file."""
    pid_path = get_pid_path(task_id)
    with open(pid_path, 'w') as f:
        f.write(str(os.getpid()))


def cleanup_pid(task_id: str):
    """Remove PID file."""
    try:
        pid_path = get_pid_path(task_id)
        if os.path.exists(pid_path):
            os.remove(pid_path)
    except Exception:
        pass


def cleanup_all_stale_pids():
    """Remove PID files for processes that no longer exist."""
    try:
        os.makedirs(PID_DIR, exist_ok=True)
        for f in os.listdir(PID_DIR):
            if f.endswith(".pid"):
                path = os.path.join(PID_DIR, f)
                try:
                    with open(path, 'r') as fh:
                        pid = int(fh.read().strip())
                    os.kill(pid, 0)  # check if alive
                except (ProcessLookupError, ValueError):
                    os.remove(path)
                    log(f"Cleaned stale PID file: {f}")
    except Exception:
        pass

# Status rendering (matches n8n StatusRenderer exactly)


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


# ── Telegram helpers ─────────────────────────────────────────

def send_message(chat_id: str, text: str, keyboard: dict = None) -> int:
    if not BOT_TOKEN:
        log("ERROR: BOT_TOKEN not set")
        return 0
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard) if isinstance(keyboard, dict) else keyboard
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get('ok'):
            msg_id = data['result']['message_id']
            log(f"Sent msg={msg_id} to chat={chat_id}")
            return msg_id
        else:
            log(f"Send failed {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log(f"Send error: {e}")
    return 0


def edit_message(chat_id: str, message_id: int, text: str, keyboard: dict = None):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard) if isinstance(keyboard, dict) else keyboard
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            log(f"Edit failed {resp.status_code}: {resp.text[:200]}")
        else:
            log(f"Edit OK msg={message_id}")
    except Exception as e:
        log(f"Edit error: {e}")


# ── VAPI call helpers ────────────────────────────────────────

def start_vapi_call(venue: dict, booking_data: dict) -> dict:
    """Start a VAPI call via retell_call.py"""
    cmd = [
        "python3", os.path.join(SCRIPTS_DIR, "retell_call.py"), "start",
        "--venue_phone", str(venue.get("phone", "")),
        "--venue_name", venue.get("name", ""),
        "--booking_date", booking_data.get("date", ""),
        "--booking_time", booking_data.get("time", ""),
        "--duration", str(booking_data.get("duration_minutes", 90)),
        "--city", booking_data.get("city", ""),
        "--task_id", booking_data.get("task_id", ""),
        "--chat_id", booking_data.get("chat_id", ""),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        log(f"Failed to start call: {e}")
    return {"success": False, "error": "Failed to start call"}


def check_vapi_status(call_id: str) -> dict:
    """Check VAPI call status via retell_call.py"""
    cmd = [
        "python3", os.path.join(SCRIPTS_DIR, "retell_call.py"), "status",
        "--call_id", call_id,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        log(f"Failed to check status: {e}")
    return {"success": False, "status": "unknown"}


# ── Progress message builder ─────────────────────────────────

def get_method_icon(club: dict) -> str:
    """Get method icon for venue (matches n8n StatusRenderer)."""
    has_call = bool(club.get("recording_url") or club.get("transcript_lines") or club.get("summary"))
    has_wa = bool(club.get("conversation_history"))
    if has_call and has_wa:
        return "📱+📞"
    if has_wa:
        return "📱"
    if club.get("check_method") == "whatsapp":
        return "📱"
    return "📞"


def render_status_list(all_venues: list, clubs: dict, mode: str = "normal") -> str:
    """Render status list (matches n8n StatusRenderer exactly)."""
    active_statuses = ["pending", "pending_wa", "calling"]
    status_list = ""

    for v in all_venues:
        name = v.get("name", "Unknown")
        club = clubs.get(name)
        if not club:
            continue

        icon = get_method_icon(club)
        status = club.get("status", "pending")

        # Cancel mode: active → cancelled
        if mode == "cancel" and status in active_statuses:
            status_list += f"🚫 <b>{name}</b> — cancelled\n"
        elif status == "user_declined":
            status_list += f"🚫 <b>{name}</b> — you declined\n"
        elif status in ("confirmed", "booked"):
            status_list += f"✅ <b>{name}</b> — BOOKED!\n"
        elif status == "skipped":
            status_list += f"⏭️ <b>{name}</b> — skipped\n"
        elif status == "has_times":
            times = club.get("times_available", [])
            status_list += f"🕐 <b>{name}</b> — {len(times)} slots available {icon}\n"
        elif status == "awaiting_confirmation":
            selected = club.get("selected_time", "")
            status_list += f"⏳ <b>{name}</b> — requested {selected} {icon}\n"
        elif status == "pending_wa":
            delivery = club.get("delivery_status", "")
            if delivery == "read":
                status_list += f"📱 <b>{name}</b> — read ✓✓\n"
            elif delivery == "delivered":
                status_list += f"📱 <b>{name}</b> — delivered ✓\n"
            elif delivery == "sent":
                status_list += f"📱 <b>{name}</b> — sent...\n"
            else:
                status_list += f"📱 <b>{name}</b> — sending...\n"
        elif status == "pending":
            status_list += f"📞 <b>{name}</b> — queued\n"
        elif status == "calling":
            status_list += f"📞 <b>{name}</b> — calling...\n"
        elif status == "timeout":
            status_list += f"💤 <b>{name}</b> — no WA response\n"
        elif status in ("rejected", "declined", "no_availability"):
            status_list += f"❌ <b>{name}</b> — no availability\n"
        elif status in ("hung_up", "no_answer"):
            status_list += f"📵 <b>{name}</b> — no answer\n"
        elif status == "error":
            status_list += f"⚠️ <b>{name}</b> — error\n"
        elif mode == "cancel":
            status_list += f"🚫 <b>{name}</b> — cancelled\n"

    return status_list


def build_progress_buttons(task_id: str, clubs: dict) -> dict:
    """Build reply_markup buttons (matches n8n StatusRenderer)."""
    rows = []
    added = set()

    # 1. Venues with times
    venues_with_times = [
        name for name, c in clubs.items()
        if c.get("status") == "has_times" and c.get("times_available")
    ]
    for i, name in enumerate(venues_with_times):
        club = clubs[name]
        icon = get_method_icon(club)
        times = club.get("times_available", [])
        rows.append([{
            "text": f"🎾 {name} ({len(times)} slots) {icon}",
            "callback_data": f"padel:{task_id}|pick_venue|{name}",
        }])
        added.add(name)

    # 2. Failed venues with viewable data
    viewable = ["declined", "rejected", "hung_up", "timeout", "no_availability", "no_answer",
                "awaiting_confirmation", "has_times", "booked", "confirmed", "user_declined"]
    for name, club in clubs.items():
        if name in added:
            continue
        if club.get("status") not in viewable:
            continue
        has_call = bool(club.get("recording_url") or club.get("transcript_lines"))
        if has_call:
            rows.append([{
                "text": f"📞 {name} — view call",
                "callback_data": f"padel:{task_id}|view_summary|{name}",
            }])
            added.add(name)

    # 3. Cancel button (always present)
    rows.append([{
        "text": "❌ Cancel Booking",
        "callback_data": f"padel:{task_id}|cancel_booking",
    }])

    return {"inline_keyboard": rows}


def build_progress_message(booking_data: dict, all_venues: list, clubs: dict,
                           current_venue: str = None, current_index: int = 0,
                           total_venues: int = 0) -> str:
    """Build complete progress message (matches n8n format)."""
    status_list = render_status_list(all_venues, clubs)

    is_single = len(all_venues) == 1

    if current_venue and clubs.get(current_venue, {}).get("status") == "calling":
        method = clubs[current_venue].get("check_method", "call")
        method_icon = "📱" if method == "whatsapp" else "📞"

        if is_single:
            text = f"📞 <b>Calling {current_venue}...</b>"
        else:
            action = f"\n{method_icon} <b>Calling {current_venue}...</b> ({current_index}/{total_venues})"
            text = f"📞 <b>Booking Progress</b>\n\n{status_list}{action}"
    else:
        text = f"📞 <b>Booking Progress</b>\n\n{status_list}"

    # Cost tracking
    total_cost = sum(c.get("cost_cents", 0) for c in clubs.values()) / 100
    total_duration = sum(c.get("duration_seconds", 0) for c in clubs.values())
    total_calls = sum(1 for c in clubs.values() if c.get("status") not in ["pending", "skipped"])

    if total_calls > 0:
        mins = total_duration // 60
        secs = total_duration % 60
        text += f"\n━━━━━━━━━━━━━━━━━━━\n"
        text += f"💰 ${total_cost:.2f} | ⏱ {mins}m {secs}s ({total_calls} calls)"

    return text


# ── Main booking loop ────────────────────────────────────────

def run_booking_loop(task_id: str):
    """Main booking loop - calls venues and tracks progress."""
    # Kill any existing loop for this task, write our PID
    kill_existing(task_id)
    cleanup_all_stale_pids()
    write_pid(task_id)
    atexit.register(cleanup_pid, task_id)

    # Handle SIGTERM gracefully
    def handle_signal(signum, frame):
        log(f"Received signal {signum}, cleaning up")
        cleanup_pid(task_id)
        sys.exit(0)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    state = load_state(task_id)
    if not state:
        log(f"No state found for {task_id}")
        cleanup_pid(task_id)
        return

    # Build booking_data from quiz state (plugin calls us directly, padel_quiz.py proceed may not have run)
    booking_data = state.get("booking_data", {})
    if not booking_data:
        settings = state.get("settings", {})
        venue = state.get("selected_venue", {})
        duration_map = {"1hr": 60, "1.5hr": 90, "2hr": 120}
        booking_data = {
            "task_id": task_id,
            "chat_id": state.get("chat_id", ""),
            "date": state.get("date", ""),
            "time": state.get("time", ""),
            "city": state.get("city_name", ""),
            "city_key": state.get("city_key", ""),
            "venue_name": venue.get("name", ""),
            "venue_phone": venue.get("phone", ""),
            "duration": settings.get("duration", "1.5hr"),
            "duration_minutes": duration_map.get(settings.get("duration", "1.5hr"), 90),
        }
        state["booking_data"] = booking_data
        save_state(task_id, state)

    chat_id = booking_data.get("chat_id", "") or state.get("chat_id", "")
    venues = state.get("venues", [])

    if not venues:
        log("No venues to call")
        return

    log(f"Starting booking loop: {len(venues)} venues for {booking_data.get('city', '')}")
    log(f"BOT_TOKEN set: {bool(BOT_TOKEN)}, chat_id: {chat_id}")

    # Initialize clubs tracking dict
    clubs = {}
    for venue in venues:
        name = venue.get("name", "Unknown")
        clubs[name] = {
            "status": "pending",
            "phone": venue.get("phone", ""),
            "check_method": "call",
            "times_available": [],
            "transcript_lines": [],
            "summary": "",
            "recording_url": "",
            "cost_cents": 0,
            "duration_seconds": 0,
            "call_id": "",
        }

    # Reorder venues: selected venue first, then the rest in original order
    selected_venue_name = booking_data.get("venue_name", "")
    if selected_venue_name:
        selected = [v for v in venues if v.get("name", "") == selected_venue_name]
        rest = [v for v in venues if v.get("name", "") != selected_venue_name]
        venues = selected + rest

    # Build all_venues list for StatusRenderer format
    all_venues = [{"name": v.get("name", "Unknown"), "method": "call"} for v in venues]

    # Send initial progress message with Cancel button
    text = f"📞 <b>Booking Progress</b>\n\n"
    for v in all_venues:
        text += f"📞 <b>{v['name']}</b> — queued\n"
    text += "\n⏳ Starting..."

    cancel_keyboard = {"inline_keyboard": [[{
        "text": "❌ Cancel Booking",
        "callback_data": f"padel:{task_id}|cancel_booking",
    }]]}

    progress_msg_id = send_message(chat_id, text, cancel_keyboard)

    if not progress_msg_id:
        log("Failed to send progress message")
        return

    # Save progress message ID
    state["progress_message_id"] = progress_msg_id
    state["clubs"] = clubs
    state["all_venues"] = all_venues
    state["loop_status"] = "running"
    save_state(task_id, state)

    loop_start = time.time()
    booking_confirmed = False
    total_venues = len(venues)

    # Loop through venues
    for i, venue in enumerate(venues):
        venue_name = venue.get("name", "Unknown")
        phone = venue.get("phone", "")

        # Check if cancelled
        fresh_state = load_state(task_id)
        if fresh_state.get("loop_status") == "cancelled":
            log("Loop cancelled by user")
            cleanup_pid(task_id)
            return

        if time.time() - loop_start > MAX_TOTAL_TIME:
            log("Max total time reached, stopping loop")
            break

        if booking_confirmed:
            clubs[venue_name]["status"] = "skipped"
            continue

        if not phone:
            log(f"No phone for {venue_name}, skipping")
            clubs[venue_name]["status"] = "skipped"
            continue

        # Update status: calling + update Telegram with reply_markup
        clubs[venue_name]["status"] = "calling"
        text = build_progress_message(booking_data, all_venues, clubs,
                                       current_venue=venue_name,
                                       current_index=i + 1,
                                       total_venues=total_venues)
        buttons = build_progress_buttons(task_id, clubs)
        edit_message(chat_id, progress_msg_id, text, buttons)

        # Start VAPI call
        call_result = start_vapi_call(venue, booking_data)

        if not call_result.get("success"):
            log(f"Failed to start call to {venue_name}: {call_result.get('error')}")
            clubs[venue_name]["status"] = "error"
            text = build_progress_message(booking_data, all_venues, clubs)
            buttons = build_progress_buttons(task_id, clubs)
            edit_message(chat_id, progress_msg_id, text, buttons)
            continue

        call_id = call_result.get("call_id", "")
        clubs[venue_name]["call_id"] = call_id
        log(f"Call started to {venue_name}: {call_id}")

        # Poll for call result
        call_start = time.time()

        while time.time() - call_start < MAX_CALL_WAIT:
            time.sleep(POLL_INTERVAL)

            # Check cancel during poll wait
            fresh = load_state(task_id)
            if fresh.get("loop_status") == "cancelled":
                log("Cancelled during poll wait")
                cleanup_pid(task_id)
                return

            status_result = check_vapi_status(call_id)
            call_status = status_result.get("status", "unknown")
            log(f"Poll {venue_name}: {call_status}")

            if not status_result.get("success"):
                continue

            if call_status in ("ended", "error"):
                # Call ended - process result
                was_picked_up = status_result.get("was_picked_up", False)
                was_successful = status_result.get("was_successful", False)
                ended_reason = status_result.get("ended_reason", "")
                times_available = status_result.get("times_available", [])

                clubs[venue_name]["transcript_lines"] = status_result.get("transcript_lines", [])
                clubs[venue_name]["summary"] = status_result.get("summary", "")
                clubs[venue_name]["recording_url"] = status_result.get("recording_url", "")
                clubs[venue_name]["cost_cents"] = status_result.get("cost_cents", 0)
                clubs[venue_name]["duration_seconds"] = status_result.get("duration_seconds", 0)

                if not was_picked_up:
                    clubs[venue_name]["status"] = "hung_up"
                    log(f"{venue_name}: no answer ({ended_reason})")
                elif was_successful:
                    clubs[venue_name]["status"] = "confirmed"
                    clubs[venue_name]["times_available"] = times_available
                    booking_confirmed = True
                    log(f"{venue_name}: BOOKING CONFIRMED!")
                elif times_available:
                    clubs[venue_name]["status"] = "has_times"
                    clubs[venue_name]["times_available"] = times_available
                    log(f"{venue_name}: {len(times_available)} times available")
                else:
                    clubs[venue_name]["status"] = "declined"
                    log(f"{venue_name}: no availability")

                break

        else:
            # Timeout
            clubs[venue_name]["status"] = "timeout"
            log(f"{venue_name}: call timed out after {MAX_CALL_WAIT}s")

        # Update progress message after each venue (with reply_markup)
        text = build_progress_message(booking_data, all_venues, clubs)
        buttons = build_progress_buttons(task_id, clubs)
        edit_message(chat_id, progress_msg_id, text, buttons)

        # Save state after each venue
        state["clubs"] = clubs
        save_state(task_id, state)

    # ── Loop complete ──

    state["loop_status"] = "completed"
    state["clubs"] = clubs
    save_state(task_id, state)

    # Build final message using StatusRenderer format
    venues_with_times = [
        name for name, c in clubs.items()
        if c.get("times_available") and c.get("status") == "has_times"
    ]
    confirmed_venue = next(
        (name for name, c in clubs.items() if c.get("status") in ("confirmed", "booked")),
        None
    )

    text = build_progress_message(booking_data, all_venues, clubs)
    buttons = build_progress_buttons(task_id, clubs)

    if confirmed_venue:
        text += f"\n\n✅ <b>Booked at {confirmed_venue}!</b>"
        info = clubs[confirmed_venue]
        if info.get("times_available"):
            text += f"\n🕐 {info['times_available'][0]}"

        # Add calendar event button
        buttons["inline_keyboard"].insert(0, [{
            "text": "📅 Create Calendar Event",
            "callback_data": f"padel:{task_id}|create_event|{confirmed_venue}",
        }])

    elif venues_with_times:
        count = len(venues_with_times)
        text += f"\n\n🎾 <b>{count} venue(s) offered alternative times!</b>\n"
        text += "📋 Pick a venue to see available slots:"

    else:
        text += "\n\n❌ <b>All venues contacted — no availability.</b>\nTry a different date or time."

    edit_message(chat_id, progress_msg_id, text, buttons)

    cleanup_pid(task_id)
    log(f"Booking loop completed. Confirmed: {confirmed_venue or 'None'}, Alternatives: {len(venues_with_times)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task_id', required=True)
    args = parser.parse_args()
    run_booking_loop(args.task_id)


if __name__ == "__main__":
    main()
