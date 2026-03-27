"""
Google Contacts (People) API Client
Uses gcloud ADC (Application Default Credentials)
"""

from typing import Optional
from google.auth import default
from googleapiclient.discovery import build


class GoogleContactsClient:
    def __init__(self):
        """Initialize with gcloud ADC"""
        credentials, project = default(
            scopes=['https://www.googleapis.com/auth/contacts.readonly']
        )
        self.service = build('people', 'v1', credentials=credentials)

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

    def get_by_email(self, email: str) -> Optional[dict]:
        """Get a contact by email address."""
        try:
            results = self.service.people().searchContacts(
                query=email,
                pageSize=5,
                readMask='names,emailAddresses,phoneNumbers,organizations'
            ).execute()

            for person in results.get('results', []):
                p = person.get('person', {})
                emails = p.get('emailAddresses', [])
                for e in emails:
                    if e.get('value', '').lower() == email.lower():
                        return self._parse_person(p)

            return None

        except Exception as e:
            return {'error': str(e)}

    def list_connections(self, max_results: int = 100) -> list:
        """List all contacts."""
        try:
            results = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=max_results,
                personFields='names,emailAddresses,phoneNumbers,organizations'
            ).execute()

            contacts = []
            for person in results.get('connections', []):
                contact = self._parse_person(person)
                if contact:
                    contacts.append(contact)

            return contacts

        except Exception as e:
            return [{'error': str(e)}]

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
            'organization': orgs[0].get('name') if orgs else None,
            'title': orgs[0].get('title') if orgs else None
        }

        return contact
