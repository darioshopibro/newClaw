---
name: timezone
description: Check or update user timezone via n8n webhook. Use when: (1) getting current user timezone, (2) updating user timezone, or (3) syncing timezone settings with n8n backend. Posts to shpilman.app.n8n.cloud webhook with user_id, chat_id, bot_token, and timezone data. Requires bot_token and chat_id for workflow response routing.
---

# Timezone Skill

Check and update user timezone settings via n8n automation.

## Quick Start

### Check Current Timezone

```bash
TASK_ID="tz_$(date +%s)000"
BOT_TOKEN="your_bot_token_here"
CHAT_ID="5127607280"

curl -X POST https://shpilman.app.n8n.cloud/webhook/timezone-agent \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"5127607280\",
    \"chat_id\": \"$CHAT_ID\",
    \"bot_token\": \"$BOT_TOKEN\",
    \"timezone\": \"UTC\",
    \"is_update\": false,
    \"task_id\": \"$TASK_ID\"
  }"
```

### Update Timezone

```bash
TASK_ID="tz_$(date +%s)000"
BOT_TOKEN="your_bot_token_here"
CHAT_ID="5127607280"

curl -X POST https://shpilman.app.n8n.cloud/webhook/timezone-agent \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"5127607280\",
    \"chat_id\": \"$CHAT_ID\",
    \"bot_token\": \"$BOT_TOKEN\",
    \"timezone\": \"Asia/Dubai\",
    \"is_update\": true,
    \"task_id\": \"$TASK_ID\"
  }"
```

## Webhook Endpoint

**URL:** `https://shpilman.app.n8n.cloud/webhook/timezone-agent`

**Method:** POST

**Content-Type:** application/json

## Request Schema

### Example: Check Current Timezone

```json
{
  "user_id": "5127607280",
  "chat_id": "5127607280",
  "bot_token": "123456789:ABCdefGHIjklmnoPQRstuvWXYZ",
  "timezone": "UTC",
  "is_update": false,
  "task_id": "tz_1710067200000"
}
```

### Example: Update Timezone

```json
{
  "user_id": "5127607280",
  "chat_id": "5127607280",
  "bot_token": "123456789:ABCdefGHIjklmnoPQRstuvWXYZ",
  "timezone": "Asia/Dubai",
  "is_update": true,
  "task_id": "tz_1710067200000"
}
```

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `user_id` | string | Yes | Always `5127607280` (Telegram user ID) |
| `chat_id` | string | Yes | Current Telegram chat ID (for response routing) |
| `bot_token` | string | Yes | Telegram bot token: `8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs` (OpenclawSam bot) |
| `timezone` | string | Yes | IANA timezone string (e.g., `Europe/Berlin`, `UTC`, `Asia/Dubai`) |
| `is_update` | boolean | Yes | `true` = update timezone, `false` = check current timezone |
| `task_id` | string | Yes | Generated as `"tz_" + current_timestamp_ms` (e.g., `"tz_1710067200000"`) |

## Common Timezones

- `Europe/Berlin` - Central European Time (CET/CEST)
- `Europe/London` - Greenwich Mean Time (GMT/BST)
- `America/New_York` - Eastern Time (EST/EDT)
- `America/Los_Angeles` - Pacific Time (PST/PDT)
- `Asia/Tokyo` - Japan Standard Time (JST)
- `Australia/Sydney` - Australian Eastern Time (AEST/AEDT)
- `UTC` - Coordinated Universal Time

[See full IANA timezone list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

## Implementation Notes

### Required Fields Explained

**bot_token**: Your Telegram bot token. The n8n workflow uses this to send responses back to your Telegram chat. Get it from @BotFather.

**chat_id**: Current Telegram chat ID where the response should be sent. In OpenClaw, this comes from the inbound message metadata.

**task_id**: Unique identifier for tracking. Generated as `"tz_" + current_timestamp_ms` for uniqueness.

### Agent Reply Behavior

**See:** [AGENT_PATTERN.md](references/AGENT_PATTERN.md) for complete calling pattern.

**TL;DR:** 
- If webhook returns `"ok": true` → Respond with `NO_REPLY` (n8n already posted to Telegram)
- If webhook fails or errors → Reply with error message

### task_id Generation

```bash
# Bash example
task_id="tz_$(date +%s)000"

# JavaScript example
const task_id = `tz_${Date.now()}`;
```

### Script Usage

Use the bundled script for easy calling with automatic context:

### Check Current Timezone

```bash
./scripts/check-timezone.sh "5127607280" "your_bot_token" "UTC" "false"
```

### Update Timezone

```bash
./scripts/check-timezone.sh "5127607280" "your_bot_token" "Asia/Dubai" "true"
```

### With Environment Variable

```bash
export BOT_TOKEN="your_bot_token"
./scripts/check-timezone.sh "5127607280" "$BOT_TOKEN" "Europe/Berlin" "true"
```

## Manual cURL Usage

```bash
#!/bin/bash

# Set your values
USER_ID="5127607280"
CHAT_ID="5127607280"  # From current conversation
BOT_TOKEN="123456789:ABCdefGHIjklmnoPQRstuvWXYZ"  # Your bot token
TIMEZONE="Asia/Dubai"  # Or UTC to check
IS_UPDATE="true"  # or false to check
TASK_ID="tz_$(date +%s)000"

# Make the request
curl -X POST https://shpilman.app.n8n.cloud/webhook/timezone-agent \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"chat_id\": \"$CHAT_ID\",
    \"bot_token\": \"$BOT_TOKEN\",
    \"timezone\": \"$TIMEZONE\",
    \"is_update\": $IS_UPDATE,
    \"task_id\": \"$TASK_ID\"
  }"
```

## Response & Agent Behavior

**Important:** The n8n workflow sends responses directly to Telegram via the bot_token and chat_id. 

**Agent should:**
- Call the webhook
- If `status: 200` → Stay silent (NO_REPLY). User receives response directly from n8n
- If webhook fails or returns error → Reply with error details

**Why:** Avoids duplicate messages. n8n already posted to Telegram, so agent should not echo the response.

### Webhook Response

The n8n webhook returns:
- HTTP `200` + message posted to Telegram on success
- Error details if timezone is invalid or workflow fails
- Includes task_id for request tracking
