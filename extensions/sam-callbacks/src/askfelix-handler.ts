import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import type { IncomingMessage, ServerResponse } from "node:http";

const STATE_DIR = "/root/.openclaw/padel_state";
const SCRIPTS_DIR = "/root/.openclaw/workspace/agents/padel/scripts";

// Pending responses: call_id → resolve function
// When Retell calls webhook, we store a Promise resolver.
// When Felix clicks button, we resolve it with his choice.
const pendingResponses = new Map<string, {
  resolve: (value: string) => void;
  timeout: ReturnType<typeof setTimeout>;
  options: string[];
}>();

function getBotToken(): string {
  let token = process.env.TELEGRAM_BOT_TOKEN || "";
  if (!token) {
    try {
      const env = readFileSync("/etc/environment", "utf-8");
      const match = env.match(/TELEGRAM_BOT_TOKEN=["']?([^"'\n]+)/);
      if (match) token = match[1];
    } catch {}
  }
  return token;
}

function sendTelegram(chatId: string, text: string, replyMarkup: any): number {
  const token = getBotToken();
  if (!token) return 0;
  try {
    const payload = JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: "HTML",
      reply_markup: replyMarkup,
      disable_web_page_preview: true,
    });
    const result = execSync(
      `curl -s -X POST "https://api.telegram.org/bot${token}/sendMessage" -H "Content-Type: application/json" -d '${payload.replace(/'/g, "'\\''")}'`,
      { encoding: "utf-8", timeout: 10_000 }
    );
    const data = JSON.parse(result);
    return data.ok ? data.result.message_id : 0;
  } catch {
    return 0;
  }
}

function editTelegram(chatId: string, messageId: number, text: string, replyMarkup: any = null) {
  const token = getBotToken();
  if (!token) return;
  try {
    const payload: any = { chat_id: chatId, message_id: messageId, text, parse_mode: "HTML" };
    if (replyMarkup) payload.reply_markup = replyMarkup;
    const payloadStr = JSON.stringify(payload).replace(/'/g, "'\\''");
    execSync(
      `curl -s -X POST "https://api.telegram.org/bot${token}/editMessageText" -H "Content-Type: application/json" -d '${payloadStr}'`,
      { encoding: "utf-8", timeout: 10_000 }
    );
  } catch {}
}

/**
 * Convert ISO time to 12h AM/PM format (matches n8n to12hLabel)
 */
function to12hLabel(value: string): string {
  if (!value || typeof value !== "string") return String(value);
  const s = value.trim();

  // Pass through non-time options
  if (/cancel\s*booking/i.test(s)) return "Cancel booking";

  // ISO format: ...THH:mm
  let m = s.match(/T(\d{2}):(\d{2})/);
  if (!m) m = s.match(/^(\d{2}):(\d{2})(?::\d{2})?$/);

  if (m) {
    let h = parseInt(m[1], 10);
    const mm = m[2];
    const period = h >= 12 ? "PM" : "AM";
    h = h % 12;
    if (h === 0) h = 12;
    return `${h}:${mm} ${period}`;
  }

  // Already 12h format
  const m12 = s.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$/i);
  if (m12) {
    const h = parseInt(m12[1], 10);
    const mm = (m12[2] ?? "00").padStart(2, "0");
    return `${h}:${mm} ${m12[3].toUpperCase()}`;
  }

  return s;
}

/**
 * HTTP route handler for askFelix webhook.
 * Retell calls this mid-call to ask Felix which option to pick.
 */
