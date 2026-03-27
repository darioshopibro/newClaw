---
name: contact
description: Contact CRUD operations - Create, Update, Delete contacts in Google Contacts. ALWAYS use quiz for confirmation before adding.
---

# Contact CRUD Skill

Create, Update, and Delete contacts in Google Contacts.

---

## ⚠️ CRITICAL: ALWAYS USE QUIZ BEFORE ADDING ⚠️

**NEVER call `create_contact.py` directly!**
**ALWAYS use `contact_quiz.py` to show confirmation buttons first.**

| Scenario | Use This Script |
|----------|-----------------|
| New contact (no duplicate) | `contact_quiz.py confirm` |
| Duplicate found | `contact_quiz.py start` |
| Update existing | `update_contact.py` |
| Delete contact | `delete_contact.py` |

**Why?** The quiz shows Telegram buttons `[✅ Add] [❌ Cancel]`. User clicks to confirm. Without the quiz, user has no way to verify or cancel.

---

## Scripts Location

All scripts: `/root/.openclaw/workspace/skills/contact/scripts/`

| Script | Purpose |
|--------|---------|
| `contact_quiz.py confirm` | Confirmation quiz (new contact) |
| `contact_quiz.py start` | Merge quiz (duplicate found) |
| `contact_quiz.py handle` | Handle button callbacks |
| `update_contact.py` | Update existing contact |
| `delete_contact.py` | Delete contact |
| `create_contact.py` | ⚠️ INTERNAL ONLY - called by quiz, never directly! |

---

## Create Contact Flow

### Step 1: Search for Duplicates

```bash
python3 /root/.openclaw/workspace/skills/contact-search/scripts/search_google.py \
  --query "John Doe" \
  --max 10
```

### Step 2A: No Duplicate Found → Confirmation Quiz

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/contact_quiz.py confirm \
  --task_id "contact_$(date +%s)" \
  --chat_id "5127607280" \
  --first_name "John" \
  --last_name "Doe" \
  --phone "+1234567890" \
  --email "john@example.com"
```

**Then say ONLY:** `ANNOUNCE_SKIP`

**This shows:**
```
📇 Add this contact?

👤 John Doe
📱 +1234567890
📧 john@example.com

[✅ Add] [❌ Cancel]
```

### Step 2B: Duplicate Found → Merge Quiz

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/contact_quiz.py start \
  --task_id "contact_$(date +%s)" \
  --chat_id "5127607280" \
  --existing_id "people/c1234567890" \
  --existing_name "John Doe" \
  --existing_email "john@old.com" \
  --existing_phone "+111" \
  --new_email "john@new.com" \
  --new_phone "+222" \
  --new_first_name "John" \
  --new_last_name "Doe"
```

**Then say ONLY:** `ANNOUNCE_SKIP`

**This shows:**
```
📇 Similar contact found: John Doe

What to add to existing contact?

✅ Email: john@new.com
⬜ Phone: +222

[Toggle Email] [Toggle Phone]
[Create New] [Merge] [Cancel]
```

---

## Confirmation Quiz Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--task_id` | Yes | Unique ID (use `contact_$(date +%s)`) |
| `--chat_id` | Yes | Telegram chat ID |
| `--first_name` | No | First name |
| `--last_name` | No | Last name |
| `--phone` | No | Phone number |
| `--email` | No | Email address |

---

## Merge Quiz Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--task_id` | Yes | Unique ID |
| `--chat_id` | Yes | Telegram chat ID |
| `--existing_id` | Yes | Resource name of existing contact |
| `--existing_name` | Yes | Display name of existing contact |
| `--existing_email` | No | Current email |
| `--existing_phone` | No | Current phone |
| `--new_email` | No | New email to potentially add |
| `--new_phone` | No | New phone to potentially add |
| `--new_first_name` | No | First name (for create new option) |
| `--new_last_name` | No | Last name (for create new option) |

---

## Update Contact

Update existing contact fields.

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/update_contact.py \
  --contact_id "people/c1234567890" \
  --email "new@example.com" \
  --phone "+9876543210"
