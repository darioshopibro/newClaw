"""
Supabase Client for task state management
"""

import os
import json
from datetime import datetime
from typing import Optional
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://qluqynpozzukaoxyuqou.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')


class SupabaseClient:
    def __init__(self):
        """Initialize Supabase client"""
        if not SUPABASE_KEY:
            raise ValueError("SUPABASE_SERVICE_KEY environment variable not set")
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ==================== task_temp_data ====================

    def get_temp_data(self, task_id: str) -> Optional[dict]:
        """Get temporary data for a task."""
        try:
            result = self.client.table('task_temp_data').select('*').eq('task_id', task_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            return {'error': str(e)}

    def set_temp_data(self, task_id: str, data: dict) -> dict:
        """Set or update temporary data for a task."""
        try:
            existing = self.get_temp_data(task_id)

            if existing and 'error' not in existing:
                # Update
                result = self.client.table('task_temp_data').update({
                    'data': json.dumps(data),
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('task_id', task_id).execute()
            else:
                # Insert
                result = self.client.table('task_temp_data').insert({
                    'task_id': task_id,
                    'data': json.dumps(data),
                    'created_at': datetime.utcnow().isoformat()
                }).execute()

            return {'success': True, 'task_id': task_id}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def delete_temp_data(self, task_id: str) -> dict:
        """Delete temporary data for a task."""
        try:
            self.client.table('task_temp_data').delete().eq('task_id', task_id).execute()
            return {'success': True, 'task_id': task_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ==================== user_settings ====================

    def get_user_settings(self, user_id: str) -> Optional[dict]:
        """Get user settings (timezone, preferences, etc.)."""
        try:
            result = self.client.table('user_settings').select('*').eq('user_id', user_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            return {'error': str(e)}

    def get_user_timezone(self, user_id: str, default: str = 'UTC') -> str:
        """Get user's timezone."""
        settings = self.get_user_settings(user_id)
        if settings and 'error' not in settings:
            return settings.get('timezone', default)
        return default

    # ==================== task_conversations ====================

    def add_conversation_message(
        self,
        task_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """Add a message to task conversation history."""
        try:
            result = self.client.table('task_conversations').insert({
                'task_id': task_id,
                'role': role,
                'content': content,
                'metadata': json.dumps(metadata) if metadata else None,
                'created_at': datetime.utcnow().isoformat()
            }).execute()

            return {'success': True, 'task_id': task_id}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_conversation_history(self, task_id: str, limit: int = 50) -> list:
        """Get conversation history for a task."""
        try:
            result = self.client.table('task_conversations').select('*').eq(
                'task_id', task_id
            ).order('created_at').limit(limit).execute()

            return result.data or []

        except Exception as e:
            return [{'error': str(e)}]