export async function handleAskFelixWebhook(
  req: IncomingMessage,
  res: ServerResponse,
): Promise<boolean> {
  // Read body
  let body = "";
  for await (const chunk of req) {
    body += chunk;
  }

  let data: any;
  try {
    data = JSON.parse(body);
  } catch {
    res.writeHead(400);
    res.end(JSON.stringify({ error: "Invalid JSON" }));
    return true;
  }

  // Extract data (same as n8n "Extract VAPI Data")
  const args = data.args || data.body?.args || data;
  const call = data.call || data.body?.call || {};
  const callId = args.call_id || call.call_id || `call_${Date.now()}`;
  const chatId = args.chat_id || call.retell_llm_dynamic_variables?.telegram_chat_id || "";
  const userId = args.user_id || call.retell_llm_dynamic_variables?.telegram_user_id || "";
  const question = args.question || "Which option do you prefer?";
  const rawOptions: string[] = Array.isArray(args.options) ? args.options : [];
  const venueName = args.venue_name || call.retell_llm_dynamic_variables?.venue_name || "";

  // Convert options to 12h format
  const options = rawOptions.map(to12hLabel);

  if (!chatId) {
    res.writeHead(400);
    res.end(JSON.stringify({ error: "Missing chat_id" }));
    return true;
  }

  // Build Telegram buttons (matching n8n format: vp|call_id|index)
  const keyboard: any[][] = [];
  let row: any[] = [];
  for (let i = 0; i < options.length; i++) {
    const opt = options[i];
    if (/cancel/i.test(opt)) {
      // Cancel goes on its own row
      if (row.length) { keyboard.push(row); row = []; }
      keyboard.push([{ text: "\ud83d\udd04 Next Club", callback_data: `vp:${callId}|-1` }]);
    } else {
      row.push({ text: opt, callback_data: `vp:${callId}|${i}` });
      if (row.length >= 3) { keyboard.push(row); row = []; }
    }
  }
  if (row.length) keyboard.push(row);

  // Send Telegram message
  const text = `\ud83c\udfbe <b>Venue Update for ${venueName}:</b>\n${question}`;
  const msgId = sendTelegram(chatId, text, { inline_keyboard: keyboard });

  // Create promise that resolves when Felix clicks button
  const responsePromise = new Promise<string>((resolve) => {
    const timeout = setTimeout(() => {
      pendingResponses.delete(callId);
      // Edit message to show timeout
      if (msgId) {
        editTelegram(chatId, msgId, `\u23f3 <b>${venueName}:</b> Time expired - no response`, { inline_keyboard: [] });
      }
      resolve("Felix is unavailable currently. We will contact you when he makes a decision.");
    }, 8000); // 8 second timeout

    pendingResponses.set(callId, { resolve, timeout, options });
  });

  // Wait for Felix's response (max 8 seconds)
  const felixResponse = await responsePromise;

  // Edit Telegram message to show selection
  if (msgId) {
    const selectedText = felixResponse.includes("unavailable")
      ? `\u23f3 <b>${venueName}:</b> Timed out`
      : `\u2705 <b>${venueName}:</b> Selected ${felixResponse}`;
    editTelegram(chatId, msgId, selectedText, { inline_keyboard: [] });
  }

  // Respond to Retell
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ result: felixResponse }));
  return true;
}

/**
 * Handle Felix's button click (vp:callId|optionIndex)
 */
export async function handleVpCallback(
  payload: string,
  respond: any,
): Promise<{ handled: boolean }> {
  // payload = "callId|optionIndex" (vp: prefix already stripped)
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const callId = parts[0];
  const optionIndex = parseInt(parts[1], 10);

  const pending = pendingResponses.get(callId);
  if (!pending) {
    await respond.editMessage({ text: "\u23f3 Response expired.", buttons: [] });
    return { handled: true };
  }

  // Resolve the promise with Felix's choice
  clearTimeout(pending.timeout);

  let choice: string;
  if (optionIndex === -1) {
    choice = "Cancel booking";
  } else if (optionIndex >= 0 && optionIndex < pending.options.length) {
    choice = pending.options[optionIndex];
  } else {
    choice = "Cancel booking";
  }

  pending.resolve(choice);
  pendingResponses.delete(callId);

  return { handled: true };
}
