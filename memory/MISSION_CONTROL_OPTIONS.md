# Mission Control Dashboards for OpenClaw

Research done: 2026-02-28 21:40  
Dario asked: Find fancy dashboards people use instead of the default OpenClaw dashboard

---

## Top 3 Options Found on GitHub

### 1. **Mission Control by Jzineldin** ⭐⭐⭐ (Most Polished)
**URL:** https://github.com/Jzineldin/mission-control

**What it does:**
- Dashboard with activity feed, quick actions (email/calendar/heartbeat)
- Real-time streaming chat widget (talk to your agent)
- Task queue/Kanban board (Workshop) — queue tasks, execute with sub-agents
- Cost tracker with token usage per model
- Cron job manager (toggle, run now, delete, create)
- Scout Engine — auto-discovers freelance gigs, bug bounties, grants, news
- Skills browser (enable/disable/install)
- Agent monitoring + session browser

**Design:**
- macOS-native feel (frosted glass, SF Pro typography)
- Navy blue brushed steel background
- Built with React 19 + Vite 7 + Framer Motion

**Setup:**
```bash
git clone https://github.com/Jzineldin/mission-control.git
cd mission-control
npm install
cd frontend && npm install && npm run build && cd ..
cp mc-config.default.json mc-config.json
node server.js
# Visit http://localhost:3333
```

**Features:**
- ✅ Everything auto-detects your OpenClaw setup
- ✅ Pages: Dashboard, Conversations, Workshop, Cost Tracker, Cron Monitor, Scout, Agent Hub, Settings, Skills
- ✅ Optional AWS integration (Bedrock, image gen)
- ✅ Fast (sub-3ms cache hits)

**Best for:** Complete mission control — you want a beautiful, fully-featured UI for everything

---

### 2. **OpsDeck by ewimsatt** ⭐⭐ (Lightweight)
**URL:** https://github.com/ewimsatt/openclaw-opsdeck-core

**What it does:**
- Agent Round Table — live view of active/idle agents with roles
- Cron Dashboard — health, next-run times, manual triggers
- Local Chat — send messages to your main agent from the UI
- Project Tracking — git-status monitoring for local repos
- Lightweight, minimal, fast

**Setup:**
```bash
git clone https://github.com/ewimsatt/openclaw-opsdeck-core.git
cd openclaw-opsdeck-core
npm install
cp opsdeck.config.example.js opsdeck.config.js
npm run dev:full
# Visit http://localhost:4173
```

**Tech:**
- React + Fastify + Vite
- MIT License
- All data from local OpenClaw CLI (no cloud)

**Best for:** Minimal overhead, just want to see agents + crons + quick chat

---

### 3. **Mission Control by crshdn** ⭐ (AI-Focused Orchestration)
**URL:** https://github.com/crshdn/mission-control

**What it does:**
- Kanban task board (drag-and-drop status columns)
- AI Planning flow — AI asks clarifying questions before starting
- Agent System — auto-creates specialized agents, assigns tasks
- Gateway Agent Discovery — import existing agents with one click
- WebSocket connection to OpenClaw Gateway
- Docker ready

**Tech:**
- Next.js 14 + TypeScript + SQLite
- Docker included

**Best for:** Task-driven workflows — create tasks, have AI plan, dispatch to agents, watch progress

---

## Comparison Table

| Feature | Mission Control (Jzineldin) | OpsDeck (ewimsatt) | Mission Control (crshdn) |
|---------|-------|--------|---------|
| Dashboard | ✅ Rich | ✅ Minimal | ❌ Task-focused |
| Chat | ✅ Streaming | ✅ Simple | ❌ None |
| Task Queue | ✅ Yes | ❌ No | ✅ Kanban |
| Cron Manager | ✅ Full | ✅ Yes | ❌ No |
| Cost Tracker | ✅ Yes | ❌ No | ❌ No |
| Scout Engine | ✅ Yes | ❌ No | ❌ No |
| Setup Complexity | Medium | Easy | Medium |
| License | BSL 1.1 (→MIT 2030) | MIT | MIT |

---

## Recommendation for Dario

**If you want "everything in one place":** Use **Mission Control (Jzineldin)**
- Most polished
- Beautiful design
- Full feature set (cron, tasks, costs, chat, opportunities)
- ~15 min setup

**If you want "minimal + fast":** Use **OpsDeck (ewimsatt)**
- Lightweight
- Agent overview + cron + chat
- No dependencies bloat
- ~5 min setup

**If you want "task automation":** Use **Mission Control (crshdn)**
- AI-powered task creation/assignment
- Kanban workflow
- Good if you dispatch a lot to sub-agents

---

## Next Steps

1. Try one of these (I recommend starting with Mission Control by Jzineldin)
2. Clone to your workspace
3. Start it alongside your OpenClaw gateway
4. Access via dashboard port (usually 3333 or 4173)
5. Let me know which one you like

When you're back, just say which one to install + I'll handle the setup.