```

| Argument | Required | Description |
|----------|----------|-------------|
| `--contact_id` | Yes | Resource name (people/c...) |
| `--first_name` | No | New first name |
| `--last_name` | No | New last name |
| `--email` | No | New email |
| `--phone` | No | New phone |
| `--company` | No | New company |
| `--title` | No | New job title |
| `--notes` | No | New notes |

**Output:**
```json
{
  "success": true,
  "contact_id": "people/c1234567890",
  "updated_fields": ["email", "phone"]
}
```

---

## Delete Contact

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/delete_contact.py \
  --contact_id "people/c1234567890"
```

**Output:**
```json
{
  "success": true,
  "deleted": "people/c1234567890"
}
```

---

## Callback Handling

When you see `callbackData` containing `contact|`:

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/contact_quiz.py handle \
  --callback_data "THE_CALLBACK_DATA" \
  --chat_id "CHAT_ID" \
  --message_id "MESSAGE_ID"
```

**Then say ONLY:** `ANNOUNCE_SKIP`

### Callback Patterns

| Pattern | Action |
|---------|--------|
| `contact\|taskId\|add` | Confirm add (from confirm quiz) |
| `contact\|taskId\|cancel` | Cancel operation |
| `contact\|taskId\|te` | Toggle Email selection |
| `contact\|taskId\|tp` | Toggle Phone selection |
| `contact\|taskId\|confirm` | Confirm merge with selected fields |
| `contact\|taskId\|new` | Create as new contact (ignore duplicate) |

---

## Examples

### Example 1: Add New Contact (No Duplicate)

**User:** "Add contact John Doe +1234567890 john@example.com"

**Agent steps:**
1. Search for "John Doe"
2. No results found
3. Show confirmation quiz:

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/contact_quiz.py confirm \
  --task_id "contact_$(date +%s)" \
  --chat_id "5127607280" \
  --first_name "John" \
  --last_name "Doe" \
  --phone "+1234567890" \
  --email "john@example.com"
```

4. Say: `ANNOUNCE_SKIP`

### Example 2: Duplicate Found

**User:** "Add contact John Doe +9999999999 john@new.com"

**Agent steps:**
1. Search for "John Doe"
2. Found existing "John Doe" (people/c123) with email john@old.com
3. Show merge quiz:

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/contact_quiz.py start \
  --task_id "contact_$(date +%s)" \
  --chat_id "5127607280" \
  --existing_id "people/c123" \
  --existing_name "John Doe" \
  --existing_email "john@old.com" \
  --new_email "john@new.com" \
  --new_phone "+9999999999" \
  --new_first_name "John" \
  --new_last_name "Doe"
```

4. Say: `ANNOUNCE_SKIP`

### Example 3: Update Existing Contact

**User:** "Update Mike's email to mike@newcompany.com"

**Agent steps:**
1. Search for "Mike" → find people/c456
2. Update:

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/update_contact.py \
  --contact_id "people/c456" \
  --email "mike@newcompany.com"
```

3. Confirm update to user

### Example 4: Delete Contact

**User:** "Delete the contact for Old Client"

**Agent steps:**
1. Search for "Old Client" → find people/c789
2. Delete:

```bash
python3 /root/.openclaw/workspace/skills/contact/scripts/delete_contact.py \
  --contact_id "people/c789"
```

3. Confirm deletion to user

---

## State Storage

Quiz state stored in `/tmp/openclaw_contact/` as JSON files.

---

## CRITICAL RULES

1. **NEVER use create_contact.py directly** - Always use contact_quiz.py
2. **SEARCH FIRST** - Always check for duplicates before adding
3. **New contact → contact_quiz.py confirm**
4. **Duplicate found → contact_quiz.py start**
5. **After quiz → ANNOUNCE_SKIP** - Say nothing else
6. **USE python3** - Not `python`

---

## Dependencies

- Google People API (read+write via gcloud ADC)
- Python 3
- Telegram Bot API (for quiz messages)

---

## After Create: LinkedIn Enrichment

After contact is added via quiz callback, optionally search LinkedIn:

```bash
python3 linkedin_search.py --name "John Doe" --company "Acme Inc"
```

Returns LinkedIn profile URL if found.
