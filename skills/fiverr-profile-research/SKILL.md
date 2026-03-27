# Kenny's Fiverr Profile Research Skill (v2)

## Your Daily Job

Research Fiverr marketplace to find keyword gaps and competitor positioning for Dario's n8n automation gig.

**Time Required:** 20-30 minutes  
**Frequency:** Daily (1 PM Berlin time)  
**Output:** Markdown report + Telegram message

---

## Step 0: Preparation (Read Context Files)

Before starting research, read these reference files:
```
/root/.openclaw/workspace/brain/fiverr/FIVERR.md
/root/.openclaw/workspace/brain/fiverr/FIVERR-SEO.md
/root/.openclaw/workspace/brain/fiverr/KEYWORD-RESEARCH.md
```

**What you're looking for:**
- Current profile: Level 2, 228 reviews, $200-$1,500 pricing
- Main gig: 17 reviews, 5.0 stars, "n8n openclaw ai agent automation"
- Performance issue: Impressions dropped 40-50% (Feb 5 → Feb 25)
- Current tags: n8n, automation, AI, voice agent, chatbot, workflow, openclaw, agent

---

## Step 1: Research Competitors (Using web_search + web_fetch)

### 1a. Search for Top Competitors

**Use: web_search tool**

Run 3 separate searches:

**Search 1:** n8n automation experts
```
query: "fiverr n8n automation expert" OR "fiverr n8n workflows"
count: 5 results
```

**Search 2:** AI voice agents  
```
query: "fiverr voice automation AI agents" OR "fiverr AI voice calls"
count: 5 results
```

**Search 3:** Automations & Agents category
```
query: "site:fiverr.com category automations agents top rated"
count: 5 results
```

### 1b. Extract Competitor Details

**Use: web_fetch tool**

For top 3-5 competitors from searches, fetch their Fiverr gig pages:

**For each competitor, extract:**
- Gig title (exact)
- Tags (list all visible tags)
- Price (basic, standard, premium packages)
- Review count + rating
- Gig description (first 200 chars)
- Seller level + badge info
- Portfolio items (if visible)

