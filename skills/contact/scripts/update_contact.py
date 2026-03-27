#!/usr/bin/env python3
"""
Update Contact Script
Updates an existing contact in Google Contacts.
"""

import argparse
import json
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from google_contacts_write import GoogleContactsWriteClient


def main():
    parser = argparse.ArgumentParser(description='Update an existing contact')
    parser.add_argument('--contact_id', '-i', required=True, help='Contact resource name (people/c...)')
    parser.add_argument('--first_name', '-f', help='First name')
    parser.add_argument('--last_name', '-l', help='Last name')
    parser.add_argument('--phone', '-p', help='Phone number (replaces existing)')
    parser.add_argument('--email', '-e', help='Email address (replaces existing)')
    parser.add_argument('--add_phone', help='Phone number to ADD (keeps existing)')
    parser.add_argument('--add_email', help='Email address to ADD (keeps existing)')
    parser.add_argument('--company', '-c', help='Company name')
    parser.add_argument('--title', '-t', help='Job title')
    parser.add_argument('--notes', '-n', help='Additional notes')

    args = parser.parse_args()

    try:
        client = GoogleContactsWriteClient()
        result = client.update(
            contact_id=args.contact_id,
            first_name=args.first_name,
            last_name=args.last_name,
            phone=args.phone,
            email=args.email,
            add_phone=args.add_phone,
            add_email=args.add_email,
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
