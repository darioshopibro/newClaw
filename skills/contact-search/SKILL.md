---
name: contact-search
description: Smart contact search with voice variation matching, VIP lookup, and scoring. Used by CalendarContactAgent and any other agent needing contact lookup.
---

# Contact Search Skill

Search contacts intelligently with voice variation matching and VIP support.

## How to Use This Skill

As the agent, YOU generate variations based on the rules below, then call the search script multiple times if needed.

## Voice Variation Rules

When searching for a name, THINK about these common mishearing patterns:

### Cyrillic/Russian Names
| Original | Variations to Try |
|----------|-------------------|
| Yulia | Julia, Yuliya |
| Zhanna | Janna, Zanna |
| Zhenya | Jenya, Genya, Evgeny |
| Sergey | Sergei, Serge |

### Common Patterns
| Pattern | Example |
|---------|---------|
| `Zh` ↔ `J` | Zhenya → Jenya |
| `Yu` ↔ `Ju` | Yulia → Julia |
| `-eva` ↔ `-ova` | Petrova → Petreova |
| `-sky` ↔ `-ski` | Brodsky → Brodzki |
| `i` ↔ `y` | Yuliya → Yuliia |
| `S` ↔ `Z` | Sasha → Zasha |
| Double letters | Anna → Ana, Alla → Ala |

### Arabic Names
| Pattern | Example |
|---------|---------|
| `Mohammed` variations | Mohamed, Muhammad, Mohamad |
| `Abdul` variations | Abdel, Abd |
| `Al-` prefix | Al-Rashid → Alrashid, Al Rashid |

### European Names
| Pattern | Example |
|---------|---------|
| German ü → u | Müller → Muller |
| Spanish ñ → n | Nuñez → Nunez |
| French accents | René → Rene |

## Search Process

1. **Check VIP First**
   - If input is a relationship word ("assistant", "wife", "boss"), check VIP contacts
   - VIP contacts are stored in `vip_contacts.json` or Supabase

2. **Generate Variations**
   - Apply relevant rules from above
   - For common names, generate 2-4 variations
   - For unique names, just search as-is

3. **Call Search Script**
   ```bash
   python3 /root/.openclaw/workspace/skills/contact-search/scripts/search_google.py \
     --query "Name" \
     --max 10
   ```

4. **Combine & Deduplicate**
   - Merge results from multiple searches
   - Remove duplicates by `resource_name`

5. **Score Results**

| Match Type | Base Score |
|------------|------------|
| Exact full name match | 95 |
| First name only match | 75 |
| Partial/fuzzy match | 60 |
| VIP contact | +10 bonus |

6. **Auto-Select Rules**
   - If exactly 1 contact with score >= 85: auto-select
   - If query was `full_name` type and 1 exact match: auto-select
   - Otherwise: return list for user selection

## Search Script

**Location:** `/root/.openclaw/workspace/skills/contact-search/scripts/search_google.py`

**Input:**
```bash
python3 search_google.py --query "John" --max 10
```

**Output:**
```json
{
  "success": true,
  "contacts": [
    {
      "resource_name": "people/c1234567890",
      "name": "John Doe",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "organization": "Acme Inc",
      "title": "CEO"
    }
  ],
  "count": 1,
  "query": "John"
}
```

## VIP Contacts

VIP contacts have special relationships (assistant, family, etc.).

**Local file:** `/root/.openclaw/workspace/skills/contact-search/vip_contacts.json`

```json
{
  "vips": [
    {"keyword": "assistant", "name": "Yulia", "contact_id": "people/c123"},
    {"keyword": "wife", "name": "Anna", "contact_id": "people/c456"}
  ]
}
```

When user says "call my assistant", match keyword "assistant" → return Yulia.

## Example Agent Thinking

**User says:** "Find Yulia's number"

**Agent thinks:**
1. "Yulia" could be heard as "Julia" or "Yuliya" (Russian name, Yu↔Ju rule)
2. First, search "Yulia"
3. If few results, also search "Julia"
4. Combine, dedupe, score
5. If one high-confidence match, auto-select
6. Otherwise, show list

**Agent calls:**
```bash
python3 search_google.py --query "Yulia" --max 10
python3 search_google.py --query "Julia" --max 10
```

**Agent combines results, returns:**
```json
{
  "auto_select": true,
  "contact": {
    "name": "Yulia Yakovleva",
    "email": "yulia@example.com",
    "phone": "+79161234567"
  }
}
```

## Return Format

Always return structured JSON:

**Single result (auto-selected):**
```json
{
  "auto_select": true,
  "contact": { ... }
}
```

**Multiple results (user must choose):**
```json
{
  "auto_select": false,
  "contacts": [ ... ],
  "message": "Found 3 contacts matching 'John'. Which one?"
}
```

**No results:**
```json
{
  "auto_select": false,
  "contacts": [],
  "message": "No contacts found matching 'Xyz'"
}
```

---

## Dependencies

- Google People API (via gcloud ADC)
- Python 3

## Environment

Uses same gcloud ADC as calendar skill.
