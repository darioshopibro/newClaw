import { execSync } from "node:child_process";
import { loadPadelState, deletePadelState } from "./state.js";

type Buttons = Array<Array<{ text: string; callback_data: string }>>;

interface Respond {
  reply: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editMessage: (params: { text: string; buttons?: Buttons }) => Promise<void>;
  editButtons: (params: { buttons: Buttons }) => Promise<void>;
  clearButtons: () => Promise<void>;
  deleteMessage: () => Promise<void>;
}

/**
 * Handle padel booking quiz callbacks.
 * Delegates to padel_quiz.py handle command for all logic.
 * Plugin only intercepts to provide instant response (no LLM roundtrip).
 */
export async function handlePadelCallback(
  payload: string,
  respond: Respond,
): Promise<{ handled: boolean }> {
  // payload format: "task_id|action|value" (namespace "padel:" already stripped)
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const taskId = parts[0];
  const action = parts[1];

  // Check if state exists
  const state = loadPadelState(taskId);
  if (!state) {
    await respond.editMessage({ text: "\u26a0\ufe0f Padel session expired.", buttons: [] });
    return { handled: true };
  }

  const chatId = state.chat_id || "";
  const messageId = state.message_id || "";

  // Delegate to padel_quiz.py handle
  try {
    const cmd = [
      "python3",
      "/root/.openclaw/workspace/agents/padel/scripts/padel_quiz.py",
      "handle",
      "--callback_data", payload,
      "--chat_id", String(chatId),
      "--message_id", String(messageId),
    ];

    execSync(cmd.join(" "), {
      timeout: 20_000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
  } catch (err: any) {
    // padel_quiz.py handles its own Telegram message editing
    // If it fails, show error
    const errMsg = err.stderr?.slice(0, 200) || err.message?.slice(0, 200) || "Unknown error";
    await respond.editMessage({
      text: `\u274c <b>Error</b>\n\n${errMsg}`,
      buttons: [],
    });
    deletePadelState(taskId);
  }

  return { handled: true };
}
