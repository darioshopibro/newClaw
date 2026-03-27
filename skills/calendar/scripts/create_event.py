#!/usr/bin/env python3
"""
Create a calendar event.

IMPORTANT: This script REQUIRES a completed quiz session before creating events.
If you try to create an event without quiz completion, it will be BLOCKED.

Usage:
    python3 create_event.py --task_id "cal_123" --title "Meeting" --date 2024-03-15 --time 14:00 \
        --calendar moses --attendees "john@example.com,jane@example.com"

The --task_id must match a quiz session in Supabase with status="completed".

Output: JSON with created event details
"""

import argparse
import json
import os
import sys
from supabase import create_client

# Add lib to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from logger import create_event_log as log_to_telegram

# Only import calendar client when actually creating event
# from lib.google_calendar import GoogleCalendarClient

# Supabase config
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://qdrtfwnftwfuykjyvyxd.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

# Telegram logging
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
LOG_CHAT_ID = "5127607280"


def check_quiz_completion(task_id: str) -> dict:
    """
    Check if quiz is completed for this task_id.
    Returns quiz data if completed, error if not.
    """
    log_to_telegram(f"Checking quiz completion for task_id: {task_id}")

    if not SUPABASE_KEY:
        return {'completed': False, 'error': 'SUPABASE_SERVICE_KEY not set'}

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = supabase.table('task_temp_data').select('*').eq('task_id', task_id).eq('data_type', 'quiz_session').execute()

        if not result.data:
            log_to_telegram(f"❌ No quiz found for {task_id}")
            return {
                'completed': False,
                'error': f'No quiz session found for task_id: {task_id}. You MUST start a quiz first using start_quiz.py'
            }

        record = result.data[0]
        data = record.get('data', {})
        if isinstance(data, str):
            data = json.loads(data)

        # Check if quiz is completed
        questions = data.get('questions', [])
        answers = data.get('answers', {})

        # Quiz is complete if all questions have answers
        if len(answers) < len(questions):
            log_to_telegram(f"⏳ Quiz incomplete: {len(answers)}/{len(questions)}")
            return {
                'completed': False,
                'error': f'Quiz not completed. Answered {len(answers)} of {len(questions)} questions. Wait for user to complete the quiz.'
            }

        log_to_telegram(f"✅ Quiz completed: {len(answers)} answers")
        return {
            'completed': True,
            'answers': answers,
            'original_data': data.get('original_data', {}),
            'data': data
        }

    except Exception as e:
        log_to_telegram(f"❌ Error: {str(e)}")
        return {'completed': False, 'error': f'Failed to check quiz: {str(e)}'}


def main():
    parser = argparse.ArgumentParser(description='Create calendar event (REQUIRES quiz completion)')
    parser.add_argument('--task_id', help='Task ID from quiz session (REQUIRED unless --skip_quiz_check)')
    parser.add_argument('--title', required=True, help='Event title')
    parser.add_argument('--date', required=True, help='Date in YYYY-MM-DD format')
    parser.add_argument('--time', required=True, help='Time in HH:MM format')
    parser.add_argument('--duration', type=int, default=60, help='Duration in minutes')
    parser.add_argument('--calendar', default='moses', help='Calendar key or ID')
    parser.add_argument('--attendees', help='Comma-separated email addresses')
    parser.add_argument('--description', help='Event description')
    parser.add_argument('--location', help='Event location')
    parser.add_argument('--skip_quiz_check', action='store_true', help='DANGEROUS: Skip quiz check (for callbacks only)')

    args = parser.parse_args()

    log_to_telegram(f"Called with: title={args.title}, date={args.date}, time={args.time}, task_id={args.task_id}")

    # ENFORCE QUIZ COMPLETION
    if not args.skip_quiz_check:
        if not args.task_id:
            error_msg = 'BLOCKED: --task_id is REQUIRED. You must start a quiz first with start_quiz.py and pass the task_id.'
            log_to_telegram(f"❌ {error_msg}")
            print(json.dumps({
                'success': False,
                'error': 'TASK_ID_REQUIRED',
                'message': error_msg,
                'action_required': 'Start a quiz using start_quiz.py, then use the task_id when creating the event after quiz completion.'
            }, indent=2))
            sys.exit(1)

        quiz_status = check_quiz_completion(args.task_id)

        if not quiz_status.get('completed'):
            log_to_telegram(f"❌ BLOCKED - quiz not completed")
            print(json.dumps({
                'success': False,
                'error': 'QUIZ_NOT_COMPLETED',
                'message': quiz_status.get('error', 'Quiz not completed'),
                'action_required': 'You MUST start a quiz using start_quiz.py and wait for user to complete it before creating events.'
            }, indent=2))
            sys.exit(1)

        log_to_telegram(f"✅ Quiz verified, proceeding to create event")

    attendees = None
    if args.attendees:
        attendees = [e.strip() for e in args.attendees.split(',')]

    try:
        # Import here to avoid loading if quiz check fails
        from lib.google_calendar import GoogleCalendarClient

        client = GoogleCalendarClient()
        result = client.create_event(
            title=args.title,
            date=args.date,
            time=args.time,
            duration_minutes=args.duration,
            calendar=args.calendar,
            attendees=attendees,
            description=args.description,
            location=args.location
        )
        log_to_telegram(f"✅ Event created: {result.get('event_id', 'unknown')}")
        print(json.dumps(result, indent=2))

    except Exception as e:
        log_to_telegram(f"❌ Failed to create event: {str(e)}")
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
