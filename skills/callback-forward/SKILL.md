---
name: callback-handler
description: Handle Telegram button clicks (callback_query) DIRECTLY - no forwarding to n8n. Processes quiz navigation, settings toggles, and all callback patterns locally using Python scripts. Identical logic to n8n QUIZ.json and CalendarSettingsHandler.
---

# Callback Handler Skill

Process Telegram callback query events (button clicks) DIRECTLY in OpenClaw.

**NO FORWARDING TO N8N** - Everything is processed locally by Python scripts.

## What are Callback Queries?

Callback queries are triggered when users click inline buttons in Telegram messages:
- User clicks "Confirm" button → callback_query event fires
- User clicks option in quiz → callback_query event fires
- User clicks Prev/Next for pagination → callback_query event fires

## Callback Patterns

| Pattern | Description | Handler |
|---------|-------------|---------|
| `quiz\|taskId\|questionIndex\|answerIndex` | User selects quiz option | quiz_progress.py |
| `quiz_nav\|taskId\|questionIndex\|page` | User clicks Prev/Next | quiz_navigate.py |
| `quiz_back\|taskId\|targetStep` | User clicks ⬅️ Back | quiz_back.py |
| `cs\|taskId\|field\|value` | Calendar settings toggle | settings_handler.py |
| `noop` / `ignore` | No action (page indicator) | Just answer callback |

## How to Use

When agent detects `CallbackQueryData` in context, run:

```bash
python3 /root/.openclaw/workspace/skills/callback-forward/scripts/handle_callback.py \
  "$callback_data" \
  "$chat_id" \
  "$message_id" \
  "$callback_query_id"
```

Then return `NO_REPLY` - the script handles everything.

## Agent Context

When a button is clicked, the agent receives:

```json
{
  "CallbackQueryData": {
    "message_id": 12847293,
    "callback_query_id": "abc123xyz",
    "callback_data": "quiz|task123|2|5",
    "chat_id": 5127607280
  }
}
```

## Agent Logic

```
IF context contains CallbackQueryData:
  1. Extract: callback_data, chat_id, message_id, callback_query_id
  2. Run: python3 handle_callback.py <callback_data> <chat_id> <message_id> <callback_query_id>
  3. Return: NO_REPLY
```

## Scripts

All scripts in `/root/.openclaw/workspace/skills/callback-forward/scripts/`:

### handle_callback.py
Main router - parses callback_data pattern and calls appropriate handler.

### quiz_progress.py
Handles `quiz|taskId|questionIndex|answerIndex`:
1. Lookup quiz session from Supabase (task_temp_data)
2. Get options for current question
3. Save answer
4. If last question → show completion
5. Else → build next question with pagination
6. Call Telegram editMessageText API
7. Update Supabase state

### quiz_navigate.py
Handles `quiz_nav|taskId|questionIndex|page`:
1. Lookup quiz session
2. Get options from cache
3. Paginate to new page
4. Rebuild keyboard with back button + navigation
5. Call Telegram editMessageReplyMarkup API (buttons only)

### quiz_back.py
Handles `quiz_back|taskId|targetStep`:
1. Lookup quiz session
2. Clear answers from targetStep onwards
3. Rebuild options for targetStep
4. Call Telegram editMessageText API

### settings_handler.py
Handles `cs|taskId|field|value`:
1. Lookup session
2. Toggle setting (calendar/duration/type)
3. Rebuild 3-column button layout
4. Call Telegram editMessageReplyMarkup API

## Supabase Storage

**Table:** `task_temp_data`

**Filter:** `task_id = ? AND data_type = 'quiz_session'`

**Data structure:**
```json
{
  "questions": [
    {"id": 1, "text": "Which venue?", "type": "venue_choice", "options": [...]},
    {"id": 2, "text": "Which time?", "type": "time_choice", "options": [...]}
  ],
  "answers": {"1": "Central Padel", "2": "14:00"},
  "current_step": 2,
  "context": "📅 Booking for...",
  "venues_by_city": {"Dubai": [...], "Belgrade": [...]},
  "all_options_cache": {"1": [...], "2": [...]},
  "detected_city": "Dubai"
}
```

## Keyboard Layout

IDENTICAL to n8n:

```
Row 0: [⬅️] [Option A] [Option B]     ← Back button takes 1 slot (only if step > 1)
Row 1: [Option C] [Option D] [Option E]
Row 2: [Option F] [Option G] [Option H]
Row 3: [Option I]
─────────────────────────────────────────
Nav:   [⬅️ Prev] [📄 1/3] [Next ➡️]   ← Only if totalPages > 1
```

## Pagination

IDENTICAL to n8n:

```python
ITEMS_PER_PAGE = 9
total_pages = (len(all_options) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
start_idx = page * ITEMS_PER_PAGE
page_options = all_options[start_idx:start_idx + ITEMS_PER_PAGE]
```

## Telegram API Calls

| Action | API |
|--------|-----|
| New question / Back | `editMessageText` (text + buttons) |
| Pagination only | `editMessageReplyMarkup` (buttons only) |

## Environment Variables

Required:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key

## Dependencies

```
pip install supabase requests
```

## Flow Diagram

```
User clicks button
      ↓
OpenClaw receives callback_query
      ↓
Agent detects CallbackQueryData in context
      ↓
Agent runs: python3 handle_callback.py <args>
      ↓
handle_callback.py parses pattern
      ↓
Routes to appropriate handler (quiz_progress, quiz_navigate, etc.)
      ↓
Handler:
  - Lookups Supabase
  - Processes action
  - Updates Supabase
  - Calls Telegram API (editMessageText or editMessageReplyMarkup)
      ↓
Agent returns NO_REPLY
      ↓
INSTANT - no LLM calls for button clicks
```

## Message Text Format

IDENTICAL to n8n:

```
📅 Booking padel for today at 18:00

✅ Which venue?: Central Padel
✅ Which location?: Dubai Marina

📋 Step 3 of 4: Which time slot?
```

---

**Last Updated:** 2026-03-13
