---
name: padel-booking
description: Book padel courts via interactive Telegram quiz. Parse user messages for city, venue, date, time, duration, court type. Fetches venues from Airtable, checks calendar conflicts, collects all booking data.
---

# Padel Booking Agent

Book padel courts using an interactive Telegram quiz.

---

## STEP 1: PARSE USER MESSAGE FIRST

**BEFORE running any script, extract these from the user's message:**

### City Detection

| If user says | City key |
|--------------|----------|
| "Dubai", "dubai" | `Dubai` |
| "Belgrade", "belgrade" | `Belgrade` |
| "Lisbon", "lisbon" | `Lisbon` |
| "Tel Aviv", "tel aviv" | `Tel Aviv` |
| "Jurmala", "jurmala" | `Jurmala` |

### Venue Detection

If user names a specific venue (e.g., "Central Padel", "Padel 360"), pass it as `--venue`.

### Date/Time Detection

| If user says | Convert to |
|--------------|------------|
| "tomorrow" | Tomorrow's date YYYY-MM-DD |
| "next Tuesday" | Next Tuesday YYYY-MM-DD |
| "6pm", "18:00" | `--time 18:00` |
| "7:30pm" | `--time 19:30` |

### Duration Detection

| If user says | Argument |
|--------------|----------|
| "1 hour", "1hr", "1h" | `--duration 1hr` |
| "1.5 hour", "90 min", "hour and a half" | `--duration 1.5hr` |
| "2 hours", "2hr", "2h" | `--duration 2hr` |
| *(not mentioned)* | *(omit, defaults to 1.5hr)* |

### Court Type Detection

| If user says | Argument |
|--------------|----------|
| "indoor", "inside" | `--court_type indoor` |
| "outdoor", "outside" | `--court_type outdoor` |
| *(not mentioned)* | *(omit, defaults to any)* |

### Players Detection

| If user says | Argument |
|--------------|----------|
| "doubles", "4 players", "4 people" | `--players 4` |
| "singles", "2 players", "just us two" | `--players 2` |
| *(not mentioned)* | *(omit, defaults to 4)* |

---

## STEP 2: RUN THE QUIZ SCRIPT

```bash
python3 /root/.openclaw/workspace/agents/padel/scripts/padel_quiz.py start \
  --task_id "padel_$(date +%s)" \
  --chat_id "CHAT_ID" \
  --city "Dubai" \
  --venue "Central Padel" \
  --date "2026-04-03" \
  --time "18:00" \
  --duration "1.5hr" \
  --court_type "indoor" \
  --players "4"
```

**Only include flags you detected.** The quiz will ask for missing info via buttons.

| Argument | Required | Description |
|----------|----------|-------------|
| `--task_id` | Yes | Unique ID (use `padel_$(date +%s)`) |
| `--chat_id` | Yes | Telegram chat ID |
| `--city` | No | Detected city name |
| `--venue` | No | Detected venue name |
| `--date` | No | Date YYYY-MM-DD |
| `--time` | No | Time HH:MM (24hr) |
| `--duration` | No | `1hr`, `1.5hr`, `2hr` |
| `--court_type` | No | `indoor`, `outdoor`, `any` |
| `--players` | No | `2` or `4` |

---

## STEP 3: BE SILENT

After running the script, respond with ONLY: `ANNOUNCE_SKIP`

**DO NOT:**
- Explain what you did
- Summarize the request
- List the steps
- Say "I've started the quiz..."

**DO:** Run the script, then say `ANNOUNCE_SKIP`

---

## Callback Handling

Quiz button clicks are handled **automatically** by the sam-callbacks plugin (padel: namespace).
You do NOT need to handle callbacks manually.

If you see `callbackData` containing `padel:`, the plugin already handled it.

---

## Examples

### Example 1: "Book padel tomorrow 6pm in Dubai"

Detected: city=Dubai, date=tomorrow, time=18:00

```bash
python3 /root/.openclaw/workspace/agents/padel/scripts/padel_quiz.py start \
  --task_id "padel_$(date +%s)" \
  --chat_id "CHAT_ID" \
  --city "Dubai" \
  --date "2026-04-03" \
  --time "18:00"
```
Then: `ANNOUNCE_SKIP`

### Example 2: "Padel at Central Padel Friday 7pm 2 hours indoor"

Detected: venue=Central Padel, city=Dubai (inferred), date=Friday, time=19:00, duration=2hr, court=indoor

```bash
python3 /root/.openclaw/workspace/agents/padel/scripts/padel_quiz.py start \
  --task_id "padel_$(date +%s)" \
  --chat_id "CHAT_ID" \
  --city "Dubai" \
  --venue "Central Padel" \
  --date "2026-04-04" \
  --time "19:00" \
  --duration "2hr" \
  --court_type "indoor"
```
Then: `ANNOUNCE_SKIP`

### Example 3: "Book padel"

Detected: nothing specific

```bash
python3 /root/.openclaw/workspace/agents/padel/scripts/padel_quiz.py start \
  --task_id "padel_$(date +%s)" \
  --chat_id "CHAT_ID"
```
Then: `ANNOUNCE_SKIP`

Quiz will ask for city, then venue, then settings via buttons.

### Example 4: "Padel in Belgrade Saturday morning singles"

Detected: city=Belgrade, date=Saturday, time=09:00 (morning), players=2

```bash
python3 /root/.openclaw/workspace/agents/padel/scripts/padel_quiz.py start \
  --task_id "padel_$(date +%s)" \
  --chat_id "CHAT_ID" \
  --city "Belgrade" \
  --date "2026-04-05" \
  --time "09:00" \
  --players "2"
```
Then: `ANNOUNCE_SKIP`

---

## Available Cities

| City | Airtable Table |
|------|---------------|
| Dubai | DubaiPriority (priority-sorted) |
| Belgrade | Belgrade |
| Lisbon | Lisbon |
| Tel Aviv | Tel Aviv |
| Jurmala | Jurmala |

---

## CRITICAL RULES

1. **PARSE FIRST** - Extract city/venue/date/time/duration/court/players BEFORE running script
2. **BE SILENT** - After script, say ONLY `ANNOUNCE_SKIP`
3. **USE python3** - Not `python`
4. **INCLUDE FLAGS** - If you detect any value, ADD the argument
5. **DATE FORMAT** - Always YYYY-MM-DD
6. **TIME FORMAT** - Always HH:MM (24-hour)
7. **DON'T HANDLE CALLBACKS** - Plugin handles padel: buttons automatically
8. **NO HARDCODED IDS** - Always use `padel_$(date +%s)` for task_id

---

**User Timezone:** Europe/Berlin (UTC+1, or UTC+2 during DST)
