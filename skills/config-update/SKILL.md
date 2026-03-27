---
name: config-update
description: "Safely update OpenClaw config with auto-backup, validation, and Git commit. Usage: /config-update key1=value1 key2=value2"
user-invocable: true
---

# config-update — Safe Configuration Changes

Update OpenClaw config safely. Every change is backed up, validated, tested, and committed to Git.

## Usage

```
/config-update gateway.bind=loopback channels.telegram.dmPolicy=restricted
/config-update gateway.controlUi.allowInsecureAuth=false
```

## Process

1. **Parse arguments** — Extract key=value pairs
2. **Back up current config** — Save to `.config.backup`
3. **Apply changes** — Use `openclaw config set`
4. **Validate** — Check syntax and structure
5. **Test** — Restart gateway, verify it comes back online
6. **Commit to Git** — Save to GitHub (config + this change log)
7. **Report** — Tell user what happened

## Error Handling

If validation fails:
- Rollback to backup
- Restart gateway
- Report what went wrong

If restart fails:
- Rollback to backup
- Try restart again
- Alert user to manually fix (include SSH command)

## Supported Keys

```
gateway.bind = loopback | lan | all
gateway.port = <number>
gateway.controlUi.allowInsecureAuth = true | false
channels.telegram.dmPolicy = open | restricted
channels.telegram.allowFrom = <user_id>
```

## Example Flow

```
User: /config-update gateway.controlUi.allowInsecureAuth=false

Agent:
1. Backing up current config...
2. Applying: gateway.controlUi.allowInsecureAuth = false
3. Restarting gateway...
4. Testing connection... ✅ Online
5. Committing to Git...
6. Done! Config updated and backed up to GitHub.

Restore if needed:
  git checkout -- openclaw.config.json
  openclaw gateway restart
```

## Implementation

The skill will:
1. Run: `openclaw config get gateway > /tmp/config.backup`
2. Run: `openclaw config set <key> <value>` for each pair
3. Run: `openclaw gateway restart`
4. Check: `openclaw status | grep "state active"`
5. If ok: Run: `git add openclaw.config.json && git commit -m "Config: <changes>"`
6. Report result

## Never

- Don't apply changes without backup
- Don't restart without backup available
- Don't commit if restart failed
- Don't silently fail — always report status
