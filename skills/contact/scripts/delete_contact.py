#!/usr/bin/env python3
"""
Delete Contact Script
Deletes a contact from Google Contacts.
"""

import argparse
import json
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from google_contacts_write import GoogleContactsWriteClient


def main():
    parser = argparse.ArgumentParser(description='Delete a contact')
    parser.add_argument('--contact_id', '-i', required=True, help='Contact resource name (people/c...)')

    args = parser.parse_args()

    try:
        client = GoogleContactsWriteClient()
        result = client.delete(contact_id=args.contact_id)

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
