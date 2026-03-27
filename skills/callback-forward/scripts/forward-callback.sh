#!/bin/bash
# forward-callback.sh - Extract CallbackQueryData from agent context and forward to webhook

# This script is called when a callback_query is detected
# It extracts the structured data from the agent's inbound context and forwards to n8n

# Usage: forward-callback.sh

# The agent context should include CallbackQueryData with:
# - message_id: actual Telegram message ID
# - callback_query_id: callback query ID
# - callback_data: button callback data  
# - chat_id: chat ID

# For now, this is a template. The actual extraction happens in the skill
# when it detects CallbackQueryData in the agent's inbound context.

BOT_TOKEN="8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
WEBHOOK_URL="https://shpilman.app.n8n.cloud/webhook/callback-handler"

# Extract from context (these would come from agent context in real usage)
MESSAGE_ID="${1:-0}"
CALLBACK_QUERY_ID="${2:-0}"
CALLBACK_DATA="${3:-}"
CHAT_ID="${4:-5127607280}"

if [ -z "$CALLBACK_DATA" ] || [ "$MESSAGE_ID" = "0" ]; then
  echo "ERROR: Missing callback data or message_id"
  exit 1
fi

# Forward to webhook
curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"callback_data\": \"$CALLBACK_DATA\",
    \"chat_id\": \"$CHAT_ID\",
    \"message_id\": \"$MESSAGE_ID\",
    \"callback_query_id\": \"$CALLBACK_QUERY_ID\",
    \"bot_token\": \"$BOT_TOKEN\",
    \"user_id\": \"5127607280\"
  }"

echo "✓ Forwarded to n8n"
