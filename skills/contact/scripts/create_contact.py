#!/usr/bin/env python3
"""
Create Contact Script - DEPRECATED!

⚠️ WARNING: DO NOT USE THIS SCRIPT DIRECTLY!
Use contact_quiz.py confirm instead - it shows a confirmation quiz first.

This script exists only for internal use by contact_quiz.py callbacks.
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from google_contacts_write import GoogleContactsWriteClient

LOG_FILE = "/var/log/openclaw_calendar.log"


def log(msg: str):
    """Log to calendar log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] [create_contact] {msg}\n")
    except:
        pass
    print(f"[create_contact] {msg}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Create a new contact')
    parser.add_argument('--first_name', '-f', required=True, help='First name')
    parser.add_argument('--last_name', '-l', help='Last name')
    parser.add_argument('--phone', '-p', required=True, help='Phone number')
    parser.add_argument('--email', '-e', help='Email address')
    parser.add_argument('--company', '-c', help='Company name')
    parser.add_argument('--title', '-t', help='Job title')
    parser.add_argument('--notes', '-n', help='Additional notes')

    args = parser.parse_args()

    # Log warning - this script should not be used directly!
    log(f"⚠️ WARNING: create_contact.py called directly! Should use contact_quiz.py confirm instead!")
    log(f"Creating: {args.first_name} {args.last_name or ''} phone={args.phone} email={args.email}")

    try:
        client = GoogleContactsWriteClient()
        result = client.create(
            first_name=args.first_name,
            last_name=args.last_name,
            phone=args.phone,
            email=args.email,
            company=args.company,
            title=args.title,
            notes=args.notes
        )

        print(json.dumps(result, indent=2, ensure_ascii=False))

        if not result.get('success'):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