**Format as JSON internally (don't share yet):**
```json
{
  "competitors": [
    {
      "seller": "competitor1",
      "title": "...",
      "tags": ["tag1", "tag2"],
      "prices": {"basic": 200, "standard": 500},
      "reviews": 45,
      "rating": 5.0,
      "description_snippet": "...",
      "level": "Pro",
      "positioning": "voice automation focus"
    }
  ]
}
```

---

## Step 2: Compare to Dario's Profile

### 2a. Read Current Profile

**Use: read tool**

```
path: /root/.openclaw/workspace/brain/fiverr/FIVERR.md
```

Extract:
- Current title
- Current tags (8 tags)
- Current pricing ($200, $500, $1500)
- Current reviews (17 on main gig)
- Current positioning language

### 2b. Gap Analysis

**Compare competitors to Dario:**

1. **Keywords they use we don't:**
   - Look at their titles and tags
   - Identify 3-5 keywords missing from Dario's profile
   
2. **Tags comparison:**
   - Which tags appear in multiple competitors? (high volume)
   - Which tags appear only once? (niche)
   - Which tags does Dario have that competitors don't? (unique angle)
   
3. **Positioning differences:**
   - How do they position? (price, speed, specialization?)
   - What's Dario's unique angle vs competitors?
   - What positioning is missing?

4. **Pricing analysis:**
   - What's the price range for basic/standard/premium?
   - Is Dario competitive, premium, or budget?

---

## Step 3: Generate Markdown Report

### 3a. Create Markdown File

**Use: write tool**

**File path:**
```
/root/.openclaw/workspace/brain/fiverr/research-reports/{TODAY}.md
```

Replace `{TODAY}` with actual date: `2026-03-01.md`

### 3b. Markdown Template

Follow this exact structure:

```markdown
# Fiverr Profile Research — {DATE}

## Current Metrics
- **Impressions:** {current_impressions} (target: 550+, was {peak} Feb 5)
- **Clicks:** {current_clicks} per day (target: 1-3)
- **CTR:** {current_ctr}% (target: 3-5%)
- **Orders:** {sporadic} (target: 1+ every 3 days)
- **Status:** ⚠️ NEEDS ATTENTION (impressions dropping)

---

## Competitor Analysis

### Competitor 1: {Name}
- **Title:** {exact title}
- **Tags:** {tag1}, {tag2}, {tag3}, {tag4}, {tag5}
- **Pricing:** Basic ${X}, Standard ${Y}, Premium ${Z}
- **Reviews:** {count} @ {rating} stars
- **Positioning:** {what's their unique angle}
- **Key Strength:** {what they do well}

### Competitor 2: {Name}
[Same format]

### Competitor 3: {Name}
[Same format]

---

## Gap Analysis

### Keywords We're Missing
List 3-5 keywords competitors use that we don't:
1. "{keyword1}" — Used by {2-3 competitors}, trending
2. "{keyword2}" — High volume, medium competition
3. "{keyword3}" — Emerging, low competition

### Tags Strategy

**Current tags:** n8n, automation, AI, voice agent, chatbot, workflow, openclaw, agent

**Tags to add (priority):**
1. "{new_tag1}" — Why: Competitor {X} uses this, high volume
2. "{new_tag2}" — Why: Seen in {Y} competitors, trending keyword
3. "{new_tag3}" — Why: Niche but high-intent searches

**Tags to remove:**
1. "chatbot" — Too generic, competitors use more specific terms
2. "{tag}" — Why: underperforming, low search volume

### Title Improvement

**Current:** "n8n openclaw ai agent automation for voice and chat"

**Recommendation:** "{new_title}"
- **Why:** Includes {keyword}, better structure, adds power word
- **Keywords:** {keyword1}, {keyword2}, {keyword3}

### Positioning Insights

**Competitors focus on:**
- {insight1} (3/5 use this angle)
- {insight2} (2/5 emphasize this)
- {insight3} (1/5 unique angle)

**Dario's opportunity:**
- {position_gap1}
- {position_gap2}

---

## Recommended Actions (This Week)

Highest priority first:

1. **UPDATE TAGS** (takes 5 min)
   - [ ] Remove: chatbot, workflow
   - [ ] Add: {tag1}, {tag2}, {tag3}
   - Why: Matches competitor strategy, increases visibility

2. **UPDATE TITLE** (takes 5 min)
   - [ ] Change to: "{new_title}"
   - Why: {keyword} is trending, better structure

3. **REQUEST REVIEWS** (takes 10 min)
   - [ ] Message 3-5 recent clients requesting reviews
   - Why: Social proof, increases CTR

4. **MONITOR IMPRESSIONS** (daily)
   - [ ] Check Fiverr Analytics
   - [ ] Target: Get impressions back to 550+ within 2 weeks

---

## Next Steps

**If impressions don't improve within 2 weeks:**
- Consider Promoted Gigs budget ($10/day)
- Expected ROI: 186% (based on historical data)

**Check results:**
- Next report due: {TOMORROW_DATE}
- Measure: Did impressions increase? CTR improvement? Orders?

---

## Quality Checklist (Before Sending)

- [ ] All 3+ competitors researched
- [ ] Tags extracted completely (at least 5 per competitor)
- [ ] Gap analysis identifies 3+ missing keywords
- [ ] Title suggestion provided
- [ ] 3+ recommended actions listed
- [ ] Markdown is properly formatted
- [ ] No incomplete sections
- [ ] File saved to correct location
- [ ] Ready to send to Dario

---

## Step 4: Send Telegram Notification

**Use: message tool**

Send directly to Telegram chat (this chat where Dario sees updates):

```javascript
// Use the message tool to send:
action: "send"
channel: "telegram"
target: "5127607280"  // Dario's Telegram chat ID
message: """
✅ Fiverr Profile Research Complete — {DATE}

📊 Full Report: /brain/fiverr/research-reports/{DATE}.md

🎯 Quick Summary:
• Competitors analyzed: {X} gigs
• Top keywords missing: {keyword1}, {keyword2}, {keyword3}
• Tags to add: {tag1}, {tag2}, {tag3}
• Suggested title: "{new_title}"
• Priority action: {action}

⚠️ Status: Impressions dropping 45% (critical)

👉 Full analysis in the report file above
Ready to implement recommendations?
"""
```

**Important:** 
- Replace {DATE} with actual date (e.g., 2026-03-01)
- Use exact target ID: 5127607280
- Message will appear in THIS CHAT (Dario's Telegram)

---

## Error Handling

**If web_search fails:**
- Try alternative search terms
- Fall back to manual competitor list from KEYWORD-RESEARCH.md
- Use web_fetch on Fiverr category pages directly

**If Telegram message fails:**
- Log the failure in the markdown report
- Note: "Message delivery failed - please check report manually"

**If markdown file can't be written:**
- Check directory exists: `/root/.openclaw/workspace/brain/fiverr/research-reports/`
- Check permissions: `ls -la /root/.openclaw/workspace/brain/fiverr/`
- Try alternative path if needed

---

## Example Search Queries That Work

These are proven queries, use these exactly:

```
Site-specific (most reliable):
- "site:fiverr.com n8n automation" 
- "site:fiverr.com voice automation agents"
- "site:fiverr.com automations agents category"

General (may work):
- "fiverr top n8n experts"
- "best fiverr n8n automation sellers"
- "fiverr AI voice agent automation"
```

---

## Tips for Quality Research

1. **Look for patterns:** If 3+ competitors use a keyword, it's probably important
2. **Check review themes:** Read a few reviews to understand what clients actually want
3. **Pricing analysis:** Don't just list prices, analyze positioning (are they cheap, premium, niche?)
4. **Unique angle:** What can Dario do that competitors aren't doing?
5. **Realistic recommendations:** Only suggest changes that make sense for Dario's positioning

---

## Reference: Dario's Strengths (From FIVERR.md)

Keep these in mind when analyzing:
- 228 total reviews (5 stars)
- 17 reviews on main gig (5.0 stars)
- Level 2 seller (trusted, experienced)
- Repeat clients: 40% return rate
- Fast delivery: 1-5 days typical
- Technical expertise: n8n + AI + integrations
- Portfolio: 5 complete projects (clinic, Telegram, cybersecurity, lead scraping, social media)

**Positioning angle:** Technical expertise + reliability + fast delivery
**Why clients choose Dario:** Problem solvers, think beyond requirements, "goes above and beyond"

---

## Timeline

- **Start:** When task triggers (1 PM)
- **Research:** 10-15 minutes
- **Analysis:** 5-10 minutes
- **Writing:** 5 minutes
- **Total:** 20-30 minutes
- **Message sent:** After file is created

---

## Success Criteria

✅ Research complete when:
1. 3+ competitors researched
2. Markdown report written with all sections
3. Gap analysis identifies specific actions
4. Telegram message sent with link
5. File saved to correct location
6. No errors in report

---

## Notes for Improvement (Iterate on This)

After each run, Dario might suggest improvements:
- "The tags you suggested didn't help"
- "We need more detail on {topic}"
- "I want you to also research {new area}"

When Dario updates this skill file, follow the new instructions next run. This is how we continuously improve.

---

**Version:** 2.0 (Tool-specific, actionable)  
**Last Updated:** 2026-03-01  
**Next Review:** After first test run
