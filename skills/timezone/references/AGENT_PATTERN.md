---
name: timezone-call-pattern
description: Pattern for agents calling the timezone skill - detect success vs error and reply only on failure
---

# Timezone Skill: Agent Call Pattern

When an agent calls the timezone webhook, follow this pattern:

## Success Path (No Reply)

```bash
# Call webhook
RESPONSE=$(curl -s -X POST https://shpilman.app.n8n.cloud/webhook/timezone-agent ...)

# Check if successful (contains "ok":true or similar)
if echo "$RESPONSE" | jq -e '.ok' > /dev/null 2>&1; then
  # Webhook succeeded, n8n sent message to Telegram
  # Agent responds with: NO_REPLY
  exit 0
fi
```

## Error Path (Reply with Error)

```bash
# If webhook failed or returned error
if ! echo "$RESPONSE" | jq -e '.ok' > /dev/null 2>&1; then
  # Webhook failed
  echo "Timezone lookup failed: $(echo $RESPONSE | jq -r '.message')"
  exit 1
fi
```

## Complete Example

```bash
#!/bin/bash

BOT_TOKEN=$(cat /root/.openclaw/workspace/.secrets/telegram_bot_token)
TASK_ID="tz_$(date +%s)000"

RESPONSE=$(curl -s -X POST https://shpilman.app.n8n.cloud/webhook/timezone-agent \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"5127607280\",
    \"chat_id\": \"5127607280\",
    \"bot_token\": \"$BOT_TOKEN\",
    \"timezone\": \"UTC\",
    \"is_update\": false,
    \"task_id\": \"$TASK_ID\"
  }")

# Check for success
if echo "$RESPONSE" | jq -e '.ok' > /dev/null 2>&1; then
  # Success - n8n sent response to Telegram
  # Stay silent
  NO_REPLY
else
  # Error - report to user
  ERROR=$(echo "$RESPONSE" | jq -r '.message // "Unknown error"')
  echo "Timezone lookup failed: $ERROR"
fi
```

## Why This Pattern?

The n8n workflow handles Telegram messaging directly. If the agent also sends a reply, the user sees duplicate messages:

❌ **Bad (duplicate):**
- n8n posts: "Your timezone is Europe/Belgrade"
- Agent posts: "Europe/Belgrade"

✅ **Good (clean):**
- n8n posts: "Your timezone is Europe/Belgrade"
- Agent stays silent
