import { execSync } from "node:child_process";
import { loadQuizState, saveQuizState, deleteQuizState } from "./state.js";

type Buttons = Array<Array<{ text: string; callback_data: string }>>;

interface Respond {
  reply: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editMessage: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editButtons: (params: { buttons: Buttons }) => Promise<void>;
  clearButtons: () => Promise<void>;
  deleteMessage: () => Promise<void>;
}

const DEFAULT_SETTINGS = {
  calendar: "shopibro",
  type: "in-person",
  duration: "1hr",
};

const STEP_CONTACT = "contact";
const STEP_SETTINGS = "settings";
const PAGE_SIZE = 4;

// ── Keyboard builders ──────────────────────────────────────────

function cb(selected: boolean, label: string): string {
  return `${selected ? "✅" : "⬜"} ${label}`;
}

function buildContactKeyboard(taskId: string, contacts: any[], page = 0): Buttons {
  const total = contacts.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const start = page * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, total);
  const pageContacts = contacts.slice(start, end);

  const rows: Buttons = [];

  for (let i = 0; i < pageContacts.length; i++) {
    const idx = start + i;
    const contact = pageContacts[i];
    const name = contact.name || "Unknown";
    const email = contact.email || "";
    let label = name;
    if (email) {
      const emailShort = email.length > 23 ? email.slice(0, 20) + "..." : email;
      label = `${name} (${emailShort})`;
    }
    rows.push([{ text: label, callback_data: `quiz:${taskId}|contact|${idx}` }]);
  }

  if (totalPages > 1) {
    const navRow: Array<{ text: string; callback_data: string }> = [];
    if (page > 0) {
      navRow.push({ text: "⬅️ Prev", callback_data: `quiz:${taskId}|page|${page - 1}` });
    }
    navRow.push({ text: `📄 ${page + 1}/${totalPages}`, callback_data: "noop" });
    if (page < totalPages - 1) {
      navRow.push({ text: "Next ➡️", callback_data: `quiz:${taskId}|page|${page + 1}` });
    }
    rows.push(navRow);
  }

  rows.push([{ text: "❌ Cancel", callback_data: `quiz:${taskId}|cancel` }]);
  return rows;
}

function buildSettingsKeyboard(taskId: string, settings: Record<string, string>): Buttons {
  const cal = settings.calendar || "shopibro";
  const typ = settings.type || "in-person";
  const dur = settings.duration || "1hr";

  return [
    [
      { text: cb(cal === "shopibro", "Shopibro"), callback_data: `quiz:${taskId}|cal|shopibro` },
      { text: cb(cal === "private", "Private"), callback_data: `quiz:${taskId}|cal|private` },
    ],
    [
      { text: cb(typ === "in-person", "In-person"), callback_data: `quiz:${taskId}|type|in-person` },
      { text: cb(typ === "online", "Online"), callback_data: `quiz:${taskId}|type|online` },
    ],
    [
      { text: cb(dur === "30m", "30m"), callback_data: `quiz:${taskId}|dur|30m` },
      { text: cb(dur === "1hr", "1hr"), callback_data: `quiz:${taskId}|dur|1hr` },
      { text: cb(dur === "1.5hr", "1.5hr"), callback_data: `quiz:${taskId}|dur|1.5hr` },
      { text: cb(dur === "2hr", "2hr"), callback_data: `quiz:${taskId}|dur|2hr` },
    ],
    [
      { text: "⏩ Proceed", callback_data: `quiz:${taskId}|proceed` },
      { text: "❌ Cancel", callback_data: `quiz:${taskId}|cancel` },
    ],
  ];
}

function buildSettingsKeyboardWithBack(taskId: string, settings: Record<string, string>): Buttons {
  const keyboard = buildSettingsKeyboard(taskId, settings);
  const lastRow = keyboard[keyboard.length - 1];
  lastRow.unshift({ text: "⬅️ Back", callback_data: `quiz:${taskId}|back_to_contact` });
  return keyboard;
}

// ── Message builder ────────────────────────────────────────────

function buildMessage(state: Record<string, any>): string {
  const currentStep = state.current_step || STEP_SETTINGS;
  const contacts: any[] = state.contacts || [];
  const selectedContact = state.selected_contact;

  let text = `📅 <b>Schedule Event</b>\n\n`;
  text += `Title: ${state.title}\n`;
  text += `Date: ${state.date}\n`;
  text += `Time: ${state.time}\n\n`;

  if (currentStep === STEP_CONTACT) {
    text += `👥 <b>Multiple contacts found (${contacts.length})</b>\n`;
    text += `Select which one to invite:`;
  } else {
    if (selectedContact) {
      const contactName = selectedContact.name || "Unknown";
      const contactEmail = selectedContact.email || "";
      text += `👤 Attendee: <b>${contactName}</b>`;
      if (contactEmail) text += ` (${contactEmail})`;
      text += "\n\n";
    }
    text += `📋 Configure event settings:`;
  }

  return text;
}

// ── Get the right keyboard for current state ───────────────────

function getKeyboardForState(taskId: string, state: Record<string, any>): Buttons {
  const contacts: any[] = state.contacts || [];
  const settings = state.settings || { ...DEFAULT_SETTINGS };

  if (state.current_step === STEP_CONTACT) {
    return buildContactKeyboard(taskId, contacts, state.contact_page || 0);
  }
  if (state.selected_contact && contacts.length > 1) {
    return buildSettingsKeyboardWithBack(taskId, settings);
  }
  return buildSettingsKeyboard(taskId, settings);
}

// ── Main handler ───────────────────────────────────────────────

