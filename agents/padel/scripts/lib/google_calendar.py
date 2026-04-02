"""
Google Calendar API Client
Uses OAuth2 credentials (token.json) - run oauth_setup.py first
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from .logger import calendar_log as log

# Paths
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')

SCOPES = ['https://www.googleapis.com/auth/calendar']

# Calendar IDs - 'primary' = the logged-in user's main calendar
CALENDARS = {
    'primary': 'primary',
    'shopibro': 'primary',  # Maps to user's primary calendar
    'moses': 'primary',     # Alias for quiz compatibility
}

DEFAULT_CALENDAR = 'shopibro'


def get_credentials():
    """Load and refresh OAuth credentials."""
    log("Loading OAuth credentials...")

    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"No token.json found at {TOKEN_FILE}\n"
            f"Run: python3 oauth_setup.py"
        )

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        log("Token expired, refreshing...")
        creds.refresh(Request())
        # Save refreshed token
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        log("Token refreshed and saved")
    else:
        log("Token valid")

    return creds


class GoogleCalendarClient:
    def __init__(self):
        """Initialize with OAuth credentials"""
        log("Initializing GoogleCalendarClient")
        credentials = get_credentials()
        self.service = build('calendar', 'v3', credentials=credentials)
        log("GoogleCalendarClient ready")

    def check_conflicts(
        self,
        date: str,
        time: str,
        duration_minutes: int = 60,
        calendars: Optional[list] = None
    ) -> dict:
        """
        Check for conflicts across calendars.

        Args:
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            duration_minutes: Event duration
            calendars: List of calendar keys to check (default: all)

        Returns:
            dict with 'has_conflicts', 'conflicts' list, 'free_calendars' list
        """
        if calendars is None:
            calendars = list(CALENDARS.keys())

        # Parse datetime
        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        time_min = start_dt.isoformat() + 'Z'
        time_max = end_dt.isoformat() + 'Z'

        conflicts = []
        free_calendars = []

        for cal_key in calendars:
            cal_id = CALENDARS.get(cal_key, cal_key)

            try:
                events_result = self.service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = events_result.get('items', [])

                if events:
                    for event in events:
                        conflicts.append({
                            'calendar': cal_key,
                            'title': event.get('summary', 'No title'),
                            'start': event['start'].get('dateTime', event['start'].get('date')),
                            'end': event['end'].get('dateTime', event['end'].get('date'))
                        })
                else:
                    free_calendars.append(cal_key)

            except Exception as e:
                conflicts.append({
                    'calendar': cal_key,
                    'error': str(e)
                })

        return {
            'has_conflicts': len(conflicts) > 0,
            'conflicts': conflicts,
            'free_calendars': free_calendars,
            'checked_time': {
                'date': date,
                'time': time,
                'duration_minutes': duration_minutes
            }
        }

    def create_event(
        self,
        title: str,
        date: str,
        time: str,
        duration_minutes: int = 60,
        calendar: str = DEFAULT_CALENDAR,
        attendees: Optional[list] = None,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> dict:
        """
        Create a calendar event.

        Args:
            title: Event title
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            duration_minutes: Event duration
            calendar: Calendar key or ID
            attendees: List of email addresses
            description: Event description
            location: Event location

        Returns:
            dict with event details or error
        """
        cal_id = CALENDARS.get(calendar, calendar)
        log(f"Creating event: '{title}' on {date} at {time}, calendar={calendar} (id={cal_id})")

        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            'summary': title,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC'
            }
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        if description:
            event['description'] = description

        if location:
            event['location'] = location

        try:
            log("Calling Google Calendar API...")
            created = self.service.events().insert(
                calendarId=cal_id,
                body=event,
                sendUpdates='all' if attendees else 'none'
            ).execute()

            event_id = created.get('id')
            link = created.get('htmlLink')
            log(f"SUCCESS! Event created: id={event_id}")
            log(f"Event link: {link}")

            return {
                'success': True,
                'event_id': event_id,
                'link': link,
                'calendar': calendar,
                'title': title,
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat()
            }

        except Exception as e:
            log(f"FAILED to create event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def list_events(
        self,
        calendar: str = DEFAULT_CALENDAR,
        days_ahead: int = 7
    ) -> list:
        """List upcoming events from a calendar."""
        cal_id = CALENDARS.get(calendar, calendar)

        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

        try:
            events_result = self.service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            return events_result.get('items', [])

        except Exception as e:
            return [{'error': str(e)}]
