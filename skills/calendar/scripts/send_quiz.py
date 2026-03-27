#!/usr/bin/env python3
"""
Send Telegram quiz/buttons for user selection.

Usage:
    python send_quiz.py --task_id "123_456" --type "contact" --chat_id 123456789 \
        --data '[{"name": "John", "email": "john@example.com"}]'

Types:
    - contact: Contact selection buttons
    - confirm: Event confirmation buttons

Output: JSON with message_id
"""

import argparse
import json
import sys
from lib.telegram_api import TelegramAPI
from lib.supabase_client import SupabaseClient


def main():
    parser = argparse.ArgumentParser(description='Send Telegram quiz')
    parser.add_argument('--task_id', required=True, help='Task identifier')
    parser.add_argument('--type', required=True, choices=['contact', 'confirm'], help='Quiz type')
    parser.add_argument('--chat_id', required=True, help='Telegram chat ID')
    parser.add_argument('--data', required=True, help='JSON data for quiz')

    args = parser.parse_args()

    try:
        data = json.loads(args.data)
        telegram = TelegramAPI()

        if args.type == 'contact':
            # data should be list of contacts
            result = telegram.send_contact_choice(
                chat_id=args.chat_id,
                task_id=args.task_id,
                contacts=data,
                step='select'
            )

        elif args.type == 'confirm':
            # data should be event details dict
            result = telegram.send_confirmation(
                chat_id=args.chat_id,
                task_id=args.task_id,
                event_details=data
            )

        else:
            result = {'success': False, 'error': f'Unknown type: {args.type}'}

        # Store quiz state in Supabase
        if result.get('success'):
            try:
                supabase = SupabaseClient()
                supabase.set_temp_data(args.task_id, {
                    'quiz_type': args.type,
                    'quiz_data': data,
                    'message_id': result.get('message_id'),
                    'chat_id': args.chat_id,
                    'status': 'pending'
                })
            except Exception as e:
                result['warning'] = f'Failed to store quiz state: {e}'

        print(json.dumps(result, indent=2))

    except json.JSONDecodeError as e:
        print(json.dumps({
            'success': False,
            'error': f'Invalid JSON data: {e}'
        }))
        sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
