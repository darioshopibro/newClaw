---
name: calendar
description: Schedule calendar events via interactive quiz. Parse user messages AND OCR screenshots for meeting type, duration, timezone. Converts timezones to Berlin. Handles Google Calendar, contacts lookup, conflict detection.
---

# Calendar Skill

Schedule calendar events using an interactive Telegram quiz.

---

## ⚠️ CONTACT SEARCH FLOW (CRITICAL!) ⚠️

**When user mentions a NAME (e.g., "schedule meeting with Dario"):**

### Step 1: Search for the Contact

Use the contact-search skill to find matching contacts:

```bash
python3 /root/.openclaw/workspace/skills/contact-search/scripts/search_google.py --query "Dario" --max 10
```

### Step 2: Handle Search Results

| Result | Action |
|--------|--------|
| **0 contacts** | Create event without attendee, or ask user |
| **1 contact** | Pass that contact to quiz (auto-selected) |
| **2+ contacts** | Pass ALL contacts to quiz for user selection |

### Step 3: Pass Contacts to Quiz

**For multiple contacts (user must choose):**

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Meeting with Dario" \
  --date "2026-03-20" \
  --time "15:00" \
  --contacts '[{"name": "Dario Amodei", "email": "dario@anthropic.com"}, {"name": "Dario Smith", "email": "dsmith@gmail.com"}]'
```

The quiz will:
1. Show contact selection buttons (Step 1)
2. After user selects → show settings (Step 2)
3. After proceed → create event

**For single contact (auto-selected):**

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Meeting with Dario Amodei" \
  --date "2026-03-20" \
  --time "15:00" \
  --contacts '[{"name": "Dario Amodei", "email": "dario@anthropic.com"}]'
```

Quiz skips contact selection (only 1 contact), goes directly to settings.

### Example Flow: "schedule meeting with Dario tomorrow 3pm"

1. **Search:** `python3 search_google.py --query "Dario"`
2. **Result:** 3 contacts found
3. **Quiz:**
   ```bash
   python3 simple_quiz.py start \
     --task_id "cal_$(date +%s)" \
     --chat_id "5127607280" \
     --title "Meeting with Dario" \
     --date "2026-03-20" \
     --time "15:00" \
     --contacts '[{"name": "Dario A", "email": "a@x.com"}, {"name": "Dario B", "email": "b@y.com"}, {"name": "Dario C", "email": "c@z.com"}]'
   ```
4. **User sees:**
   ```
   📅 Schedule Event

   Title: Meeting with Dario
   Date: 2026-03-20
   Time: 15:00

   👥 Multiple contacts found (3)
   Select which one to invite:

   [Dario A (a@x.com)]
   [Dario B (b@y.com)]
   [Dario C (c@z.com)]
   [❌ Cancel]
   ```
5. **User clicks "Dario B"** → Shows settings step
6. **User configures & clicks Proceed** → Event created with Dario B as attendee

Then: `ANNOUNCE_SKIP`

---

## ⚠️ STEP 1: PARSE USER MESSAGE FIRST ⚠️

**BEFORE running any script, scan the user's message for these keywords:**

### Meeting Type Detection

| If user says ANY of these | Add this argument |
|---------------------------|-------------------|
| "online", "call", "video", "zoom", "teams", "virtual", "remote", "meet", "google meet" | `--type online` |
| "in-person", "in person", "lunch", "coffee", "dinner", "breakfast", "office", "face to face", "f2f" | `--type in-person` |
| *(none of the above)* | *(omit --type, defaults to in-person)* |

### Duration Detection

| If user says ANY of these | Add this argument |
|---------------------------|-------------------|
| "30 min", "30m", "30 minutes", "half hour", "30min", "30-min" | `--duration 30m` |
| "1 hour", "1hr", "1h", "1 h", "one hour", "an hour", "1hour", "60 min", "60m" | `--duration 1hr` |
| "1.5 hour", "1.5hr", "1.5h", "1.5 h", "90 min", "90 minutes", "90m", "hour and a half" | `--duration 1.5hr` |
| "2 hour", "2hr", "2h", "2 h", "two hour", "2hours", "2 hours", "120 min", "120m" | `--duration 2hr` |
| *(no duration mentioned)* | *(omit --duration, defaults to 1hr)* |

