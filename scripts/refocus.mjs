import { readFileSync } from "node:fs";
import { join } from "node:path";
import {
  parseStdin,
  isDisabled,
  loadMetrics,
  saveMetrics,
  log,
} from "./lib.mjs";

const HOOK = "refocus";

// --- tuning knobs ---------------------------------------------------------
const MIN_REPLIES = 6;     // need at least this many recorded chat replies
const BASELINE_WINDOW = 3; // "fresh" baseline = first N replies of the session
const RECENT_WINDOW = 3;   // "now" = average of the last N replies
const DRIFT_RATIO = 1.6;   // recent must exceed baseline by this factor
const FLOOR_WORDS = 120;   // ...and clear this absolute floor
const COOLDOWN = 5;        // replies to stay quiet after a nudge
// --------------------------------------------------------------------------

const median = (arr) => {
  const s = [...arr].sort((a, b) => a - b);
  const n = s.length;
  return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
};

const avg = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;

const input = parseStdin(HOOK);
const session = input.session_id || "unknown";

if (isDisabled(HOOK)) {
  log({ hook: HOOK, session, action: "skip", reason: "disabled" });
  process.exit(0);
}

const m = loadMetrics(session, HOOK);
const counts = m.counts || [];

if (counts.length < MIN_REPLIES) {
  log({
    hook: HOOK,
    session,
    action: "skip",
    reason: "insufficient",
    have: counts.length,
    need: MIN_REPLIES,
  });
  process.exit(0);
}

const baseline = median(counts.slice(0, BASELINE_WINDOW));
const recent = avg(counts.slice(-RECENT_WINDOW));
const threshold = Math.max(baseline * DRIFT_RATIO, FLOOR_WORDS);
const sinceNudge = counts.length - (m.lastNudgeAt ?? -999);

const stats = {
  baseline,
  recent: Math.round(recent),
  threshold: Math.round(threshold),
};

if (sinceNudge < COOLDOWN) {
  log({
    hook: HOOK,
    session,
    action: "skip",
    reason: "cooldown",
    sinceNudge,
    cooldown: COOLDOWN,
    ...stats,
  });
  process.exit(0);
}

if (recent < threshold) {
  log({ hook: HOOK, session, action: "no-inject", ...stats });
  process.exit(0);
}

const reminderPath = join(
  process.env.CLAUDE_PLUGIN_ROOT || "",
  "prompt",
  "reminder.md",
);

let reminder;
try {
  reminder = readFileSync(reminderPath, "utf8");
} catch (e) {
  log({
    hook: HOOK,
    session,
    action: "error",
    stage: "read-reminder",
    error: e.message,
    code: e.code,
    path: reminderPath,
  });
  process.exit(0);
}

process.stdout.write(reminder);
m.lastNudgeAt = counts.length;
saveMetrics(session, m, HOOK);
log({ hook: HOOK, session, action: "inject", ...stats });
