#!/usr/bin/env python3
"""
edit_message.py - Edit a Telegram message with HTML parse_mode.
Used by plugin to send HTML-formatted messages.

Usage:
  python3 edit_message.py --chat_id "123" --message_id "456" --text "Hello <b>Bold</b>" --buttons '[...]'
"""

import os
import sys
import json
import argparse
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not BOT_TOKEN:
    try:
        with open("/etc/environment", "r") as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    BOT_TOKEN = line.strip().split("=", 1)[1].strip('"').strip("'")
                    break
    except Exception:
        pass


def main():
    # Read JSON payload from stdin for reliable text transfer (no shell escaping issues)
    if not sys.stdin.isatty():
        data = json.loads(sys.stdin.read())
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("--chat_id", required=True)
        parser.add_argument("--message_id", required=True)
        parser.add_argument("--text", required=True)
        parser.add_argument("--buttons", default="[]")
        args = parser.parse_args()
        data = {
            "chat_id": args.chat_id,
            "message_id": args.message_id,
            "text": args.text,
            "buttons": json.loads(args.buttons),
        }

    payload = {
        "chat_id": data["chat_id"],
        "message_id": int(data["message_id"]),
        "text": data["text"],
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": data.get("buttons", [])},
    }

    resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
        json=payload,
        timeout=10,
    )
    print(json.dumps({"ok": resp.json().get("ok", False)}))


if __name__ == "__main__":
    main()
