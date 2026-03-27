# MEMORY.md - Long-Term Memory

## ⚠️ CRITICAL VPS SAFETY RULE ⚠️

**BEFORE giving ANY command that affects VPS infrastructure:**

1. **CHECK what's currently running:**
   - `ss -tulpn` - see all listening ports
   - `pm2 status` - see running processes
   - `ufw status` - see firewall rules

2. **NEVER enable/change firewall without first adding ALL needed ports:**
   - 22 (SSH - will lock you out!)
   - 443 (Telegram webhook)
   - Any other ports currently in use

3. **If command might break something running - STOP and ask first**

---

## Who I Am
- Clyde, Dario's personal assistant
- I help you with what you do — your projects, tasks, workflows
- I learn what you need and get better at helping over time

## About Dario

**Name:** Dario Acimovic  
**Location:** Belgrade, Serbia  
**Timezone:** GMT+1 (Europe)  
**What I do:** AI Automation Engineer

### Current Work
- Fiverr: n8n AI Agent Developer (200+ 5-star reviews)
- Side: Co-founder Adsgun (Shopify app, with friend)
- Active: Building important AI automation project with team of 2
- Work intensity: 10+ hours/day

### Background
- 4 years: Shopify development + web development + app development
- 2 years: AI automation + n8n specialist

### Tech Stack
- n8n (workflows + automation)
- Python (backend logic)
- Supabase / PostgreSQL
- REST APIs + webhooks
- AI / LangChain
- OAuth integrations

### Team
- Solo + 2 teammates on AI automation project

### Communication
- Telegram: @Dejri61

## Current Setup
✅ OpenClaw on VPS (161.97.83.88)
✅ Telegram integration (need to verify bot token)
✅ GitHub repo: darioshopibro/dejriOpenClaw
✅ OpenRouter API configured
✅ Memory system enabled
✅ Skills framework in place

### Telegram Middleware (PM2)
**PM2 name:** `telegram-middleware`
**Script:** `/root/.openclaw/workspace/telegram_middleware.py`
**Port:** 443 (webhook)

⚠️ **CRITICAL:** See SOUL.md for full rules. Summary:
- **NEVER run manually** - always use `pm2 restart telegram-middleware`
- **NEVER use systemd** - we use PM2 exclusively
- Manual run = port conflict = crash

## What We're Working On
- Getting to know each other better
- Making me a better assistant for your needs
- Understanding what you actually do (projects, workflows, priorities)

## What We're NOT Doing
- Migrating from n8n (deferred)
- Building calendar/contact agents
- Complex multi-agent systems yet

## Next Steps
1. Learn what Dario's main projects/needs are
2. Understand his workflow and priorities
3. Figure out what I can help with
4. Build skills/tools as needed
