#!/bin/bash
# check-timezone.sh - Check user timezone via n8n webhook with automatic context

set -e

# Get values from OpenClaw context
USER_ID="5127607280"
CHAT_ID="${1:-5127607280}"  # Pass as arg or default to user_id
BOT_TOKEN="${2}"  # Must be passed or set as env var
TIMEZONE="${3:-UTC}"  # Default to UTC if not specified
IS_UPDATE="${4:-false}"  # Default to false (checking)

# Generate task_id
TASK_ID="tz_$(date +%s)000"

# Validate bot_token
if [ -z "$BOT_TOKEN" ]; then
  echo "Error: BOT_TOKEN not provided"
  echo "Usage: $0 [chat_id] [bot_token] [timezone] [is_update]"
  echo "Or set BOT_TOKEN environment variable"
  exit 1
fi

# Build JSON payload
PAYLOAD=$(cat <<EOF
{
  "user_id": "$USER_ID",
  "chat_id": "$CHAT_ID",
  "bot_token": "$BOT_TOKEN",
  "timezone": "$TIMEZONE",
  "is_update": $IS_UPDATE,
  "task_id": "$TASK_ID"
}
EOF
)

echo "Calling timezone webhook..."
echo "Payload:"
echo "$PAYLOAD" | jq .

# Make the request
curl -s -X POST https://shpilman.app.n8n.cloud/webhook/timezone-agent \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
