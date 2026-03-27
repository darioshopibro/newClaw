import { execSync } from "node:child_process";
import { loadContactState, saveContactState, deleteContactState } from "./state.js";

type Buttons = Array<Array<{ text: string; callback_data: string }>>;

interface Respond {
  reply: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editMessage: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editButtons: (params: { buttons: Buttons }) => Promise<void>;
  clearButtons: () => Promise<void>;
  deleteMessage: () => Promise<void>;
}

// ── Keyboard builders ──────────────────────────────────────────

function buildMergeKeyboard(taskId: string, state: Record<string, any>): Buttons {
  const selections: Record<string, boolean> = state.selections || {};
  const newData: Record<string, any> = state.new_data || {};

  const rows: Buttons = [];
  const toggleRow: Array<{ text: string; callback_data: string }> = [];

  if (newData.email) {
    const selected = selections.email !== false; // default true
    toggleRow.push({
      text: `${selected ? "✅" : "⬜"} Email`,
      callback_data: `contact:${taskId}|te`,
    });
  }

  if (newData.phone) {
    const selected = selections.phone !== false; // default true
    toggleRow.push({
      text: `${selected ? "✅" : "⬜"} Phone`,
      callback_data: `contact:${taskId}|tp`,
    });
  }

  if (toggleRow.length) rows.push(toggleRow);

  rows.push([
    { text: "➕ Create New", callback_data: `contact:${taskId}|new` },
    { text: "🔀 Merge", callback_data: `contact:${taskId}|confirm` },
  ]);
  rows.push([{ text: "❌ Cancel", callback_data: `contact:${taskId}|cancel` }]);

  return rows;
}

function buildMergeMessage(state: Record<string, any>): string {
  const existing: Record<string, any> = state.existing_contact || {};
  const newData: Record<string, any> = state.new_data || {};
  const selections: Record<string, boolean> = state.selections || {};

  let text = `📇 <b>Similar contact found: ${existing.name || "Unknown"}</b>\n\n`;

  if (existing.email) text += `📧 Current email: ${existing.email}\n`;
  if (existing.phone) text += `📱 Current phone: ${existing.phone}\n`;

  text += "\n<b>What to add to existing contact?</b>\n\n";

  if (newData.email) {
    const emoji = selections.email !== false ? "✅" : "⬜";
    text += `${emoji} Email: ${newData.email}\n`;
  }
  if (newData.phone) {
    const emoji = selections.phone !== false ? "✅" : "⬜";
    text += `${emoji} Phone: ${newData.phone}\n`;
  }

  return text;
}

// ── Main handler ───────────────────────────────────────────────

