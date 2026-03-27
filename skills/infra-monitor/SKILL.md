---
name: infra-monitor
description: Monitor VPS infrastructure (PM2, ports) and alert on issues
---

# Infrastructure Monitor

Monitors PM2 processes and ports every 3 minutes. Sends Telegram alert if something is wrong.

## What It Checks

| Check | Expected | Alert If |
|-------|----------|----------|
| `openclaw-gateway` | online | stopped/errored |
| `telegram-middleware` | online | stopped/errored |
| Port 443 | listening | not listening |
| Port 18789 | listening | not listening |
| Unknown ports | none | new port detected |

## Usage

### Manual Check
```bash
python3 /root/.openclaw/workspace/skills/infra-monitor/scripts/check.py
```

### Setup Cron (every 3 min)
```bash
crontab -e
# Add this line:
*/3 * * * * python3 /root/.openclaw/workspace/skills/infra-monitor/scripts/check.py >> /var/log/infra-monitor.log 2>&1
```

## Alert Format

When something is wrong, sends to Telegram:
```
⚠️ INFRASTRUCTURE ALERT

PM2 Issues:
- telegram-middleware: stopped

Port Issues:
- Port 443: NOT listening

Run: pm2 status
```

## Configuration

Edit `scripts/check.py` to change:
- `CHAT_ID` - Your Telegram chat ID
- `BOT_TOKEN` - Your bot token
- `EXPECTED_PROCESSES` - PM2 processes to monitor
- `EXPECTED_PORTS` - Ports that should be listening
