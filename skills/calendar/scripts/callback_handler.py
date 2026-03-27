#!/usr/bin/env python3
"""
Handle Telegram callback button clicks.

Usage:
    python callback_handler.py --callback_data "cc|task123|select|0" \
        --message_id 789 --chat_id 123456789

Callback patterns:
    cc|task_id|step|value  - Contact choice
    cs|task_id|field|value - Calendar settings/confirmation

Output: JSON with action result
"""

import argparse
import json
import sys
from lib.telegram_api import TelegramAPI
from lib.supabase_client import SupabaseClient


def parse_callback(callback_data: str) -> dict:
    """Parse callback_data string into components."""
    parts = callback_data.split('|')
    if len(parts) < 4:
        return {'error': 'Invalid callback format'}

    return {
        'type': parts[0],  # cc = contact choice, cs = calendar settings
        'task_id': parts[1],
        'step': parts[2],
        'value': parts[3]
    }


def handle_contact_choice(parsed: dict, temp_data: dict, telegram: TelegramAPI, supabase: SupabaseClient, args) -> dict:
    """Handle contact selection callback."""
    task_id = parsed['task_id']
    step = parsed['step']
    value = parsed['value']

    if step == 'cancel':
        # User cancelled
        telegram.edit_message_text(
            chat_id=args.chat_id,
            message_id=args.message_id,
            text="Contact selection cancelled."
        )
        supabase.delete_temp_data(task_id)
        return {'success': True, 'action': 'cancelled'}

    # Get selected contact
    contacts = temp_data.get('quiz_data', [])
    try:
        index = int(value)
        if 0 <= index < len(contacts):
            selected = contacts[index]

            # Update temp data with selection
            temp_data['selected_contact'] = selected
            temp_data['status'] = 'selected'
            supabase.set_temp_data(task_id, temp_data)

            # Update message
            telegram.edit_message_text(
                chat_id=args.chat_id,
                message_id=args.message_id,
                text=f"Selected: {selected.get('name', 'Unknown')} ({selected.get('email', 'no email')})"
            )

            return {
                'success': True,
                'action': 'contact_selected',
                'contact': selected
            }
        else:
            return {'success': False, 'error': 'Invalid selection index'}

    except (ValueError, IndexError) as e:
        return {'success': False, 'error': str(e)}


def handle_calendar_settings(parsed: dict, temp_data: dict, telegram: TelegramAPI, supabase: SupabaseClient, args) -> dict:
    """Handle calendar settings/confirmation callback."""
    task_id = parsed['task_id']
    field = parsed['step']
    value = parsed['value']

    if field == 'cancel':
        telegram.edit_message_text(
            chat_id=args.chat_id,
            message_id=args.message_id,
            text="Event creation cancelled."
        )
        supabase.delete_temp_data(task_id)
        return {'success': True, 'action': 'cancelled'}

    if field == 'confirm':
        # User confirmed event creation
        temp_data['status'] = 'confirmed'
        supabase.set_temp_data(task_id, temp_data)

        event_details = temp_data.get('quiz_data', {})
        telegram.edit_message_text(
            chat_id=args.chat_id,
            message_id=args.message_id,
            text=f"Event confirmed: {event_details.get('title', 'Event')}\nCreating..."
        )

        return {
            'success': True,
            'action': 'event_confirmed',
            'event_details': event_details
        }

    return {'success': False, 'error': f'Unknown field: {field}'}


def main():
    parser = argparse.ArgumentParser(description='Handle Telegram callbacks')
    parser.add_argument('--callback_data', required=True, help='Callback data string')
    parser.add_argument('--message_id', required=True, type=int, help='Message ID')
    parser.add_argument('--chat_id', required=True, help='Chat ID')

    args = parser.parse_args()

    try:
        parsed = parse_callback(args.callback_data)
        if 'error' in parsed:
            print(json.dumps(parsed))
            sys.exit(1)

        telegram = TelegramAPI()
        supabase = SupabaseClient()

        # Get stored temp data
        temp_data = supabase.get_temp_data(parsed['task_id'])
        if not temp_data or 'error' in temp_data:
            temp_data = {}

        # Route to handler based on type
        if parsed['type'] == 'cc':
            result = handle_contact_choice(parsed, temp_data, telegram, supabase, args)
        elif parsed['type'] == 'cs':
            result = handle_calendar_settings(parsed, temp_data, telegram, supabase, args)
        else:
            result = {'success': False, 'error': f"Unknown callback type: {parsed['type']}"}

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
