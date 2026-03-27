"""
Google Contacts (People) API Client with Write Access
Uses gcloud ADC (Application Default Credentials) or OAuth token
"""

import json
import os
from datetime import datetime
from typing import Optional

from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

LOG_FILE = "/var/log/openclaw_calendar.log"


def _log(msg: str):
    """Log to calendar log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] [google_contacts] {msg}\n")
    except:
        pass


class GoogleContactsWriteClient:
    """Google Contacts client with full CRUD access."""

    SCOPES = ['https://www.googleapis.com/auth/contacts']

    def __init__(self):
        """Initialize with OAuth token or gcloud ADC"""
        credentials = self._get_credentials()
        self.service = build('people', 'v1', credentials=credentials)

    def _get_credentials(self):
        """Get credentials - try OAuth token first, then ADC"""
        # Try OAuth token file (same location as calendar skill)
        token_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'token.json'
        )

        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                if creds and creds.valid:
                    return creds
            except Exception:
                pass

        # Fall back to gcloud ADC
        try:
            credentials, project = default(scopes=self.SCOPES)
            return credentials
        except DefaultCredentialsError as e:
            raise RuntimeError(f"No valid credentials found: {e}")

    def create(
        self,
        first_name: str,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        title: Optional[str] = None,
        notes: Optional[str] = None
    ) -> dict:
        """
        Create a new contact.

        Args:
            first_name: Given name (required)
            last_name: Family name
            phone: Phone number
            email: Email address
            company: Organization name
            title: Job title
            notes: Additional notes

        Returns:
            dict with success status and contact_id
        """
        name = f"{first_name} {last_name or ''}".strip()
        _log(f"CREATE: {name} phone={phone} email={email}")

        try:
            person = {
                'names': [{
                    'givenName': first_name,
                    'familyName': last_name or ''
                }]
            }

            if phone:
                person['phoneNumbers'] = [{'value': phone}]

            if email:
                person['emailAddresses'] = [{'value': email}]

            if company or title:
                person['organizations'] = [{
                    'name': company or '',
                    'title': title or ''
                }]

            if notes:
                person['biographies'] = [{'value': notes}]

            result = self.service.people().createContact(
                body=person
            ).execute()

            display_name = f"{first_name} {last_name}".strip() if last_name else first_name

            return {
                'success': True,
                'contact_id': result.get('resourceName'),
                'name': display_name,
                'linkedin_search': f"{display_name} {company or ''}".strip()
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def update(
        self,
        contact_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        add_email: Optional[str] = None,
        add_phone: Optional[str] = None
    ) -> dict:
        """
        Update an existing contact.

        Args:
            contact_id: Resource name (e.g., people/c1234567890)
            Other args: Fields to update (None = don't change)
            add_email: Email to ADD (not replace)
            add_phone: Phone to ADD (not replace)

        Returns:
            dict with success status
        """
        try:
            # First, get the current contact
            current = self.service.people().get(
                resourceName=contact_id,
                personFields='names,emailAddresses,phoneNumbers,organizations,biographies,metadata'
            ).execute()

            # Build update mask
            update_fields = []

            # Update names if provided
            if first_name is not None or last_name is not None:
                names = current.get('names', [{}])
                if names:
                    if first_name is not None:
                        names[0]['givenName'] = first_name
                    if last_name is not None:
                        names[0]['familyName'] = last_name
                else:
                    names = [{'givenName': first_name or '', 'familyName': last_name or ''}]
                current['names'] = names
                update_fields.append('names')

            # Update/add email
            if email is not None or add_email is not None:
                emails = current.get('emailAddresses', [])
                if add_email:
                    # Add new email
                    emails.append({'value': add_email})
                elif email is not None:
                    # Replace first email
                    if emails:
                        emails[0]['value'] = email
                    else:
                        emails = [{'value': email}]
                current['emailAddresses'] = emails
                update_fields.append('emailAddresses')

            # Update/add phone
            if phone is not None or add_phone is not None:
                phones = current.get('phoneNumbers', [])
                if add_phone:
                    # Add new phone
                    phones.append({'value': add_phone})
                elif phone is not None:
                    # Replace first phone
                    if phones:
                        phones[0]['value'] = phone
                    else:
                        phones = [{'value': phone}]
                current['phoneNumbers'] = phones
                update_fields.append('phoneNumbers')

            # Update organization
            if company is not None or title is not None:
                orgs = current.get('organizations', [{}])
                if orgs:
                    if company is not None:
                        orgs[0]['name'] = company
                    if title is not None:
                        orgs[0]['title'] = title
                else:
                    orgs = [{'name': company or '', 'title': title or ''}]
                current['organizations'] = orgs
                update_fields.append('organizations')

            # Update notes
            if notes is not None:
                current['biographies'] = [{'value': notes}]
                update_fields.append('biographies')

            if not update_fields:
                return {
                    'success': False,
                    'error': 'No fields to update'
                }

            # Get etag from metadata
            etag = current.get('etag')

            # Perform update
            result = self.service.people().updateContact(
                resourceName=contact_id,
                updatePersonFields=','.join(update_fields),
                body=current
            ).execute()

            return {
                'success': True,
                'contact_id': contact_id,
                'updated_fields': update_fields
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def delete(self, contact_id: str) -> dict:
        """
        Delete a contact.

        Args:
            contact_id: Resource name (e.g., people/c1234567890)

        Returns:
            dict with success status
        """
        try:
            self.service.people().deleteContact(
                resourceName=contact_id
            ).execute()

            return {
                'success': True,
                'deleted': contact_id
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get(self, contact_id: str) -> Optional[dict]:
        """
        Get a contact by ID.

        Args:
            contact_id: Resource name

        Returns:
            Contact dict or None
        """
        try:
            result = self.service.people().get(
                resourceName=contact_id,
                personFields='names,emailAddresses,phoneNumbers,organizations'
            ).execute()

            names = result.get('names', [])
            emails = result.get('emailAddresses', [])
            phones = result.get('phoneNumbers', [])
            orgs = result.get('organizations', [])

            return {
                'resource_name': result.get('resourceName'),
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

        except Exception as e:
            return None