export async function handleContactCallback(
  payload: string,
  respond: Respond,
): Promise<{ handled: boolean }> {
  // payload format: "task_id|action"
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const taskId = parts[0];
  const action = parts[1];

  const state = loadContactState(taskId);
  if (!state) {
    await respond.editMessage({ text: "⚠️ Contact session expired.", buttons: [] });
    return { handled: true };
  }

  const selections: Record<string, boolean> = state.selections || {};

  // ── Toggle email ──
  if (action === "te") {
    selections.email = !(selections.email !== false);
    state.selections = selections;
    saveContactState(taskId, state);

    await respond.editMessage({
      text: buildMergeMessage(state),
      buttons: buildMergeKeyboard(taskId, state),
    });
    return { handled: true };
  }

  // ── Toggle phone ──
  if (action === "tp") {
    selections.phone = !(selections.phone !== false);
    state.selections = selections;
    saveContactState(taskId, state);

    await respond.editMessage({
      text: buildMergeMessage(state),
      buttons: buildMergeKeyboard(taskId, state),
    });
    return { handled: true };
  }

  // ── Merge confirm ──
  if (action === "confirm") {
    const existing = state.existing_contact || {};
    const newData = state.new_data || {};
    const contactName = existing.name || "Unknown";

    await respond.editMessage({
      text: `⏳ <b>Merging...</b>\n\nAdding selected fields to ${contactName}`,
      buttons: [],
    });

    try {
      const scriptDir = "/root/.openclaw/workspace/skills/contact/scripts";
      const args: string[] = [];

      if (selections.email !== false && newData.email) {
        args.push(`--add_email ${JSON.stringify(newData.email)}`);
      }
      if (selections.phone !== false && newData.phone) {
        args.push(`--add_phone ${JSON.stringify(newData.phone)}`);
      }

      if (args.length > 0) {
        const cmd = `python3 -c "
from google_contacts_write import GoogleContactsWriteClient
import json, sys
client = GoogleContactsWriteClient()
result = client.update(contact_id=${JSON.stringify(existing.id)}${selections.email !== false && newData.email ? `, add_email=${JSON.stringify(newData.email)}` : ""}${selections.phone !== false && newData.phone ? `, add_phone=${JSON.stringify(newData.phone)}` : ""})
print(json.dumps(result))
"`;

        const result = execSync(cmd, { cwd: scriptDir, timeout: 30_000, encoding: "utf-8" });
        const parsed = JSON.parse(result.trim());

        if (parsed.success) {
          const fieldsAdded: string[] = [];
          if (selections.email !== false && newData.email) fieldsAdded.push(`📧 ${newData.email}`);
          if (selections.phone !== false && newData.phone) fieldsAdded.push(`📱 ${newData.phone}`);

          await respond.editMessage({
            text: `✅ <b>Contact Merged</b>\n\nUpdated: ${contactName}\n\nAdded:\n${fieldsAdded.join("\n")}`,
            buttons: [],
          });
        } else {
          await respond.editMessage({
            text: `❌ <b>Merge Failed</b>\n\n${parsed.error || "Unknown error"}`,
            buttons: [],
          });
        }
      } else {
        await respond.editMessage({
          text: `ℹ️ <b>No Changes</b>\n\nNo fields were selected to merge.`,
          buttons: [],
        });
      }
    } catch (err: any) {
      await respond.editMessage({
        text: `❌ <b>Error</b>\n\n${err.message?.slice(0, 200) || "Unknown error"}`,
        buttons: [],
      });
    }

    deleteContactState(taskId);
    return { handled: true };
  }

  // ── Create new (ignore duplicate) ──
  if (action === "new") {
    const newData = state.new_data || {};
    await respond.editMessage({ text: `⏳ <b>Creating new contact...</b>`, buttons: [] });

    try {
      const scriptDir = "/root/.openclaw/workspace/skills/contact/scripts";
      const firstName = newData.first_name || "Unknown";
      const lastName = newData.last_name || "";

      const cmd = `python3 -c "
from google_contacts_write import GoogleContactsWriteClient
import json
client = GoogleContactsWriteClient()
result = client.create(first_name=${JSON.stringify(firstName)}, last_name=${JSON.stringify(lastName)}${newData.email ? `, email=${JSON.stringify(newData.email)}` : ""}${newData.phone ? `, phone=${JSON.stringify(newData.phone)}` : ""})
print(json.dumps(result))
"`;

      const result = execSync(cmd, { cwd: scriptDir, timeout: 30_000, encoding: "utf-8" });
      const parsed = JSON.parse(result.trim());

      if (parsed.success) {
        let text = `✅ <b>Contact Created</b>\n\n📇 ${firstName} ${lastName}\n`;
        if (newData.email) text += `📧 ${newData.email}\n`;
        if (newData.phone) text += `📱 ${newData.phone}\n`;
        await respond.editMessage({ text, buttons: [] });
      } else {
        await respond.editMessage({
          text: `❌ <b>Failed to Create</b>\n\n${parsed.error || "Unknown error"}`,
          buttons: [],
        });
      }
    } catch (err: any) {
      await respond.editMessage({
        text: `❌ <b>Error</b>\n\n${err.message?.slice(0, 200) || "Unknown error"}`,
        buttons: [],
      });
    }

    deleteContactState(taskId);
    return { handled: true };
  }

  // ── Simple add (no duplicate) ──
  if (action === "add") {
    const newData = state.new_data || {};
    await respond.editMessage({ text: `⏳ <b>Adding contact...</b>`, buttons: [] });

    try {
      const scriptDir = "/root/.openclaw/workspace/skills/contact/scripts";
      const firstName = newData.first_name || newData.name?.split(" ")[0] || "Unknown";
      const lastName = newData.last_name || newData.name?.split(" ").slice(1).join(" ") || "";

      const cmd = `python3 -c "
from google_contacts_write import GoogleContactsWriteClient
import json
client = GoogleContactsWriteClient()
result = client.create(first_name=${JSON.stringify(firstName)}, last_name=${JSON.stringify(lastName)}${newData.email ? `, email=${JSON.stringify(newData.email)}` : ""}${newData.phone ? `, phone=${JSON.stringify(newData.phone)}` : ""})
print(json.dumps(result))
"`;

      const result = execSync(cmd, { cwd: scriptDir, timeout: 30_000, encoding: "utf-8" });
      const parsed = JSON.parse(result.trim());

      if (parsed.success) {
        const name = newData.name || `${firstName} ${lastName}`.trim();
        let text = `✅ <b>Contact Added!</b>\n\n👤 ${name}\n`;
        if (newData.phone) text += `📱 ${newData.phone}\n`;
        if (newData.email) text += `📧 ${newData.email}\n`;
        text += `\n🆔 ${parsed.contact_id || "N/A"}`;
        await respond.editMessage({ text, buttons: [] });
      } else {
        await respond.editMessage({
          text: `❌ <b>Failed to Add</b>\n\n${parsed.error || "Unknown error"}`,
          buttons: [],
        });
      }
    } catch (err: any) {
      await respond.editMessage({
        text: `❌ <b>Error</b>\n\n${err.message?.slice(0, 200) || "Unknown error"}`,
        buttons: [],
      });
    }

    deleteContactState(taskId);
    return { handled: true };
  }

  // ── Cancel ──
  if (action === "cancel") {
    deleteContactState(taskId);
    await respond.editMessage({
      text: "❌ <b>Operation Cancelled</b>\n\nContact was not created or modified.",
      buttons: [],
    });
    return { handled: true };
  }

  return { handled: false };
}
