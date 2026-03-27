#!/usr/bin/env python3
"""
Search Google Contacts by name.

Usage:
    python search_contacts.py --query "John"

Output: JSON with matching contacts
"""

import argparse
import json
import sys
from lib.google_contacts import GoogleContactsClient


def main():
    parser = argparse.ArgumentParser(description='Search contacts')
    parser.add_argument('--query', required=True, help='Search query (name, email, etc.)')
    parser.add_argument('--max', type=int, default=10, help='Maximum results')

    args = parser.parse_args()

    try:
        client = GoogleContactsClient()
        result = client.search(
            query=args.query,
            max_results=args.max
        )
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e),
            'contacts': [],
            'count': 0
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
