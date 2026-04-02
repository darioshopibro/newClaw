"""
Telegram Bot API Client
For sending messages and inline buttons
"""

import os
import json
import requests
from typing import Optional, Union

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs')
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


class TelegramAPI:
    def __init__(self, token: Optional[str] = None):
        """Initialize Telegram API client"""
        self.token = token or TELEGRAM_BOT_TOKEN
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: str = 'Markdown',
        reply_markup: Optional[dict] = None
    ) -> dict:
        """
        Send a text message.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: 'Markdown', 'MarkdownV2', or 'HTML'
            reply_markup: Inline keyboard or other markup

        Returns:
            dict with 'success', 'message_id', etc.
        """
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=10
            )
            data = response.json()

            if data.get('ok'):
                return {
                    'success': True,
                    'message_id': data['result']['message_id'],
                    'chat_id': chat_id
                }
            else:
                return {
                    'success': False,
                    'error': data.get('description', 'Unknown error')
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def edit_message_text(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        parse_mode: str = 'Markdown',
        reply_markup: Optional[dict] = None
    ) -> dict:
        """Edit an existing message."""
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode
        }

        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)

        try:
            response = requests.post(
                f"{self.base_url}/editMessageText",
                json=payload,
                timeout=10
            )
            data = response.json()

            return {
                'success': data.get('ok', False),
                'error': data.get('description') if not data.get('ok') else None
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def send_inline_buttons(
        self,
        chat_id: Union[int, str],
        text: str,
        buttons: list,
        columns: int = 2
    ) -> dict:
        """
        Send a message with inline keyboard buttons.

        Args:
            chat_id: Telegram chat ID
            text: Message text
            buttons: List of {'text': 'Label', 'callback_data': 'data'} dicts
            columns: Number of button columns

        Returns:
            dict with 'success', 'message_id'
        """
        # Organize buttons into rows
        keyboard = []
        row = []
        for i, btn in enumerate(buttons):
            row.append({
                'text': btn['text'],
                'callback_data': btn['callback_data']
            })
            if len(row) >= columns:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        reply_markup = {'inline_keyboard': keyboard}

        return self.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> dict:
        """Answer a callback query (button click)."""
        payload = {
            'callback_query_id': callback_query_id,
            'show_alert': show_alert
        }

        if text:
            payload['text'] = text

        try:
            response = requests.post(
                f"{self.base_url}/answerCallbackQuery",
                json=payload,
                timeout=10
            )
            data = response.json()

            return {
                'success': data.get('ok', False),
                'error': data.get('description') if not data.get('ok') else None
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ==================== Quiz Helpers ====================

    def send_contact_choice(
        self,
        chat_id: Union[int, str],
        task_id: str,
        contacts: list,
        step: str = 'select'
    ) -> dict:
        """
        Send contact selection buttons.

        Args:
            chat_id: Telegram chat ID
            task_id: Task identifier
            contacts: List of contact dicts with 'name', 'email'
            step: Quiz step identifier

        Returns:
            dict with message result
        """
        text = "Select a contact:"

        buttons = []
        for i, contact in enumerate(contacts):
            name = contact.get('name', contact.get('email', f'Contact {i+1}'))
            email = contact.get('email', '')
            buttons.append({
                'text': f"{name}" + (f" ({email})" if email else ""),
                'callback_data': f"cc|{task_id}|{step}|{i}"
            })

        # Add cancel button
        buttons.append({
            'text': 'Cancel',
            'callback_data': f"cc|{task_id}|cancel|0"
        })

        return self.send_inline_buttons(
            chat_id=chat_id,
            text=text,
            buttons=buttons,
            columns=1
        )

    def send_confirmation(
        self,
        chat_id: Union[int, str],
        task_id: str,
        event_details: dict
    ) -> dict:
        """
        Send event confirmation buttons.

        Args:
            chat_id: Telegram chat ID
            task_id: Task identifier
            event_details: Dict with 'title', 'date', 'time', 'attendees'

        Returns:
            dict with message result
        """
        text = f"*Confirm Event:*\n\n"
        text += f"Title: {event_details.get('title', 'N/A')}\n"
        text += f"Date: {event_details.get('date', 'N/A')}\n"
        text += f"Time: {event_details.get('time', 'N/A')}\n"

        attendees = event_details.get('attendees', [])
        if attendees:
            text += f"Attendees: {', '.join(attendees)}\n"

        buttons = [
            {'text': 'Confirm', 'callback_data': f"cs|{task_id}|confirm|1"},
            {'text': 'Cancel', 'callback_data': f"cs|{task_id}|cancel|0"}
        ]

        return self.send_inline_buttons(
            chat_id=chat_id,
            text=text,
            buttons=buttons,
            columns=2
        )
