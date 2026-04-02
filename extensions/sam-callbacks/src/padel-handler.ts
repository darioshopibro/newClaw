import { execSync } from "node:child_process";

type Buttons = Array<Array<{ text: string; callback_data: string }>>;

interface Respond {
  reply: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editMessage: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editButtons: (params: { buttons: Buttons }) => Promise<void>;
  clearButtons: () => Promise<void>;
  deleteMessage: () => Promise<void>;
}

export async function handlePadelCallback(
  payload: string,
  respond: Respond,
): Promise<{ handled: boolean }> {
  // payload = "taskId|action|value" (OpenClaw strips "padel:" prefix before passing to handler)
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const taskId = parts[0];
  const action = parts[1];
  const value = parts[2] || "";

  // Script expects callback_data WITHOUT "padel:" prefix (it strips it internally)
  const callbackData = value
    ? `${taskId}|${action}|${value}`
    : `${taskId}|${action}`;

  try {
    // Get chat_id and message_id from state file
    const stateDir = "/root/.openclaw/padel_state";
    const stateFile = `${stateDir}/${taskId}.json`;

    let chatId = "";
    let messageId = "";

    try {
      const stateRaw = execSync(`cat ${stateFile}`, { encoding: "utf-8" });
      const state = JSON.parse(stateRaw);
      chatId = String(state.chat_id || "");
      messageId = String(state.message_id || "");
    } catch {
      await respond.editMessage({ text: "⚠️ Padel session expired.", buttons: [] });
      return { handled: true };
    }

    if (!chatId || !messageId) {
      await respond.editMessage({ text: "⚠️ Padel session expired.", buttons: [] });
      return { handled: true };
    }

    const cmd = `python3 /root/.openclaw/workspace/agents/padel/scripts/padel_quiz.py handle \
      --callback_data ${JSON.stringify(callbackData)} \
      --chat_id ${JSON.stringify(chatId)} \
      --message_id ${JSON.stringify(messageId)}`;

    execSync(cmd, { timeout: 15_000, encoding: "utf-8" });

    return { handled: true };
  } catch (err: any) {
    try {
      await respond.editMessage({
        text: `❌ <b>Error</b>\n\n${err.message?.slice(0, 200) || "Unknown error"}`,
        buttons: [],
      });
    } catch {}
    return { handled: true };
  }
}