export async function handleQuizCallback(
  payload: string,
  respond: Respond,
): Promise<{ handled: boolean }> {
  // payload format: "task_id|action|value" (the part after "quiz:")
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const taskId = parts[0];
  const action = parts[1];
  const value = parts[2] || "";

  const state = loadQuizState(taskId);
  if (!state) {
    await respond.editMessage({ text: "⚠️ Quiz session expired.", buttons: [] });
    return { handled: true };
  }

  const settings: Record<string, string> = state.settings || { ...DEFAULT_SETTINGS };
  const contacts: any[] = state.contacts || [];

  // ── Contact selection ──
  if (action === "contact") {
    const contactIdx = parseInt(value, 10);
    if (contactIdx >= 0 && contactIdx < contacts.length) {
      const selected = contacts[contactIdx];
      state.selected_contact = selected;
      state.attendee_email = selected.email || "";
      state.current_step = STEP_SETTINGS;
      saveQuizState(taskId, state);

      await respond.editMessage({
        text: buildMessage(state),
        buttons: buildSettingsKeyboardWithBack(taskId, settings),
      });
    }
    return { handled: true };
  }

  // ── Page navigation ──
  if (action === "page") {
    const page = parseInt(value, 10);
    state.contact_page = page;
    saveQuizState(taskId, state);

    await respond.editMessage({
      text: buildMessage(state),
      buttons: buildContactKeyboard(taskId, contacts, page),
    });
    return { handled: true };
  }

  // ── Back to contact ──
  if (action === "back_to_contact") {
    state.current_step = STEP_CONTACT;
    state.selected_contact = null;
    state.attendee_email = "";
    saveQuizState(taskId, state);

    await respond.editMessage({
      text: buildMessage(state),
      buttons: buildContactKeyboard(taskId, contacts, state.contact_page || 0),
    });
    return { handled: true };
  }

  // ── Settings toggles ──
  if (action === "cal" || action === "type" || action === "dur") {
    const keyMap: Record<string, string> = { cal: "calendar", type: "type", dur: "duration" };
    settings[keyMap[action]] = value;
    state.settings = settings;
    saveQuizState(taskId, state);

    await respond.editMessage({
      text: buildMessage(state),
      buttons: getKeyboardForState(taskId, state),
    });
    return { handled: true };
  }

  // ── Proceed ──
  if (action === "proceed") {
    await respond.editMessage({
      text: `⏳ <b>Creating event...</b>\n\n📅 ${state.title}\n📆 ${state.date} at ${state.time}`,
      buttons: [],
    });

    try {
      const durationMap: Record<string, number> = { "30m": 30, "1hr": 60, "1.5hr": 90, "2hr": 120 };
      const durationMinutes = durationMap[settings.duration] || 60;

      const cmd = [
        "python3", "create_event.py",
        "--skip_quiz_check",
        "--title", JSON.stringify(state.title),
        "--date", JSON.stringify(state.date),
        "--time", JSON.stringify(state.time),
        "--duration", String(durationMinutes),
        "--calendar", settings.calendar,
        "--description", settings.type,
      ];
      if (state.attendee_email) {
        cmd.push("--attendees", JSON.stringify(state.attendee_email));
      }

      const result = execSync(cmd.join(" "), {
        cwd: "/root/.openclaw/workspace/skills/calendar/scripts",
        timeout: 30_000,
        encoding: "utf-8",
      });

      let eventResult: Record<string, any>;
      try {
        eventResult = JSON.parse(result);
      } catch {
        eventResult = { success: false, error: `Invalid JSON: ${result.slice(0, 200)}` };
      }

      const durDisplay: Record<string, string> = { "30m": "30 min", "1hr": "1 hour", "1.5hr": "1.5 hours", "2hr": "2 hours" };
      const calDisplay: Record<string, string> = { shopibro: "Shopibro", private: "Private" };
      const typeDisplay: Record<string, string> = { "in-person": "In-person", online: "Online" };

      if (eventResult.success) {
        let text = `✅ <b>Event Created!</b>\n\n`;
        text += `📅 ${state.title}\n`;
        text += `📆 ${state.date} at ${state.time}\n`;
        text += `⏱ ${durDisplay[settings.duration] || settings.duration}\n`;
        text += `🏢 ${typeDisplay[settings.type] || settings.type}\n`;
        text += `📍 Calendar: ${calDisplay[settings.calendar] || settings.calendar}\n`;
        if (state.selected_contact) {
          text += `👤 Attendee: ${state.selected_contact.name || ""}`;
          if (state.selected_contact.email) text += ` (${state.selected_contact.email})`;
          text += "\n";
        }
        if (eventResult.link) {
          text += `\n🔗 <a href="${eventResult.link}">Open in Calendar</a>`;
        }
        await respond.editMessage({ text, buttons: [] });
      } else {
        await respond.editMessage({
          text: `❌ <b>Failed to create event</b>\n\n⚠️ Error: ${(eventResult.error || "Unknown").slice(0, 200)}`,
          buttons: [],
        });
      }
    } catch (err: any) {
      await respond.editMessage({
        text: `❌ <b>Error</b>\n\n${err.message?.slice(0, 200) || "Unknown error"}`,
        buttons: [],
      });
    }

    deleteQuizState(taskId);
    return { handled: true };
  }

  // ── Cancel ──
  if (action === "cancel") {
    deleteQuizState(taskId);
    await respond.editMessage({
      text: `❌ <b>Event Cancelled</b>\n\nYou cancelled the event creation.`,
      buttons: [],
    });
    return { handled: true };
  }

  return { handled: false };
}
