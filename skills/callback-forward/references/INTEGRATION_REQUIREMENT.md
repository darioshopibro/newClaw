# Telegram Callback Integration Requirement

## Issue

When Telegram sends a button click (callback_query), OpenClaw needs to forward the **full callback_query object** including `callback_query.message.message_id` so agents can properly handle the callback.

## Required Structure

OpenClaw Telegram integration should pass this in inbound metadata:

```json
{
  "callback_query": {
    "id": "123456789",
    "data": "cc|cal_1773181162000|1|3",
    "message": {
      "message_id": 12847293,
      "chat": {
        "id": 5127607280,
        "type": "private"
      },
      "text": "Select a time:"
    }
  }
}
```

## What Agent Needs to Extract

```bash
callback_data="${CALLBACK_QUERY[data]}"              # "cc|cal_1773181162000|1|3"
message_id="${CALLBACK_QUERY[message.message_id]}"   # 12847293 (LARGE number)
chat_id="${CALLBACK_QUERY[message.chat.id]}"         # 5127607280
callback_query_id="${CALLBACK_QUERY[id]}"            # "123456789"
```

## Why This Matters

Without `callback_query.message.message_id`, the n8n workflow cannot:
- Edit the original message with updated buttons
- Track which message the button was on
- Provide consistent UX (e.g., edit message in-place vs send new message)

## Current Status

❌ OpenClaw Telegram integration currently does NOT forward full callback_query structure
- Agent only receives basic chat metadata
- Cannot access `message_id` for editing messages
- Callbacks cannot properly route to message edits

## Fix Required

Update OpenClaw Telegram plugin to:
1. Detect callback_query events
2. Forward full `callback_query` object in inbound metadata
3. Include all nested fields: `id`, `data`, `message.message_id`, `message.chat.id`

## For Now

Until OpenClaw integration is updated, agents cannot properly handle Telegram callbacks that need message editing. Callback forwarding works for stateless actions only.