**IMPORTANT:** Check for these keywords BEFORE calling the script!

---

## ⚠️ HANDLING OCR / SCREENSHOT INPUT ⚠️

When input contains `Extracted content from image:` or looks like OCR text (messy, multi-line, chat format), you must parse it to extract scheduling details.

### What to Extract from OCR

| Field | How to find it |
|-------|----------------|
| **Name** | Who are they meeting? Look for names in the conversation |
| **Date** | "thursday", "march 20", "tomorrow", "next week" |
| **Time** | "3pm", "15:00", "at 3", "around 3pm" |
| **Timezone** | "PST", "EST", "PT", "ET", "GMT", "CET" - **CONVERT TO BERLIN!** |
| **Duration** | "30 min", "1 hour", "2h" (same keywords as above) |
| **Type** | "call", "video", "zoom", "lunch", "coffee" (same keywords as above) |

### Timezone Conversion (CRITICAL!)

User timezone is **Europe/Berlin**. Convert ALL times to Berlin:

| Original | Berlin Time | Notes |
|----------|-------------|-------|
| 3pm PST | 00:00 +1 day | PST is UTC-8, Berlin is UTC+1 (9hr diff) |
| 3pm EST | 21:00 same day | EST is UTC-5, Berlin is UTC+1 (6hr diff) |
| 3pm GMT | 16:00 same day | GMT is UTC+0, Berlin is UTC+1 (1hr diff) |
| 3pm CET | 15:00 same day | CET = Berlin, no conversion |

**If no timezone mentioned** → assume Berlin timezone, use time as-is.

### OCR Example 1: Chat screenshot

Input:
```
Extracted content from image:
hey can we meet thursday at 3pm PST for a quick call?
sure that works for me
great see you then!
```

You extract:
- Name: (unknown - may need to ask or use "Meeting")
- Date: Thursday → 2026-03-20
- Time: 3pm PST → **00:00 Berlin (next day: 2026-03-21)**
- Type: "call" → `--type online`
- Duration: not specified

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Meeting" \
  --date "2026-03-21" \
  --time "00:00" \
  --type online
```
Then: `ANNOUNCE_SKIP`

### OCR Example 2: With name visible

Input:
```
Extracted content from image:
John Smith
Let's do a 30 min video call tomorrow at 2pm EST
```

You extract:
- Name: John Smith
- Date: tomorrow → 2026-03-20
- Time: 2pm EST → **20:00 Berlin**
- Type: "video call" → `--type online`
- Duration: "30 min" → `--duration 30m`

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Video call with John Smith" \
  --date "2026-03-20" \
  --time "20:00" \
  --type online \
  --duration 30m
```
Then: `ANNOUNCE_SKIP`

### OCR Example 3: Lunch meeting, no timezone

Input:
```
Extracted content from image:
Sarah: lunch next Tuesday at 12:30?
Me: perfect!
```

You extract:
- Name: Sarah
- Date: next Tuesday → 2026-03-25
- Time: 12:30 (no timezone = Berlin) → **12:30**
- Type: "lunch" → `--type in-person`

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Lunch with Sarah" \
  --date "2026-03-25" \
  --time "12:30" \
  --type in-person
```
Then: `ANNOUNCE_SKIP`

### If info is missing

| Missing | Action |
|---------|--------|
| Name | Use "Meeting" as title |
| Date | Cannot proceed - quiz won't work without date |
| Time | Cannot proceed - quiz won't work without time |
| Timezone | Assume Berlin |
| Duration | Omit flag (defaults to 1hr) |
| Type | Omit flag (defaults to in-person) |

---

## ⚠️ STEP 2: BE SILENT ⚠️

After running any calendar script, respond with ONLY: `ANNOUNCE_SKIP`

**DO NOT:**
- Explain what you did
- Summarize the request
- List the steps taken
- Say "I've started the quiz..."

**DO:** Just run the script, then say `ANNOUNCE_SKIP`

---

## Scripts Location

All scripts: `{baseDir}/scripts/`

| Script | Purpose |
|--------|---------|
| `simple_quiz.py` | **PRIMARY** - Start quiz for event creation |
| `check_conflicts.py` | Check calendar conflicts |
| `search_contacts.py` | Search Google Contacts by name |

---

## Start Quiz (Event Creation)

**This is the ONLY way to create events.**

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "CHAT_ID" \
  --title "Meeting with NAME" \
  --date "YYYY-MM-DD" \
  --time "HH:MM" \
  --type online \
  --duration 2hr
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--task_id` | Yes | Unique ID (use `cal_$(date +%s)`) |
| `--chat_id` | Yes | Telegram chat ID |
| `--title` | Yes | Event title |
| `--date` | Yes | Date in YYYY-MM-DD |
| `--time` | Yes | Time in HH:MM (24hr) |
| `--type` | No | `online` or `in-person` (detected from message) |
| `--duration` | No | `30m`, `1hr`, `1.5hr`, `2hr` (detected from message) |
| `--attendee_email` | No | Email to invite |

