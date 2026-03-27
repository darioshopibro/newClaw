# Agent Implementation: Handle CallbackQueryData

How agents should implement callback forwarding using CallbackQueryData from context.

## Detection

Check if `CallbackQueryData` exists in the agent's inbound context:

```javascript
if (context.CallbackQueryData) {
  // This is a button click - handle callback
}
```

## Extraction

Extract the required fields from CallbackQueryData:

```javascript
const {
  message_id,      // Telegram message ID (e.g., 12847293)
  callback_query_id, // Callback query ID
  callback_data,    // Button data (e.g., "cc|cal_123|1|4")
  chat_id          // Chat ID
} = context.CallbackQueryData;
```

## Webhook Forwarding

POST to n8n webhook with extracted data:

```bash
#!/bin/bash

# Extract from context
MESSAGE_ID="${1}" # context.CallbackQueryData.message_id
CALLBACK_QUERY_ID="${2}" # context.CallbackQueryData.callback_query_id
CALLBACK_DATA="${3}" # context.CallbackQueryData.callback_data
CHAT_ID="${4}" # context.CallbackQueryData.chat_id

BOT_TOKEN="8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"
USER_ID="5127607280"

# POST to webhook
curl -s -X POST https://shpilman.app.n8n.cloud/webhook/callback-handler \
  -H "Content-Type: application/json" \
  -d "{
    \"callback_data\": \"$CALLBACK_DATA\",
    \"message_id\": \"$MESSAGE_ID\",
    \"callback_query_id\": \"$CALLBACK_QUERY_ID\",
    \"chat_id\": \"$CHAT_ID\",
    \"bot_token\": \"$BOT_TOKEN\",
    \"user_id\": \"$USER_ID\"
  }"
```

## Python Implementation

```python
import requests
import json

def handle_callback(context):
    # Check if this is a callback
    if not context.get("CallbackQueryData"):
        return None
    
    callback_data = context["CallbackQueryData"]
    
    # Extract fields
    message_id = callback_data["message_id"]
    callback_query_id = callback_data["callback_query_id"]
    callback_data_str = callback_data["callback_data"]
    chat_id = callback_data["chat_id"]
    
    # Forward to webhook
    payload = {
        "callback_data": callback_data_str,
        "message_id": str(message_id),
        "callback_query_id": callback_query_id,
        "chat_id": str(chat_id),
        "bot_token": "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs",
        "user_id": "5127607280"
    }
    
    response = requests.post(
        "https://shpilman.app.n8n.cloud/webhook/callback-handler",
        json=payload
    )
    
    return response.json()
```

## Response Behavior

**After forwarding:**
- Do NOT send a reply message to the user
- n8n handles all Telegram responses
- Return `NO_REPLY` to prevent duplicate messages
- The webhook handles message editing, acknowledgment, etc.

## Complete Agent Pattern

```typescript
// Detect callback in inbound context
if (inboundContext.CallbackQueryData) {
  const cb = inboundContext.CallbackQueryData;
  
  // Forward to webhook
  await fetch('https://shpilman.app.n8n.cloud/webhook/callback-handler', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      callback_data: cb.callback_data,
      message_id: cb.message_id,
      callback_query_id: cb.callback_query_id,
      chat_id: cb.chat_id,
      bot_token: '8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs',
      user_id: '5127607280'
    })
  });
  
  // Stay silent - n8n sends the response
  return 'NO_REPLY';
}

// Handle regular messages...
```

## Field Reference

| Field | Type | Example | Source |
|-------|------|---------|--------|
| `callback_data` | string | `"cc\|cal_123\|1\|4"` | Button click value |
| `message_id` | number | `12847293` | Telegram message ID |
| `callback_query_id` | string | `"abc123xyz"` | Callback query ID |
| `chat_id` | number | `5127607280` | Telegram chat ID |
| `bot_token` | string | `"829...kxKs"` | OpenclawSam bot token |
| `user_id` | string | `"5127607280"` | Telegram user ID |
