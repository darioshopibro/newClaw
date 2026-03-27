import { readFileSync, writeFileSync, mkdirSync, unlinkSync, existsSync } from "node:fs";
import { join } from "node:path";

const QUIZ_STATE_DIR = "/root/.openclaw/quiz_state";
const CONTACT_STATE_DIR = "/root/.openclaw/contact_state";

function ensureDir(dir: string) {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

function safeName(taskId: string): string {
  return taskId.replace(/[/\\]/g, "_");
}

export function loadQuizState(taskId: string): Record<string, any> | null {
  ensureDir(QUIZ_STATE_DIR);
  const path = join(QUIZ_STATE_DIR, `${safeName(taskId)}.json`);
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, "utf-8"));
}

export function saveQuizState(taskId: string, state: Record<string, any>) {
  ensureDir(QUIZ_STATE_DIR);
  const path = join(QUIZ_STATE_DIR, `${safeName(taskId)}.json`);
  writeFileSync(path, JSON.stringify(state, null, 2));
}

export function deleteQuizState(taskId: string) {
  const path = join(QUIZ_STATE_DIR, `${safeName(taskId)}.json`);
  if (existsSync(path)) unlinkSync(path);
}

export function loadContactState(taskId: string): Record<string, any> | null {
  ensureDir(CONTACT_STATE_DIR);
  const path = join(CONTACT_STATE_DIR, `${safeName(taskId)}.json`);
  if (!existsSync(path)) return null;
  return JSON.parse(readFileSync(path, "utf-8"));
}

export function saveContactState(taskId: string, state: Record<string, any>) {
  ensureDir(CONTACT_STATE_DIR);
  const path = join(CONTACT_STATE_DIR, `${safeName(taskId)}.json`);
  writeFileSync(path, JSON.stringify(state, null, 2));
}

export function deleteContactState(taskId: string) {
  const path = join(CONTACT_STATE_DIR, `${safeName(taskId)}.json`);
  if (existsSync(path)) unlinkSync(path);
}