**After starting:** Say `ANNOUNCE_SKIP` and STOP. Quiz handles everything via buttons.

---

## Examples

### Example 1: "schedule meeting with Kelsi tomorrow at 1pm online 2 hours"

Detected: "online" → `--type online`, "2 hours" → `--duration 2hr`

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Meeting with Kelsi" \
  --date "2026-03-20" \
  --time "13:00" \
  --type online \
  --duration 2hr
```
Then: `ANNOUNCE_SKIP`

### Example 2: "30 min call with John Friday 10am"

Detected: "call" → `--type online`, "30 min" → `--duration 30m`

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Call with John" \
  --date "2026-03-21" \
  --time "10:00" \
  --type online \
  --duration 30m
```
Then: `ANNOUNCE_SKIP`

### Example 3: "lunch with Mike Tuesday 12:30"

Detected: "lunch" → `--type in-person`, no duration

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Lunch with Mike" \
  --date "2026-03-25" \
  --time "12:30" \
  --type in-person
```
Then: `ANNOUNCE_SKIP`

### Example 4: "meeting with Bob tomorrow 3pm"

Detected: nothing → no `--type`, no `--duration`

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Meeting with Bob" \
  --date "2026-03-20" \
  --time "15:00"
```
Then: `ANNOUNCE_SKIP`

### Example 5: "2h video call with Sarah next Monday 2pm"

Detected: "video call" → `--type online`, "2h" → `--duration 2hr`

```bash
python3 {baseDir}/scripts/simple_quiz.py start \
  --task_id "cal_$(date +%s)" \
  --chat_id "5127607280" \
  --title "Video call with Sarah" \
  --date "2026-03-24" \
  --time "14:00" \
  --type online \
  --duration 2hr
```
Then: `ANNOUNCE_SKIP`

---

## Check Conflicts

```bash
python3 {baseDir}/scripts/check_conflicts.py \
  --date "YYYY-MM-DD" \
  --time "HH:MM" \
  --duration 60
```

---

## Search Contacts

```bash
python3 {baseDir}/scripts/search_contacts.py --query "Name"
```

---

## Callback Handling

Quiz button clicks are handled **automatically** by middleware. You don't need to do anything.

When you see `callbackData` containing `quiz|` or `quiz_back|`, run:

```bash
python3 {baseDir}/scripts/simple_quiz.py handle \
  --callback_data "THE_CALLBACK_DATA" \
  --chat_id "CHAT_ID" \
  --message_id "MESSAGE_ID"
```

Then: `ANNOUNCE_SKIP`

---

## Calendar Reference

| Key | Calendar |
|-----|----------|
| `moses` | felix@mosescapital.com |
| `etg` | felix@emergingtravel.com |
| `family` | Family calendar |

---

## CRITICAL RULES

1. **PARSE FIRST** - Check user message for type/duration keywords BEFORE running script
2. **CONVERT TIMEZONES** - If OCR shows PST/EST/GMT, convert to Berlin time!
3. **BE SILENT** - After any script, say ONLY `ANNOUNCE_SKIP`
4. **USE QUIZ** - Never call `create_event.py` directly
5. **USE python3** - Not `python`
6. **INCLUDE FLAGS** - If you detect type or duration, ADD the arguments

---

**User Timezone:** Europe/Berlin (UTC+1, or UTC+2 during DST)
