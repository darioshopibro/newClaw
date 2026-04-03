import { execSync } from "node:child_process";

/**
 * askFelix button handler.
 *
 * Flow:
 * 1. Retell mid-call → calls n8n askFelix webhook (stays on n8n)
 * 2. n8n sends Telegram buttons with callback_data: vp:callId|optionIndex
 * 3. n8n saves wait_url + options to Supabase task_temp_data
 * 4. Felix clicks button → OpenClaw intercepts (this handler)
 * 5. We read wait_url from Supabase → POST felix_response → n8n resumes
 *
 * callback_data format: vp:callId|optionIndex
 * Supabase task_id format: vapi_callId
 */

interface Respond {
  reply: (params: { text: string; buttons?: any }) => Promise<void>;
  editMessage: (params: { text: string; buttons?: any }) => Promise<void>;
}

function to12hLabel(value: string): string {
  if (!value || typeof value !== "string") return String(value);
  const s = value.trim();
  if (/cancel\s*booking/i.test(s)) return "Cancel booking";

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

  const m12 = s.match(/^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$/i);
  if (m12) {
    const h = parseInt(m12[1], 10);
    const mm = (m12[2] ?? "00").padStart(2, "0");
    return `${h}:${mm} ${m12[3].toUpperCase()}`;
  }

  return s;
}

export async function handleVpCallback(
  payload: string,
  respond: Respond,
): Promise<{ handled: boolean }> {
  // payload = "callId|optionIndex" (vp: prefix already stripped by OpenClaw)
  const parts = payload.split("|");
  if (parts.length < 2) return { handled: false };

  const callId = parts[0];
  const optionIndex = parseInt(parts[1], 10);

  // Read session from Supabase: task_id = vapi_{callId}
  const supabaseTaskId = `vapi_${callId}`;

  try {
    const result = execSync(
      `python3 -c "
import json, os, sys
sys.path.insert(0, '/root/.openclaw/workspace/agents/padel/scripts/lib')
from supabase_client import SupabaseClient
client = SupabaseClient()
data = client.get_temp_data('${supabaseTaskId}')
print(json.dumps(data or {}))
"`,
      { encoding: "utf-8", timeout: 10_000 }
    );

    const session = JSON.parse(result.trim());

    if (!session || !session.data) {
      await respond.editMessage({ text: "\u23f3 Response expired.", buttons: [] });
      return { handled: true };
    }

    // Parse session data
    let sessionData = session.data;
    if (typeof sessionData === "string") {
      sessionData = JSON.parse(sessionData);
    }

    const waitUrl = sessionData.wait_url;
    const options: string[] = (sessionData.options || []).map(to12hLabel);

    if (!waitUrl) {
      await respond.editMessage({ text: "\u23f3 Session expired - no wait URL.", buttons: [] });
      return { handled: true };
    }

    // Map option index to actual choice
    let felixChoice: string;
    if (optionIndex === -1) {
      felixChoice = "Cancel booking";
    } else if (optionIndex >= 0 && optionIndex < options.length) {
      felixChoice = options[optionIndex];
    } else {
      felixChoice = "Cancel booking";
    }

    // POST response to n8n wait_url
    execSync(
      `python3 -c "
import requests
requests.post('${waitUrl}', json={'felix_response': '${felixChoice.replace(/'/g, "\\'")}'}, timeout=10)
"`,
      { encoding: "utf-8", timeout: 15_000 }
    );

    // Edit Telegram message to show selection
    const selectedText = felixChoice.includes("Cancel")
      ? `\ud83d\udd04 Next club requested`
      : `\u2705 Selected: ${felixChoice}`;

    await respond.editMessage({ text: selectedText, buttons: [] });

    return { handled: true };

  } catch (err: any) {
    await respond.editMessage({
      text: `\u26a0\ufe0f Failed to send response: ${err.message?.slice(0, 100)}`,
      buttons: [],
    });
    return { handled: true };
  }
}
