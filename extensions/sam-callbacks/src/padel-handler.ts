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

    // Launch booking loop in background with nohup
    try {
      const logFile = "/var/log/openclaw_padel.log";
      const cmd = `nohup python3 -u ${SCRIPTS_DIR}/booking_loop.py --task_id ${taskId} >> ${logFile} 2>&1 &`;
      execSync(cmd, { encoding: "utf-8" });

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
    // Rebuild alternatives view from state
    const clubs: Record<string, any> = state.clubs || {};
    const bd = state.booking_data || {};

    let text = `\ud83d\udcde <b>Booking Progress</b>\n\n`;
    text += `\ud83d\udcc6 ${bd.date || ""} at ${bd.time || ""}\n`;
    text += `\ud83c\udf0d ${bd.city || ""}\n\n`;

    const venuesWithTimes: string[] = [];
    for (const [name, info] of Object.entries(clubs)) {
      const times = (info as any).times_available || [];
      if (times.length > 0) venuesWithTimes.push(name);
    }

    text += `\ud83c\udfbe <b>${venuesWithTimes.length} venue(s) have available times!</b>\nPick a venue:`;

    const rows: Buttons = [];
    for (const name of venuesWithTimes) {
      const info = clubs[name] as any;
      rows.push([{
        text: `\ud83c\udfbe ${name} (${info.times_available.length} slots)`,
        callback_data: `padel:${taskId}|pick_venue|${name}`,
      }]);
    }
    rows.push([{ text: "\u274c Cancel", callback_data: `padel:${taskId}|cancel_booking` }]);

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

    let text = `\ud83d\udcdd <b>Call Summary — ${venueName}</b>\n\n`;
    if (info.summary) text += `${info.summary}\n\n`;
    if (lines.length) {
      text += `<b>Transcript:</b>\n`;
      for (const line of lines.slice(0, 20)) {
        text += `${line}\n`;
      }
    }

    await respond.editMessage({
      text,
      buttons: [[{ text: "\u2b05\ufe0f Back", callback_data: `padel:${taskId}|back_to_alternatives` }]],
    });
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
