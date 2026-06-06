import {
  parseStdin,
  countProseWords,
  loadMetrics,
  saveMetrics,
  log,
} from "./lib.mjs";

const HOOK = "measure";
const HISTORY_CAP = 50; // keep only the most recent N replies per session

const input = parseStdin(HOOK);
const session = input.session_id || "unknown";

if (input.stop_hook_active) {
  log({ hook: HOOK, session, action: "skip", reason: "stop_hook_active" });
  process.exit(0);
}

const words = countProseWords(input.last_assistant_message || "");
if (words === 0) {
  log({ hook: HOOK, session, action: "skip", reason: "no-prose" });
  process.exit(0);
}

const m = loadMetrics(session, HOOK);
m.counts.push(words);
if (m.counts.length > HISTORY_CAP) {
  m.counts = m.counts.slice(-HISTORY_CAP);
}
saveMetrics(session, m, HOOK);

log({
  hook: HOOK,
  session,
  action: "recorded",
  words,
  history: m.counts.length,
});
