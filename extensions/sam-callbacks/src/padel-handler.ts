import { execSync, spawn } from "node:child_process";

type Buttons = Array<Array<{ text: string; callback_data: string }>>;

interface Respond {
  reply: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editMessage: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editButtons: (params: { buttons: Buttons }) => Promise<void>;
  clearButtons: () => Promise<void>;
  deleteMessage: () => Promise<void>;
}

const SCRIPTS_DIR = "/root/.openclaw/workspace/agents/padel/scripts";
const STATE_DIR = "/root/.openclaw/padel_state";

function readState(taskId: string): Record<string, any> | null {
  try {
    const stateFile = `${STATE_DIR}/${taskId}.json`;
    const raw = execSync(`cat ${stateFile}`, { encoding: "utf-8" });
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Handle padel booking callbacks.
 * - Quiz actions (city, venue, dur, etc.) → delegate to padel_quiz.py
 * - Booking actions (proceed, pick_venue, pick_time, etc.) → handle here
 */
export async function handlePadelCallback(
  payload: string,
  respond: Respond,
): Promise<{ handled: boolean }> {
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const taskId = parts[0];
  const action = parts[1];
  const value = parts[2] || "";

  const state = readState(taskId);
  if (!state) {
    await respond.editMessage({ text: "\u26a0\ufe0f Session expired.", buttons: [] });
    return { handled: true };
  }

  const chatId = String(state.chat_id || "");
  const messageId = String(state.message_id || "");

  // ── Booking loop actions (handled directly) ──

  if (action === "proceed") {
    // Kill any existing booking_loop for this task
    try {
      execSync(`pkill -f "booking_loop.py --task_id ${taskId}" 2>/dev/null || true`, { encoding: "utf-8" });
    } catch {}

    // Launch booking loop in background
    try {
      const { openSync } = await import("node:fs");
      const logFile = "/var/log/openclaw_padel.log";
      const out = openSync(logFile, "a");
      const child = spawn("python3", ["-u", `${SCRIPTS_DIR}/booking_loop.py`, "--task_id", taskId], {
        detached: true,
        stdio: ["ignore", out, out],
      });
      child.unref();

      return { handled: true };
    } catch (err: any) {
      await respond.editMessage({
        text: `\u274c Failed to start booking: ${err.message?.slice(0, 150)}`,
        buttons: [],
      });
      return { handled: true };
    }
  }

  if (action === "pick_venue") {
    // User picked a venue from alternatives list → show times
    const venueName = value;
    const clubs: Record<string, any> = state.clubs || {};
    const venueInfo = clubs[venueName];

    if (!venueInfo || !venueInfo.times_available?.length) {
      await respond.editMessage({ text: "\u26a0\ufe0f No times available for this venue.", buttons: [] });
      return { handled: true };
    }

    const times: string[] = venueInfo.times_available;
    let text = `\ud83c\udfbe <b>${venueName}</b>\n\n`;
    text += `\ud83d\udcc6 ${state.booking_data?.date || ""} at ${state.booking_data?.time || ""}\n\n`;

    if (venueInfo.summary) {
      text += `\ud83d\udcdd ${venueInfo.summary}\n\n`;
    }

    text += `\u23f0 <b>Available times:</b>`;

    // Build times keyboard - 3 per row
    const rows: Buttons = [];
    let row: Array<{ text: string; callback_data: string }> = [];
    for (let i = 0; i < times.length; i++) {
      row.push({
        text: String(times[i]),
        callback_data: `padel:${taskId}|pick_time|${i}`,
      });
      if (row.length === 3) {
        rows.push(row);
        row = [];
      }
    }
    if (row.length) rows.push(row);

    // Recording link if available
    if (venueInfo.recording_url) {
      rows.push([{ text: "\ud83c\udfa7 Listen to call", callback_data: `padel:${taskId}|noop` }]);
    }

    rows.push([
      { text: "\u2b05\ufe0f Back", callback_data: `padel:${taskId}|back_to_alternatives` },
      { text: "\u274c Cancel", callback_data: `padel:${taskId}|cancel_booking` },
    ]);

    await respond.editMessage({ text, buttons: rows });
    return { handled: true };
  }

  if (action === "pick_time") {
    // User picked a time slot → create calendar event
    const timeIdx = parseInt(value, 10);
    const clubs: Record<string, any> = state.clubs || {};

    // Find venue with times (the one user was viewing)
    let selectedVenue = "";
    let selectedTime = "";

    for (const [name, info] of Object.entries(clubs)) {
      const times = (info as any).times_available || [];
      if (timeIdx >= 0 && timeIdx < times.length) {
        selectedVenue = name;
        selectedTime = times[timeIdx];
        break;
      }
    }

    if (!selectedVenue || !selectedTime) {
      await respond.editMessage({ text: "\u26a0\ufe0f Invalid time selection.", buttons: [] });
      return { handled: true };
    }

    await respond.editMessage({
      text: `\u23f3 <b>Creating event...</b>\n\n\ud83c\udfbe ${selectedVenue}\n\ud83d\udcc6 ${state.booking_data?.date || ""} at ${selectedTime}`,
      buttons: [],
    });

    // Create calendar event
    try {
      const cmd = `python3 ${SCRIPTS_DIR}/create_booking_event.py \
        --title ${JSON.stringify(`Padel at ${selectedVenue}`)} \
        --date ${JSON.stringify(state.booking_data?.date || "")} \
        --time ${JSON.stringify(selectedTime)} \
        --duration ${JSON.stringify(String(state.booking_data?.duration_minutes || 90))} \
        --venue ${JSON.stringify(selectedVenue)} \
        --city ${JSON.stringify(state.booking_data?.city || "")}`;

      const result = execSync(cmd, { timeout: 15_000, encoding: "utf-8" });
      const parsed = JSON.parse(result.trim());

      if (parsed.success) {
        let text = `\u2705 <b>Booking Confirmed!</b>\n\n`;
        text += `\ud83c\udfbe ${selectedVenue}\n`;
        text += `\ud83d\udcc6 ${state.booking_data?.date || ""} at ${selectedTime}\n`;
        text += `\ud83c\udf0d ${state.booking_data?.city || ""}\n`;
        if (parsed.link) {
          text += `\n\ud83d\udd17 <a href="${parsed.link}">Open in Calendar</a>`;
        }
        await respond.editMessage({ text, buttons: [] });
      } else {
        await respond.editMessage({
          text: `\u274c Failed to create event: ${parsed.error || "Unknown"}`,
          buttons: [],
        });
      }
    } catch (err: any) {
      await respond.editMessage({
        text: `\u274c Error: ${err.message?.slice(0, 200)}`,
        buttons: [],
      });
    }

    return { handled: true };
  }

  if (action === "back_to_alternatives") {
    // Rebuild FULL progress view with ALL venue statuses and buttons
    // Matches StatusRenderer logic exactly
    const clubs: Record<string, any> = state.clubs || {};
    const bd = state.booking_data || {};
    const allVenues: any[] = state.all_venues || [];

    // Rebuild status list (same as Python render_status_list)
    const statusIcons: Record<string, string> = {
      confirmed: "\u2705", booked: "\u2705", has_times: "\ud83d\udd50",
      calling: "\ud83d\udcde", pending: "\ud83d\udcde", declined: "\u274c",
      rejected: "\u274c", no_availability: "\u274c", hung_up: "\ud83d\udcf5",
      no_answer: "\ud83d\udcf5", timeout: "\ud83d\udca4", skipped: "\u23ed\ufe0f",
      error: "\u26a0\ufe0f", pending_wa: "\ud83d\udcf1",
    };
    const statusLabels: Record<string, string> = {
      confirmed: "BOOKED!", booked: "BOOKED!", calling: "calling...",
      pending: "queued", declined: "no availability", rejected: "no availability",
      no_availability: "no availability", hung_up: "no answer", no_answer: "no answer",
      timeout: "no WA response", skipped: "skipped", error: "error",
    };

    let text = `\ud83d\udcde <b>Booking Progress</b>\n\n`;
    text += `\ud83d\udcc6 ${bd.date || ""} at ${bd.time || ""}\n`;
    text += `\ud83c\udf0d ${bd.city || ""}\n\n`;

    for (const v of allVenues) {
      const club = clubs[v.name];
      if (!club) continue;
      const status = club.status || "pending";
      const icon = statusIcons[status] || "\u23f3";
      let label = statusLabels[status] || status;
      if (status === "has_times") {
        const t = club.times_available?.length || 0;
        label = `${t} slots available \ud83d\udcde`;
      }
      text += `${icon} <b>${v.name}</b> \u2014 ${label}\n`;
    }

    // Cost summary
    let totalCost = 0, totalDur = 0, totalCalls = 0;
    for (const c of Object.values(clubs) as any[]) {
      totalCost += c.cost_cents || 0;
      totalDur += c.duration_seconds || 0;
      if (!["pending", "skipped"].includes(c.status)) totalCalls++;
    }
    if (totalCalls > 0) {
      const mins = Math.floor(totalDur / 60);
      const secs = totalDur % 60;
      text += `\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n`;
      text += `\ud83d\udcb0 $${(totalCost / 100).toFixed(2)} | \u23f1 ${mins}m ${secs}s (${totalCalls} calls)`;
    }

    // Venues with times summary
    const venuesWithTimes = Object.entries(clubs).filter(
      ([, c]: any) => c.times_available?.length > 0
    );
    if (venuesWithTimes.length > 0) {
      text += `\n\n\ud83c\udfbe <b>${venuesWithTimes.length} venue(s) offered alternative times!</b>\n\ud83d\udccb Pick a venue to see available slots:`;
    }

    // Build buttons (same as Python build_progress_buttons)
    const rows: Buttons = [];
    const added = new Set<string>();

    // 1. Venues with times
    for (const [name, club] of Object.entries(clubs) as any) {
      if (club.status === "has_times" && club.times_available?.length) {
        rows.push([{
          text: `\ud83c\udfbe ${name} (${club.times_available.length} slots) \ud83d\udcde`,
          callback_data: `padel:${taskId}|pick_venue|${name}`,
        }]);
        added.add(name);
      }
    }

    // 2. Failed venues with call data
    const viewable = ["declined", "rejected", "hung_up", "timeout", "no_availability", "no_answer"];
    for (const [name, club] of Object.entries(clubs) as any) {
      if (added.has(name)) continue;
      if (!viewable.includes(club.status)) continue;
      if (club.recording_url || club.transcript_lines?.length) {
        rows.push([{
          text: `\ud83d\udcde ${name} \u2014 view call`,
          callback_data: `padel:${taskId}|view_summary|${name}`,
        }]);
        added.add(name);
      }
    }

    // 3. Cancel
    rows.push([{ text: "\u274c Cancel Booking", callback_data: `padel:${taskId}|cancel_booking` }]);

    await respond.editMessage({ text, buttons: rows });
    return { handled: true };
  }

  if (action === "create_event") {
    // Direct booking confirmation → create event
    const venueName = value;
    const bd = state.booking_data || {};

    await respond.editMessage({
      text: `\u23f3 Creating calendar event for ${venueName}...`,
      buttons: [],
    });

    try {
      const cmd = `python3 ${SCRIPTS_DIR}/create_booking_event.py \
        --title ${JSON.stringify(`Padel at ${venueName}`)} \
        --date ${JSON.stringify(bd.date || "")} \
        --time ${JSON.stringify(bd.time || "")} \
        --duration ${JSON.stringify(String(bd.duration_minutes || 90))} \
        --venue ${JSON.stringify(venueName)} \
        --city ${JSON.stringify(bd.city || "")}`;

      const result = execSync(cmd, { timeout: 15_000, encoding: "utf-8" });
      const parsed = JSON.parse(result.trim());

      if (parsed.success) {
        let text = `\u2705 <b>Booking Confirmed!</b>\n\n\ud83c\udfbe ${venueName}\n\ud83d\udcc6 ${bd.date} at ${bd.time}\n\ud83c\udf0d ${bd.city}`;
        if (parsed.link) text += `\n\n\ud83d\udd17 <a href="${parsed.link}">Open in Calendar</a>`;
        await respond.editMessage({ text, buttons: [] });
      } else {
        await respond.editMessage({ text: `\u274c ${parsed.error || "Failed"}`, buttons: [] });
      }
    } catch (err: any) {
      await respond.editMessage({ text: `\u274c ${err.message?.slice(0, 200)}`, buttons: [] });
    }
    return { handled: true };
  }

  if (action === "view_summary") {
    const venueName = value;
    const clubs: Record<string, any> = state.clubs || {};
    const info = clubs[venueName] || {};
    const lines: string[] = info.transcript_lines || [];
    const bd = state.booking_data || {};

    // Header
    let text = `\ud83c\udfaf <b>${venueName}</b> \u2014 ${bd.date || ""}\n`;
    text += `\ud83d\udccd ${bd.city || ""}\n`;
    text += `\u23f1\ufe0f ${bd.duration || "1.5hr"}\n\n`;

    // Summary
    if (info.summary) {
      text += `\ud83d\udcdd <b>Call Summary:</b>\n${info.summary}\n\n`;
    }

    // Call stats
    if (info.duration_seconds) {
      const cost = ((info.cost_cents || 0) / 100).toFixed(2);
      text += `\u23f1 ${info.duration_seconds}s | \ud83d\udcb0 $${cost}\n\n`;
    }

    // Transcript
    if (lines.length) {
      text += `\ud83d\udcac <b>Conversation:</b>\n`;
      for (const line of lines.slice(0, 30)) {
        text += `${line}\n`;
      }
    }

    // Buttons - matching n8n
    const rows: Buttons = [];

    // Recording link
    if (info.recording_url) {
      rows.push([{ text: "\ud83c\udfa7 Listen to call", callback_data: `padel:${taskId}|noop` }]);
    }

    // Full transcript button (if transcript is long)
    if (lines.length > 10) {
      rows.push([{ text: "\ud83d\udcdd Full Transcript", callback_data: `padel:${taskId}|full_transcript|${venueName}` }]);
    }

    // Back + Cancel
    rows.push([
      { text: "\u2b05\ufe0f Back", callback_data: `padel:${taskId}|back_to_alternatives` },
      { text: "\u274c Cancel", callback_data: `padel:${taskId}|cancel_booking` },
    ]);

    await respond.editMessage({ text, buttons: rows });
    return { handled: true };
  }

  if (action === "full_transcript") {
    const venueName = value;
    const clubs: Record<string, any> = state.clubs || {};
    const info = clubs[venueName] || {};
    const lines: string[] = info.transcript_lines || [];

    let text = `\ud83d\udcdd <b>Full Transcript \u2014 ${venueName}</b>\n\n`;
    for (const line of lines) {
      text += `${line}\n\n`;
    }

    const rows: Buttons = [
      [
        { text: "\u2b05\ufe0f Back", callback_data: `padel:${taskId}|view_summary|${venueName}` },
        { text: "\u274c Cancel", callback_data: `padel:${taskId}|cancel_booking` },
      ],
    ];
    if (info.recording_url) {
      rows.unshift([{ text: "\ud83c\udfa7 Listen to call", callback_data: `padel:${taskId}|noop` }]);
    }

    await respond.editMessage({ text, buttons: rows });
    return { handled: true };
  }

  if (action === "cancel_booking") {
    // Mark cancelled in state + kill booking_loop process
    try {
      const { writeFileSync } = await import("node:fs");
      const st = readState(taskId);
      if (st) {
        st.loop_status = "cancelled";
        writeFileSync(`${STATE_DIR}/${taskId}.json`, JSON.stringify(st, null, 2));
      }
    } catch {}
    try {
      execSync(`pkill -f "booking_loop.py --task_id ${taskId}" 2>/dev/null || true`);
    } catch {}
    await respond.editMessage({ text: "\u274c Booking Cancelled", buttons: [] });
    return { handled: true };
  }

  if (action === "retry") {
    // TODO: restart quiz or loop
    await respond.editMessage({
      text: "\ud83d\udd04 Please send a new booking request.",
      buttons: [],
    });
    return { handled: true };
  }

  if (action === "noop") {
    return { handled: true };
  }

  // ── Quiz actions → delegate to padel_quiz.py ──
  const quizActions = ["city", "venue", "page", "dur", "back_to_city", "back_to_venues", "cancel"];
  if (quizActions.includes(action)) {
    const callbackData = value ? `${taskId}|${action}|${value}` : `${taskId}|${action}`;

    try {
      const cmd = `python3 ${SCRIPTS_DIR}/padel_quiz.py handle \
        --callback_data ${JSON.stringify(callbackData)} \
        --chat_id ${JSON.stringify(chatId)} \
        --message_id ${JSON.stringify(messageId)}`;

      execSync(cmd, { timeout: 15_000, encoding: "utf-8" });
    } catch (err: any) {
      const errMsg = err.stderr?.slice(0, 200) || err.message?.slice(0, 200) || "Unknown";
      await respond.editMessage({ text: `\u274c ${errMsg}`, buttons: [] });
    }

    return { handled: true };
  }

  return { handled: false };
}
