# RECOVERY.md - Config Changes & Fixes

## Change #1: Register sam-callbacks Plugin + Add Sonnet Model
**Date:** 2026-03-27 22:31  
**What changed:** 
1. Added `sam-callbacks` plugin entry to openclaw.json (was missing)
2. Added `openrouter/anthropic/claude-sonnet-4-6` to allowed models

**Why:** 
- sam-callbacks plugin exists at `/root/.openclaw/extensions/sam-callbacks` but wasn't registered. OpenClaw was throwing: "plugin not found: sam-callbacks"
- Sonnet needed for complex config/debugging tasks (can't switch without it being in config)

**Status:** ✅ APPLIED LOCALLY (verified in config)

**If you need to revert (command to run):**
```bash
cd /root/.openclaw
cp openclaw.json.bak openclaw.json
# Then restart if on VPS:
openclaw gateway restart
```

**Verification:**
```bash
# Check models are registered:
cat /root/.openclaw/openclaw.json | python3 -c "import json,sys; data=json.load(sys.stdin); print('Models:', list(data['agents']['defaults']['models'].keys())); print('Plugins:', list(data['plugins']['entries'].keys()))"
```

**Expected result:**
- Models include: `openrouter/anthropic/claude-haiku-4.5` and `openrouter/anthropic/claude-sonnet-4-6`
- Plugins include: `duckduckgo` and `sam-callbacks`
