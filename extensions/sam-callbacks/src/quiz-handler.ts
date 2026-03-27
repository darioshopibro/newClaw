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

function cb(selected: boolean, label: string): string {
  return `${selected ? "\u2705" : "\u2b1c"} ${label}`;
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
      navRow.push({ text: "\u2b05\ufe0f Prev", callback_data: `quiz:${taskId}|page|${page - 1}` });
    }
    navRow.push({ text: `\ud83d\udcc4 ${page + 1}/${totalPages}`, callback_data: "noop" });
    if (page < totalPages - 1) {
      navRow.push({ text: "Next \u27a1\ufe0f", callback_data: `quiz:${taskId}|page|${page + 1}` });
    }
    rows.push(navRow);
  }

  rows.push([{ text: "\u274c Cancel", callback_data: `quiz:${taskId}|cancel` }]);
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
      { text: "\u23e9 Proceed", callback_data: `quiz:${taskId}|proceed` },
      { text: "\u274c Cancel", callback_data: `quiz:${taskId}|cancel` },
    ],
  ];
}

function buildSettingsKeyboardWithBack(taskId: string, settings: Record<string, string>): Buttons {
  const keyboard = buildSettingsKeyboard(taskId, settings);
  const lastRow = keyboard[keyboard.length - 1];
  lastRow.unshift({ text: "\u2b05\ufe0f Back", callback_data: `quiz:${taskId}|back_to_contact` });
  return keyboard;
}

function buildMessage(state: Record<string, any>): string {
  const currentStep = state.current_step || STEP_SETTINGS;
  const contacts: any[] = state.contacts || [];
  const selectedContact = state.selected_contact;

  let text = `\ud83d\udcc5 <b>Schedule Event</b>\n\n`;
  text += `Title: ${state.title}\n`;
  text += `Date: ${state.date}\n`;
  text += `Time: ${state.time}\n\n`;

  if (currentStep === STEP_CONTACT) {
    text += `\ud83d\udc65 <b>Multiple contacts found (${contacts.length})</b>\n`;
    text += `Select which one to invite:`;
  } else {
    if (selectedContact) {
      const contactName = selectedContact.name || "Unknown";
      const contactEmail = selectedContact.email || "";
      text += `\ud83d\udc64 Attendee: <b>${contactName}</b>`;
      if (contactEmail) text += ` (${contactEmail})`;
      text += "\n\n";
    }
    text += `\ud83d\udccb Configure event settings:`;
  }

  return text;
}

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

export async function handleQuizCallback(
  payload: string,
  respond: Respond,
): Promise<{ handled: boolean }> {
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const taskId = parts[0];
  const action = parts[1];
  const value = parts[2] || "";

  const state = loadQuizState(taskId);
  if (!state) {
    await respond.editMessage({ text: "\u26a0\ufe0f Quiz session expired.", buttons: [] });
    return { handled: true };
  }

  const settings: Record<string, string> = state.settings || { ...DEFAULT_SETTINGS };
  const contacts: any[] = state.contacts || [];

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

  if (action === "proceed") {
    await respond.editMessage({
      text: `\u23f3 <b>Creating event...</b>\n\n\ud83d\udcc5 ${state.title}\n\ud83d\udcc6 ${state.date} at ${state.time}`,
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
        let text = `\u2705 <b>Event Created!</b>\n\n`;
        text += `\ud83d\udcc5 ${state.title}\n`;
        text += `\ud83d\udcc6 ${state.date} at ${state.time}\n`;
        text += `\u23f1 ${durDisplay[settings.duration] || settings.duration}\n`;
        text += `\ud83c\udfe2 ${typeDisplay[settings.type] || settings.type}\n`;
        text += `\ud83d\udccd Calendar: ${calDisplay[settings.calendar] || settings.calendar}\n`;
        if (state.selected_contact) {
          text += `\ud83d\udc64 Attendee: ${state.selected_contact.name || ""}`;
          if (state.selected_contact.email) text += ` (${state.selected_contact.email})`;
          text += "\n";
        }
        if (eventResult.link) {
          text += `\n\ud83d\udd17 <a href="${eventResult.link}">Open in Calendar</a>`;
        }
        await respond.editMessage({ text, buttons: [] });
      } else {
        await respond.editMessage({
          text: `\u274c <b>Failed to create event</b>\n\n\u26a0\ufe0f Error: ${(eventResult.error || "Unknown").slice(0, 200)}`,
          buttons: [],
        });
      }
    } catch (err: any) {
      await respond.editMessage({
        text: `\u274c <b>Error</b>\n\n${err.message?.slice(0, 200) || "Unknown error"}`,
        buttons: [],
      });
    }

    deleteQuizState(taskId);
    return { handled: true };
  }

  if (action === "cancel") {
    deleteQuizState(taskId);
    await respond.editMessage({
      text: `\u274c <b>Event Cancelled</b>\n\nYou cancelled the event creation.`,
      buttons: [],
    });
    return { handled: true };
  }

  return { handled: false };
}
