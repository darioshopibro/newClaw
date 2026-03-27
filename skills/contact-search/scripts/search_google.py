#!/usr/bin/env python3
"""
Contact Search Script
Searches Google Contacts using People API.
Agent handles variation logic - this script just searches.
"""

import argparse
import json
import sys
from typing import Optional

from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build


class GoogleContactsClient:
    def __init__(self):
        """Initialize with gcloud ADC"""
        try:
            credentials, project = default(
                scopes=['https://www.googleapis.com/auth/contacts.readonly']
            )
            self.service = build('people', 'v1', credentials=credentials)
        except DefaultCredentialsError as e:
            print(json.dumps({
                "success": False,
                "error": f"Google credentials not configured: {e}",
                "contacts": [],
                "count": 0
            }))
            sys.exit(1)

    def search(self, query: str, max_results: int = 10) -> dict:
        """
        Search contacts by name.

        Args:
            query: Search query (name, email, etc.)
            max_results: Maximum results to return

        Returns:
            dict with 'contacts' list and 'count'
        """
        try:
            results = self.service.people().searchContacts(
                query=query,
                pageSize=max_results,
                readMask='names,emailAddresses,phoneNumbers,organizations'
            ).execute()

            contacts = []
            for person in results.get('results', []):
                p = person.get('person', {})
                contact = self._parse_person(p)
                if contact:
                    contacts.append(contact)

            return {
                'success': True,
                'contacts': contacts,
                'count': len(contacts),
                'query': query
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'contacts': [],
                'count': 0
            }

    def _parse_person(self, person: dict) -> Optional[dict]:
        """Parse a person resource into a clean contact dict."""
        names = person.get('names', [])
        emails = person.get('emailAddresses', [])
        phones = person.get('phoneNumbers', [])
        orgs = person.get('organizations', [])

        if not names and not emails:
            return None

        contact = {
            'resource_name': person.get('resourceName'),
            'name': names[0].get('displayName') if names else None,
            'first_name': names[0].get('givenName') if names else None,
            'last_name': names[0].get('familyName') if names else None,
            'email': emails[0].get('value') if emails else None,
            'all_emails': [e.get('value') for e in emails],
            'phone': phones[0].get('value') if phones else None,
            'all_phones': [p.get('value') for p in phones],
            'organization': orgs[0].get('name') if orgs else None,
            'title': orgs[0].get('title') if orgs else None
        }

        return contact


def main():
    parser = argparse.ArgumentParser(description='Search Google Contacts')
    parser.add_argument('--query', '-q', required=True, help='Search query (name)')
    parser.add_argument('--max', '-m', type=int, default=10, help='Max results')

    args = parser.parse_args()

    client = GoogleContactsClient()
    result = client.search(args.query, args.max)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
